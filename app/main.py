from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.llm import router as llm_router
from app.routers.payment import router as payment_router
from app.routers.session import router as session_router
from app.routers.admin import router as admin_router
from app.models.database import init_db
from app.services.params_service import params_service
from app.services import rate_limit


def _parse_cors_origins() -> list:
    """
    Разрешённые origins берутся из env CORS_ALLOWED_ORIGINS (список через
    запятую). Wildcard "*" больше не используется: он разрешал запросы с
    любого сайта. Если env не задан, дефолт — локальные адреса для приёмки
    в браузере; в production необходимо указать боевой домен, иначе браузер
    с чужого origin получит отказ (fail closed).
    """
    raw = os.getenv("CORS_ALLOWED_ORIGINS", "").strip()
    if raw:
        return [o.strip() for o in raw.split(",") if o.strip()]
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
    app = FastAPI(title="LLM Backend", lifespan=lifespan)

    # Настройка CORS - должен быть первым middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_parse_cors_origins(),  # конкретные origins вместо "*"
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type"],
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
    app.include_router(admin_router, prefix="/admin", tags=["admin"])
    return app


app = create_app()




