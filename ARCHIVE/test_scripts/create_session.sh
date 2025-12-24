#!/bin/bash
# Скрипт для создания тестового сеанса в Docker контейнере
# Использование: ./create_session.sh [email]

EMAIL=${1:-"test@example.com"}

echo "Создание тестового сеанса для $EMAIL..."

docker-compose exec backend python -c "
from app.models.database import init_db, SessionLocal
from app.services.session_service import session_service
import os
os.environ['DB_PATH'] = '/app/data/sessions.db'
init_db()
db = SessionLocal()
try:
    session = session_service.create_session(db, '$EMAIL')
    print(f'[OK] Сеанс создан: {session.email}')
    styles = session_service.get_available_styles(session)
    available = len([s for s in styles.values() if s == 1])
    print(f'[OK] Доступно стилей: {available}/9')
except Exception as e:
    print(f'[ERROR] Ошибка: {e}')
finally:
    db.close()
"

echo "Готово! Теперь можно использовать email: $EMAIL"

