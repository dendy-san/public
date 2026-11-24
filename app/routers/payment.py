"""
Роутер для обработки оплаты через ЮКассу.
"""
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.services.payment_service import payment_service
from app.services.session_service import session_service
from app.services.params_service import params_service


router = APIRouter()


class PaymentRequest(BaseModel):
    email: EmailStr
    # amount и duration_minutes не принимаются от клиента - берутся из Redis (админ-панель) или .env


class PaymentResponse(BaseModel):
    payment_id: str
    confirmation_url: str
    status: str


@router.post("/create", response_model=PaymentResponse)
async def create_payment(
    request: PaymentRequest,
    db: Session = Depends(get_db)
) -> PaymentResponse:
    """
    БЛОК 06: Обновление параметров W, Price, Shop ID и Ykassa API из админ-панели (Redis).
    БЛОК 06: ОПЛАТА - создание платежа в ЮКассе с обновленными параметрами.
    """
    if not payment_service:
        raise HTTPException(
            status_code=500,
            detail="Сервис оплаты не настроен. Проверьте ShopID и Ykassa_API в .env"
        )

    try:
        # БЛОК 06: Обновление параметров W, Price, Shop ID и Ykassa API значениями из админ-панели (Redis)
        # Параметры уже находятся в Redis (устанавливаются через админ-панель или инициализируются из .env при старте)
        # Явно загружаем параметры из Redis перед созданием платежа
        try:
            await params_service.get_all_params()  # Загружаем все параметры из Redis
        except Exception:
            pass  # Игнорируем ошибки, если Redis недоступен - будут использованы значения из .env
        
        # БЛОК 06: ОПЛАТА - создание платежа в ЮКассе с параметрами из Redis
        # payment_service автоматически получает все параметры (W, Price, ShopID, Ykassa_API) из Redis при создании платежа
        payment_data = await payment_service.create_payment(
            email=request.email,
            description=f"Оплата сеанса генерации публикаций для {request.email}",
            duration_minutes=None,  # W будет получен из Redis в payment_service
        )

        payment_id = payment_data.get("id")
        confirmation_url = payment_data.get("confirmation", {}).get("confirmation_url", "")

        if not payment_id or not confirmation_url:
            raise HTTPException(
                status_code=500,
                detail="Не удалось создать платеж. ЮКасса вернула неполные данные."
            )

        return PaymentResponse(
            payment_id=payment_id,
            confirmation_url=confirmation_url,
            status=payment_data.get("status", "pending")
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при создании платежа: {str(e)}"
        )


