# Создание нового SSH ключа без пароля для GitHub Actions

Write-Host "🔑 Создание нового SSH ключа БЕЗ пароля..." -ForegroundColor Cyan
Write-Host ""

$oldKeyPath = "$env:USERPROFILE\.ssh\github_actions_deploy"
$newKeyPath = "$env:USERPROFILE\.ssh\github_actions_deploy_new"

# Создание резервной копии старого ключа
if (Test-Path $oldKeyPath) {
    Write-Host "📦 Создание резервной копии старого ключа..." -ForegroundColor Yellow
    Copy-Item $oldKeyPath "$oldKeyPath.backup" -ErrorAction SilentlyContinue
    Copy-Item "$oldKeyPath.pub" "$oldKeyPath.pub.backup" -ErrorAction SilentlyContinue
    Write-Host "✅ Резервная копия создана" -ForegroundColor Green
    Write-Host ""
}

# Генерация нового ключа
Write-Host "🔨 Генерация нового SSH ключа..." -ForegroundColor Cyan
ssh-keygen -t ed25519 -C "github-actions-deploy" -f $newKeyPath -N '""' -q

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Новый SSH ключ успешно создан!" -ForegroundColor Green
    Write-Host ""
    
    # Показываем публичный ключ
    Write-Host "📋 НОВЫЙ публичный ключ (добавьте его на VPS):" -ForegroundColor Yellow
    Write-Host ("=" * 80) -ForegroundColor Gray
    $publicKey = Get-Content "$newKeyPath.pub"
    Write-Host $publicKey -ForegroundColor White
    Write-Host ("=" * 80) -ForegroundColor Gray
    Write-Host ""
    
    Write-Host "📋 НОВЫЙ приватный ключ (для GitHub Secrets):" -ForegroundColor Yellow
    Write-Host ("=" * 80) -ForegroundColor Gray
    $privateKey = Get-Content $newKeyPath -Raw
    Write-Host $privateKey -ForegroundColor White
    Write-Host ("=" * 80) -ForegroundColor Gray
    Write-Host ""
    
    Write-Host "📝 СЛЕДУЮЩИЕ ШАГИ:" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "1. Подключитесь к VPS:" -ForegroundColor White
    Write-Host "   ssh root@5.101.4.137" -ForegroundColor Gray
    Write-Host ""
    Write-Host "2. На VPS замените ключ:" -ForegroundColor White
    Write-Host "   echo '$publicKey' > ~/.ssh/authorized_keys" -ForegroundColor Gray
    Write-Host "   chmod 600 ~/.ssh/authorized_keys" -ForegroundColor Gray
    Write-Host ""
    Write-Host "3. Выйдите из VPS (exit) и проверьте:" -ForegroundColor White
    Write-Host "   ssh -i `"$newKeyPath`" root@5.101.4.137 `"echo '✅ Работает!'`"" -ForegroundColor Gray
    Write-Host ""
    Write-Host "4. Если работает, замените старый ключ новым:" -ForegroundColor White
    Write-Host "   Move-Item $newKeyPath $oldKeyPath -Force" -ForegroundColor Gray
    Write-Host "   Move-Item `"$newKeyPath.pub`" `"$oldKeyPath.pub`" -Force" -ForegroundColor Gray
    Write-Host ""
} else {
    Write-Host "❌ Ошибка при создании ключа" -ForegroundColor Red
}

Write-Host ""

