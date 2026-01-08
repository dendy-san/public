# Скрипт для проверки SSH подключения с приватным ключом

Write-Host "🧪 Проверка SSH подключения к VPS..." -ForegroundColor Cyan
Write-Host ""

$privateKeyPath = "$env:USERPROFILE\.ssh\github_actions_deploy"
$VPS_HOST = "5.101.4.137"
$VPS_USER = "root"

if (-not (Test-Path $privateKeyPath)) {
    Write-Host "❌ Приватный SSH ключ не найден: $privateKeyPath" -ForegroundColor Red
    exit 1
}

Write-Host "🔑 Используется ключ: $privateKeyPath" -ForegroundColor Gray
Write-Host "🔗 Подключение к: $VPS_USER@$VPS_HOST" -ForegroundColor Gray
Write-Host ""

Write-Host "⏳ Попытка подключения..." -ForegroundColor Yellow
Write-Host ""

try {
    $result = ssh -i $privateKeyPath -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o BatchMode=yes $VPS_USER@$VPS_HOST "echo '✅ SSH подключение работает!' && whoami && pwd && echo '✅ Все проверки пройдены!'" 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host $result -ForegroundColor Green
        Write-Host ""
        Write-Host "🎉 УСПЕХ! Подключение работает без пароля!" -ForegroundColor Green
        Write-Host ""
        Write-Host "✅ GitHub Actions сможет подключаться к VPS" -ForegroundColor Green
        Write-Host ""
        Write-Host "📋 Следующий шаг: Добавьте секреты в GitHub" -ForegroundColor Cyan
        Write-Host "   https://github.com/dendy-san/public/settings/secrets/actions" -ForegroundColor Gray
    } else {
        Write-Host $result -ForegroundColor Red
        Write-Host ""
        Write-Host "❌ Ошибка подключения" -ForegroundColor Red
        Write-Host ""
        Write-Host "💡 Возможные причины:" -ForegroundColor Yellow
        Write-Host "   1. Ключ не добавлен в authorized_keys на VPS" -ForegroundColor White
        Write-Host "   2. Неправильные права доступа на VPS (~/.ssh должен быть 700, authorized_keys - 600)" -ForegroundColor White
        Write-Host "   3. Ключ добавлен неправильно (с переносами строк или лишними символами)" -ForegroundColor White
        Write-Host ""
        Write-Host "📋 Проверьте на VPS:" -ForegroundColor Cyan
        Write-Host "   ssh $VPS_USER@$VPS_HOST" -ForegroundColor Gray
        Write-Host "   cat ~/.ssh/authorized_keys | grep github-actions-deploy" -ForegroundColor Gray
        Write-Host "   ls -la ~/.ssh/authorized_keys" -ForegroundColor Gray
    }
} catch {
    Write-Host "❌ Ошибка: $_" -ForegroundColor Red
}

Write-Host ""

