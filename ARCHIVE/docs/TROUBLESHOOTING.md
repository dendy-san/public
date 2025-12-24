# 🔧 УСТРАНЕНИЕ ПРОБЛЕМ

## Проблема: 404 при проверке сеанса

### Симптомы:
- Frontend показывает ошибку: "Failed to load resource: the server responded with a status of 404"
- Сеанс не находится даже с тестовым email

### Решение:

#### 1. Проверьте, что backend запущен:
```bash
docker-compose ps
```

Должны быть запущены:
- ✅ `public-backend` (может быть unhealthy, но это нормально)
- ✅ `public-redis` (healthy)
- ✅ `public-frontend` (healthy)

#### 2. Проверьте, что сеанс создан в контейнере:

**Важно:** Сеанс нужно создавать в контейнере backend, так как БД находится там!

```bash
# Windows PowerShell
.\create_session.ps1 test@example.com

# Linux/Mac
./create_session.sh test@example.com

# Или напрямую
docker-compose exec backend python -c "from app.models.database import init_db, SessionLocal; from app.services.session_service import session_service; import os; os.environ['DB_PATH'] = '/app/data/sessions.db'; init_db(); db = SessionLocal(); session = session_service.create_session(db, 'test@example.com'); print('Сеанс создан:', session.email); db.close()"
```

#### 3. Проверьте endpoint напрямую:

```bash
curl "http://localhost:8000/session/check/test%40example.com"
```

Должен вернуть JSON с `has_session: true`

#### 4. Проверьте логи backend:

```bash
docker-compose logs backend --tail 50
```

Ищите запросы к `/session/check/` - они должны возвращать 200, а не 404.

#### 5. Проверьте консоль браузера:

Откройте DevTools (F12) → Console и Network. Проверьте:
- Какой URL запрашивается
- Какой статус возвращается
- Есть ли ошибки CORS

### Частые причины 404:

1. **Сеанс не создан в контейнере** - создайте сеанс через скрипт выше
2. **Backend не запущен** - запустите `docker-compose up -d`
3. **Неправильный URL** - проверьте, что frontend использует `http://localhost:8000`
4. **Проблема с кодировкой email** - frontend использует `encodeURIComponent`, это правильно

### Проверка работы:

После создания сеанса проверьте:

```bash
# Проверка через curl
curl "http://localhost:8000/session/check/test%40example.com"

# Должен вернуть:
# {"has_session":true,"is_active":true,"email":"test@example.com",...}
```

Если всё работает через curl, но не работает в браузере:
- Проверьте консоль браузера на ошибки
- Проверьте Network tab в DevTools
- Убедитесь, что backend доступен на `http://localhost:8000`

---

## Другие проблемы

### Backend помечен как unhealthy

Это нормально, если backend работает. Healthcheck может не проходить из-за отсутствия curl в контейнере или других причин. Главное - проверить, что API отвечает:

```bash
curl http://localhost:8000/health
```

### База данных не сохраняется

Убедитесь, что volume настроен в `docker-compose.yml`:

```yaml
volumes:
  - ./data:/app/data
```

И переменная окружения:
```yaml
environment:
  - DB_PATH=/app/data/sessions.db
```

---

**Если проблема не решена, проверьте логи:**
```bash
docker-compose logs backend --tail 100
docker-compose logs frontend --tail 100
```

