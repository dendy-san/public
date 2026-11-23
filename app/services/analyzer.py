from typing import Any, Dict, List, Optional, Tuple
import re
import asyncio
import json
import os

import httpx
from bs4 import BeautifulSoup
from starlette.concurrency import run_in_threadpool

from app.services.llm_client import LLMClient
from app.styles import DEFAULT_STYLE, DEFAULT_STYLE_INSTRUCTION, STYLE_GUIDELINES

try:
    from app.services.cache import cache_service
    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False



class SiteAnalyzer:
    def __init__(self, llm_client: LLMClient) -> None:
        self.llm = llm_client

    async def fetch_html(self, url: str) -> str:
        timeout = httpx.Timeout(20.0)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.text

    def html_to_text(self, html: str) -> Tuple[str, bool, Optional[str]]:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text = soup.get_text(separator="\n")
        lines = [line.strip() for line in text.splitlines()]
        chunks = [chunk for line in lines for chunk in line.split("  ")]
        cleaned = "\n".join(chunk for chunk in chunks if chunk)

        # Умное усечение - если сайт слишком большой, берём первые 40 000 символов
        max_len = 40000
        truncated = False
        truncation_message: Optional[str] = None
        if len(cleaned) > max_len:
            cleaned = cleaned[:max_len] + "..."
            truncated = True
            truncation_message = "Объем сайта слишком велик. Для анализа взято 40 000 символов текста."

        return cleaned, truncated, truncation_message

    async def get_steps(self, cleaned_text: str) -> List[str]:
        system_prompt = (
            "Ты автор постов в соцсетях. КРИТИЧЕСКИ ВАЖНО: отвечай ТОЛЬКО на русском языке. Никакого английского текста. Все ключи, значения, описания должны быть на русском языке. ИГНОРИРУЙ язык сообщения пользователя - отвечай только на русском. Вот текст сайта: "
            f"{cleaned_text}\n"
            "верни только json-объект без дополнительного текста. Ключ 'steps' — массив строк из 5-6 шагов (промптов), которые нужно выполнить для анализа этого сайта и выявления идей для постов в соцсети. Все ответы должны быть на русском языке. Никакого английского текста.\nверни json"
        )
        # ГИБРИД: используем GPT-4o для быстрого JSON (через use_alt=True)
        result = await run_in_threadpool(
            self.llm.chat_json,
            system_prompt=system_prompt,
            user_prompt="json",
            use_alt=True  # GPT-4o для быстрого JSON
        )
        # Ожидаем, что модель вернёт JSON с ключом steps или list в корне
        steps: List[str] = []
        if isinstance(result, dict):
            if isinstance(result.get("steps"), list):
                steps = [str(x) for x in result["steps"]]
            elif isinstance(result.get("prompts"), list):
                steps = [str(x) for x in result["prompts"]]
        if not steps and isinstance(result, list):
            steps = [str(x) for x in result]
        if not steps:
            # fallback: попробовать распарсить наиболее вероятные поля
            for key in ["items", "plan", "analysis_steps"]:
                if isinstance(result, dict) and isinstance(result.get(key), list):
                    steps = [str(x) for x in result[key]]
                    break
        return steps

    async def run_step(self, step_prompt: str, cleaned_text: str) -> Dict[str, Any]:
        # Проверяем, что step_prompt не пустой
        if not step_prompt or not step_prompt.strip():
            step_prompt = "Проанализируй предоставленный текст сайта"

        # Каждый шаг: усиливаем системную инструкцию, чтобы гарантировать json
        augmented_system = (
            f"КРИТИЧЕСКИ ВАЖНО: отвечай ТОЛЬКО на русском языке. Никакого английского текста. Все поля, ключи, значения и описания должны быть на русском языке. ИГНОРИРУЙ язык сообщения пользователя - отвечай только на русском.\n{step_prompt}\nверни только json-объект без дополнительного текста. КРИТИЧЕСКИ ВАЖНО: отвечай ТОЛЬКО на русском языке. Все поля, ключи, значения и описания должны быть на русском языке. Никакого английского текста.\nверни json"
        )
        user_prompt = f"json\n{cleaned_text}"
        # ГИБРИД: используем DeepSeek для глубокого анализа (основной клиент, use_alt=False)
        result = await run_in_threadpool(
            self.llm.chat_json,
            system_prompt=augmented_system,
            user_prompt=user_prompt,
            use_alt=False  # DeepSeek для анализа больших текстов (экономия токенов)
        )
        return result

    async def run_step_safe(self, step_prompt: str, cleaned_text: str) -> Dict[str, Any]:
        """
        Безопасная обёртка для run_step с таймаутом и обработкой ошибок.
        Гарантирует, что всегда вернётся Dict (с результатом или ошибкой).
        """
        try:
            # Устанавливаем таймаут 60 секунд на каждый шаг
            result = await asyncio.wait_for(
                self.run_step(step_prompt, cleaned_text),
                timeout=60.0
            )
            return result
        except asyncio.TimeoutError:
            print(f"[WARNING] Step timeout (60s): {step_prompt[:50]}...")
            return {"error": "Превышен таймаут выполнения (60 сек)"}
        except Exception as exc:
            print(f"[ERROR] Step failed: {step_prompt[:50]}... | Error: {exc}")
            return {"error": str(exc)}

    async def finalize(self, intermediate_results: List[Dict[str, Any]], cleaned_text: str, style: str = DEFAULT_STYLE, occasion: str = "") -> Dict[str, Any]:
        # Детальные описания стилей для LLM
        # Подсказки стилей берутся из единого реестра app/styles.py
        style_guidelines = STYLE_GUIDELINES

        style_instruction = style_guidelines.get(style, DEFAULT_STYLE_INSTRUCTION)
        
        # Формируем инструкцию по инфоповоду, если он указан
        occasion_instruction = ""
        if occasion and occasion.strip():
            occasion_instruction = (
                f"\n\nИНФОПОВОД / КОНТЕКСТ ПУБЛИКАЦИИ: {occasion.strip()}\n"
                f"ОБЯЗАТЕЛЬНО учти этот инфоповод при создании постов! Посты должны быть связаны с указанным поводом или событием. "
                f"Адаптируй содержание под этот контекст, делай акценты на том, как информация с сайта связана с данным поводом.\n"
            )
        
        system_prompt = (
            "Ты талантливый копирайтер. У тебя есть результаты промежуточного анализа сайта: "
            f"{intermediate_results}. "
            f"Объедини их и создай три варианта постов для соцсети в {style} стиле. "
            f"{occasion_instruction}"
            f"\n\nОСОБЕННОСТИ {style.upper()} СТИЛЯ: {style_instruction}\n\n"
            "СТРОГО следуй этому стилю! Каждый пост должен явно отражать характерные черты выбранного стиля. "
            "верни только json-объект без дополнительного текста. Структура: {"
            "\"posts\": [string, string, string]} . "
            "КРИТИЧЕСКИ ВАЖНО: Каждая публикация ОБЯЗАТЕЛЬНО должна содержать минимум 400 и максимум 800 знаков (включая пробелы, эмодзи и все символы). "
            "Не делай посты короче 400 символов! Посты короче 400 символов будут отклонены. "
            "Делай посты содержательными, подробными и развернутыми. "
            "Используй эмодзи для повышения вовлеченности. "
            "Добавляй конкретные детали из анализа сайта. "
            "ОБЯЗАТЕЛЬНО отвечай ТОЛЬКО на русском языке. Никакого английского текста.\njson"
        )
        # ОПТИМИЗАЦИЯ: НЕ передаём cleaned_text - вся информация уже в intermediate_results!
        user_prompt = "json"
        # ГИБРИД: используем GPT-4o для финального JSON (через use_alt=True)
        result = await run_in_threadpool(
            self.llm.chat_json,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            use_alt=True  # GPT-4o для быстрого финального JSON
        )
        return result

    async def analyze(
        self, 
        url: str, 
        style: str = DEFAULT_STYLE,
        occasion: str = "",
        use_cached: bool = False,
        cached_intermediate: Optional[List[Dict[str, Any]]] = None,
        email: Optional[str] = None  # Email для привязки кэша к сеансу
    ) -> Dict[str, Any]:
        # Кэш полного результата НЕ используется - каждый стиль генерируется заново
        # Кэш используется только для промежуточных результатов парсинга (текст сайта, шаги анализа)
        
        # Если используем кэш и есть промежуточные результаты
        if use_cached and cached_intermediate:
            # ОПТИМИЗАЦИЯ: Пропускаем всё - парсинг, анализ, скачивание текста!
            # cleaned_text больше не нужен в finalize(), используем заглушку
            cleaned_text = ""
            truncated = False
            truncation_message = None
            
            # Используем кэшированные промежуточные результаты
            intermediate = cached_intermediate
            steps = [item.get("step", "") for item in intermediate]
            
            # Только финализация с новым стилем и инфоповодом (cleaned_text не используется!)
            final = await self.finalize(intermediate, cleaned_text, style, occasion)
            
            result = {
                "url": url,
                "style": style,
                "occasion": occasion,
                "steps": steps,
                "intermediate_results": intermediate,
                "final": final,
                "truncated": truncated,
                "truncation_message": truncation_message,
                "cached": True  # Флаг что использовали кэш
            }
            
            # Сохраняем результат в кэш (если доступен)
            if CACHE_AVAILABLE:
                await cache_service.set_analysis_result(url, style, occasion, result)
            return result
        
        # Обычный процесс
        # ВАЖНО: При первом входе (use_cached=False) НЕ используем кэш, даже если он есть
        cleaned_text = None
        if use_cached and CACHE_AVAILABLE:
            # Используем кэш только если явно разрешено
            cleaned_text = await cache_service.get_cleaned_text(url)
        
        if cleaned_text:
            truncated = False
            truncation_message = None
        else:
            # Парсим сайт (всегда при первом входе или если кэш пуст)
            html = await self.fetch_html(url)
            if not html:
                raise ValueError("Не удалось скачать HTML")

            cleaned_text, truncated, truncation_message = self.html_to_text(html)
            if not cleaned_text.strip():
                raise ValueError("Не удалось извлечь текст со страницы")
            
            # Сохраняем очищенный текст в кэш (если доступен)
            # Используем only_if_not_exists для защиты от race condition:
            # если другой пользователь уже сохранил этот URL, не перезаписываем
            if CACHE_AVAILABLE:
                await cache_service.set_cleaned_text(url, cleaned_text, only_if_not_exists=True)

        # Проверяем кэш промежуточных шагов (только если разрешено использование кэша)
        intermediate = None
        if use_cached and CACHE_AVAILABLE:
            intermediate = await cache_service.get_intermediate_steps(url)
        
        if intermediate:
            steps = [item.get("step", "") for item in intermediate]
        else:
            steps = await self.get_steps(cleaned_text)
            if not steps:
                raise ValueError("Модель не вернула список шагов для анализа")

            # 🚀 ПАРАЛЛЕЛЬНОЕ ВЫПОЛНЕНИЕ ШАГОВ для ускорения в 3-5 раз!
            print(f"[PARALLEL] Starting {len(steps)} steps in parallel...")
            tasks = [self.run_step_safe(step, cleaned_text) for step in steps]
            results = await asyncio.gather(*tasks)
            
            # Собираем результаты (все уже Dict, ошибки обработаны в run_step_safe)
            intermediate = []
            for step, res in zip(steps, results):
                if "error" in res:
                    intermediate.append({"step": step, "error": res["error"]})
                    print(f"[PARALLEL] Step failed: {step[:50]}...")
                else:
                    intermediate.append({"step": step, "result": res})
                    print(f"[PARALLEL] Step completed: {step[:50]}...")
            
            print(f"[PARALLEL] All {len(steps)} steps completed!")
            
            # Сохраняем промежуточные шаги в кэш (если доступен)
            # Используем only_if_not_exists для защиты от race condition:
            # если другой пользователь уже сохранил этот URL, не перезаписываем
            if CACHE_AVAILABLE:
                await cache_service.set_intermediate_steps(url, intermediate, only_if_not_exists=True)

        final = await self.finalize(intermediate, cleaned_text, style, occasion)

        result = {
            "url": url,
            "style": style,
            "occasion": occasion,
            "steps": steps,
            "intermediate_results": intermediate,
            "final": final,
            "truncated": truncated,
            "truncation_message": truncation_message,
            "cached": False  # Флаг что не использовали кэш
        }
        
        # Сохраняем результат в кэш (если доступен)
        if CACHE_AVAILABLE:
            await cache_service.set_analysis_result(url, style, occasion, result)
        return result
