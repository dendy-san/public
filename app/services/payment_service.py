"""
Сервис для работы с оплатой через ЮКассу.
Параметры ShopID, Ykassa_API и Price берутся из Redis (через params_service).
"""
import os
import base64
import httpx
from typing import Dict, Any, Optional
from urllib.parse import urlencode


class YooKassaPaymentService:
    """Сервис для работы с платежами ЮКассы."""

    def __init__(self):
        # Базовый URL API ЮКассы
        self.base_url = "https://api.yookassa.ru/v3"
        # Параметры будут загружаться динамически из Redis
    
    async def _get_credentials(self):
        """Получить учетные данные из Redis или .env."""
        from app.services.params_service import params_service
        
        shop_id = await params_service.get_param("ShopID") or os.getenv("ShopID", "")
        api_key = await params_service.get_param("Ykassa_API") or os.getenv("Ykassa_API", "")
        
        if not shop_id or not api_key:
            raise ValueError("ShopID и Ykassa_API должны быть заданы в админ-панели или .env")
        
        return shop_id, api_key
    
    async def _get_price(self) -> int:
        """Получить цену из Redis или .env."""
        from app.services.params_service import params_service
        
        price_str = await params_service.get_param("Price") or os.getenv("Price", "1000")
        return int(price_str)
    
    def _create_auth_header(self, shop_id: str, api_key: str) -> str:
        """Создать заголовок авторизации."""
        credentials = f"{shop_id}:{api_key}"
        return base64.b64encode(credentials.encode()).decode()

    async def create_payment(
        self,
        email: str,
        description: str = "Оплата сеанса генерации публикаций",
        return_url: Optional[str] = None,
        duration_minutes: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Создание платежа в ЮКассе.
        Все параметры (Price, ShopID, Ykassa_API, W) берутся из Redis (через params_service), при отсутствии - из .env.
        
        Args:
            email: Email клиента
            description: Описание платежа
            return_url: URL для возврата после оплаты
            duration_minutes: Продолжительность сеанса в минутах (если None, берется W из Redis)
        
        Returns:
            Словарь с данными платежа, включая confirmation_url
        """
        # Получаем учетные данные и цену из Redis
        shop_id, api_key = await self._get_credentials()
        price = await self._get_price()
        auth_header = self._create_auth_header(shop_id, api_key)
        
        # Если duration_minutes не передан, получаем W из Redis
        if duration_minutes is None:
            from app.services.params_service import params_service
            w_value = await params_service.get_param("W")
            if w_value:
                duration_minutes = int(w_value)
            else:
                # Fallback на .env, если в Redis нет значения
                duration_minutes = int(os.getenv("W", os.getenv("SESSION_DURATION_MINUTES", "1440")))
        
        # Используем цену из Redis
        amount = float(price)
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
            "Authorization": f"Basic {auth_header}",
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
        shop_id, api_key = await self._get_credentials()
        auth_header = self._create_auth_header(shop_id, api_key)
        
        headers = {
            "Authorization": f"Basic {auth_header}",
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


# Глобальный экземпляр сервиса (без проверки, так как параметры загружаются динамически)
payment_service = YooKassaPaymentService()



