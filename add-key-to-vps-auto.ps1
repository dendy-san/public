# Автоматическое добавление публичного SSH ключа на VPS через SSH
# Выполняет команды на VPS для добавления ключа в authorized_keys

param(
    [Parameter(Mandatory=$true)]
    [string]$VPS_USER = "root",
    
    [Parameter(Mandatory=$true)]
    [string]$VPS_HOST = "5.101.4.137",
    
    [Parameter(Mandatory=$false)]
    [string]$VPS_SSH_PORT = "22"
)

Write-Host "📤 Автоматическое добавление SSH ключа на VPS" -ForegroundColor Cyan
Write-Host ""

$pubKeyPath = "$env:USERPROFILE\.ssh\github_actions_deploy.pub"

if (-not (Test-Path $pubKeyPath)) {
    Write-Host "❌ Публичный SSH ключ не найден: $pubKeyPath" -ForegroundColor Red
    Write-Host "💡 Сначала выполните: .\setup-github-actions.ps1" -ForegroundColor Yellow
    exit 1
}

# Читаем публичный ключ
$publicKey = Get-Content $pubKeyPath -Raw
$publicKey = $publicKey.Trim()

Write-Host "✅ Публичный ключ найден" -ForegroundColor Green
Write-Host "📋 Ключ: $publicKey" -ForegroundColor Gray
Write-Host ""
Write-Host "🔗 Подключение к VPS: $VPS_USER@$VPS_HOST" -ForegroundColor Yellow
Write-Host ""

# Формируем команду для выполнения на VPS
$sshCommand = @"
mkdir -p ~/.ssh && chmod 700 ~/.ssh && 
if ! grep -q "$publicKey" ~/.ssh/authorized_keys 2>/dev/null; then
    echo '$publicKey' >> ~/.ssh/authorized_keys && 
    chmod 600 ~/.ssh/authorized_keys && 
    echo '✅ Ключ добавлен'
else
    echo '⚠️  Ключ уже существует в authorized_keys'
fi
"@

Write-Host "🔧 Выполнение команд на VPS..." -ForegroundColor Cyan
Write-Host ""

# Выполняем команду через SSH (с таймаутом и без интерактивных запросов)
Write-Host "⏳ Подключение к VPS (может потребоваться ввод пароля)..." -ForegroundColor Yellow
Write-Host "💡 Если запросит пароль - введите его" -ForegroundColor Cyan
Write-Host ""

$sshArgs = @(
    "-o", "ConnectTimeout=10",
    "-o", "StrictHostKeyChecking=no",
    "-o", "BatchMode=no"
)

if ($VPS_SSH_PORT -ne "22") {
    $sshArgs += "-p", $VPS_SSH_PORT
}

$sshArgs += "${VPS_USER}@${VPS_HOST}"
$sshArgs += $sshCommand

try {
    $process = Start-Process -FilePath "ssh" -ArgumentList $sshArgs -NoNewWindow -Wait -PassThru -RedirectStandardOutput "ssh_output.txt" -RedirectStandardError "ssh_error.txt"
    
    if (Test-Path "ssh_output.txt") {
        Get-Content "ssh_output.txt" | Write-Host
    }
    if (Test-Path "ssh_error.txt") {
        $errorContent = Get-Content "ssh_error.txt" -Raw
        if ($errorContent -and $errorContent -notmatch "Warning: Permanently added") {
            Write-Host $errorContent -ForegroundColor Yellow
        }
    }
    
    $exitCode = $process.ExitCode
} catch {
    Write-Host "❌ Ошибка при выполнении SSH команды: $_" -ForegroundColor Red
    $exitCode = 1
} finally {
    if (Test-Path "ssh_output.txt") { Remove-Item "ssh_output.txt" -ErrorAction SilentlyContinue }
    if (Test-Path "ssh_error.txt") { Remove-Item "ssh_error.txt" -ErrorAction SilentlyContinue }
}

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ Ключ успешно добавлен на VPS!" -ForegroundColor Green
    Write-Host ""
    Write-Host "🧪 Проверка подключения с приватным ключом..." -ForegroundColor Cyan
    
    # Проверяем подключение с приватным ключом
    $testCommand = "echo '✅ SSH подключение с приватным ключом работает!'"
    if ($VPS_SSH_PORT -eq "22") {
        ssh -i "$env:USERPROFILE\.ssh\github_actions_deploy" -o StrictHostKeyChecking=no $VPS_USER@$VPS_HOST $testCommand
    } else {
        ssh -i "$env:USERPROFILE\.ssh\github_actions_deploy" -p $VPS_SSH_PORT -o StrictHostKeyChecking=no $VPS_USER@$VPS_HOST $testCommand
    }
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "🎉 Всё готово! GitHub Actions сможет подключаться к VPS." -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "⚠️  Подключение с приватным ключом не работает. Проверьте настройки." -ForegroundColor Yellow
    }
} else {
    Write-Host ""
    Write-Host "❌ Ошибка при добавлении ключа" -ForegroundColor Red
    Write-Host "💡 Убедитесь, что:" -ForegroundColor Yellow
    Write-Host "   1. У вас есть доступ к VPS через SSH" -ForegroundColor White
    Write-Host "   2. Пользователь $VPS_USER существует" -ForegroundColor White
    Write-Host "   3. Порт $VPS_SSH_PORT открыт" -ForegroundColor White
    Write-Host ""
    Write-Host "📋 Выполните команды вручную:" -ForegroundColor Cyan
    Write-Host "   ssh $VPS_USER@$VPS_HOST" -ForegroundColor Gray
    Write-Host "   mkdir -p ~/.ssh && chmod 700 ~/.ssh" -ForegroundColor Gray
    Write-Host "   echo '$publicKey' >> ~/.ssh/authorized_keys" -ForegroundColor Gray
    Write-Host "   chmod 600 ~/.ssh/authorized_keys" -ForegroundColor Gray
}

Write-Host ""

