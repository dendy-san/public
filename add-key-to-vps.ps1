# Скрипт для добавления публичного SSH ключа на VPS
# Использует ssh-copy-id или ручное добавление через SSH

Write-Host "📤 Добавление публичного SSH ключа на VPS" -ForegroundColor Cyan
Write-Host ""

$pubKeyPath = "$env:USERPROFILE\.ssh\github_actions_deploy.pub"

if (-not (Test-Path $pubKeyPath)) {
    Write-Host "❌ Публичный SSH ключ не найден: $pubKeyPath" -ForegroundColor Red
    Write-Host "💡 Сначала выполните: .\setup-github-actions.ps1" -ForegroundColor Yellow
    exit 1
}

# Читаем публичный ключ
$publicKey = Get-Content $pubKeyPath

Write-Host "✅ Публичный ключ найден" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Публичный ключ:" -ForegroundColor Yellow
Write-Host ("=" * 80) -ForegroundColor Gray
Write-Host $publicKey -ForegroundColor White
Write-Host ("=" * 80) -ForegroundColor Gray
Write-Host ""

# Спрашиваем данные VPS
Write-Host "📝 Введите данные для подключения к VPS:" -ForegroundColor Yellow
Write-Host ""

$VPS_USER = Read-Host "VPS_USER (имя пользователя, например: root)"
$VPS_HOST = Read-Host "VPS_HOST (IP или домен, например: 192.168.1.100)"
$VPS_SSH_PORT = Read-Host "VPS_SSH_PORT (порт SSH, по умолчанию: 22)"
if ([string]::IsNullOrWhiteSpace($VPS_SSH_PORT)) {
    $VPS_SSH_PORT = "22"
}

Write-Host ""
Write-Host "🔧 Попытка автоматического добавления ключа..." -ForegroundColor Cyan
Write-Host ""

# Проверяем наличие ssh-copy-id
$sshCopyIdAvailable = $false
try {
    $null = Get-Command ssh-copy-id -ErrorAction Stop
    $sshCopyIdAvailable = $true
} catch {
    Write-Host "⚠️  ssh-copy-id не найден, используем ручной метод" -ForegroundColor Yellow
}

if ($sshCopyIdAvailable) {
    # Используем ssh-copy-id
    Write-Host "Используем ssh-copy-id..." -ForegroundColor Gray
    if ($VPS_SSH_PORT -eq "22") {
        ssh-copy-id -i $pubKeyPath "${VPS_USER}@${VPS_HOST}"
    } else {
        ssh-copy-id -i $pubKeyPath -p $VPS_SSH_PORT "${VPS_USER}@${VPS_HOST}"
    }
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "✅ Ключ успешно добавлен на VPS!" -ForegroundColor Green
        Write-Host ""
        Write-Host "🧪 Проверка подключения:" -ForegroundColor Cyan
        if ($VPS_SSH_PORT -eq "22") {
            ssh -i "$env:USERPROFILE\.ssh\github_actions_deploy" "${VPS_USER}@${VPS_HOST}" "echo '✅ SSH подключение работает!'"
        } else {
            ssh -i "$env:USERPROFILE\.ssh\github_actions_deploy" -p $VPS_SSH_PORT "${VPS_USER}@${VPS_HOST}" "echo '✅ SSH подключение работает!'"
        }
    } else {
        Write-Host ""
        Write-Host "❌ Ошибка при добавлении ключа автоматически" -ForegroundColor Red
        Write-Host "💡 Используйте ручной метод (см. ниже)" -ForegroundColor Yellow
    }
} else {
    Write-Host "⚠️  ssh-copy-id недоступен" -ForegroundColor Yellow
}

Write-Host ""
Write-Host ("=" * 80) -ForegroundColor Gray
Write-Host "📋 РУЧНОЙ МЕТОД (если автоматический не сработал):" -ForegroundColor Yellow
Write-Host ("=" * 80) -ForegroundColor Gray
Write-Host ""
Write-Host "1. Подключитесь к VPS:" -ForegroundColor White
if ($VPS_SSH_PORT -eq "22") {
    Write-Host "   ssh $VPS_USER@$VPS_HOST" -ForegroundColor Gray
} else {
    Write-Host "   ssh -p $VPS_SSH_PORT $VPS_USER@$VPS_HOST" -ForegroundColor Gray
}
Write-Host ""
Write-Host "2. На VPS выполните следующие команды:" -ForegroundColor White
Write-Host "   mkdir -p ~/.ssh" -ForegroundColor Gray
Write-Host "   chmod 700 ~/.ssh" -ForegroundColor Gray
Write-Host "   echo '$publicKey' >> ~/.ssh/authorized_keys" -ForegroundColor Gray
Write-Host "   chmod 600 ~/.ssh/authorized_keys" -ForegroundColor Gray
Write-Host ""
Write-Host "3. Или скопируйте и выполните одну команду:" -ForegroundColor White
Write-Host "   mkdir -p ~/.ssh && chmod 700 ~/.ssh && echo '$publicKey' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys" -ForegroundColor Gray
Write-Host ""
Write-Host "4. Проверьте подключение:" -ForegroundColor White
if ($VPS_SSH_PORT -eq "22") {
    Write-Host "   ssh -i `"$env:USERPROFILE\.ssh\github_actions_deploy`" $VPS_USER@$VPS_HOST `"echo '✅ Работает!'`"" -ForegroundColor Gray
} else {
    Write-Host "   ssh -i `"$env:USERPROFILE\.ssh\github_actions_deploy`" -p $VPS_SSH_PORT $VPS_USER@$VPS_HOST `"echo '✅ Работает!'`"" -ForegroundColor Gray
}
Write-Host ""

