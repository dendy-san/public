# Создание SSH ключа БЕЗ пароля (правильный способ)

$keyPath = "$env:USERPROFILE\.ssh\github_actions_deploy_new"

# Удаление старого ключа
Remove-Item "$keyPath*" -Force -ErrorAction SilentlyContinue

Write-Host "🔧 Создание SSH ключа БЕЗ пароля..." -ForegroundColor Cyan
Write-Host ""

# Создание ключа с пустым паролем
# Используем -N "" для Windows PowerShell
ssh-keygen -t ed25519 -f $keyPath -N '""' -C "github-actions-deploy" -q

if (Test-Path "$keyPath.pub") {
    Write-Host "✅ Ключ создан успешно!" -ForegroundColor Green
    Write-Host ""
    
    $publicKey = Get-Content "$keyPath.pub"
    
    Write-Host "📋 ПУБЛИЧНЫЙ КЛЮЧ (добавьте на VPS):" -ForegroundColor Yellow
    Write-Host ("=" * 80) -ForegroundColor Gray
    Write-Host $publicKey -ForegroundColor White
    Write-Host ("=" * 80) -ForegroundColor Gray
    Write-Host ""
    
    Write-Host "📝 ИНСТРУКЦИЯ:" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "1. Подключитесь к VPS:" -ForegroundColor White
    Write-Host "   ssh root@5.101.4.137" -ForegroundColor Gray
    Write-Host ""
    Write-Host "2. На VPS выполните:" -ForegroundColor White
    Write-Host "   echo '$publicKey' > ~/.ssh/authorized_keys" -ForegroundColor Gray
    Write-Host "   chmod 600 ~/.ssh/authorized_keys" -ForegroundColor Gray
    Write-Host "   chmod 700 ~/.ssh" -ForegroundColor Gray
    Write-Host ""
    Write-Host "3. Выйдите из VPS (exit) и проверьте:" -ForegroundColor White
    Write-Host "   ssh -i `"$keyPath`" root@5.101.4.137 `"echo '✅ Работает!'`"" -ForegroundColor Gray
    Write-Host ""
} else {
    Write-Host "❌ Ошибка при создании ключа" -ForegroundColor Red
}

Write-Host ""

