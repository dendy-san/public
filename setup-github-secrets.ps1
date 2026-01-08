# Интерактивный скрипт для подготовки данных для GitHub Secrets
# Собирает все необходимые данные и создает готовые инструкции

Write-Host "🔐 Подготовка данных для GitHub Secrets" -ForegroundColor Cyan
Write-Host ""

# Чтение приватного ключа
$sshKeyPath = "$env:USERPROFILE\.ssh\github_actions_deploy"
if (-not (Test-Path $sshKeyPath)) {
    Write-Host "❌ SSH ключ не найден: $sshKeyPath" -ForegroundColor Red
    Write-Host "💡 Сначала выполните: .\setup-github-actions.ps1" -ForegroundColor Yellow
    exit 1
}

$privateKey = Get-Content $sshKeyPath -Raw
$publicKey = Get-Content "$sshKeyPath.pub"

Write-Host "✅ SSH ключ найден" -ForegroundColor Green
Write-Host ""

# Сбор данных от пользователя
Write-Host "📝 Введите данные для подключения к VPS:" -ForegroundColor Yellow
Write-Host ""

$VPS_HOST = Read-Host "VPS_HOST (IP или домен, например: 192.168.1.100 или example.com)"
$VPS_USER = Read-Host "VPS_USER (имя пользователя для SSH, например: root)"
$VPS_SSH_PORT = Read-Host "VPS_SSH_PORT (порт SSH, по умолчанию: 22)"
if ([string]::IsNullOrWhiteSpace($VPS_SSH_PORT)) {
    $VPS_SSH_PORT = "22"
}

$VPS_PROJECT_PATH = Read-Host "VPS_PROJECT_PATH (путь к проекту, по умолчанию: ~/public)"
if ([string]::IsNullOrWhiteSpace($VPS_PROJECT_PATH)) {
    $VPS_PROJECT_PATH = "~/public"
}

Write-Host ""
Write-Host "📝 Порт сервисов (можно оставить пустым для значений по умолчанию):" -ForegroundColor Yellow
Write-Host ""

$BACKEND_PORT = Read-Host "BACKEND_PORT (по умолчанию: 8000)"
if ([string]::IsNullOrWhiteSpace($BACKEND_PORT)) {
    $BACKEND_PORT = "8000"
}

$FRONTEND_PORT = Read-Host "FRONTEND_PORT (по умолчанию: 3000)"
if ([string]::IsNullOrWhiteSpace($FRONTEND_PORT)) {
    $FRONTEND_PORT = "3000"
}

$ADMIN_FRONTEND_PORT = Read-Host "ADMIN_FRONTEND_PORT (по умолчанию: 3001)"
if ([string]::IsNullOrWhiteSpace($ADMIN_FRONTEND_PORT)) {
    $ADMIN_FRONTEND_PORT = "3001"
}

Write-Host ""
Write-Host "📝 Telegram уведомления (опционально, можно оставить пустым):" -ForegroundColor Yellow
Write-Host ""

$TELEGRAM_BOT_TOKEN = Read-Host "TELEGRAM_BOT_TOKEN (опционально)"
$TELEGRAM_CHAT_ID = Read-Host "TELEGRAM_CHAT_ID (опционально)"

Write-Host ""
Write-Host "🔗 Получение URL репозитория GitHub..." -ForegroundColor Yellow
$gitRemote = git remote get-url origin 2>$null
if ($gitRemote) {
    # Преобразуем SSH URL в HTTPS, если нужно
    if ($gitRemote -match 'git@github\.com:(.+?)/(.+?)\.git') {
        $repoOwner = $matches[1]
        $repoName = $matches[2] -replace '\.git$', ''
        $repoUrl = "https://github.com/$repoOwner/$repoName"
    } elseif ($gitRemote -match 'https://github\.com/(.+?)/(.+?)(\.git)?$') {
        $repoUrl = $gitRemote -replace '\.git$', ''
    } else {
        $repoUrl = $gitRemote
    }
    Write-Host "✅ Репозиторий: $repoUrl" -ForegroundColor Green
} else {
    $repoUrl = "https://github.com/your-username/your-repo"
    Write-Host "⚠️  Git remote не найден, используется шаблон" -ForegroundColor Yellow
}

# Создание файла с инструкциями
$instructionsFile = "GITHUB_SECRETS_SETUP.txt"
$instructionsContent = @"
========================================
ИНСТРУКЦИЯ ПО ДОБАВЛЕНИЮ СЕКРЕТОВ В GITHUB
========================================

1. Откройте репозиторий в GitHub: $repoUrl
2. Перейдите: Settings → Secrets and variables → Actions
3. Нажмите: New repository secret
4. Добавьте каждый секрет отдельно (см. ниже)

========================================
ОБЯЗАТЕЛЬНЫЕ СЕКРЕТЫ
========================================

