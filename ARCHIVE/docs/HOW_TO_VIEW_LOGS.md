# 📋 Как посмотреть логи

## 1. Логи в браузере (консоль разработчика)

Это **самый важный** способ для отладки frontend!

### Шаги:

1. **Откройте приложение в браузере:**
   - Перейдите на `http://localhost:3000`

2. **Откройте консоль разработчика:**
   
   **Способ 1 (самый быстрый):**
   - Нажмите клавишу **`F12`** на клавиатуре
   
   **Способ 2:**
   - Нажмите **`Ctrl+Shift+I`** (Windows/Linux)
   - Или **`Cmd+Option+I`** (Mac)
   
   **Способ 3 (через меню):**
   - **Chrome/Edge:** Правый клик → "Просмотреть код" или "Inspect"
   - **Firefox:** Правый клик → "Исследовать элемент" или "Inspect Element"

3. **Перейдите на вкладку "Console":**
   - В открывшемся окне разработчика найдите вкладку **"Console"** (Консоль)
   - Если не видите вкладки, нажмите на иконку `>>` или `⋮` для показа всех вкладок

4. **Войдите в приложение:**
   - Введите email: `test@example.com`
   - Нажмите "Проверить сеанс"

5. **Проверьте логи:**
   - В консоли появятся сообщения с префиксом `[DEBUG]`
   - Ищите строки:
     - `[DEBUG] handleSessionValid called with:`
     - `[DEBUG] Directly setting URL and INFO from sessionData:`
     - `[DEBUG SiteAnalyzer] Props received:`

### Что искать в логах:

```javascript
[DEBUG] handleSessionValid called with: {
  email: "test@example.com",
  sessionData: {...},
  url: "https://www.searest.su/",  // ← Должен быть заполнен
  info: "Новый год"                 // ← Должен быть заполнен
}

[DEBUG] Directly setting URL and INFO from sessionData: {
  urlValue: "https://www.searest.su/",
  infoValue: "Новый год",
  urlLength: 23,
  infoLength: 9
}

[DEBUG SiteAnalyzer] Props received: {
  url: "https://www.searest.su/",
  occasion: "Новый год",
  urlLocked: true,      // ← Должно быть true
  occasionLocked: true  // ← Должно быть true
}
```

---

## 2. Логи Backend (Docker)

### Просмотр логов backend:

```bash
# Последние 50 строк
docker-compose logs backend --tail 50

# Все логи
docker-compose logs backend

# Логи в реальном времени (следить за новыми)
docker-compose logs -f backend
```

### Просмотр логов frontend:

```bash
docker-compose logs frontend --tail 30
```

### Просмотр всех сервисов:

```bash
docker-compose logs --tail 50
```

---

## 3. Проверка API напрямую

### Проверка сеанса через curl:

```bash
# Windows PowerShell
curl "http://localhost:8000/session/check/test%40example.com"

# Или через Python
python -c "import requests; import json; r = requests.get('http://localhost:8000/session/check/test@example.com'); print(json.dumps(r.json(), indent=2, ensure_ascii=False))"
```

### Ожидаемый ответ:

```json
{
  "has_session": true,
  "is_active": true,
  "email": "test@example.com",
  "url": "https://www.searest.su/",
  "info": "Новый год",
  "available_styles": {...},
  "has_unused_styles": true,
  "message": "Сеанс активен."
}
```

---

## 4. Проверка базы данных

### Просмотр всех сеансов в БД:

```bash
docker-compose exec backend python -c "from app.models.database import init_db, SessionLocal, ClientSession; import os; os.environ['DB_PATH'] = '/app/data/sessions.db'; init_db(); db = SessionLocal(); sessions = db.query(ClientSession).all(); print('All sessions:'); [print(f'Email: {s.email}, URL: {repr(s.url)}, INFO: {repr(s.info)}') for s in sessions]; db.close()"
```

---

## 🎯 Быстрая проверка проблемы

1. **Откройте консоль браузера (F12)**
2. **Войдите с email `test@example.com`**
3. **Скопируйте все логи с `[DEBUG]`**
4. **Пришлите их мне** - я смогу точно определить проблему!

---

## 💡 Полезные советы

- **Очистка консоли:** Нажмите иконку 🚫 или `Ctrl+L`
- **Фильтрация логов:** Введите `DEBUG` в поле поиска консоли
- **Сохранение логов:** Правый клик на логах → "Save as..."
- **Экспорт Network запросов:** Вкладка Network → правый клик → "Save all as HAR"

