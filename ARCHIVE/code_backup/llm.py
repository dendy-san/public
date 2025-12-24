from typing import Any, Dict, List, Optional
import httpx
import json

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
    
    # Проверяем время сеанса
    if not session_service.check_session_time(session):
        session_service.delete_session(db, request.email)
        raise HTTPException(
            status_code=410,
            detail="Время сеанса истекло."
        )
    
    # Проверяем доступность стиля
    available_styles = session_service.get_available_styles(session)
    if available_styles.get(request.style, 0) != 1:
        raise HTTPException(
            status_code=400,
            detail=f"Стиль '{request.style}' уже использован или недоступен."
        )
    
    try:
        result = await site_analyzer.analyze(
            request.url, 
            style=request.style,
            occasion=request.occasion,
            use_cached=request.use_cached,
            cached_intermediate=request.cached_intermediate
        )
        
        # Помечаем стиль как использованный
        session_service.mark_style_as_used(db, session, request.style)
        
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
    print(f"[ANALYZE-SYNC] Request received: email={request.email}, url={request.url}, style={request.style}")
    
    # Проверяем сеанс клиента
    session = session_service.get_session_by_email(db, request.email)
    print(f"[ANALYZE-SYNC] Session found: {session is not None}")
    
    if not session:
        raise HTTPException(
            status_code=403,
            detail="У вас нет оплаченных заказов."
        )
    
    # Проверяем время сеанса
    if not session_service.check_session_time(session):
        session_service.delete_session(db, request.email)
        raise HTTPException(
            status_code=410,
            detail="Время сеанса истекло."
        )
    
    # Проверяем доступность стиля
    available_styles = session_service.get_available_styles(session)
    if available_styles.get(request.style, 0) != 1:
        raise HTTPException(
            status_code=400,
            detail=f"Стиль '{request.style}' уже использован или недоступен."
        )
    
    # Обновляем URL и инфоповод в сеансе
    # Всегда обновляем, чтобы гарантировать сохранение данных
    occasion_value = request.occasion if request.occasion is not None else ""
    session_service.update_session(
        db,
        session,
        url=request.url,
        info=occasion_value
    )
    # Обновляем сессию после изменения
    db.refresh(session)
    
    try:
        # Проверяем, есть ли сохраненный результат парсинга
        saved_parsed_text, saved_intermediate_json = session_service.get_parsing_result(session)
        saved_intermediate = None
        
        if saved_parsed_text and saved_intermediate_json:
            try:
                saved_intermediate = json.loads(saved_intermediate_json)
                print(f"[ANALYZE] Found saved parsing result for {request.email}")
            except json.JSONDecodeError:
                print(f"[ANALYZE] Error parsing saved intermediate results, will re-parse")
                saved_parsed_text = None
                saved_intermediate = None
        
        # Выполняем анализ
        print(f"[ANALYZE] Starting analysis for {request.email}, URL: {request.url}, style: {request.style}")
        result = await site_analyzer.analyze(
            request.url, 
            style=request.style,
            occasion=request.occasion,
            use_cached=request.use_cached,
            cached_intermediate=request.cached_intermediate,
            saved_parsed_text=saved_parsed_text,
            saved_intermediate=saved_intermediate
        )
        print(f"[ANALYZE] Analysis completed successfully for {request.email}")
        
        # Сохраняем результат парсинга, если он был выполнен заново
        if not saved_parsed_text and result.get("intermediate_results") and result.get("cleaned_text"):
            try:
                cleaned_text = result["cleaned_text"]
                intermediate_json = json.dumps(result["intermediate_results"], ensure_ascii=False)
                session_service.save_parsing_result(
                    db,
                    session,
                    parsed_text=cleaned_text,
                    parsed_intermediate=intermediate_json
                )
                print(f"[ANALYZE] Saved parsing result for {request.email}")
            except Exception as e:
                print(f"[ANALYZE] Error saving parsing result: {e}")
                import traceback
                traceback.print_exc()
        
        # Помечаем стиль как использованный
        session_service.mark_style_as_used(db, session, request.style)
        
        return result
        
    except httpx.HTTPError as exc:
        print(f"[ANALYZE ERROR] HTTPError for {request.email}: {exc}")
        raise HTTPException(status_code=400, detail=f"Ошибка скачивания: {exc}") from exc
    except ValueError as exc:
        print(f"[ANALYZE ERROR] ValueError for {request.email}: {exc}")
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        print(f"[ANALYZE ERROR] Exception for {request.email}: {exc}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(exc)) from exc


