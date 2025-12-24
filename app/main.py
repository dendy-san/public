from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.llm import router as llm_router
from app.routers.payment import router as payment_router
from app.routers.session import router as session_router
from app.routers.admin import router as admin_router
from app.services.task_queue import start_task_processor
from app.models.database import init_db
from app.services.params_service import params_service


def create_app() -> FastAPI:
    app = FastAPI(title="LLM Backend")
    
    # Настройка CORS - должен быть первым middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Разрешаем все origins для тестирования
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
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


@app.on_event("startup")
async def startup_event():
    """Запуск фоновых процессов при старте приложения."""
    # Инициализация базы данных
    init_db()
    # Инициализация параметров W и Price из .env (если еще не установлены в Redis)
    await params_service.initialize_from_env()
    # Запуск обработчика задач
    await start_task_processor()



