# Скрипт деплоя на VPS (PowerShell версия для Windows)
# Удаляет старые контейнеры и разворачивает новую версию

$ErrorActionPreference = "Stop"

Write-Host "🚀 Начало деплоя..." -ForegroundColor Cyan

# 1. Остановка и удаление старых контейнеров
Write-Host "📦 Остановка старых контейнеров..." -ForegroundColor Yellow
docker-compose down --remove-orphans

# 2. Удаление старых образов (опционально)
Write-Host "🗑️  Удаление старых образов..." -ForegroundColor Yellow
docker-compose down --rmi local --remove-orphans

# 3. Очистка неиспользуемых образов (опционально)
Write-Host "🧹 Очистка неиспользуемых образов..." -ForegroundColor Yellow
docker image prune -f

# 4. Обновление кода из Git (если используется Git)
if (Test-Path ".git") {
    Write-Host "📥 Обновление кода из Git..." -ForegroundColor Yellow
    try {
        git pull origin main
    } catch {
        try {
            git pull origin master
        } catch {
            Write-Host "⚠️  Не удалось обновить из Git" -ForegroundColor Yellow
        }
    }
}

# 5. Сборка новых образов
Write-Host "🔨 Сборка новых образов..." -ForegroundColor Yellow
docker-compose build --no-cache

# 6. Запуск новых контейнеров
Write-Host "▶️  Запуск новых контейнеров..." -ForegroundColor Yellow
docker-compose up -d

# 7. Ожидание готовности сервисов
Write-Host "⏳ Ожидание готовности сервисов..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# 8. Проверка статуса
Write-Host "📊 Статус контейнеров:" -ForegroundColor Yellow
docker-compose ps

Write-Host "✅ Деплой завершен успешно!" -ForegroundColor Green
Write-Host "🌐 Frontend: http://localhost:3000" -ForegroundColor Green
Write-Host "🔧 Backend: http://localhost:8000" -ForegroundColor Green
Write-Host "📊 Redis Commander: http://localhost:8081" -ForegroundColor Green

