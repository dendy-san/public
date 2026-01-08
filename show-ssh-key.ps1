# Скрипт для отображения приватного SSH ключа
# Используется для копирования ключа в GitHub Secrets

$keyPath = "$env:USERPROFILE\.ssh\github_actions_deploy"

if (Test-Path $keyPath) {
    Write-Host "✅ Приватный SSH ключ найден!" -ForegroundColor Green
    Write-Host ""
    Write-Host "📄 Путь к ключу: $keyPath" -ForegroundColor Cyan
    Write-Host ""
    Write-Host ("=" * 80) -ForegroundColor Gray
    Write-Host "🔑 ПРИВАТНЫЙ SSH КЛЮЧ (скопируйте ВЕСЬ текст ниже):" -ForegroundColor Yellow
    Write-Host ("=" * 80) -ForegroundColor Gray
    Write-Host ""
    
    # Читаем и выводим приватный ключ
    $privateKey = Get-Content $keyPath -Raw
    Write-Host $privateKey -ForegroundColor White
    
    Write-Host ""
    Write-Host ("=" * 80) -ForegroundColor Gray
    Write-Host ""
    Write-Host "💡 ИНСТРУКЦИЯ:" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "1. Скопируйте весь ключ выше (включая строки -----BEGIN... и -----END...)" -ForegroundColor White
    Write-Host ""
    Write-Host "2. Перейдите в GitHub:" -ForegroundColor White
    Write-Host "   https://github.com/dendy-san/public/settings/secrets/actions" -ForegroundColor Gray
    Write-Host ""
    Write-Host "3. Нажмите: New repository secret" -ForegroundColor White
    Write-Host ""
    Write-Host "4. Заполните:" -ForegroundColor White
    Write-Host "   Name: VPS_SSH_KEY" -ForegroundColor Gray
    Write-Host "   Value: (вставьте скопированный ключ)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "5. Нажмите: Add secret" -ForegroundColor White
    Write-Host ""
    
    # Также показываем публичный ключ для справки
    $pubKeyPath = "$keyPath.pub"
    if (Test-Path $pubKeyPath) {
        Write-Host ("=" * 80) -ForegroundColor Gray
        Write-Host "📋 ПУБЛИЧНЫЙ SSH КЛЮЧ (для добавления на VPS):" -ForegroundColor Yellow
        Write-Host ("=" * 80) -ForegroundColor Gray
        Write-Host ""
        $publicKey = Get-Content $pubKeyPath
        Write-Host $publicKey -ForegroundColor White
        Write-Host ""
        Write-Host "💡 Добавьте этот публичный ключ на VPS в ~/.ssh/authorized_keys" -ForegroundColor Cyan
        Write-Host ""
    }
} else {
    Write-Host "❌ Приватный SSH ключ не найден!" -ForegroundColor Red
    Write-Host ""
    Write-Host "💡 Сначала создайте ключ, выполнив:" -ForegroundColor Yellow
    Write-Host "   .\setup-github-actions.ps1" -ForegroundColor White
    Write-Host ""
    Write-Host "Или создайте ключ вручную:" -ForegroundColor Yellow
    Write-Host "   ssh-keygen -t ed25519 -C `"github-actions-deploy`" -f `"$keyPath`" -N '""'" -ForegroundColor White
    Write-Host ""
}

