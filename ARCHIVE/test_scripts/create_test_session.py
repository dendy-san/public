"""
Скрипт для создания тестового сеанса в базе данных.
Использование: 
  - Локально: python create_test_session.py [email]
  - В Docker: docker-compose exec backend python create_test_session.py [email]
"""
import sys
import os
import io
from datetime import datetime

# Установка кодировки UTF-8 для Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Если запущено в Docker, используем путь из переменной окружения
if os.getenv('DB_PATH'):
    os.environ['DB_PATH'] = os.getenv('DB_PATH')

from app.models.database import init_db, SessionLocal
from app.services.session_service import session_service


def create_test_session(email: str = "test@example.com"):
    """Создание тестового сеанса."""
    print(f"[INFO] Создание тестового сеанса для {email}...")
    
    # Инициализация БД
    init_db()
    
    # Создание сеанса
    db = SessionLocal()
    try:
        session = session_service.create_session(db, email)
        print(f"[OK] Сеанс создан успешно!")
        print(f"\n[INFO] Информация о сеансе:")
        print(f"   Email: {session.email}")
        print(f"   Время создания: {session.dt}")
        print(f"   Активен: {session.is_active}")
        print(f"\n[INFO] Доступные стили (все 9):")
        styles = session_service.get_available_styles(session)
        for style, available in styles.items():
            status = "[OK] Доступен" if available == 1 else "[USED] Использован"
            print(f"   {status} - {style}")
        
        print(f"\n[INFO] Теперь вы можете:")
        print(f"   1. Открыть frontend: http://localhost:3000")
        print(f"   2. Ввести email: {email}")
        print(f"   3. Протестировать анализ сайта")
        
        return True
    except Exception as e:
        print(f"[ERROR] Ошибка при создании сеанса: {e}")
        return False
    finally:
        db.close()


if __name__ == "__main__":
    email = sys.argv[1] if len(sys.argv) > 1 else "test@example.com"
    success = create_test_session(email)
    sys.exit(0 if success else 1)

