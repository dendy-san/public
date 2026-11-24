"""
Простой rate limiter на Redis (фиксированное окно).

Защищает ресурсоёмкие эндпоинты (генерация через LLM) от перебора и DoS.
Считаем по ключу "кем" (email+ip), окно фиксированное: INCR + EXPIRE.
Если Redis недоступен — запрос пропускаем (fail open), чтобы не ломать
генерацию у реальных клиентов: это защита от abuse, а не контроль доступа.
"""
import os

import redis.asyncio as redis


_redis_client = None


async def _get_redis():
    global _redis_client
    if _redis_client is None:
        url = os.getenv("REDIS_URL", "redis://localhost:6379")
        _redis_client = await redis.from_url(url, decode_responses=True)
    return _redis_client


async def close():
    """Закрыть соединение с Redis (вызывается при остановке приложения)."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None


async def is_limited(
    bucket: str,
    identity: str,
    limit: int,
    window_seconds: int,
) -> bool:
    """
    Возвращает True, если для identity в окне window_seconds превышен limit
    обращений к bucket. False — запрос разрешён.
    """
    try:
        r = await _get_redis()
        key = f"ratelimit:{bucket}:{identity}"
        count = await r.incr(key)
        if count == 1:
            # Первый запрос в окне — ставим TTL на весь интервал.
            await r.expire(key, window_seconds)
        return count > limit
    except Exception:
        # Redis недоступен — не блокируем легальных клиентов.
        return False
