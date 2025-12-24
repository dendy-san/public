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


router = APIRouter()


class PaymentRequest(BaseModel):
    email: EmailStr
    # amount и duration_minutes не принимаются от клиента - берутся из .env


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
    Создание платежа для клиента.
    """
    if not payment_service:
        raise HTTPException(
            status_code=500,
            detail="Сервис оплаты не настроен. Проверьте ShopID и Ykassa_API в .env"
        )

    try:
        # W и Price берутся из .env, не от клиента
        import os
        duration_minutes = int(os.getenv("W", os.getenv("SESSION_DURATION_MINUTES", "1440")))
        
        # Создаем платеж в ЮКассе с фиксированной суммой из .env
        payment_data = await payment_service.create_payment(
            email=request.email,
            description=f"Оплата сеанса генерации публикаций для {request.email}",
            duration_minutes=duration_minutes,
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
    Webhook для обработки уведомлений от ЮКассы о статусе платежа.
    """
    if not payment_service:
        raise HTTPException(
            status_code=500,
            detail="Сервис оплаты не настроен"
        )

    try:
        # Проверяем webhook
        if not payment_service.verify_webhook(webhook_data):
            raise HTTPException(status_code=400, detail="Невалидный webhook")

        event = webhook_data.get("event")
        payment_object = webhook_data.get("object", {})

        # Обрабатываем только успешные платежи
        if event == "payment.succeeded":
            payment_id = payment_object.get("id")
            email = payment_service.extract_email_from_payment(payment_object)
            # Получаем сумму оплаты из объекта платежа (целочисленные рубли)
            amount_object = payment_object.get("amount", {})
            amount = int(float(amount_object.get("value", 0))) if amount_object else None
            # Получаем продолжительность сеанса (W) из метаданных платежа
            duration_minutes_str = payment_object.get("metadata", {}).get("duration_minutes")
            duration_minutes = int(duration_minutes_str) if duration_minutes_str else None

            if email and payment_id:
                # Создаем или обновляем сеанс клиента
                session_service.create_session(db, email, payment_id=payment_id, amount=amount, duration_minutes=duration_minutes)
                return {"status": "ok", "message": "Сеанс создан"}

        return {"status": "ok", "message": "Webhook обработан"}

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
            if email:
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
    Получение фиксированной суммы оплаты из .env (Price).
    """
    if not payment_service:
        raise HTTPException(
            status_code=500,
            detail="Сервис оплаты не настроен"
        )
    return {
        "price": payment_service.price,
        "currency": "RUB"
    }



