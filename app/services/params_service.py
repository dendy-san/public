"""
Сервис для управления параметрами W и Price из .env и Redis.
"""
import os
import json
from datetime import datetime
from typing import Optional, Dict, List, Any
import aioredis


class ParamsService:
    """Сервис управления параметрами W (длительность сеанса) и Price (цена)."""
    
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis: Optional[aioredis.Redis] = None
    
    async def _get_redis(self):
        """Получить подключение к Redis."""
        if not self.redis:
            self.redis = await aioredis.from_url(self.redis_url, decode_responses=True)
        return self.redis
    
    async def initialize_from_env(self):
        """
        Инициализация параметров W, Price, ShopID и Ykassa_API из .env в Redis (если еще не установлены).
        """
        try:
            redis = await self._get_redis()
            
            # W - продолжительность сеанса в минутах (по умолчанию 1440 = 24 часа)
            w_value = os.getenv("W", os.getenv("SESSION_DURATION_MINUTES", "1440"))
            existing_w = await redis.get("W")
            if not existing_w:
                await redis.set("W", w_value)
                await self._add_to_history("W", w_value, "initialized_from_env")
            
            # Price - цена в рублях (по умолчанию 1000)
            price_value = os.getenv("Price", "1000")
            existing_price = await redis.get("Price")
            if not existing_price:
                await redis.set("Price", price_value)
                await self._add_to_history("Price", price_value, "initialized_from_env")
            
            # ShopID - ID магазина ЮКассы
            shop_id_value = os.getenv("ShopID", "")
            existing_shop_id = await redis.get("ShopID")
            if not existing_shop_id and shop_id_value:
                await redis.set("ShopID", shop_id_value)
            
            # Ykassa_API - API ключ ЮКассы
            ykassa_api_value = os.getenv("Ykassa_API", "")
            existing_ykassa_api = await redis.get("Ykassa_API")
            if not existing_ykassa_api and ykassa_api_value:
                await redis.set("Ykassa_API", ykassa_api_value)
            
            # Если оба параметра были инициализированы, добавляем в совместную историю
            if (not existing_shop_id and shop_id_value) or (not existing_ykassa_api and ykassa_api_value):
                await self._add_yookassa_history(shop_id_value or existing_shop_id, ykassa_api_value or existing_ykassa_api, "initialized_from_env")
        except Exception as e:
            # Если Redis недоступен, просто логируем ошибку, но не падаем
            print(f"[ParamsService] Warning: Could not initialize params in Redis: {e}")
    
    async def _add_to_history(self, param_name: str, value: str, source: str = "manual"):
        """Добавить запись в историю изменений параметра."""
        try:
            redis = await self._get_redis()
            history_key = f"params:history:{param_name}"
            entry = {
                "value": value,
                "timestamp": datetime.now().isoformat(),
                "source": source
            }
            # Используем список для хранения истории (добавляем в начало)
            await redis.lpush(history_key, json.dumps(entry))
            # Ограничиваем историю последними 100 записями
            await redis.ltrim(history_key, 0, 99)
        except Exception as e:
            print(f"[ParamsService] Warning: Could not add to history: {e}")
    
    async def _add_yookassa_history(self, shop_id: str, api_key: str, source: str = "manual"):
        """Добавить запись в историю изменений параметров ЮКассы (ShopID и Ykassa_API вместе)."""
        try:
            redis = await self._get_redis()
            history_key = "params:history:yookassa"
            entry = {
                "shop_id": shop_id,
                "api_key": api_key,
                "timestamp": datetime.now().isoformat(),
                "source": source
            }
            await redis.lpush(history_key, json.dumps(entry))
            await redis.ltrim(history_key, 0, 99)
        except Exception as e:
            print(f"[ParamsService] Warning: Could not add YooKassa history: {e}")
    
    async def get_param(self, param_name: str) -> Optional[str]:
        """Получить текущее значение параметра."""
        try:
            redis = await self._get_redis()
            return await redis.get(param_name)
        except Exception as e:
            print(f"[ParamsService] Error getting param {param_name}: {e}")
            return None
    
    async def set_param(self, param_name: str, value: str, source: str = "manual") -> bool:
        """Установить значение параметра и добавить в историю."""
        try:
            redis = await self._get_redis()
            await redis.set(param_name, value)
            await self._add_to_history(param_name, value, source)
            return True
        except Exception as e:
            print(f"[ParamsService] Error setting param {param_name}: {e}")
            return False
    
    async def set_yookassa_params(self, shop_id: str, api_key: str, source: str = "manual") -> bool:
        """Установить оба параметра ЮКассы одновременно и добавить в совместную историю."""
        try:
            redis = await self._get_redis()
            await redis.set("ShopID", shop_id)
            await redis.set("Ykassa_API", api_key)
            await self._add_yookassa_history(shop_id, api_key, source)
            return True
        except Exception as e:
            print(f"[ParamsService] Error setting YooKassa params: {e}")
            return False
    
    async def get_history(self, param_name: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Получить историю изменений параметра."""
        try:
            redis = await self._get_redis()
            history_key = f"params:history:{param_name}"
            # Получаем последние записи
            entries = await redis.lrange(history_key, 0, limit - 1)
            result = []
            for entry_json in entries:
                try:
                    entry = json.loads(entry_json)
                    result.append(entry)
                except json.JSONDecodeError:
                    continue
            return result
        except Exception as e:
            print(f"[ParamsService] Error getting history for {param_name}: {e}")
            return []
    
    async def get_all_params(self) -> Dict[str, str]:
        """Получить все текущие параметры."""
        try:
            redis = await self._get_redis()
            w = await redis.get("W") or os.getenv("W", "1440")
            price = await redis.get("Price") or os.getenv("Price", "1000")
            shop_id = await redis.get("ShopID") or os.getenv("ShopID", "")
            ykassa_api = await redis.get("Ykassa_API") or os.getenv("Ykassa_API", "")
            return {
                "W": w,
                "Price": price,
                "ShopID": shop_id,
                "Ykassa_API": ykassa_api
            }
        except Exception as e:
            print(f"[ParamsService] Error getting all params: {e}")
            return {
                "W": os.getenv("W", "1440"),
                "Price": os.getenv("Price", "1000"),
                "ShopID": os.getenv("ShopID", ""),
                "Ykassa_API": os.getenv("Ykassa_API", "")
            }
    
    async def get_yookassa_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Получить историю изменений параметров ЮКассы."""
        try:
            redis = await self._get_redis()
            history_key = "params:history:yookassa"
            entries = await redis.lrange(history_key, 0, limit - 1)
            result = []
            for entry_json in entries:
                try:
                    entry = json.loads(entry_json)
                    result.append(entry)
                except json.JSONDecodeError:
                    continue
            return result
        except Exception as e:
            print(f"[ParamsService] Error getting YooKassa history: {e}")
            return []


# Создаем экземпляр сервиса
params_service = ParamsService()
