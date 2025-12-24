from typing import Any, Dict, List, Optional
import httpx

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.services.llm_client import LLMClient
from app.services.analyzer import SiteAnalyzer
from app.models.database import get_db
from app.services.session_service import session_service


router = APIRouter()


# Инициализируем LLM клиент в ГИБРИДНОМ РЕЖИМЕ:
# - Основной: DeepSeek (экономичный для анализа)
# - Альтернативный: GPT-4o (быстрый для chat/JSON)
llm_client = LLMClient(
    # DeepSeek как основной (для анализа больших текстов)
    # Параметры берутся из .env: BASE_URL, API_KEY
    # Альтернативный GPT-4o (для быстрых JSON)
    # Параметры берутся из .env: OPENAI_BASE_URL, OPENAI_API_KEY
)
site_analyzer = SiteAnalyzer(llm_client)


class ChatRequest(BaseModel):
    prompt: str
    model: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: float = 0.0


class ChatWithSystemRequest(BaseModel):
    system_prompt: str
    user_prompt: str
    model: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: float = 0.0


class ChatJsonRequest(BaseModel):
    system_prompt: str
    user_prompt: str
    jsonStandard: Optional[str] = None  # по ТЗ поле есть; используем как подсказку модели
    model: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: float = 0.0


@router.post("/chat")
def chat(req: ChatRequest) -> Dict[str, Any]:
    try:
        text = llm_client.chat(
            prompt=req.prompt,
            model=req.model,
            max_tokens=req.max_tokens,
            temperature=req.temperature,
        )
        return {"text": text}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/chat-with-system")
def chat_with_system(req: ChatWithSystemRequest) -> Dict[str, Any]:
    try:
        text = llm_client.chat_with_system(
            system_prompt=req.system_prompt,
            user_prompt=req.user_prompt,
            model=req.model,
            max_tokens=req.max_tokens,
            temperature=req.temperature,
        )
        return {"text": text}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/chat-json")
def chat_json(req: ChatJsonRequest) -> Dict[str, Any]:
    try:
        system_prompt = req.system_prompt
        if req.jsonStandard:
            system_prompt = f"{req.system_prompt}\nСтрого соблюдай стандарт JSON: {req.jsonStandard}"

        data = llm_client.chat_json(
            system_prompt=system_prompt,
            user_prompt=req.user_prompt,
            model=req.model,
            max_tokens=req.max_tokens,
            temperature=req.temperature,
        )
        return data
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


class AnalyzeRequest(BaseModel):
    url: str
    email: EmailStr  # Email клиента для проверки сеанса
    style: Optional[str] = "убедительно-позитивном"
    occasion: Optional[str] = ""
    use_cached: Optional[bool] = False
    cached_intermediate: Optional[List[Dict[str, Any]]] = None


