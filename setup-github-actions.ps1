# Скрипт для автоматизации настройки GitHub Actions
# Выполняет все возможные автоматические шаги

Write-Host "🚀 Настройка GitHub Actions для автоматического деплоя" -ForegroundColor Cyan
Write-Host ""

# Шаг 1: Генерация SSH ключа
Write-Host "📝 Шаг 1: Генерация SSH ключа для GitHub Actions..." -ForegroundColor Yellow

$sshKeyPath = "$env:USERPROFILE\.ssh\github_actions_deploy"
$sshKeyPubPath = "$sshKeyPath.pub"

if (Test-Path $sshKeyPath) {
    Write-Host "⚠️  SSH ключ уже существует: $sshKeyPath" -ForegroundColor Yellow
    Write-Host "✅ Используем существующий ключ (для пересоздания удалите файл вручную)" -ForegroundColor Green
}

if (-not (Test-Path $sshKeyPath)) {
    Write-Host "🔑 Генерация нового SSH ключа..." -ForegroundColor Cyan
    ssh-keygen -t ed25519 -C "github-actions-deploy" -f $sshKeyPath -N '""'
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ SSH ключ успешно создан!" -ForegroundColor Green
    } else {
        Write-Host "❌ Ошибка при создании SSH ключа" -ForegroundColor Red
        exit 1
    }
}

# Шаг 2: Вывод публичного ключа
Write-Host ""
Write-Host "📋 Шаг 2: Публичный ключ (добавьте его на VPS):" -ForegroundColor Yellow
Write-Host "=" * 80 -ForegroundColor Gray
$publicKey = Get-Content $sshKeyPubPath
Write-Host $publicKey -ForegroundColor White
Write-Host "=" * 80 -ForegroundColor Gray
Write-Host ""
Write-Host "💡 Скопируйте публичный ключ выше и добавьте его на VPS:" -ForegroundColor Cyan
Write-Host "   ssh-copy-id -i $sshKeyPubPath user@your-vps-host" -ForegroundColor Gray
Write-Host ""

# Шаг 3: Вывод приватного ключа
Write-Host "📋 Шаг 3: Приватный ключ (добавьте как секрет VPS_SSH_KEY в GitHub):" -ForegroundColor Yellow
Write-Host "=" * 80 -ForegroundColor Gray
$privateKey = Get-Content $sshKeyPath -Raw
Write-Host $privateKey -ForegroundColor White
Write-Host "=" * 80 -ForegroundColor Gray
Write-Host ""
Write-Host "💡 Скопируйте приватный ключ выше и добавьте его в GitHub:" -ForegroundColor Cyan
Write-Host "   Settings → Secrets and variables → Actions → New repository secret" -ForegroundColor Gray
Write-Host "   Name: VPS_SSH_KEY" -ForegroundColor Gray
Write-Host "   Value: (вставьте приватный ключ выше)" -ForegroundColor Gray
Write-Host ""

# Шаг 4: Проверка наличия workflow файла
Write-Host "📝 Шаг 4: Проверка workflow файла..." -ForegroundColor Yellow
$workflowPath = ".github\workflows\deploy.yml"
if (Test-Path $workflowPath) {
    Write-Host "✅ Workflow файл найден: $workflowPath" -ForegroundColor Green
} else {
    Write-Host "❌ Workflow файл не найден: $workflowPath" -ForegroundColor Red
    exit 1
}

# Шаг 5: Создание файла с инструкциями по секретам
Write-Host ""
Write-Host "📝 Шаг 5: Создание файла с инструкциями по секретам..." -ForegroundColor Yellow

$secretsFile = "GITHUB_SECRETS_INSTRUCTIONS.txt"
$secretsContent = @"
========================================
ИНСТРУКЦИЯ ПО НАСТРОЙКЕ СЕКРЕТОВ В GITHUB
========================================

Перейдите в GitHub: Settings → Secrets and variables → Actions → New repository secret

