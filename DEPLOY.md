# Инструкция по деплою на VPS

## Подготовка

### 1. Инициализация Git репозитория (локально)

```bash
# Инициализация репозитория
git init
git add .
git commit -m "Initial commit"

# Создание репозитория на GitHub/GitLab (опционально)
# git remote add origin <URL_РЕПОЗИТОРИЯ>
# git push -u origin main
```

### 2. Настройка VPS

#### Установка необходимых компонентов:

```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Установка Docker Compose
sudo apt install docker-compose -y

# Добавление пользователя в группу docker
sudo usermod -aG docker $USER
newgrp docker
```

#### Клонирование репозитория на VPS:

```bash
# Создание директории для проекта
mkdir -p ~/projects
cd ~/projects

# Клонирование репозитория (если используете Git)
git clone <URL_РЕПОЗИТОРИЯ> public_gen
cd public_gen/public

# Или создание директории и копирование файлов вручную
mkdir -p ~/projects/public_gen/public
# Скопируйте все файлы проекта в эту директорию
```

#### Настройка .env файла:

```bash
# Создание .env файла на VPS
nano .env

# Добавьте необходимые переменные:
# W=60
# Price=1000
# ShopID=your_shop_id
# Ykassa_API=your_api_key
# OPENAI_API_KEY=your_openai_key
# и т.д.
```

## Деплой

### Вариант 1: Использование скрипта деплоя

```bash
# Сделать скрипт исполняемым
chmod +x deploy.sh

# Запуск деплоя
./deploy.sh
```

### Вариант 2: Ручной деплой

```bash
# 1. Остановка и удаление старых контейнеров
docker-compose down --remove-orphans

# 2. Удаление старых образов (опционально)
docker-compose down --rmi local --remove-orphans

# 3. Обновление кода (если используется Git)
git pull origin main

# 4. Сборка новых образов
docker-compose build --no-cache

# 5. Запуск новых контейнеров
docker-compose up -d

# 6. Проверка статуса
docker-compose ps
```

## Обновление после изменений

### Локально:

```bash
# 1. Внести изменения в код
# 2. Закоммитить изменения
git add .
git commit -m "Описание изменений"
git push origin main
```

### На VPS:

```bash
# 1. Перейти в директорию проекта
cd ~/projects/public_gen/public

# 2. Обновить код из Git
git pull origin main

# 3. Запустить деплой
./deploy.sh
```

## Проверка работы

```bash
# Проверка статуса контейнеров
docker-compose ps

# Просмотр логов
docker-compose logs -f

# Просмотр логов конкретного сервиса
docker-compose logs -f backend
docker-compose logs -f frontend

# Проверка здоровья сервисов
curl http://localhost:8000/health
```

## Откат к предыдущей версии

```bash
# 1. Перейти в директорию проекта
cd ~/projects/public_gen/public

# 2. Откатить код к предыдущему коммиту
git log  # Найти нужный коммит
git checkout <HASH_КОММИТА>

# 3. Запустить деплой
./deploy.sh
```

## Полезные команды

```bash
# Остановка всех контейнеров
docker-compose stop

# Запуск контейнеров
docker-compose start

# Перезапуск контейнеров
docker-compose restart

# Просмотр использования ресурсов
docker stats

# Очистка неиспользуемых ресурсов
docker system prune -a

# Резервное копирование базы данных
docker exec public-backend sqlite3 /app/sessions.db .dump > backup.sql

# Восстановление базы данных
cat backup.sql | docker exec -i public-backend sqlite3 /app/sessions.db
```

## Решение проблем

### Контейнеры не запускаются:

```bash
# Проверить логи
docker-compose logs

# Проверить конфигурацию
docker-compose config

# Пересобрать образы
docker-compose build --no-cache
```

### Проблемы с портами:

```bash
# Проверить занятые порты
sudo netstat -tulpn | grep :8000
sudo netstat -tulpn | grep :3000

# Изменить порты в docker-compose.yml при необходимости
```

### Проблемы с правами:

```bash
# Проверить права на файлы
ls -la

# Изменить владельца
sudo chown -R $USER:$USER .
```

