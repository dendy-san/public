# Простое создание SSH ключа БЕЗ пароля

$keyPath = "$env:USERPROFILE\.ssh\github_actions_deploy_new"

# Удаление старого ключа
Remove-Item "$keyPath*" -Force -ErrorAction SilentlyContinue

Write-Host "Создание ключа БЕЗ пароля..." -ForegroundColor Cyan

# Создание ключа через cmd с правильным синтаксисом
$keyFileEscaped = $keyPath -replace ' ', '` '
cmd /c "echo. | ssh-keygen -t ed25519 -C github-actions-deploy -f `"$keyPath`" -N `"`" -q"

if (Test-Path "$keyPath.pub") {
    Write-Host "`n✅ Ключ создан!`n" -ForegroundColor Green
    Write-Host "📋 Публичный ключ:" -ForegroundColor Yellow
    Get-Content "$keyPath.pub"
    Write-Host ""
    Write-Host "💡 Добавьте этот ключ на VPS" -ForegroundColor Cyan
} else {
    Write-Host "❌ Ошибка создания ключа" -ForegroundColor Red
}