ОБЯЗАТЕЛЬНЫЕ СЕКРЕТЫ:
====================

1. VPS_HOST
   Описание: IP адрес или домен вашего VPS
   Пример: 192.168.1.100 или example.com

2. VPS_USER
   Описание: Имя пользователя для SSH подключения
   Пример: root или deploy

3. VPS_SSH_KEY
   Описание: Приватный SSH ключ (полное содержимое файла)
   Пример: (см. вывод скрипта выше)
   ВАЖНО: Включите строки -----BEGIN OPENSSH PRIVATE KEY----- и -----END OPENSSH PRIVATE KEY-----

ОПЦИОНАЛЬНЫЕ СЕКРЕТЫ (со значениями по умолчанию):
===================================================

4. VPS_SSH_PORT
   Описание: SSH порт (по умолчанию: 22)
   Пример: 22 или 2222

5. VPS_PROJECT_PATH
   Описание: Путь к проекту на VPS (по умолчанию: ~/public)
   Пример: ~/public или /home/user/public

6. BACKEND_PORT
   Описание: Порт Backend API (по умолчанию: 8000)
   Пример: 8000

7. FRONTEND_PORT
   Описание: Порт Frontend (по умолчанию: 3000)
   Пример: 3000

8. ADMIN_FRONTEND_PORT
   Описание: Порт Admin Frontend (по умолчанию: 3001)
   Пример: 3001

9. TELEGRAM_BOT_TOKEN
   Описание: Токен Telegram бота для уведомлений (опционально)
   Пример: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz

10. TELEGRAM_CHAT_ID
    Описание: ID чата для Telegram уведомлений (опционально)
    Пример: 123456789

========================================
ПОСЛЕ НАСТРОЙКИ СЕКРЕТОВ:
========================================

1. Убедитесь, что проект склонирован на VPS:
   ssh user@vps-host
   cd ~/public  # или ваш путь из VPS_PROJECT_PATH
   git clone https://github.com/your-username/your-repo.git .

2. Создайте .env файл на VPS с необходимыми переменными:
   ENVIRONMENT=prod
   # ... остальные переменные

3. Протестируйте деплой:
   - Сделайте push в main ветку
   - Или используйте workflow_dispatch для ручного запуска

========================================
"@

Set-Content -Path $secretsFile -Value $secretsContent -Encoding UTF8
Write-Host "✅ Файл с инструкциями создан: $secretsFile" -ForegroundColor Green

# Шаг 6: Проверка Git репозитория
Write-Host ""
Write-Host "📝 Шаг 6: Проверка Git репозитория..." -ForegroundColor Yellow
$gitRemote = git remote get-url origin 2>$null
if ($gitRemote) {
    Write-Host "✅ Git remote найден: $gitRemote" -ForegroundColor Green
} else {
    Write-Host "⚠️  Git remote не найден. Убедитесь, что репозиторий подключен к GitHub" -ForegroundColor Yellow
}

# Итоговая информация
Write-Host ""
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "✅ НАСТРОЙКА ЗАВЕРШЕНА!" -ForegroundColor Green
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host ""
Write-Host "📋 СЛЕДУЮЩИЕ ШАГИ:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Добавьте публичный SSH ключ на VPS:" -ForegroundColor White
Write-Host "   ssh-copy-id -i $sshKeyPubPath user@your-vps-host" -ForegroundColor Gray
Write-Host ""
Write-Host "2. Добавьте секреты в GitHub (см. файл $secretsFile)" -ForegroundColor White
Write-Host ""
Write-Host "3. Убедитесь, что проект настроен на VPS" -ForegroundColor White
Write-Host ""
Write-Host "4. Сделайте тестовый push в main ветку для проверки деплоя" -ForegroundColor White
Write-Host ""
Write-Host "📖 Подробные инструкции: GITHUB_ACTIONS_SETUP.md" -ForegroundColor Cyan
Write-Host ""






