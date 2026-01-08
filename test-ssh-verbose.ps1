# Детальная проверка SSH подключения с подробным выводом

Write-Host "🔍 Детальная диагностика SSH подключения..." -ForegroundColor Cyan
Write-Host ""

$privateKeyPath = "$env:USERPROFILE\.ssh\github_actions_deploy"
$VPS_HOST = "5.101.4.137"
$VPS_USER = "root"

if (-not (Test-Path $privateKeyPath)) {
    Write-Host "❌ Приватный SSH ключ не найден: $privateKeyPath" -ForegroundColor Red
    exit 1
}

Write-Host "🔑 Ключ: $privateKeyPath" -ForegroundColor Gray
Write-Host "🔗 VPS: $VPS_USER@$VPS_HOST" -ForegroundColor Gray
Write-Host ""

# Проверка формата приватного ключа
Write-Host "📋 Проверка формата приватного ключа..." -ForegroundColor Yellow
$keyContent = Get-Content $privateKeyPath -Raw
if ($keyContent -match "BEGIN.*PRIVATE KEY" -and $keyContent -match "END.*PRIVATE KEY") {
    Write-Host "   ✅ Формат ключа правильный" -ForegroundColor Green
} else {
    Write-Host "   ❌ Формат ключа неправильный!" -ForegroundColor Red
}

# Проверка прав на приватный ключ
$keyInfo = Get-Item $privateKeyPath
Write-Host "   Права файла: $($keyInfo.Mode)" -ForegroundColor Gray
Write-Host ""

# Попытка подключения с подробным выводом
Write-Host "🔧 Попытка подключения с подробным выводом (ssh -v)..." -ForegroundColor Yellow
Write-Host ""

$sshArgs = @(
    "-v",  # Подробный вывод
    "-i", $privateKeyPath,
    "-o", "StrictHostKeyChecking=no",
    "-o", "ConnectTimeout=10",
    "-o", "BatchMode=yes",
    "${VPS_USER}@${VPS_HOST}",
    "echo '✅ Подключение работает!'"
)

Write-Host "Выполняется команда:" -ForegroundColor Gray
Write-Host "ssh $($sshArgs -join ' ')" -ForegroundColor DarkGray
Write-Host ""

ssh @sshArgs 2>&1 | ForEach-Object {
    if ($_ -match "debug1|Permission denied|Authentication failed|publickey") {
        Write-Host $_ -ForegroundColor Yellow
    } elseif ($_ -match "✅") {
        Write-Host $_ -ForegroundColor Green
    } else {
        Write-Host $_ -ForegroundColor Gray
    }
}

Write-Host ""