@router.post("/analyze-site")
async def analyze_site(
    request: AnalyzeRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Анализ сайта с проверкой сеанса."""
    # Проверяем сеанс клиента
    session = session_service.get_session_by_email(db, request.email)
    
    if not session:
        raise HTTPException(
            status_code=403,
            detail="У вас нет оплаченных заказов."
        )
    
    # Проверяем доступность стиля ПЕРЕД генерацией
    available_styles = session_service.get_available_styles(session)
    if available_styles.get(request.style, 0) != 1:
        raise HTTPException(
            status_code=400,
            detail=f"Стиль '{request.style}' уже использован или недоступен."
        )
    
    # Проверяем время сеанса ПЕРЕД генерацией
    # ВАЖНО: Если время истекло, но генерация уже началась - результат все равно вернется
    is_time_valid = session_service.check_session_time(session)
    
    try:
        # Выполняем анализ (используем кэш только если разрешено)
        # ВАЖНО: Генерация выполняется независимо от статуса времени сеанса
        # Если клиент запустил генерацию до окончания сеанса - он получит результат
        result = await site_analyzer.analyze(
            request.url, 
            style=request.style,
            occasion=request.occasion,
            use_cached=request.use_cached,
            cached_intermediate=request.cached_intermediate,
            email=request.email  # Передаем email для привязки кэша к сеансу
        )
        
        # ПОСЛЕ генерации результата выполняем проверки окончания сеанса (блоки 17 и 18)
        # Помечаем стиль как использованный
        session_service.mark_style_as_used(db, session, request.style)
        
        # Проверяем время сеанса ПОСЛЕ генерации (блок 18)
        if not is_time_valid:
            session_service.delete_session(db, request.email)
            result['session_ended'] = True
            result['message'] = 'Время сеанса истекло. Сеанс завершен.'
            return result  # Возвращаем результат, даже если сеанс истек
        
        # Проверяем, остались ли еще доступные стили ПОСЛЕ генерации (блок 17)
        # Обновляем сеанс из БД, чтобы получить актуальные данные
        db.refresh(session)
        has_unused = session_service.has_unused_styles(session)
        
        # Если все стили использованы - завершаем сеанс (блок 20 блок-схемы)
        if not has_unused:
            session_service.delete_session(db, request.email)
            result['session_ended'] = True
            result['message'] = 'Все стили использованы. Сеанс завершен.'
        
        return result
        
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=400, detail=f"Ошибка скачивания: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/analyze-site-sync")
async def analyze_site_sync(
    request: AnalyzeRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Синхронный анализ сайта - используется frontend для прямого получения результатов.
    Включает проверку сеанса и доступности стиля.
    """
    # Проверяем сеанс клиента
    session = session_service.get_session_by_email(db, request.email)
    
    if not session:
        raise HTTPException(
            status_code=403,
            detail="У вас нет оплаченных заказов."
        )
    
    # Проверяем доступность стиля ПЕРЕД генерацией
    available_styles = session_service.get_available_styles(session)
    if available_styles.get(request.style, 0) != 1:
        raise HTTPException(
            status_code=400,
            detail=f"Стиль '{request.style}' уже использован или недоступен."
        )
    
    # Проверяем время сеанса ПЕРЕД генерацией
    # ВАЖНО: Если время истекло, но генерация уже началась - результат все равно вернется
    is_time_valid = session_service.check_session_time(session)
    
    # БЛОК 09: Сохранение URL и INFO в БД
    # ВАЖНО: Если данные еще не сохранены (пустые строки), сохраняем их
    # Это может быть первый анализ после оплаты, когда фронтенд еще не сохранил данные
    import sys
    current_url = session.url if session.url else ""
    current_info = session.info if session.info else ""
    
    sys.stdout.write(f"[DEBUG analyze_site_sync] Session before update: url='{current_url}', info='{current_info}'\n")
    sys.stdout.flush()
    sys.stdout.write(f"[DEBUG analyze_site_sync] Request data: url='{request.url}', info='{request.occasion}'\n")
    sys.stdout.flush()
    
    # Сохраняем URL и INFO, если они пустые или изменились
    # ВАЖНО: При первом анализе session.url и session.info пустые, поэтому сохраняем
    url_changed = current_url != request.url
    info_changed = current_info != request.occasion
    url_is_empty = not current_url or current_url.strip() == ""
    info_is_empty = not current_info or current_info.strip() == ""
    
    should_update_url = url_is_empty or url_changed
    should_update_info = info_is_empty or info_changed
    
    sys.stdout.write(f"[DEBUG analyze_site_sync] Update check: url_is_empty={url_is_empty}, info_is_empty={info_is_empty}, url_changed={url_changed}, info_changed={info_changed}\n")
    sys.stdout.flush()
    sys.stdout.write(f"[DEBUG analyze_site_sync] Should update: url={should_update_url}, info={should_update_info}\n")
    sys.stdout.flush()
    
    if should_update_url or should_update_info:
        sys.stdout.write(f"[DEBUG analyze_site_sync] UPDATING session: url='{request.url}', info='{request.occasion}'\n")
        sys.stdout.flush()
        
        session_service.update_session(
            db,
            session,
            url=request.url if should_update_url else None,
            info=request.occasion if should_update_info else None
        )
        # Обновляем сеанс из БД для актуальных данных
        db.refresh(session)
        
        sys.stdout.write(f"[DEBUG analyze_site_sync] Session updated: url='{session.url}', info='{session.info}'\n")
        sys.stdout.flush()
    else:
        sys.stdout.write(f"[DEBUG analyze_site_sync] No update needed\n")
        sys.stdout.flush()
    
    # Определяем, можно ли использовать кэш:
    # 1. Это НЕ первый анализ после оплаты (session.url уже установлен и не пустой)
    # 2. URL не изменился (session.url == request.url)
    # 3. Клиент явно запросил кэш
    # ВАЖНО: При первом входе после оплаты session.url пустой, поэтому кэш НЕ используется
    can_use_cache = (
        session.url and  # URL уже был установлен (не первый анализ)
        session.url != "" and  # URL не пустой (важно для первого входа)
        session.url == request.url and  # URL не изменился
        request.use_cached  # Клиент явно запросил кэш
    )
    
    try:
        # Выполняем анализ (используем кэш только если разрешено)
        # ВАЖНО: Генерация выполняется независимо от статуса времени сеанса
        # Если клиент запустил генерацию до окончания сеанса - он получит результат
        result = await site_analyzer.analyze(
            request.url, 
            style=request.style,
            occasion=request.occasion,
            use_cached=can_use_cache,
            cached_intermediate=request.cached_intermediate if can_use_cache else None,
            email=request.email  # Передаем email для привязки кэша к сеансу
        )
        
        # БЛОК 16: Обновление записи в базе (помечаем стиль как использованный)
        session_service.mark_style_as_used(db, session, request.style)
        
        # БЛОК 17: ВЫВОД ПУБЛИКАЦИЙ - результат возвращается пользователю
        # Пользователь может сохранить результат по кнопке сохранения
        # ВАЖНО: Проверки времени и стилей (блоки 19-20) НЕ выполняются здесь!
        # Согласно блок-схеме: "Переход на блок 19 только после завершения блока 17 или при переходе на блок 18"
        # Проверки будут выполнены при следующем запросе (выбор нового стиля) или при закрытии результатов
        
        # БЛОК 18: ПОВТОР - переход на новую генерацию (если сеанс не завершен)
        # Возвращаем результат без проверок - проверки будут при следующем запросе
        return result
        
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=400, detail=f"Ошибка скачивания: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


