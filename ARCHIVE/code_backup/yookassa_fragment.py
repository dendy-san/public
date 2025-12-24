"""
Архивный фрагмент кода, отвечающий за интеграцию с ЮКассой.
Содержит актуальные на 2025-11-15 версии ключевых частей
`app/services/payment_service.py` и `app/routers/payment.py`.
"""

import os
import base64
import httpx
from typing import Dict, Any, Optional
from urllib.parse import urlencode  # noqa: F401 (оставлено для полноты копии)

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.models.database import get_db  # type: ignore
from app.services.session_service import session_service  # type: ignore


# --- Фрагмент из app/services/payment_service.py ---


class YooKassaPaymentService:
    """Сервис для работы с платежами ЮКассы."""

    def __init__(self):
        self.shop_id = os.getenv("ShopID", "")
        self.api_key = os.getenv("Ykassa_API", "")
        price_env = os.getenv("Price", "1000")
        try:
            self.default_amount = float(price_env)
        except ValueError as exc:
            raise ValueError("Параметр Price в .env должен быть числом") from exc

        if not self.shop_id or not self.api_key:
            raise ValueError("ShopID и Ykassa_API должны быть заданы в .env")

        self.base_url = "https://api.yookassa.ru/v3"
        credentials = f"{self.shop_id}:{self.api_key}"
        self.auth_header = base64.b64encode(credentials.encode()).decode()

    async def create_payment(
        self,
        amount: float,
        email: str,
        description: str = "Оплата сеанса генерации публикаций",
        return_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not return_url:
            frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
            return_url = os.getenv("RETURN_URL", f"{frontend_url}/payment-return.html")

        payment_metadata: Dict[str, Any] = {"email": email}
        if metadata:
            payment_metadata.update({k: v for k, v in metadata.items() if v is not None})

        payment_data = {
            "amount": {"value": f"{amount:.2f}", "currency": "RUB"},
            "confirmation": {"type": "redirect", "return_url": return_url},
            "capture": True,
            "description": description,
            "metadata": payment_metadata,
        }

        headers = {
            "Authorization": f"Basic {self.auth_header}",
            "Content-Type": "application/json",
            "Idempotence-Key": f"{email}_{int(os.urandom(4).hex(), 16)}",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/payments",
                json=payment_data,
                headers=headers,
            )
            response.raise_for_status()
            return response.json()

    async def get_payment_status(self, payment_id: str) -> Dict[str, Any]:
        headers = {"Authorization": f"Basic {self.auth_header}"}

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/payments/{payment_id}",
                headers=headers,
            )
            response.raise_for_status()
            return response.json()

    def verify_webhook(self, webhook_data: Dict[str, Any]) -> bool:
        return (
            "event" in webhook_data
            and "object" in webhook_data
            and webhook_data.get("object", {}).get("metadata", {}).get("email")
        )

    def extract_email_from_payment(self, payment_data: Dict[str, Any]) -> Optional[str]:
        return payment_data.get("metadata", {}).get("email")

    def extract_metadata(self, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        metadata = payment_data.get("metadata") or {}
        if not isinstance(metadata, dict):
            return {}
        return metadata


# --- Фрагмент из app/routers/payment.py ---


router = APIRouter()


class PaymentRequest(BaseModel):
    email: EmailStr
    amount: Optional[float] = None


class PaymentResponse(BaseModel):
    payment_id: str
    confirmation_url: str
    status: str


@router.post("/create", response_model=PaymentResponse)
async def create_payment(
    request: PaymentRequest,
    duration: Optional[int] = Query(None, description="Длительность сеанса в минутах"),
    db: Session = Depends(get_db),
) -> PaymentResponse:
    if not payment_service:
        raise HTTPException(
            status_code=500,
            detail="Сервис оплаты не настроен. Проверьте ShopID и Ykassa_API в .env",
        )

    try:
        final_amount = (
            request.amount if request.amount is not None else payment_service.default_amount
        )
        price_to_store = int(final_amount)
        duration_to_store = (
            duration if duration is not None else session_service.default_duration_minutes
        )
        payment_data = await payment_service.create_payment(
            amount=final_amount,
            email=request.email,
            description=f"Оплата сеанса генерации публикаций для {request.email}",
            metadata={"price": price_to_store, "duration_minutes": duration_to_store},
        )

        payment_id = payment_data.get("id")
        confirmation_url = payment_data.get("confirmation", {}).get("confirmation_url", "")

        if not payment_id or not confirmation_url:
            raise HTTPException(
                status_code=500,
                detail="Не удалось создать платеж. ЮКасса вернула неполные данные.",
            )

        return PaymentResponse(
            payment_id=payment_id,
            confirmation_url=confirmation_url,
            status=payment_data.get("status", "pending"),
        )

    except Exception as e:  # pragma: no cover - архивная копия
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при создании платежа: {str(e)}",
        )


