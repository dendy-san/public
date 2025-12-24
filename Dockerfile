# Backend Dockerfile для проекта Public (Production)
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

# Открытие порта
EXPOSE 8000

# Запуск приложения через Gunicorn для production
CMD ["gunicorn", "app.main:app", "-c", "gunicorn.conf.py"]




