"""
Сервис для работы с оплатой через ЮКассу.
"""
import os
import base64
import httpx
from typing import Dict, Any, Optional
from urllib.parse import urlencode


class YooKassaPaymentService:
    """Сервис для работы с платежами ЮКассы."""

    def __init__(self):
        self.shop_id = os.getenv("ShopID", "")
        self.api_key = os.getenv("Ykassa_API", "")
        # Price из .env (целочисленные рубли)
        self.price = int(os.getenv("Price", "1000"))
        
        if not self.shop_id or not self.api_key:
            raise ValueError("ShopID и Ykassa_API должны быть заданы в .env")
        
        # Базовый URL API ЮКассы
        self.base_url = "https://api.yookassa.ru/v3"
        
        # Создаем заголовок авторизации
        credentials = f"{self.shop_id}:{self.api_key}"
        self.auth_header = base64.b64encode(credentials.encode()).decode()

    async def create_payment(
        self,
        email: str,
        description: str = "Оплата сеанса генерации публикаций",
        return_url: Optional[str] = None,
        duration_minutes: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Создание платежа в ЮКассе.
        Сумма берется из .env (Price) и не может быть изменена.
        
        Args:
            email: Email клиента
            description: Описание платежа
            return_url: URL для возврата после оплаты
            duration_minutes: Продолжительность сеанса в минутах (W из .env)
        
        Returns:
            Словарь с данными платежа, включая confirmation_url
        """
        # Используем фиксированную сумму из .env
        amount = float(self.price)
        if not return_url:
            # По умолчанию используем текущий домен с параметром успешной оплаты
            frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
            return_url = f"{frontend_url}?payment_success=true"

        payment_data = {
            "amount": {
                "value": f"{amount:.2f}",
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": return_url
            },
            "capture": True,
            "description": description,
            "metadata": {
                "email": email,
                **({"duration_minutes": str(duration_minutes)} if duration_minutes is not None else {})
            }
        }

        headers = {
            "Authorization": f"Basic {self.auth_header}",
            "Content-Type": "application/json",
            "Idempotence-Key": f"{email}_{int(os.urandom(4).hex(), 16)}"
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/payments",
                json=payment_data,
                headers=headers
            )
            response.raise_for_status()
            return response.json()

    async def get_payment_status(self, payment_id: str) -> Dict[str, Any]:
        """
        Получение статуса платежа.
        
        Args:
            payment_id: ID платежа в ЮКассе
        
        Returns:
            Словарь с данными платежа
        """
        headers = {
            "Authorization": f"Basic {self.auth_header}",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/payments/{payment_id}",
                headers=headers
            )
            response.raise_for_status()
            return response.json()

    def verify_webhook(self, webhook_data: Dict[str, Any]) -> bool:
        """
        Проверка webhook от ЮКассы (базовая проверка).
        В production нужно добавить проверку подписи.
        """
        # Базовая проверка структуры
        return (
            "event" in webhook_data and
            "object" in webhook_data and
            webhook_data.get("object", {}).get("metadata", {}).get("email")
        )

    def extract_email_from_payment(self, payment_data: Dict[str, Any]) -> Optional[str]:
        """Извлечение email из данных платежа."""
        return payment_data.get("metadata", {}).get("email")


# Глобальный экземпляр сервиса
try:
    payment_service = YooKassaPaymentService()
except ValueError:
    # Если нет настроек, создаем заглушку
    payment_service = None



