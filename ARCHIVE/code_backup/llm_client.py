import json
import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from openai import OpenAI


# Инициализация переменных окружения из .env
load_dotenv()


class LLMClient:
    """
    Клиент для общения с LLM через совместимый с OpenAI API.
    
    ГИБРИДНЫЙ РЕЖИМ:
    - Поддерживает несколько провайдеров одновременно (GPT-4o + DeepSeek)
    - Можно задать основной и альтернативный клиент для разных задач
    - Авторизация через заголовок: "Authorization: Bearer <api_key>"
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: str = "deepseek-chat",
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        # Новые параметры для гибридного режима
        alt_base_url: Optional[str] = None,
        alt_api_key: Optional[str] = None,
        alt_model: Optional[str] = None,
    ) -> None:
        # Основной клиент (DeepSeek по умолчанию)
        self.base_url: str = base_url or os.getenv("BASE_URL", "").strip()
        if not self.base_url:
            raise ValueError(
                "BASE_URL не задан. Укажите base_url в конструкторе или переменную окружения BASE_URL."
            )

        self.api_key: str = (api_key or os.getenv("API_KEY") or "").strip()
        if not self.api_key:
            raise ValueError(
                "API ключ не задан. Передайте api_key в конструктор или установите API_KEY в окружении."
            )

        self.model: str = model
        self.system_prompt: Optional[str] = system_prompt
        self.max_tokens: int = max_tokens

        # Явно укажем заголовок Authorization
        default_headers = {"Authorization": f"Bearer {self.api_key}"}

        self.client: OpenAI = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            default_headers=default_headers,
        )

        # Альтернативный клиент (GPT-4o через ProxyAPI)
        self.alt_client: Optional[OpenAI] = None
        self.alt_model: Optional[str] = alt_model
        
        if alt_base_url or os.getenv("OPENAI_BASE_URL"):
            alt_url = alt_base_url or os.getenv("OPENAI_BASE_URL", "").strip()
            alt_key = alt_api_key or os.getenv("OPENAI_API_KEY", "").strip()
            
            if alt_url and alt_key:
                alt_headers = {"Authorization": f"Bearer {alt_key}"}
                self.alt_client = OpenAI(
                    base_url=alt_url,
                    api_key=alt_key,
                    default_headers=alt_headers,
                )
                self.alt_model = alt_model or "gpt-4o"
                print(f"[LLMClient] Hybrid mode: Primary={self.model}, Alternative={self.alt_model}")

    # --- Публичные методы настройки ---
    def set_system_prompt(self, system_prompt: Optional[str]) -> None:
        self.system_prompt = system_prompt

    def set_max_tokens(self, max_tokens: int) -> None:
        if max_tokens <= 0:
            raise ValueError("max_tokens должен быть положительным числом")
        self.max_tokens = max_tokens

    # --- Вспомогательные методы ---
    def _build_messages(
        self, system_prompt: Optional[str], user_prompt: str
    ) -> List[Dict[str, str]]:
        messages: List[Dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})
        return messages

    def _extract_text(self, completion: Any) -> str:
        try:
            return completion.choices[0].message.content or ""
        except Exception as exc:
            raise RuntimeError(f"Не удалось извлечь текст из ответа модели: {exc}")

    def _debug_log_messages(self, messages: List[Dict[str, str]]) -> None:
        try:
            preview: List[Dict[str, str]] = []
            for m in messages:
                content = (m.get("content") or "")
                # обрежем до 200 символов, чтобы не засорять логи
                preview.append({
                    "role": m.get("role", ""),
                    "content": content[:200]
                })
            print("[LLMClient.chat_json] messages:", json.dumps(preview, ensure_ascii=False))
        except Exception:
            pass

    # --- Основной функционал ---
    def chat(
        self,
        prompt: str,
        *,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.0,
        use_alt: bool = False,  # Новый параметр для выбора клиента
    ) -> str:
        """Простой запрос. Возвращает текстовый ответ."""
        # Выбор клиента и модели
        if use_alt and self.alt_client:
            client = self.alt_client
            effective_model = model or self.alt_model
        else:
            client = self.client
            effective_model = model or self.model
            
        effective_max_tokens = max_tokens if max_tokens is not None else self.max_tokens

        messages = self._build_messages(self.system_prompt, prompt)

        completion = client.chat.completions.create(
            model=effective_model,
            messages=messages,
            max_tokens=effective_max_tokens,
            temperature=temperature,
        )
        return self._extract_text(completion)

    def chat_with_system(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.0,
        use_alt: bool = False,  # Новый параметр для выбора клиента
    ) -> str:
        """Запрос с явным системным промптом. Возвращает текстовый ответ."""
        # Выбор клиента и модели
        if use_alt and self.alt_client:
            client = self.alt_client
            effective_model = model or self.alt_model
        else:
            client = self.client
            effective_model = model or self.model
            
        effective_max_tokens = max_tokens if max_tokens is not None else self.max_tokens

        messages = self._build_messages(system_prompt, user_prompt)

        completion = client.chat.completions.create(
            model=effective_model,
            messages=messages,
            max_tokens=effective_max_tokens,
            temperature=temperature,
        )
        return self._extract_text(completion)

    def chat_json(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.0,
        response_format_json: bool = True,
        use_alt: bool = False,  # Новый параметр для выбора клиента
    ) -> Dict[str, Any]:
        """
        Запрос, ожидающий структурированный JSON-ответ.
        Возвращает распарсенный словарь Python.
        """
        # Выбор клиента и модели
        if use_alt and self.alt_client:
            client = self.alt_client
            effective_model = model or self.alt_model
        else:
            client = self.client
            effective_model = model or self.model
            
        effective_max_tokens = max_tokens if max_tokens is not None else self.max_tokens

        messages = self._build_messages(system_prompt, user_prompt)
        # Логируем состав сообщений для диагностики
        self._debug_log_messages(messages)
        # Упрощенная логика без множественных retry
        kwargs = {
            "model": effective_model,
            "messages": messages,
            "max_tokens": effective_max_tokens,
            "temperature": temperature,
        }
        if response_format_json:
            kwargs["response_format"] = {"type": "json_object"}
        
        completion = client.chat.completions.create(**kwargs)

        content = self._extract_text(completion)
        # Прямая попытка
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # Fallback 1: вырезать блок кода ```json ... ``` или ``` ... ```
        text = content.strip()
        fences = ["```json", "```"]
        for fence in fences:
            if fence in text:
                try:
                    start = text.index(fence) + len(fence)
                    end = text.index("```", start)
                    candidate = text[start:end].strip()
                    return json.loads(candidate)
                except Exception:
                    continue

        # Fallback 2: взять подстроку между первой { и последней }
        if "{" in text and "}" in text:
            try:
                start = text.index("{")
                end = text.rindex("}") + 1
                candidate = text[start:end]
                return json.loads(candidate)
            except Exception:
                pass

        # Fallback 3: заменить одинарные кавычки на двойные, если это валидно
        try:
            normalized = text.replace("'", '"')
            return json.loads(normalized)
        except Exception as exc:
            raise ValueError(
                "Модель вернула невалидный JSON. Попробуйте уточнить инструкции или увеличить max_tokens."
            ) from exc


__all__ = ["LLMClient"]


if __name__ == "__main__":
    # Простейшие тестовые запуски методов
    try:
        client = LLMClient()
        client.set_system_prompt("Ты — краткий и полезный помощник.")
        client.set_max_tokens(300)

        print("[chat] ->", client.chat("What is JSON in one sentence?"))

        print(
            "[chat_with_system] ->",
            client.chat_with_system(
                "Answer in one sentence.",
                "What is async in Python?",
            ),
        )

        print(
            "[chat_json] ->",
            client.chat_json(
                "Response must be valid JSON with fields: title (str) and bullets (list[str]).",
                "Create a brief summary about Python exceptions (3-4 points).",
            ),
        )
    except Exception as e:
        print("Test run error:", e)


