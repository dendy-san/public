# Скрипт для создания тестового сеанса в Docker контейнере (PowerShell)
# Использование: .\create_session.ps1 [email]

param(
    [string]$Email = "test@example.com"
)

Write-Host "Создание тестового сеанса для $Email..." -ForegroundColor Cyan

docker-compose exec backend python -c @"
from app.models.database import init_db, SessionLocal
from app.services.session_service import session_service
import os
os.environ['DB_PATH'] = '/app/data/sessions.db'
init_db()
db = SessionLocal()
try:
    session = session_service.create_session(db, '$Email')
    print(f'[OK] Сеанс создан: {session.email}')
    styles = session_service.get_available_styles(session)
    available = len([s for s in styles.values() if s == 1])
    print(f'[OK] Доступно стилей: {available}/9')
except Exception as e:
    print(f'[ERROR] Ошибка: {e}')
finally:
    db.close()
"@

Write-Host "Готово! Теперь можно использовать email: $Email" -ForegroundColor Green

