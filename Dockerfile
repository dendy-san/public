# Backend Dockerfile для проекта Public (универсальный для dev/prod)
FROM python:3.10-slim

# Установка curl для healthcheck
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Установка рабочей директории
WORKDIR /app

# Копирование файла зависимостей
COPY requirements.txt .

# Установка зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода приложения и конфигурации
COPY app/ ./app/
COPY gunicorn.conf.py .
COPY start.sh .

# Делаем start.sh исполняемым
RUN chmod +x start.sh

# Открытие порта
EXPOSE 8000

# Использование скрипта для запуска (поддерживает dev/prod через ENVIRONMENT)
CMD ["./start.sh"]