@router.post("/webhook")
async def payment_webhook(
    webhook_data: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """
    Webhook от ЮКассы о статусе платежа.

    Безопасность (Этап 3): содержимому уведомления НЕ доверяем — его может
    отправить любой, кто знает URL. Доверие только данным, полученным НАМИ
    из API ЮКассы по Basic-auth (эхо-верификация). Из тела webhook берётся
    лишь payment_id, дальше платёж перезапрашивается, и сеанс создаётся только
    если реальный статус == succeeded и сумма совпадает с актуальным Price.
    """
    if not payment_service:
        raise HTTPException(
            status_code=500,
            detail="Сервис оплаты не настроен"
        )

    try:
        # 1. Минимальная структурная проверка (не доверие содержимому).
        if not payment_service.verify_webhook(webhook_data):
            raise HTTPException(status_code=400, detail="Невалидный webhook")

        event = webhook_data.get("event")
        payment_object = webhook_data.get("object", {})
        payment_id = payment_object.get("id")

        # Обрабатываем только успешные; всё равно перезапросим платёж.
        if event != "payment.succeeded" or not payment_id:
            return {"status": "ok", "message": "Webhook обработан"}

        # 2. ЭХО-ВЕРИФИКАЦИЯ: запрашиваем реальный платёж из API ЮКассы.
        try:
            payment_data = await payment_service.get_payment_status(payment_id)
        except Exception:
            # Платёж не найден или API недоступен — сеанс НЕ создаём.
            raise HTTPException(status_code=400, detail="Платёж не подтверждён")

        # 3. Реальный статус берём из ответа API, а не из тела webhook.
        if payment_data.get("status") != "succeeded":
            return {"status": "ok", "message": "Платёж не оплачен"}

        # 4. Email, сумма и W — из данных API (metadata ставили сами при создании).
        email = payment_service.extract_email_from_payment(payment_data)
        if not email:
            raise HTTPException(status_code=400, detail="В платеже нет email")

        amount_object = payment_data.get("amount", {})
        amount = int(float(amount_object.get("value", 0))) if amount_object else None

        # 5. СВЕРКА СУММЫ с актуальным Price (защита от поддельного webhook на 1 ₽).
        if not await payment_service.check_amount(amount):
            raise HTTPException(
                status_code=400,
                detail="Сумма платежа не совпадает с актуальной ценой"
            )

        # 6. Длительность сеанса: из metadata, иначе актуальный W из Redis.
        duration_minutes_str = payment_data.get("metadata", {}).get("duration_minutes")
        duration_minutes = int(duration_minutes_str) if duration_minutes_str else None
        if duration_minutes is None:
            import os
            w_value = await params_service.get_param("W")
            duration_minutes = int(w_value) if w_value else int(
                os.getenv("W", os.getenv("SESSION_DURATION_MINUTES", "1440"))
            )

        session_service.create_session(
            db, email, payment_id=payment_id,
            amount=amount, duration_minutes=duration_minutes
        )
        return {"status": "ok", "message": "Сеанс создан"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при обработке webhook: {str(e)}"
        )


@router.get("/status/{payment_id}")
async def get_payment_status(
    payment_id: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Проверка статуса платежа и создание сеанса при успешной оплате.
    """
    if not payment_service:
        raise HTTPException(
            status_code=500,
            detail="Сервис оплаты не настроен"
        )

    try:
        payment_data = await payment_service.get_payment_status(payment_id)
        status = payment_data.get("status")

        # Если платеж успешен, создаем сеанс
        if status == "succeeded":
            email = payment_service.extract_email_from_payment(payment_data)
            # Получаем сумму оплаты из данных платежа (целочисленные рубли)
            amount_object = payment_data.get("amount", {})
            amount = int(float(amount_object.get("value", 0))) if amount_object else None
            # Получаем продолжительность сеанса (W) из метаданных платежа
            duration_minutes_str = payment_data.get("metadata", {}).get("duration_minutes")
            duration_minutes = int(duration_minutes_str) if duration_minutes_str else None
            
            # Если W не было в метаданных, используем значение из Redis (должно быть уже установлено при создании платежа)
            if duration_minutes is None:
                w_value = await params_service.get_param("W")
                import os
                if w_value:
                    duration_minutes = int(w_value)
                else:
                    duration_minutes = int(os.getenv("W", os.getenv("SESSION_DURATION_MINUTES", "1440")))
            
            if email:
                # БЛОК 07: ФОРМИРОВАНИЕ КЛИЕНТСКОЙ ЗАПИСИ в базе с параметрами W и Price из Redis
                session_service.create_session(db, email, payment_id=payment_id, amount=amount, duration_minutes=duration_minutes)

        return {
            "payment_id": payment_id,
            "status": status,
            "paid": status == "succeeded"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при проверке статуса: {str(e)}"
        )


@router.get("/price")
async def get_price() -> Dict[str, Any]:
    """
    Получение суммы оплаты и продолжительности сеанса (W) из Redis (через params_service), при отсутствии - из .env.
    """
    try:
        import os
        
        # Получаем цену
        price = await params_service.get_param("Price")
        if price:
            price_value = int(price)
        else:
            price_value = int(os.getenv("Price", "1000"))
        
        # Получаем продолжительность сеанса (W)
        w_value = await params_service.get_param("W")
        if w_value:
            duration_minutes = int(w_value)
        else:
            duration_minutes = int(os.getenv("W", os.getenv("SESSION_DURATION_MINUTES", "1440")))
        
        return {
            "price": price_value,
            "currency": "RUB",
            "duration_minutes": duration_minutes
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при получении параметров: {str(e)}"
        )



