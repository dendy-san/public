"""
Модели базы данных для монетизированной версии.
Используется SQLite для хранения клиентских записей.
"""
import os
from datetime import datetime
from typing import Optional

from sqlalchemy import create_engine, Column, String, Integer, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# База данных SQLite
DB_PATH = os.getenv("DB_PATH", "sessions.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class ClientSession(Base):
    """Модель клиентской записи в базе данных."""
    __tablename__ = "client_sessions"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    url = Column(String, default="")  # Сайт
    info = Column(String, default="")  # Инфоповод
    # Стили: 1 = доступен, 0 = использован
    st1 = Column(Integer, default=1)  # убедительно-позитивный
    st2 = Column(Integer, default=1)  # ироничный
    st3 = Column(Integer, default=1)  # разговорный
    st4 = Column(Integer, default=1)  # провокационный
    st5 = Column(Integer, default=1)  # информационный
    st6 = Column(Integer, default=1)  # официально-деловой
    st7 = Column(Integer, default=1)  # сторителлинг
    st8 = Column(Integer, default=1)  # продающий
    st9 = Column(Integer, default=1)  # медицинский
    dt = Column(DateTime, nullable=False)  # Время оплаты (Tb)
    payment_id = Column(String, nullable=True)  # ID платежа в ЮКассе
    amount = Column(Integer, nullable=True)  # Сумма оплаты (Price) - целочисленные рубли без копеек
    duration_minutes = Column(Integer, nullable=True)  # Продолжительность сеанса (W) - в минутах
    is_active = Column(Boolean, default=True)  # Активна ли сессия

    def to_dict(self) -> dict:
        """Преобразование в словарь."""
        return {
            "id": self.id,
            "email": self.email,
            "url": self.url,
            "info": self.info,
            "st1": self.st1,
            "st2": self.st2,
            "st3": self.st3,
            "st4": self.st4,
            "st5": self.st5,
            "st6": self.st6,
            "st7": self.st7,
            "st8": self.st8,
            "st9": self.st9,
            "dt": self.dt.isoformat() if self.dt else None,
            "payment_id": self.payment_id,
            "amount": self.amount,
            "duration_minutes": self.duration_minutes,
            "is_active": self.is_active,
        }


def init_db():
    """Инициализация базы данных - создание таблиц."""
    try:
        Base.metadata.create_all(bind=engine, checkfirst=True)
    except Exception as e:
        # Если таблицы уже существуют, это нормально
        # Логируем только реальные ошибки
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"При инициализации БД произошла ошибка (возможно, таблицы уже существуют): {e}")


def get_db() -> Session:
    """Получение сессии базы данных."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



