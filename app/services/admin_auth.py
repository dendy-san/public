"""
Аутентификация админ-роутеров через HTTP Bearer-токен.

Токен берётся из переменной окружения ADMIN_TOKEN (должна быть задана в .env).
На брандмауэре VPS порт backend не публикуется, поэтому прямой доступ к API
возможен только из внутренней сети, однако admin-данные (ПДн, ключи ЮKassa)
требуют защиты на уровне приложения в соответствии с ФЗ-152.

Режимы:
  ENVIRONMENT=prod  →  ADMIN_TOKEN обязателен, без токена 503 (fail closed).
  ENVIRONMENT=dev   →  без токена разрешаем (удобнее для локальной разработки).
"""

import os
import secrets

from fastapi import Header, HTTPException, status


def require_admin_token(authorization: str = Header(default=None)) -> str:
    """
    Проверяет заголовок Authorization: Bearer <token>.

    Возвращает сам токен (для логирования/аудита).
    Если ADMIN_TOKEN не задан и ENVIRONMENT=prod — возвращает 503.
    Если ENVIRONMENT=dev и токен не передан — разрешает доступ.
    """
    expected = os.getenv("ADMIN_TOKEN", "").strip()
    env = os.getenv("ENVIRONMENT", "dev").strip()

    if not expected:
        if env == "prod":
            # Fail closed в продакшене: токен должен быть задан.
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="ADMIN_TOKEN not configured",
            )
        # Dev: токен не задан — разрешаем (для удобства локальной разработки).
        return ""

    # Заголовок должен быть "Bearer <token>"
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )

    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0] != "Bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization scheme (use 'Bearer <token>')",
        )

    provided_token = parts[1].strip()
    if not secrets.compare_digest(provided_token, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    return provided_token
