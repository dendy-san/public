# Создание SSH ключа БЕЗ пароля (правильный способ)

Write-Host "🔑 Создание SSH ключа БЕЗ пароля..." -ForegroundColor Cyan
Write-Host ""

$keyPath = "C:\Users\I7 11700k\.ssh\github_actions_deploy_new"

# Удаление старого ключа, если есть
if (Test-Path $keyPath) {
    Remove-Item "$keyPath*" -Force -ErrorAction SilentlyContinue
}

# Создание ключа БЕЗ пароля (используем пустую строку)
Write-Host "Генерация ключа..." -ForegroundColor Yellow
$process = Start-Process -FilePath "ssh-keygen" -ArgumentList @(
    "-t", "ed25519",
    "-C", "github-actions-deploy",
    "-f", $keyPath,
    "-N", '""'
) -Wait -NoNewWindow -PassThru

if ($process.ExitCode -eq 0) {
    Write-Host "✅ Ключ создан успешно!" -ForegroundColor Green
    Write-Host ""
    
    Write-Host "📋 НОВЫЙ публичный ключ (добавьте на VPS):" -ForegroundColor Yellow
    Write-Host ("=" * 80) -ForegroundColor Gray
    $publicKey = Get-Content "$keyPath.pub"
    Write-Host $publicKey -ForegroundColor White
    Write-Host ("=" * 80) -ForegroundColor Gray
    Write-Host ""
    
    Write-Host "💡 Теперь:" -ForegroundColor Cyan
    Write-Host "1. Добавьте этот ключ на VPS (замените старый)" -ForegroundColor White
    Write-Host "2. Проверьте подключение" -ForegroundColor White
    Write-Host "3. Если работает - замените старый ключ новым" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host "❌ Ошибка при создании ключа" -ForegroundColor Red
}

Write-Host ""

