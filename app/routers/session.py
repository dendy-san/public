"""
Роутер для управления сеансами клиентов.
"""
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.models.database import get_db, ClientSession
from app.services.session_service import session_service


router = APIRouter()


class SessionCheckResponse(BaseModel):
    has_session: bool
    is_active: bool
    email: Optional[str] = None
    url: Optional[str] = None  # URL сайта из сеанса
    info: Optional[str] = None  # Инфоповод из сеанса
    available_styles: Optional[Dict[str, int]] = None
    has_unused_styles: Optional[bool] = None
    message: Optional[str] = None


class SessionUpdateRequest(BaseModel):
    url: Optional[str] = None
    info: Optional[str] = None


@router.get("/check/{email}", response_model=SessionCheckResponse)
async def check_session(
    email: str,
    db: Session = Depends(get_db)
) -> SessionCheckResponse:
    """
    БЛОК 01: ВХОД С ПАРАМЕТРОМ E-mail
    Проверка наличия активного сеанса для email.
    Проверяет наличие записи и время оплаты.
    """
    # БЛОК 02: ПРОВЕРКА E-mail на наличие в базе
    session = session_service.get_session_by_email(db, email)

    if not session:
        # БЛОК 02: НЕТ -> переход на блок 05 (сообщение об отсутствии оплаченной услуги)
        # Переход на блок 06: обновление параметров и оплата
        return SessionCheckResponse(
            has_session=False,
            is_active=False,
            message="У вас нет оплаченных заказов."
        )

    # Проверяем время сеанса
    is_time_valid = session_service.check_session_time(session)

    if not is_time_valid:
        # БЛОК 03: ПРОВЕРКА ВРЕМЕНИ сеанса: НЕТ (время истекло)
        # БЛОК 04: УДАЛЕНИЕ ЗАПИСИ из базы
        session_service.delete_session(db, email)
        # БЛОК 05: Сообщение об отсутствии оплаченной услуги
        # Переход на блок 06: обновление параметров и оплата
        return SessionCheckResponse(
            has_session=False,
            is_active=False,
            message="Время сеанса истекло."
        )

    # Сеанс активен
    available_styles = session_service.get_available_styles(session)
    has_unused = session_service.has_unused_styles(session)

    return SessionCheckResponse(
        has_session=True,
        is_active=True,
        email=session.email,
        url=session.url if session.url else None,  # Возвращаем URL из сеанса
        info=session.info if session.info else None,  # Возвращаем инфоповод из сеанса
        available_styles=available_styles,
        has_unused_styles=has_unused,
        message="Сеанс активен."
    )


@router.post("/update/{email}")
async def update_session(
    email: str,
    request: SessionUpdateRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Обновление URL и инфоповода в сеансе.
    """
    session = session_service.get_session_by_email(db, email)

    if not session:
        raise HTTPException(
            status_code=404,
            detail="Сеанс не найден"
        )

    # Проверяем время
    if not session_service.check_session_time(session):
        session_service.delete_session(db, email)
        raise HTTPException(
            status_code=410,
            detail="Время сеанса истекло"
        )

    # Обновляем данные
    updated_session = session_service.update_session(
        db,
        session,
        url=request.url,
        info=request.info
    )

    return {
        "status": "ok",
        "session": updated_session.to_dict()
    }


@router.get("/styles/{email}")
async def get_available_styles(
    email: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Получение списка доступных стилей для клиента.
    """
    session = session_service.get_session_by_email(db, email)

    if not session:
        raise HTTPException(
            status_code=404,
            detail="Сеанс не найден"
        )

    # Проверяем время
    if not session_service.check_session_time(session):
        session_service.delete_session(db, email)
        raise HTTPException(
            status_code=410,
            detail="Время сеанса истекло"
        )

    available_styles = session_service.get_available_styles(session)
    has_unused = session_service.has_unused_styles(session)

    return {
        "email": email,
        "available_styles": available_styles,
        "has_unused_styles": has_unused
    }


@router.post("/mark-style-used/{email}")
async def mark_style_used(
    email: str,
    style: str = Query(..., description="Название стиля"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Пометить стиль как использованный.
    """
    session = session_service.get_session_by_email(db, email)

    if not session:
        raise HTTPException(
            status_code=404,
            detail="Сеанс не найден"
        )

    # Проверяем время
    if not session_service.check_session_time(session):
        session_service.delete_session(db, email)
        raise HTTPException(
            status_code=410,
            detail="Время сеанса истекло"
        )

    # Помечаем стиль как использованный
    session_service.mark_style_as_used(db, session, style)

    return {
        "status": "ok",
        "message": f"Стиль '{style}' помечен как использованный"
    }


@router.delete("/delete/{email}")
async def delete_session_endpoint(
    email: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    БЛОК 24: УДАЛЕНИЕ КЛИЕНТСКОЙ ЗАПИСИ из базы.
    ПЕРЕХОД на блок 06: обновление параметров и оплата.
    """
    session = session_service.get_session_by_email(db, email)
    
    if session:
        session_service.delete_session(db, email)
    
    return {
        "status": "ok",
        "message": "Сеанс удален" if session else "Сеанс не найден"
    }

