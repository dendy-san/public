from contextlib import asynccontextmanager
import os

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.llm import router as llm_router
from app.routers.payment import router as payment_router
from app.routers.session import router as session_router
from app.routers.admin import router as admin_router
from app.models.database import init_db
from app.services.params_service import params_service
from app.services.admin_auth import require_admin_token
from app.services import rate_limit


def _parse_cors_origins(is_prod: bool) -> list:
    """
    Разрешённые origins берутся из env CORS_ALLOWED_ORIGINS (список через
    запятую). Wildcard "*" больше не используется: он разрешал запросы с
    любого сайта.

    Фронт обращается к API по относительным путям через nginx своего же
    контейнера, то есть same-origin, и CORS здесь вообще не участвует.
    Поэтому в production при незаполненной переменной список остаётся
    пустым (fail closed), а локальные адреса отдаются только в dev — иначе
    боевой API разрешал бы запросы со страниц, открытых на localhost.
    """
    raw = os.getenv("CORS_ALLOWED_ORIGINS", "").strip()
    origins = [o.strip() for o in raw.split(",") if o.strip()]
    if origins:
        return origins
    if is_prod:
        return []
    return [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:5173",
    ]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Инициализация при старте и закрытие соединений при остановке."""
    # Инициализация базы данных
    init_db()
    # Инициализация параметров W и Price из .env (если еще не установлены в Redis)
    await params_service.initialize_from_env()
    yield
    # Закрытие подключения к Redis при остановке приложения
    await params_service.close()
    await rate_limit.close()


def create_app() -> FastAPI:
    is_prod = os.getenv("ENVIRONMENT", "dev").strip() == "prod"
    app = FastAPI(
        title="LLM Backend",
        lifespan=lifespan,
        # Swagger и openapi.json раскрывают полную структуру API (включая
        # админ-маршруты) любому, кто найдёт адрес. В production они выключены;
        # локально остаются доступными для отладки.
        docs_url=None if is_prod else "/docs",
        redoc_url=None,
        openapi_url=None if is_prod else "/openapi.json",
    )

    # Настройка CORS - должен быть первым middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_parse_cors_origins(is_prod),  # конкретные origins вместо "*"
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        # Authorization нужен админке, если она обращается к API с другого
        # origin (при same-origin через nginx CORS не участвует вовсе).
        # Без него предполётной запрос браузера на /admin/* отклоняется.
        allow_headers=["Content-Type", "Authorization"],
    )

    # Простой тестовый эндпоинт
    @app.get("/")
    async def root():
        return {"message": "Backend is running"}

    @app.get("/health")
    async def health():
        return {"status": "healthy"}

    app.include_router(llm_router, prefix="/llm", tags=["llm"])
    app.include_router(payment_router, prefix="/payment", tags=["payment"])
    app.include_router(session_router, prefix="/session", tags=["session"])
    # Весь админ-блок требует Bearer-токена: он отдаёт персональные данные
    # (email, IP, user-agent клиентов в /admin/leads и /admin/leads/export)
    # и позволяет менять реквизиты платежей (/admin/params/yookassa), поэтому
    # доступ без проверки токена недопустим.
    app.include_router(
        admin_router,
        prefix="/admin",
        tags=["admin"],
        dependencies=[Depends(require_admin_token)],
    )
    return app


app = create_app()




