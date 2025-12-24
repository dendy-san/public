"""
Скрипт для проверки всех сеансов в БД.
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

# Список возможных email для проверки
test_emails = [
    "test@example.com",
    "admin@example.com",
    "user@example.com"
]

print("=" * 60)
print("  ПРОВЕРКА ВСЕХ СЕАНСОВ В БД")
print("=" * 60)

for email in test_emails:
    print(f"\n[Проверка] {email}")
    try:
        response = requests.get(f"{BASE_URL}/session/check/{requests.utils.quote(email)}")
        if response.status_code == 200:
            data = response.json()
            if data.get('has_session') and data.get('is_active'):
                print(f"  [OK] Сеанс активен")
                print(f"  URL: {repr(data.get('url'))}")
                print(f"  INFO: {repr(data.get('info'))}")
            else:
                print(f"  [INFO] Сеанс не активен или не найден")
        else:
            print(f"  [INFO] Сеанс не найден (статус: {response.status_code})")
    except Exception as e:
        print(f"  [ERROR] Ошибка: {e}")

print("\n" + "=" * 60)
print("  Для проверки конкретного email используйте:")
print("  curl \"http://localhost:8000/session/check/YOUR_EMAIL\"")
print("=" * 60)

