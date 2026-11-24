"""
Модели базы данных для монетизированной версии.
Используется SQLite для хранения клиентских записей.
"""
import os
from datetime import datetime
from typing import Optional

from sqlalchemy import create_engine, Column, String, Integer, DateTime, Boolean, Float
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


# Сроки хранения ПДн (ФЗ-152): по истечении запись удаляется автоматически.
# Оплаченным срок длиннее — данные нужны для налоговых проверок и возвратов.
RETENTION_PAID_DAYS = 365
RETENTION_NEW_DAYS = 30


class Lead(Base):
    """
    Лид: любой, кто оставил email, а не только оплативший.

    До появления этой таблицы запись о человеке создавалась исключительно
    по факту оплаты, поэтому воронка «email -> оплата» была не видна.
    Email уникален: повторная оплата обновляет существующий лид и увеличивает
    счётчик pays, а не заводит дубликат.

    Согласия (consent_*) — юридически значимая часть. Они фиксируются вместе
    с версией политики, IP и временем: через год нужно доказать, на какую
    именно редакцию человек согласился, а не просто «галочка была».
    """
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)

    # new — email оставлен, оплаты нет; paid — оплачено; expired — сеанс истёк
    status = Column(String, default="new", index=True)

    created_at = Column(DateTime, default=datetime.now, index=True)  # точка входа в воронку
    paid_at = Column(DateTime, nullable=True)
    payment_id = Column(String, nullable=True)   # последний платёж
    amount = Column(Integer, nullable=True)      # последняя сумма, рубли
    pays = Column(Integer, default=0)            # сколько раз платил

    source = Column(String, default="")          # utm-метка лендинга

    # Согласия: pd и offer обязательны для оплаты, marketing не собирается
    consent_pd = Column(Boolean, default=False)
    consent_offer = Column(Boolean, default=False)
    consent_version = Column(String, default="")
    consent_at = Column(DateTime, nullable=True)
    consent_ip = Column(String, default="")
    consent_user_agent = Column(String, default="")

    delete_after = Column(DateTime, nullable=True, index=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "email": self.email,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "paid_at": self.paid_at.isoformat() if self.paid_at else None,
            "payment_id": self.payment_id,
            "amount": self.amount,
            "pays": self.pays,
            "source": self.source,
            "consent_pd": self.consent_pd,
            "consent_offer": self.consent_offer,
            "consent_version": self.consent_version,
            "consent_at": self.consent_at.isoformat() if self.consent_at else None,
            "consent_ip": self.consent_ip,
            "consent_user_agent": self.consent_user_agent,
            "delete_after": self.delete_after.isoformat() if self.delete_after else None,
        }


def init_db():
    """Инициализация базы данных - создание таблиц."""
    try:
        Base.metadata.create_all(bind=engine, checkfirst=True)
        backfill_leads_from_sessions()
    except Exception as e:
        # Если таблицы уже существуют, это нормально
        # Логируем только реальные ошибки
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"При инициализации БД произошла ошибка (возможно, таблицы уже существуют): {e}")


def backfill_leads_from_sessions():
    """
    Перенос существующих оплаченных сеансов в таблицу лидов.

    Нужно только один раз: до появления лидов запись о клиенте создавалась
    исключительно по факту оплаты, и эти люди иначе пропали бы из воронки.
    Идемпотентно — лид с тем же email не создаётся повторно.
    """
    from datetime import timedelta

    try:
        db = SessionLocal()
        try:
            existing_emails = {e[0] for e in db.query(Lead.email).all()}
            sessions = db.query(ClientSession).all()
            added = 0
            for s in sessions:
                if s.email in existing_emails:
                    continue
                paid_at = s.dt or datetime.now()
                db.add(Lead(
                    email=s.email,
                    status="paid",
                    created_at=paid_at,
                    paid_at=paid_at,
                    payment_id=s.payment_id,
                    amount=s.amount,
                    pays=1,
                    # Согласий в старых записях не собиралось — ставим False,
                    # чтобы не выдать отсутствующее согласие за полученное.
                    consent_pd=False,
                    consent_offer=False,
                    delete_after=paid_at + timedelta(days=RETENTION_PAID_DAYS),
                ))
                added += 1
            if added:
                db.commit()
                print(f"[DB] Перенесено в лиды существующих сеансов: {added}")
        finally:
            db.close()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"[DB] Backfill leads failed: {e}")


def get_db() -> Session:
    """Получение сессии базы данных."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