@router.get("/price")
async def get_payment_price() -> Dict[str, Any]:
    if not payment_service:
        raise HTTPException(status_code=500, detail="Сервис оплаты не настроен")
    return {"amount": payment_service.default_amount}


@router.post("/webhook")
async def payment_webhook(
    webhook_data: Dict[str, Any],
    db: Session = Depends(get_db),
):
    if not payment_service:
        raise HTTPException(status_code=500, detail="Сервис оплаты не настроен")

    try:
        if not payment_service.verify_webhook(webhook_data):
            raise HTTPException(status_code=400, detail="Невалидный webhook")

        event = webhook_data.get("event")
        payment_object = webhook_data.get("object", {})

        if event == "payment.succeeded":
            payment_id = payment_object.get("id")
            email = payment_service.extract_email_from_payment(payment_object)
            metadata = payment_service.extract_metadata(payment_object)
            price_value = metadata.get("price")
            duration_value = metadata.get("duration_minutes")
            try:
                price_int = int(float(price_value)) if price_value is not None else None
            except (TypeError, ValueError):
                price_int = None
            try:
                duration_int = int(duration_value) if duration_value is not None else None
            except (TypeError, ValueError):
                duration_int = None

            if email and payment_id:
                session_service.create_session(
                    db,
                    email,
                    payment_id=payment_id,
                    price=price_int,
                    duration_minutes=duration_int,
                )
                return {"status": "ok", "message": "Сеанс создан"}

        return {"status": "ok", "message": "Webhook обработан"}

    except Exception as e:  # pragma: no cover - архивная копия
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при обработке webhook: {str(e)}",
        )


@router.get("/status/{payment_id}")
async def get_payment_status(
    payment_id: str,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    if not payment_service:
        raise HTTPException(status_code=500, detail="Сервис оплаты не настроен")

    try:
        payment_data = await payment_service.get_payment_status(payment_id)
        status = payment_data.get("status")
        metadata = payment_service.extract_metadata(payment_data)
        price_value = metadata.get("price")
        duration_value = metadata.get("duration_minutes")
        try:
            price_int = int(float(price_value)) if price_value is not None else None
        except (TypeError, ValueError):
            price_int = None
        try:
            duration_int = int(duration_value) if duration_value is not None else None
        except (TypeError, ValueError):
            duration_int = None

        if status == "succeeded":
            email = payment_service.extract_email_from_payment(payment_data)
            if email:
                session_service.create_session(
                    db,
                    email,
                    payment_id=payment_id,
                    price=price_int,
                    duration_minutes=duration_int,
                )

        return {
            "payment_id": payment_id,
            "status": status,
            "paid": status == "succeeded",
        }

    except Exception as e:  # pragma: no cover - архивная копия
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при проверке статуса: {str(e)}",
        )


# Глобальный экземпляр для полноты архивной копии
try:
    payment_service = YooKassaPaymentService()
except ValueError:
    payment_service = None


