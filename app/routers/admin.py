"""
Роутер для административной панели.

Безопасность: реальный API-ключ ЮKассы никогда не отдаётся на фронтенд.
Везде, где ключ мог бы покинуть бэкенд, возвращается маска (см. mask_secret).
"""
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services.params_service import params_service, mask_secret


router = APIRouter()


@router.get("/")
async def admin_root():
    """Базовый эндпоинт административной панели."""
    return {"message": "Admin panel"}


class ParamUpdateRequest(BaseModel):
    value: str


class YooKassaParamsUpdateRequest(BaseModel):
    shop_id: str
    # Ключ опционален: если не передан, сохранённый ключ остаётся неизменным
    # (реальный ключ не возвращается на фронтенд, поэтому поле часто пустое).
    api_key: Optional[str] = None


@router.get("/params")
async def get_all_params() -> Dict[str, Any]:
    """
    Получить текущие параметры. Ykassa_API возвращается маскированным,
    флаг has_api_key сообщает, задан ли ключ (см. params_service.get_all_params).
    """
    return await params_service.get_all_params()


@router.post("/params/yookassa")
async def update_yookassa_params(request: YooKassaParamsUpdateRequest) -> Dict[str, Any]:
    """
    Обновить параметры ЮКассы. ShopID обязателен, api_key опционален:
    пустой api_key означает «оставить текущий ключ без изменения».
    """
    if not request.shop_id:
        raise HTTPException(status_code=400, detail="ShopID cannot be empty")

    success = await params_service.set_yookassa_params(
        request.shop_id,
        request.api_key,
        source="admin_panel"
    )
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update YooKassa parameters")

    return {
        "status": "ok",
        "message": "YooKassa parameters updated successfully",
        "shop_id": request.shop_id,
        "api_key_updated": bool(request.api_key),
    }


@router.post("/params/snapshot")
async def save_snapshot() -> Dict[str, Any]:
    """
    Сохранить полный снимок текущей конфигурации (W, Price, ShopID, маска ключа).

    Вызывается админ-панелью один раз после применения изменений: снимок —
    это пресет, которым можно позже вернуть всю конфигурацию целиком.
    Объявлен до маршрута /params/{param_name}, чтобы не считаться параметром.
    """
    success = await params_service.add_snapshot_history(source="admin_panel")
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save configuration snapshot")
    return {"status": "ok", "message": "Configuration snapshot saved"}


@router.get("/params/{param_name}")
async def get_param(param_name: str) -> Dict[str, Any]:
    """Получить текущее значение параметра (секрет маскируется)."""
    param_name_upper = param_name.upper()

    if param_name_upper in ["W", "PRICE"]:
        redis_param_name = "W" if param_name_upper == "W" else "Price"
        value = await params_service.get_param(redis_param_name)
        if value is None:
            raise HTTPException(status_code=404, detail=f"Parameter {redis_param_name} not found")
        return {"name": redis_param_name, "value": value}
    elif param_name_upper == "SHOPID":
        value = await params_service.get_param("ShopID")
        return {"name": "ShopID", "value": value or ""}
    elif param_name_upper == "YKASSA_API":
        value = await params_service.get_param("Ykassa_API") or ""
        # Реальный ключ наружу не отдаём — только маску и признак наличия.
        return {"name": "Ykassa_API", "value": mask_secret(value), "has_value": bool(value)}
    else:
        raise HTTPException(status_code=400, detail="Invalid parameter name. Use 'W', 'Price', 'ShopID' or 'Ykassa_API'")


async def _update_param_impl(param_name: str, request: ParamUpdateRequest) -> Dict[str, Any]:
    """Внутренняя функция для обновления параметра W или Price."""
    param_name_upper = param_name.upper()

    if param_name_upper not in ["W", "PRICE"]:
        raise HTTPException(status_code=400, detail="Invalid parameter name. Use 'W' or 'Price'")

    redis_param_name = "W" if param_name_upper == "W" else "Price"

    # Валидация значения: целое положительное число
    try:
        int_value = int(request.value)
        if int_value <= 0:
            raise ValueError("must be positive")
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid value for {redis_param_name}: must be a positive integer")

    success = await params_service.set_param(redis_param_name, request.value, source="admin_panel")
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update parameter")

    return {
        "status": "ok",
        "name": redis_param_name,
        "value": request.value,
        "message": f"Parameter {redis_param_name} updated successfully",
    }


@router.post("/params/{param_name}")
async def update_param(param_name: str, request: ParamUpdateRequest) -> Dict[str, Any]:
    """Обновить значение параметра W или Price."""
    return await _update_param_impl(param_name, request)


@router.get("/params/history/{param_name}")
async def get_param_history(
    param_name: str,
    limit: int = Query(20, ge=1, le=100, description="Number of history entries to return")
) -> Dict[str, Any]:
    """Получить историю изменений параметра."""
    param_name_lower = param_name.lower()

    # Снимки полной конфигурации (пресеты для админ-панели)
    if param_name_lower == "snapshot":
        snapshots = await params_service.get_snapshot_history(limit=limit)
        return {
            "param_name": "snapshot",
            "history": snapshots,
            "count": len(snapshots),
        }

    # История параметров ЮКассы (ShopID и Ykassa_API вместе)
    if param_name_lower in ["yookassa", "shopid", "ykassa_api"]:
        history = await params_service.get_yookassa_history(limit=limit)
        current_shop_id = await params_service.get_param("ShopID") or ""
        current_api_key = await params_service.get_param("Ykassa_API") or ""

        return {
            "param_name": "yookassa",
            "current_shop_id": current_shop_id,
            # Маска вместо реального ключа (см. mask_secret).
            "current_api_key": mask_secret(current_api_key),
            "history": history,
            "count": len(history),
        }

    # Нормализуем имя параметра (W или Price)
    param_name_upper = param_name.upper()
    if param_name_upper not in ["W", "PRICE"]:
        raise HTTPException(status_code=400, detail="Invalid parameter name. Use 'W', 'Price' or 'yookassa'")

    redis_param_name = "W" if param_name_upper == "W" else "Price"

    history = await params_service.get_history(redis_param_name, limit=limit)
    current_value = await params_service.get_param(redis_param_name)

    return {
        "param_name": redis_param_name,
        "current_value": current_value,
        "history": history,
        "count": len(history),
    }
