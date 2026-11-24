"""
Роутер для обработки оплаты через ЮКассу.
"""
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.services.payment_service import payment_service
from app.services.session_service import session_service
from app.services.params_service import params_service
from app.services.lead_service import lead_service


router = APIRouter()


def _client_ip(request: Request) -> str:
    """IP клиента за реверс-прокси (nginx ставит X-Forwarded-For)."""
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else ""


class PaymentRequest(BaseModel):
    email: EmailStr
    # Согласия на обработку ПДн и с офертой. Обязательны для создания платежа:
    # без них оплата невозможна, а не только не отправляется с фронтенда —
    # иначе ограничение можно обойти прямым POST-запросом.
    consent_pd: bool
    consent_offer: bool
    source: Optional[str] = None
    # amount и duration_minutes не принимаются от клиента - берутся из Redis (админ-панель) или .env

    @field_validator("consent_pd", "consent_offer")
    @classmethod
    def _consent_required(cls, v: bool) -> bool:
        if not v:
            raise ValueError(
                "Требуется согласие на обработку персональных данных и с офертой"
            )
        return v


class PaymentResponse(BaseModel):
    payment_id: str
    confirmation_url: str
    status: str


@router.post("/create", response_model=PaymentResponse)
async def create_payment(
    request: Request,
    payload: PaymentRequest,
    db: Session = Depends(get_db)
) -> PaymentResponse:
    """
    БЛОК 06: Обновление параметров W, Price, Shop ID и Ykassa API из админ-панели (Redis).
    БЛОК 06: ОПЛАТА - создание платежа в ЮКассе с обновленными параметрами.

    Перед созданием платежа фиксируется лид со согласиями: ПДн обрабатываются
    только после того, как согласие получено, поэтому захват идёт первым.
    """
    if not payment_service:
        raise HTTPException(
            status_code=500,
            detail="Сервис оплаты не настроен. Проверьте ShopID и Ykassa_API в .env"
        )

    try:
        # БЛОК 06: ОПЛАТА - создание платежа в ЮКассе с параметрами из Redis
        # payment_service автоматически получает все параметры (W, Price, ShopID, Ykassa_API) из Redis при создании платежа
        payment_data = await payment_service.create_payment(
            email=payload.email,
            description=f"Оплата сеанса генерации публикаций для {payload.email}",
            duration_minutes=None,  # W будет получен из Redis в payment_service
        )

        payment_id = payment_data.get("id")
        confirmation_url = payment_data.get("confirmation", {}).get("confirmation_url", "")

        if not payment_id or not confirmation_url:
            raise HTTPException(
                status_code=500,
                detail="Не удалось создать платеж. ЮКасса вернула неполные данные."
            )

        # Лид фиксируется после успешного создания платежа в ЮKassa: если
        # платёж не создан, «лида, который не смог оплатить» мы не заводим.
        # Статус new; webhook или /status переведут его в paid.
        try:
            lead_service.capture(
                db,
                email=payload.email,
                consent_pd=payload.consent_pd,
                consent_offer=payload.consent_offer,
                ip=_client_ip(request),
                user_agent=request.headers.get("user-agent", ""),
                source=payload.source or "",
            )
        except Exception as e:
            # Ошибка записи лида не должна ломать оплату клиенту.
            print(f"[Payment] Не удалось зафиксировать лид: {e}")

        return PaymentResponse(
            payment_id=payment_id,
            confirmation_url=confirmation_url,
            status=payment_data.get("status", "pending")
        )

    except HTTPException:
        raise
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

        # Лид: оплата подтверждена сервером, а не телом уведомления.
        try:
            lead_service.mark_paid(db, email, payment_id=payment_id, amount=amount)
        except Exception as e:
            print(f"[Webhook] Не удалось обновить лид: {e}")

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

                # Лид переводится в paid тем же путём, что и в webhook:
                # /status — резервная цепочка на случай недоставки уведомления.
                try:
                    lead_service.mark_paid(db, email, payment_id=payment_id, amount=amount)
                except Exception as e:
                    print(f"[Payment status] Не удалось обновить лид: {e}")

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



