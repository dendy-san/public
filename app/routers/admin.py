"""
Роутер для административной панели.
"""
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services.params_service import params_service


router = APIRouter()


@router.get("/")
async def admin_root():
    """Базовый эндпоинт административной панели."""
    return {"message": "Admin panel"}


class ParamUpdateRequest(BaseModel):
    value: str


class YooKassaParamsUpdateRequest(BaseModel):
    shop_id: str
    api_key: str


@router.get("/params")
async def get_all_params() -> Dict[str, str]:
    """Получить все текущие параметры."""
    return await params_service.get_all_params()


@router.post("/params/yookassa")
async def update_yookassa_params_post(request: YooKassaParamsUpdateRequest) -> Dict[str, Any]:
    """Обновить параметры ЮКассы (ShopID и Ykassa_API вместе)."""
    if not request.shop_id:
        raise HTTPException(status_code=400, detail="ShopID cannot be empty")
    if not request.api_key:
        raise HTTPException(status_code=400, detail="Ykassa_API cannot be empty")
    
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
        "api_key_length": len(request.api_key)
    }


@router.put("/params/yookassa")
async def update_yookassa_params_put(request: YooKassaParamsUpdateRequest) -> Dict[str, Any]:
    """Обновить параметры ЮКассы (ShopID и Ykassa_API вместе) - PUT метод."""
    return await update_yookassa_params_post(request)


@router.get("/params/{param_name}")
async def get_param(param_name: str) -> Dict[str, str]:
    """Получить текущее значение параметра."""
    param_name_upper = param_name.upper()
    
    if param_name_upper in ["W", "PRICE"]:
        redis_param_name = "W" if param_name_upper == "W" else "Price"
        value = await params_service.get_param(redis_param_name)
        if value is None:
            raise HTTPException(status_code=404, detail=f"Parameter {redis_param_name} not found")
        return {"name": redis_param_name, "value": value}
    elif param_name_upper in ["SHOPID", "YKASSA_API"]:
        redis_param_name = "ShopID" if param_name_upper == "SHOPID" else "Ykassa_API"
        value = await params_service.get_param(redis_param_name)
        return {"name": redis_param_name, "value": value or ""}
    else:
        raise HTTPException(status_code=400, detail="Invalid parameter name. Use 'W', 'Price', 'ShopID' or 'Ykassa_API'")


async def _update_param_impl(param_name: str, request: ParamUpdateRequest) -> Dict[str, Any]:
    """Внутренняя функция для обновления параметра."""
    param_name_upper = param_name.upper()
    
    if param_name_upper not in ["W", "PRICE"]:
        raise HTTPException(status_code=400, detail="Invalid parameter name. Use 'W' or 'Price'")
    
    # Используем правильное имя для Redis
    redis_param_name = "W" if param_name_upper == "W" else "Price"
    
    # Валидация значения
    try:
        if redis_param_name == "W":
            int_value = int(request.value)
            if int_value <= 0:
                raise ValueError("W must be positive")
        elif redis_param_name == "Price":
            int_value = int(request.value)
            if int_value <= 0:
                raise ValueError("Price must be positive")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid value: {str(e)}")
    
    success = await params_service.set_param(redis_param_name, request.value, source="admin_panel")
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update parameter")
    
    return {
        "status": "ok",
        "name": redis_param_name,
        "value": request.value,
        "message": f"Parameter {redis_param_name} updated successfully"
    }


@router.put("/params/{param_name}")
async def update_param_put(param_name: str, request: ParamUpdateRequest) -> Dict[str, Any]:
    """Обновить значение параметра (PUT метод)."""
    return await _update_param_impl(param_name, request)


@router.post("/params/{param_name}")
async def update_param_post(param_name: str, request: ParamUpdateRequest) -> Dict[str, Any]:
    """Обновить значение параметра (POST метод)."""
    return await _update_param_impl(param_name, request)


@router.get("/params/history/{param_name}")
async def get_param_history(
    param_name: str,
    limit: int = Query(20, ge=1, le=100, description="Number of history entries to return")
) -> Dict[str, Any]:
    """Получить историю изменений параметра."""
    param_name_lower = param_name.lower()
    
    # История параметров ЮКассы (ShopID и Ykassa_API вместе)
    if param_name_lower in ["yookassa", "shopid", "ykassa_api"]:
        history = await params_service.get_yookassa_history(limit=limit)
        current_shop_id = await params_service.get_param("ShopID") or ""
        current_api_key = await params_service.get_param("Ykassa_API") or ""
        
        return {
            "param_name": "yookassa",
            "current_shop_id": current_shop_id,
            "current_api_key": current_api_key,
            "history": history,
            "count": len(history)
        }
    
    # Нормализуем имя параметра (W или Price)
    param_name_upper = param_name.upper()
    if param_name_upper not in ["W", "PRICE"]:
        raise HTTPException(status_code=400, detail="Invalid parameter name. Use 'W', 'Price' or 'yookassa'")
    
    # Используем правильное имя для Redis
    redis_param_name = "W" if param_name_upper == "W" else "Price"
    
    history = await params_service.get_history(redis_param_name, limit=limit)
    current_value = await params_service.get_param(redis_param_name)
    
    return {
        "param_name": redis_param_name,
        "current_value": current_value,
        "history": history,
        "count": len(history)
    }
