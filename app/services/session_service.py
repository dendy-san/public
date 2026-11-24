"""
Сервис для работы с клиентскими сеансами.
Управляет проверкой времени, созданием и обновлением записей.
"""
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from sqlalchemy.orm import Session

from app.models.database import ClientSession, get_db
from app.styles import STYLE_KEYS, STYLE_TO_COLUMN


class SessionService:
    """Сервис управления клиентскими сеансами."""

    def __init__(self):
        # Значение по умолчанию для W (будет использоваться, если в Redis нет значения)
        self.default_duration_minutes = int(os.getenv("W", os.getenv("SESSION_DURATION_MINUTES", "1440")))
    
    async def _get_w_from_redis(self) -> Optional[int]:
        """Получить значение W из Redis."""
        try:
            from app.services.params_service import params_service
            w_value = await params_service.get_param("W")
            return int(w_value) if w_value else None
        except Exception:
            return None

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
            style: getattr(session, column)
            for style, column in STYLE_TO_COLUMN.items()
        }

    def has_unused_styles(self, session: ClientSession) -> bool:
        """Проверка наличия неиспользованных тем (стилей)."""
        return any(
            getattr(session, column) == 1 for column in STYLE_TO_COLUMN.values()
        )

    def mark_style_as_used(self, db: Session, session: ClientSession, style: str) -> None:
        """Пометить стиль как использованный (установить в 0)."""
        style_field = STYLE_TO_COLUMN.get(style)
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

        # Используем переданное значение W или значение по умолчанию
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

    def delete_session(self, db: Session, email: str, reason: Optional[str] = None) -> None:
        """
        Удаление записи из базы.

        reason="expired" — сеанс удалён потому, что истекло время. Тогда же
        обновляется лид: человек заплатил, но не воспользовался, и в воронке
        это отдельный исход (срок хранения ПДн при этом не сокращается —
        удаление по delete_after остаётся самостоятельным).
        Завершение сеанса по другой причине (исчерпаны стили, клиент удалил
        сам) статус лида не меняет: оплата была, и paid остаётся верным.
        """
        session = self.get_session_by_email(db, email)
        if session:
            db.delete(session)
            db.commit()

        if reason == "expired":
            try:
                from app.services.lead_service import lead_service
                lead_service.mark_expired(db, email)
            except Exception as e:
                # Ошибка статуса лида не должна рвать удаление сеанса.
                print(f"[SessionService] Не удалось обновить статус лида: {e}")


# Глобальный экземпляр сервиса
session_service = SessionService()



