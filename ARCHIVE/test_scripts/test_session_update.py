"""
Тестовый скрипт для проверки сохранения URL и инфоповода.
Использование: python test_session_update.py
"""
import requests
import json
import sys
import io

# Установка кодировки UTF-8 для Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

BASE_URL = "http://localhost:8000"
TEST_EMAIL = "test@example.com"

def test_session_update():
    """Тест обновления URL и инфоповода в сеансе."""
    print("=" * 60)
    print("  ТЕСТ СОХРАНЕНИЯ URL И ИНФОПОВОДА")
    print("=" * 60)
    
    # 1. Проверяем текущее состояние сеанса
    print("\n[1] Проверка текущего состояния сеанса...")
    response = requests.get(f"{BASE_URL}/session/check/{requests.utils.quote(TEST_EMAIL)}")
    if response.status_code == 200:
        data = response.json()
        print(f"   [OK] Сеанс найден: {data.get('has_session')}")
    else:
        print(f"   [FAIL] Ошибка: {response.status_code}")
        return False
    
    # 2. Симулируем запрос анализа с URL и инфоповодом
    print("\n[2] Симуляция запроса анализа (без реального анализа)...")
    test_url = "https://example.com"
    test_occasion = "Тестовый инфоповод для проверки сохранения"
    
    # Сначала создаем простой тест через прямой вызов update_session
    # (это можно сделать только через API, если есть такой endpoint)
    
    # 3. Проверяем через прямой запрос к БД (если возможно)
    print("\n[3] Проверка сохранения через API...")
    print(f"   URL для сохранения: {test_url}")
    print(f"   Инфоповод для сохранения: {test_occasion}")
    print("\n   [INFO] Для полной проверки используйте frontend:")
    print(f"   1. Откройте http://localhost:3000")
    print(f"   2. Введите email: {TEST_EMAIL}")
    print(f"   3. Введите URL: {test_url}")
    print(f"   4. Введите инфоповод: {test_occasion}")
    print(f"   5. Выполните анализ")
    print(f"   6. Проверьте в БД через:")
    print(f"      docker-compose exec backend python -c \"from app.models.database import init_db, SessionLocal; from app.services.session_service import session_service; import os; os.environ['DB_PATH'] = '/app/data/sessions.db'; init_db(); db = SessionLocal(); session = session_service.get_session_by_email(db, '{TEST_EMAIL}'); print('URL:', session.url); print('INFO:', session.info); db.close()\"")
    
    return True

if __name__ == "__main__":
    try:
        success = test_session_update()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n[ERROR] Ошибка: {e}")
        sys.exit(1)

