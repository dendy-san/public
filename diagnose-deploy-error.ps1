# Скрипт для диагностики ошибок деплоя
Write-Host "`n🔍 ДИАГНОСТИКА ОШИБОК ДЕПЛОЯ`n" -ForegroundColor Yellow

# Проверка SSH ключа
Write-Host "1️⃣ Проверка SSH ключа..." -ForegroundColor Cyan
$sshKeyPath = "$env:USERPROFILE\.ssh\github_actions_deploy"
if (Test-Path $sshKeyPath) {
    Write-Host "   ✅ SSH ключ найден: $sshKeyPath" -ForegroundColor Green
    $keySize = (Get-Item $sshKeyPath).Length
    Write-Host "   📏 Размер ключа: $keySize байт" -ForegroundColor Gray
} else {
    Write-Host "   ❌ SSH ключ не найден!" -ForegroundColor Red
    Write-Host "   💡 Выполните: .\setup-github-actions.ps1" -ForegroundColor Yellow
}

# Проверка подключения к VPS
Write-Host "`n2️⃣ Проверка SSH подключения к VPS..." -ForegroundColor Cyan
$VPS_HOST = "5.101.4.137"
$VPS_USER = "root"
$VPS_SSH_PORT = "22"

try {
    $result = ssh -i "$sshKeyPath" -o BatchMode=yes -o ConnectTimeout=10 -p $VPS_SSH_PORT "$VPS_USER@$VPS_HOST" "echo 'SSH OK'" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✅ SSH подключение работает" -ForegroundColor Green
    } else {
        Write-Host "   ❌ SSH подключение не работает" -ForegroundColor Red
        Write-Host "   Ошибка: $result" -ForegroundColor Red
    }
} catch {
    Write-Host "   ❌ Ошибка при проверке SSH: $_" -ForegroundColor Red
}

# Проверка проекта на VPS
Write-Host "`n3️⃣ Проверка проекта на VPS..." -ForegroundColor Cyan
try {
    $projectCheck = ssh -i "$sshKeyPath" -o BatchMode=yes -p $VPS_SSH_PORT "$VPS_USER@$VPS_HOST" "cd ~/public && pwd && ls -la docker-compose.yml 2>&1" 2>&1
    if ($projectCheck -match "docker-compose.yml") {
        Write-Host "   ✅ Проект найден на VPS" -ForegroundColor Green
    } else {
        Write-Host "   ⚠️  Проект может быть не настроен" -ForegroundColor Yellow
        Write-Host "   Результат: $projectCheck" -ForegroundColor Gray
    }
} catch {
    Write-Host "   ❌ Ошибка при проверке проекта: $_" -ForegroundColor Red
}

# Проверка Docker на VPS
Write-Host "`n4️⃣ Проверка Docker на VPS..." -ForegroundColor Cyan
try {
    $dockerCheck = ssh -i "$sshKeyPath" -o BatchMode=yes -p $VPS_SSH_PORT "$VPS_USER@$VPS_HOST" "docker --version && docker compose version" 2>&1
    if ($dockerCheck -match "version") {
        Write-Host "   ✅ Docker установлен" -ForegroundColor Green
        Write-Host "   $dockerCheck" -ForegroundColor Gray
    } else {
        Write-Host "   ❌ Docker не найден или не работает" -ForegroundColor Red
    }
} catch {
    Write-Host "   ❌ Ошибка при проверке Docker: $_" -ForegroundColor Red
}

# Проверка GitHub секретов (инструкции)
Write-Host "`n5️⃣ Проверка настроек GitHub секретов..." -ForegroundColor Cyan
Write-Host "   📋 Убедитесь, что добавлены секреты:" -ForegroundColor Yellow
Write-Host "      - VPS_HOST = 5.101.4.137" -ForegroundColor Gray
Write-Host "      - VPS_USER = root" -ForegroundColor Gray
Write-Host "      - VPS_SSH_KEY = (приватный ключ)" -ForegroundColor Gray
Write-Host "   🔗 Проверьте: https://github.com/dendy-san/public/settings/secrets/actions" -ForegroundColor Cyan

# Проверка логов GitHub Actions
Write-Host "`n6️⃣ Проверка логов деплоя..." -ForegroundColor Cyan
Write-Host "   🔗 Откройте логи здесь:" -ForegroundColor Yellow
Write-Host "   https://github.com/dendy-san/public/actions" -ForegroundColor Cyan
Write-Host "   📝 Найдите последний запуск и посмотрите, на каком шаге ошибка" -ForegroundColor Gray

Write-Host "`n✅ Диагностика завершена`n" -ForegroundColor Green
Write-Host "💡 Если проблема не решена, скопируйте текст ошибки из GitHub Actions" -ForegroundColor Yellow
