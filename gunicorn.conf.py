# Конфигурация Gunicorn для оптимальной работы с 2 vCPU
import multiprocessing

# Количество воркеров = 2 * CPU + 1
workers = 2 * multiprocessing.cpu_count() + 1

# Класс воркера - UvicornWorker для async поддержки
worker_class = "uvicorn.workers.UvicornWorker"

# Количество потоков на воркер (для UvicornWorker обычно 1)
threads = 1

# Таймауты
timeout = 90  # Максимальное время обработки запроса
keepalive = 15  # Keep-alive соединения
graceful_timeout = 60  # Время на graceful shutdown

# Настройки производительности
max_requests = 1000  # Перезапуск воркера после N запросов
max_requests_jitter = 50  # Случайный разброс для избежания одновременного перезапуска
preload_app = True  # Предзагрузка приложения для экономии памяти

# Логирование
accesslog = "-"  # stdout
errorlog = "-"   # stderr
loglevel = "info"

# Биндинг
bind = "0.0.0.0:8000"

# Настройки для production
daemon = False
pidfile = "/tmp/gunicorn.pid"
user = None
group = None
tmp_upload_dir = None

# Настройки для работы с reverse proxy
forwarded_allow_ips = "*"
secure_scheme_headers = {
    'X-FORWARDED-PROTOCOL': 'ssl',
    'X-FORWARDED-PROTO': 'https',
    'X-FORWARDED-SSL': 'on'
}







