import asyncio
import json
import os
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import aioredis
from fastapi import HTTPException


class TaskQueue:
    """Простая система очереди задач с Redis для фоновой обработки."""
    
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis: Optional[aioredis.Redis] = None
        self.active_tasks: Dict[str, asyncio.Task] = {}
        self.max_concurrent_tasks = 4  # Лимит одновременных LLM задач
    
    async def connect(self):
        """Подключение к Redis."""
        if not self.redis:
            try:
                self.redis = await aioredis.from_url(self.redis_url, decode_responses=True)
                # Проверяем подключение
                await self.redis.ping()
            except Exception as exc:
                print(f"WARNING: Redis unavailable: {exc}")
                print("INFO: Running without background tasks")
                self.redis = None
    
    async def disconnect(self):
        """Отключение от Redis."""
        if self.redis:
            await self.redis.close()
    
    async def submit_task(
        self, 
        task_type: str, 
        payload: Dict[str, Any],
        timeout: int = 300  # 5 минут
    ) -> str:
        """Отправить задачу в очередь и вернуть task_id."""
        await self.connect()
        
        if not self.redis:
            raise HTTPException(
                status_code=503, 
                detail="Фоновые задачи недоступны (Redis не подключён). Используйте /analyze-site-sync"
            )
        
        task_id = str(uuid.uuid4())
        task_data = {
            "id": task_id,
            "type": task_type,
            "payload": json.dumps(payload),  # Сериализуем в JSON
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "timeout": str(timeout)  # Преобразуем в строку
        }
        
        # Сохраняем в Redis
        await self.redis.hset(f"task:{task_id}", mapping=task_data)
        await self.redis.expire(f"task:{task_id}", timeout + 60)  # +1 минута буфер
        
        # Добавляем в очередь
        await self.redis.lpush("task_queue", task_id)
        
        return task_id
    
    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Получить статус задачи."""
        await self.connect()
        
        task_data = await self.redis.hgetall(f"task:{task_id}")
        if not task_data:
            raise HTTPException(status_code=404, detail="Задача не найдена")
        
        # Парсим payload если он есть
        if task_data.get("payload"):
            try:
                task_data["payload"] = json.loads(task_data["payload"])
            except json.JSONDecodeError:
                pass
        
        # Парсим result если он есть
        if task_data.get("result"):
            try:
                task_data["result"] = json.loads(task_data["result"])
            except json.JSONDecodeError:
                pass
        
        return task_data
    
    async def update_task_status(
        self, 
        task_id: str, 
        status: str, 
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ):
        """Обновить статус задачи."""
        await self.connect()
        
        updates = {
            "status": status,
            "updated_at": datetime.now().isoformat()
        }
        
        if result is not None:
            updates["result"] = json.dumps(result)
        
        if error is not None:
            updates["error"] = error
        
        await self.redis.hset(f"task:{task_id}", mapping=updates)
    
    async def cleanup_old_tasks(self, max_age_hours: int = 24):
        """Очистка старых задач."""
        await self.connect()
        
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        # Получаем все ключи задач
        task_keys = await self.redis.keys("task:*")
        
        for key in task_keys:
            task_data = await self.redis.hgetall(key)
            created_at_str = task_data.get("created_at")
            
            if created_at_str:
                try:
                    created_at = datetime.fromisoformat(created_at_str)
                    if created_at < cutoff_time:
                        await self.redis.delete(key)
                except ValueError:
                    # Если не можем распарсить дату, удаляем
                    await self.redis.delete(key)


# Глобальный экземпляр очереди
task_queue = TaskQueue()


async def process_task_queue():
    """Фоновая функция для обработки очереди задач."""
    while True:
        try:
            await task_queue.connect()
            
            # Если Redis недоступен, ждём и пробуем снова
            if not task_queue.redis:
                await asyncio.sleep(10)
                continue
            
            # Проверяем лимит активных задач
            if len(task_queue.active_tasks) >= task_queue.max_concurrent_tasks:
                await asyncio.sleep(1)
                continue
            
            # Получаем следующую задачу
            task_id = await task_queue.redis.brpop("task_queue", timeout=1)
            if not task_id:
                continue
            
            task_id = task_id[1]  # brpop возвращает (key, value)
            
            # Получаем данные задачи
            task_data = await task_queue.redis.hgetall(f"task:{task_id}")
            if not task_data:
                continue
            
            # Запускаем обработку в фоне
            task = asyncio.create_task(execute_task(task_id, task_data))
            task_queue.active_tasks[task_id] = task
            
        except Exception as exc:
            print(f"ERROR in task queue processing: {exc}")
            await asyncio.sleep(5)


async def execute_task(task_id: str, task_data: Dict[str, Any]):
    """Выполнение конкретной задачи."""
    try:
        # Обновляем статус на "processing"
        await task_queue.update_task_status(task_id, "processing")
        
        task_type = task_data["type"]
        payload = json.loads(task_data["payload"]) if task_data.get("payload") else {}
        
        if task_type == "analyze_site":
            from app.services.analyzer import SiteAnalyzer
            from app.services.llm_client import LLMClient
            
            # Создаем анализатор
            llm_client = LLMClient()
            analyzer = SiteAnalyzer(llm_client)
            
            # Выполняем анализ
            result = await analyzer.analyze(
                url=payload["url"],
                style=payload.get("style", "убедительно-позитивном"),
                occasion=payload.get("occasion", ""),
                use_cached=payload.get("use_cached", False),
                cached_intermediate=payload.get("cached_intermediate")
            )
            
            # Сохраняем результат
            await task_queue.update_task_status(task_id, "completed", result=result)
            
        else:
            await task_queue.update_task_status(
                task_id, 
                "failed", 
                error=f"Неизвестный тип задачи: {task_type}"
            )
            
    except Exception as exc:
        await task_queue.update_task_status(
            task_id, 
            "failed", 
            error=str(exc)
        )
    finally:
        # Удаляем из активных задач
        if task_id in task_queue.active_tasks:
            del task_queue.active_tasks[task_id]


# Функция для запуска фоновой обработки
async def start_task_processor():
    """Запуск обработчика задач."""
    await task_queue.connect()
    asyncio.create_task(process_task_queue())
