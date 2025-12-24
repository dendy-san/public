"""
Тестовый скрипт для проверки загрузки URL и INFO из БД при входе.
Использование: python test_url_info_loading.py
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


def test_url_info_loading():
    """Тест загрузки URL и INFO из БД."""
    print("=" * 60)
    print("  ТЕСТ ЗАГРУЗКИ URL И ИНФОПОВОДА ИЗ БД")
    print("=" * 60)
    
    # 1. Проверяем текущее состояние сеанса
    print(f"\n[1] Проверка сеанса для {TEST_EMAIL}...")
    response = requests.get(f"{BASE_URL}/session/check/{requests.utils.quote(TEST_EMAIL)}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"   [OK] Сеанс найден: {data.get('has_session')}")
        print(f"   [OK] Сеанс активен: {data.get('is_active')}")
        print(f"   [INFO] URL из БД: {data.get('url') or '(пусто)'}")
        print(f"   [INFO] Инфоповод из БД: {data.get('info') or '(пусто)'}")
        
        # Проверяем, что поля присутствуют в ответе
        if 'url' in data and 'info' in data:
            print(f"   [OK] Поля url и info присутствуют в ответе API")
        else:
            print(f"   [FAIL] Поля url и info отсутствуют в ответе API")
            return False
    else:
        print(f"   [FAIL] Ошибка: {response.status_code}")
        print(f"   [INFO] Ответ: {response.text}")
        return False
    
    # 2. Если URL и INFO пустые, обновляем их через API
    if not data.get('url') and not data.get('info'):
        print(f"\n[2] URL и INFO пустые. Обновляем через API...")
        test_url = "https://example.com"
        test_info = "Тестовый инфоповод"
        
        update_response = requests.post(
            f"{BASE_URL}/session/update/{requests.utils.quote(TEST_EMAIL)}",
            json={"url": test_url, "info": test_info}
        )
        
        if update_response.status_code == 200:
            print(f"   [OK] URL и INFO обновлены")
            print(f"   [INFO] URL: {test_url}")
            print(f"   [INFO] Инфоповод: {test_info}")
        else:
            print(f"   [FAIL] Ошибка обновления: {update_response.status_code}")
            return False
        
        # 3. Проверяем, что данные сохранились
        print(f"\n[3] Проверка сохранения данных...")
        check_response = requests.get(f"{BASE_URL}/session/check/{requests.utils.quote(TEST_EMAIL)}")
        if check_response.status_code == 200:
            check_data = check_response.json()
            if check_data.get('url') == test_url and check_data.get('info') == test_info:
                print(f"   [OK] Данные успешно сохранены и загружаются из БД")
                print(f"   [INFO] URL из БД: {check_data.get('url')}")
                print(f"   [INFO] Инфоповод из БД: {check_data.get('info')}")
            else:
                print(f"   [FAIL] Данные не совпадают")
                print(f"   [INFO] Ожидалось URL: {test_url}, получено: {check_data.get('url')}")
                print(f"   [INFO] Ожидалось INFO: {test_info}, получено: {check_data.get('info')}")
                return False
        else:
            print(f"   [FAIL] Ошибка проверки: {check_response.status_code}")
            return False
    else:
        print(f"\n[2] URL и INFO уже заполнены в БД")
        print(f"   [INFO] URL: {data.get('url')}")
        print(f"   [INFO] Инфоповод: {data.get('info')}")
    
    print(f"\n[SUCCESS] Все тесты пройдены!")
    print(f"\n[INFO] Теперь проверьте в frontend:")
    print(f"   1. Откройте http://localhost:3000")
    print(f"   2. Введите email: {TEST_EMAIL}")
    print(f"   3. Проверьте, что поля URL и Инфоповод заполнены и заблокированы")
    
    return True


if __name__ == "__main__":
    try:
        success = test_url_info_loading()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n[WARNING] Тестирование прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n[ERROR] Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

