# Автоматическое создание SSH ключа БЕЗ пароля

$keyPath = "$env:USERPROFILE\.ssh\github_actions_deploy_new"

# Удаление старого ключа
Remove-Item "$keyPath*" -Force -ErrorAction SilentlyContinue

Write-Host "🔧 Автоматическое создание SSH ключа БЕЗ пароля..." -ForegroundColor Cyan
Write-Host ""

# Создание ключа с автоматическим вводом пустых строк
$process = Start-Process -FilePath "ssh-keygen" -ArgumentList @(
    "-t", "ed25519",
    "-f", $keyPath,
    "-C", "github-actions-deploy"
) -NoNewWindow -Wait -PassThru -RedirectStandardInput ([System.IO.StreamWriter]::new([System.IO.MemoryStream]::new()))

# Альтернативный способ - через echo
Write-Host "Попытка через echo..." -ForegroundColor Yellow
$null = (echo ""; echo "") | ssh-keygen -t ed25519 -f $keyPath -C "github-actions-deploy" 2>&1

if (Test-Path "$keyPath.pub") {
    Write-Host "`n✅ Ключ создан!" -ForegroundColor Green
    Write-Host ""
    Write-Host "📋 Публичный ключ:" -ForegroundColor Yellow
    Get-Content "$keyPath.pub"
    Write-Host ""
} else {
    Write-Host "`n⚠️  Автоматическое создание не удалось" -ForegroundColor Yellow
    Write-Host "Создайте ключ вручную:" -ForegroundColor Cyan
    Write-Host "ssh-keygen -t ed25519 -f `"$keyPath`" -C `"github-actions-deploy`"" -ForegroundColor White
    Write-Host "Нажмите Enter дважды для пустого пароля" -ForegroundColor White
}

