#!/bin/bash
# Скрипт запуска backend приложения с поддержкой dev/prod режимов

# Получаем режим из переменной окружения (по умолчанию prod)
ENVIRONMENT=${ENVIRONMENT:-prod}

if [ "$ENVIRONMENT" = "dev" ]; then
  echo "🚀 Запуск в режиме DEVELOPMENT (uvicorn с reload)"
  exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
else
  echo "🚀 Запуск в режиме PRODUCTION (gunicorn)"
  exec gunicorn app.main:app -c gunicorn.conf.py
fi









