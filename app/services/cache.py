import json
import hashlib
import os
from typing import Any, Dict, List, Optional

import aioredis


class CacheService:
    """Сервис кэширования с Redis."""
    
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis: Optional[aioredis.Redis] = None
        self.default_ttl = 86400  # 24 часа
    
    async def connect(self):
        """Подключение к Redis."""
        if not self.redis:
            self.redis = await aioredis.from_url(self.redis_url, decode_responses=True)
    
    async def disconnect(self):
        """Отключение от Redis."""
        if self.redis:
            await self.redis.close()
    
    def _generate_key(self, prefix: str, *args) -> str:
        """Генерация ключа кэша."""
        key_data = "_".join(str(arg) for arg in args)
        key_hash = hashlib.md5(key_data.encode()).hexdigest()
        return f"{prefix}:{key_hash}"
    
    async def get(self, key: str) -> Optional[Any]:
        """Получить значение из кэша."""
        await self.connect()
        
        try:
            value = await self.redis.get(key)
            if value:
                return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            # Если не удалось распарсить, удаляем поврежденный ключ
            await self.redis.delete(key)
        
        return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Сохранить значение в кэш."""
        await self.connect()
        
        try:
            serialized_value = json.dumps(value, ensure_ascii=False)
            ttl = ttl or self.default_ttl
            await self.redis.setex(key, ttl, serialized_value)
            return True
        except (TypeError, ValueError):
            return False
    
    async def set_if_not_exists(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Сохранить значение в кэш только если ключ не существует (защита от race condition).
        Возвращает True если значение было установлено, False если ключ уже существовал.
        """
        await self.connect()
        
        try:
            serialized_value = json.dumps(value, ensure_ascii=False)
            ttl = ttl or self.default_ttl
            # Используем SETNX для атомарной проверки и установки
            result = await self.redis.set(key, serialized_value, ex=ttl, nx=True)
            return result is True
        except (TypeError, ValueError):
            return False
    
    async def delete(self, key: str) -> bool:
        """Удалить значение из кэша."""
        await self.connect()
        result = await self.redis.delete(key)
        return result > 0
    
    async def get_analysis_result(self, url: str, style: str, occasion: str = "") -> Optional[Dict[str, Any]]:
        """Получить кэшированный результат анализа сайта."""
        key = self._generate_key("analysis", url, style, occasion)
        return await self.get(key)
    
    async def set_analysis_result(
        self, 
        url: str, 
        style: str, 
        occasion: str, 
        result: Dict[str, Any],
        ttl: int = 86400  # 24 часа
    ) -> bool:
        """Сохранить результат анализа сайта в кэш."""
        key = self._generate_key("analysis", url, style, occasion)
        return await self.set(key, result, ttl)
    
    async def get_intermediate_steps(self, url: str) -> Optional[List[Dict[str, Any]]]:
        """Получить кэшированные промежуточные шаги анализа."""
        key = self._generate_key("steps", url)
        return await self.get(key)
    
    async def set_intermediate_steps(
        self, 
        url: str, 
        steps: List[Dict[str, Any]],
        ttl: int = 172800  # 48 часов
    ) -> bool:
        """Сохранить промежуточные шаги анализа в кэш."""
        key = self._generate_key("steps", url)
        return await self.set(key, steps, ttl)
    
    async def get_cleaned_text(self, url: str) -> Optional[str]:
        """Получить кэшированный очищенный текст сайта."""
        key = self._generate_key("text", url)
        return await self.get(key)
    
    async def set_cleaned_text(
        self, 
        url: str, 
        text: str,
        ttl: int = 86400,  # 24 часа
        only_if_not_exists: bool = False
    ) -> bool:
        """
        Сохранить очищенный текст сайта в кэш.
        Если only_if_not_exists=True, сохраняет только если ключ не существует (защита от race condition).
        """
        key = self._generate_key("text", url)
        if only_if_not_exists:
            return await self.set_if_not_exists(key, text, ttl)
        return await self.set(key, text, ttl)
    
    async def set_intermediate_steps(
        self, 
        url: str, 
        steps: List[Dict[str, Any]],
        ttl: int = 172800,  # 48 часов
        only_if_not_exists: bool = False
    ) -> bool:
        """
        Сохранить промежуточные шаги анализа в кэш.
        Если only_if_not_exists=True, сохраняет только если ключ не существует (защита от race condition).
        """
        key = self._generate_key("steps", url)
        if only_if_not_exists:
            return await self.set_if_not_exists(key, steps, ttl)
        return await self.set(key, steps, ttl)


# Глобальный экземпляр кэша
cache_service = CacheService()