1. VPS_HOST
   Name: VPS_HOST
   Value: $VPS_HOST

2. VPS_USER
   Name: VPS_USER
   Value: $VPS_USER

3. VPS_SSH_KEY
   Name: VPS_SSH_KEY
   Value: (см. раздел "ПРИВАТНЫЙ SSH КЛЮЧ" ниже)

========================================
ОПЦИОНАЛЬНЫЕ СЕКРЕТЫ (если отличаются от значений по умолчанию)
========================================

4. VPS_SSH_PORT
   Name: VPS_SSH_PORT
   Value: $VPS_SSH_PORT

5. VPS_PROJECT_PATH
   Name: VPS_PROJECT_PATH
   Value: $VPS_PROJECT_PATH

6. BACKEND_PORT
   Name: BACKEND_PORT
   Value: $BACKEND_PORT

7. FRONTEND_PORT
   Name: FRONTEND_PORT
   Value: $FRONTEND_PORT

8. ADMIN_FRONTEND_PORT
   Name: ADMIN_FRONTEND_PORT
   Value: $ADMIN_FRONTEND_PORT

$(
if (-not [string]::IsNullOrWhiteSpace($TELEGRAM_BOT_TOKEN)) {
    "9. TELEGRAM_BOT_TOKEN`n   Name: TELEGRAM_BOT_TOKEN`n   Value: $TELEGRAM_BOT_TOKEN`n`n10. TELEGRAM_CHAT_ID`n    Name: TELEGRAM_CHAT_ID`n    Value: $TELEGRAM_CHAT_ID"
}
)

========================================
ПРИВАТНЫЙ SSH КЛЮЧ (для секрета VPS_SSH_KEY)
========================================

Скопируйте ВЕСЬ текст ниже (включая строки -----BEGIN... и -----END...):

$privateKey

========================================
ПУБЛИЧНЫЙ SSH КЛЮЧ (для добавления на VPS)
========================================

Скопируйте и добавьте на VPS в ~/.ssh/authorized_keys:

$publicKey

Команда для добавления на VPS:
ssh-copy-id -i $env:USERPROFILE\.ssh\github_actions_deploy.pub $VPS_USER@$VPS_HOST

Или вручную:
1. Подключитесь к VPS: ssh $VPS_USER@$VPS_HOST
2. Выполните:
   mkdir -p ~/.ssh
   chmod 700 ~/.ssh
   echo "$publicKey" >> ~/.ssh/authorized_keys
   chmod 600 ~/.ssh/authorized_keys

========================================
СЛЕДУЮЩИЕ ШАГИ ПОСЛЕ ДОБАВЛЕНИЯ СЕКРЕТОВ
========================================

1. ✅ Добавьте публичный SSH ключ на VPS (команда выше)
2. ✅ Убедитесь, что проект склонирован на VPS:
   ssh $VPS_USER@$VPS_HOST
   cd $VPS_PROJECT_PATH
   git clone $gitRemote .  (если еще не склонирован)

3. ✅ Убедитесь, что на VPS есть .env файл с ENVIRONMENT=prod

4. ✅ Протестируйте деплой:
   - Сделайте push в main ветку
   - Или используйте GitHub Actions → Deploy to VPS → Run workflow

========================================
ПРОВЕРКА НАСТРОЙКИ
========================================

После добавления всех секретов:
1. Перейдите: $repoUrl/actions
2. Нажмите: Deploy to VPS
3. Нажмите: Run workflow
4. Выберите ветку: main
5. Нажмите: Run workflow
6. Проверьте, что деплой выполнился успешно

========================================
"@

Set-Content -Path $instructionsFile -Value $instructionsContent -Encoding UTF8

Write-Host ""
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "✅ ДАННЫЕ СОБРАНЫ!" -ForegroundColor Green
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host ""
Write-Host "📄 Полная инструкция сохранена в файл: $instructionsFile" -ForegroundColor Yellow
Write-Host ""
Write-Host "📋 КРАТКАЯ ИНСТРУКЦИЯ:" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Откройте файл $instructionsFile" -ForegroundColor White
Write-Host "2. Перейдите в GitHub: $repoUrl/settings/secrets/actions" -ForegroundColor White
Write-Host "3. Добавьте все секреты согласно инструкции" -ForegroundColor White
Write-Host "4. Добавьте публичный SSH ключ на VPS" -ForegroundColor White
Write-Host ""
Write-Host "🔑 ПРИВАТНЫЙ SSH КЛЮЧ (для секрета VPS_SSH_KEY):" -ForegroundColor Yellow
Write-Host "=" * 80 -ForegroundColor Gray
Write-Host $privateKey -ForegroundColor White
Write-Host "=" * 80 -ForegroundColor Gray
Write-Host ""
Write-Host "💡 Скопируйте ключ выше и добавьте как секрет VPS_SSH_KEY в GitHub" -ForegroundColor Cyan
Write-Host ""



