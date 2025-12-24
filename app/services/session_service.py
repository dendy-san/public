"""
Сервис для работы с клиентскими сеансами.
Управляет проверкой времени, созданием и обновлением записей.
"""
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from sqlalchemy.orm import Session

from app.models.database import ClientSession, get_db


class SessionService:
    """Сервис управления клиентскими сеансами."""

    def __init__(self):
        # W из .env - продолжительность сеанса в минутах (по умолчанию 24 часа = 1440 минут)
        self.default_duration_minutes = int(os.getenv("W", os.getenv("SESSION_DURATION_MINUTES", "1440")))

    def check_session_time(self, session: ClientSession) -> bool:
        """
        Проверка времени сеанса (блок 22 блок-схемы).
        Tt - Tb < W, где:
        Tt - текущее время
        Tb - время оплаты (dt)
        W - продолжительность сеанса в минутах (duration_minutes)
        """
        if not session or not session.dt:
            return False

        # Используем W из базы данных, если задано, иначе значение по умолчанию
        W = session.duration_minutes if session.duration_minutes is not None else self.default_duration_minutes

        current_time = datetime.now()
        payment_time = session.dt
        time_diff = current_time - payment_time

        # Проверяем, не истекло ли время (W в минутах)
        return time_diff < timedelta(minutes=W)

    def get_available_styles(self, session: ClientSession) -> Dict[str, int]:
        """Получить доступные стили (где значение = 1)."""
        return {
            "убедительно-позитивном": session.st1,
            "ироничном": session.st2,
            "разговорном": session.st3,
            "провокационном": session.st4,
            "информационном": session.st5,
            "официально-деловом": session.st6,
            "сторителлинга": session.st7,
            "продающем": session.st8,
            "медицинском": session.st9,
        }

    def has_unused_styles(self, session: ClientSession) -> bool:
        """Проверка наличия неиспользованных тем (стилей)."""
        return any([
            session.st1 == 1,
            session.st2 == 1,
            session.st3 == 1,
            session.st4 == 1,
            session.st5 == 1,
            session.st6 == 1,
            session.st7 == 1,
            session.st8 == 1,
            session.st9 == 1,
        ])

    def mark_style_as_used(self, db: Session, session: ClientSession, style: str) -> None:
        """Пометить стиль как использованный (установить в 0)."""
        style_map = {
            "убедительно-позитивном": "st1",
            "ироничном": "st2",
            "разговорном": "st3",
            "провокационном": "st4",
            "информационном": "st5",
            "официально-деловом": "st6",
            "сторителлинга": "st7",
            "продающем": "st8",
            "медицинском": "st9",
        }

        style_field = style_map.get(style)
        if style_field:
            setattr(session, style_field, 0)
            db.commit()

    def get_session_by_email(self, db: Session, email: str) -> Optional[ClientSession]:
        """Получить сеанс по email."""
        return db.query(ClientSession).filter(ClientSession.email == email).first()

    def create_session(
        self,
        db: Session,
        email: str,
        payment_id: Optional[str] = None,
        amount: Optional[int] = None,
        duration_minutes: Optional[int] = None
    ) -> ClientSession:
        """
        Создание новой клиентской записи.
        Все стили устанавливаются в 1, время оплаты - текущее.
        """
        # Удаляем старую запись, если есть
        old_session = self.get_session_by_email(db, email)
        if old_session:
            db.delete(old_session)
            db.commit()

        # Используем значение по умолчанию для W, если не указано
        if duration_minutes is None:
            duration_minutes = self.default_duration_minutes
        
        # Создаем новую запись
        new_session = ClientSession(
            email=email,
            url="",
            info="",
            st1=1,
            st2=1,
            st3=1,
            st4=1,
            st5=1,
            st6=1,
            st7=1,
            st8=1,
            st9=1,
            dt=datetime.now(),
            payment_id=payment_id,
            amount=int(amount) if amount is not None else None,  # Целочисленные рубли
            duration_minutes=duration_minutes,  # W - продолжительность в минутах
            is_active=True,
        )
        db.add(new_session)
        db.commit()
        db.refresh(new_session)
        return new_session

    def update_session(
        self,
        db: Session,
        session: ClientSession,
        url: Optional[str] = None,
        info: Optional[str] = None,
    ) -> ClientSession:
        """Обновление записи: URL и инфоповод."""
        if url is not None:
            session.url = url
        if info is not None:
            session.info = info
        db.commit()
        db.refresh(session)
        return session

    def delete_session(self, db: Session, email: str) -> None:
        """Удаление записи из базы."""
        session = self.get_session_by_email(db, email)
        if session:
            db.delete(session)
            db.commit()


# Глобальный экземпляр сервиса
session_service = SessionService()



