# Скрипт для проверки готовности VPS к деплою
# Выполняет проверку через SSH

$VPS_HOST = "5.101.4.137"
$VPS_USER = "root"
$VPS_PROJECT_PATH = "~/public"

Write-Host "🔍 Проверка готовности VPS к деплою..." -ForegroundColor Cyan
Write-Host "VPS: $VPS_USER@$VPS_HOST" -ForegroundColor Gray
Write-Host ""

# Функция для выполнения команд на VPS
function Invoke-VPSCommand {
    param([string]$Command)
    ssh -i "$env:USERPROFILE\.ssh\github_actions_deploy" -o BatchMode=yes $VPS_USER@$VPS_HOST $Command 2>&1
}

Write-Host "1. Проверка Docker..." -ForegroundColor Yellow
$dockerCheck = Invoke-VPSCommand "docker --version 2>/dev/null || echo 'Docker не установлен'"
Write-Host "   $dockerCheck" -ForegroundColor $(if ($dockerCheck -match "version") { "Green" } else { "Red" })

Write-Host ""
Write-Host "2. Проверка Docker Compose..." -ForegroundColor Yellow
$composeCheck = Invoke-VPSCommand "docker compose version 2>/dev/null || docker-compose --version 2>/dev/null || echo 'Docker Compose не установлен'"
Write-Host "   $composeCheck" -ForegroundColor $(if ($composeCheck -match "version") { "Green" } else { "Red" })

Write-Host ""
Write-Host "3. Проверка Git..." -ForegroundColor Yellow
$gitCheck = Invoke-VPSCommand "git --version 2>/dev/null || echo 'Git не установлен'"
Write-Host "   $gitCheck" -ForegroundColor $(if ($gitCheck -match "version") { "Green" } else { "Red" })

Write-Host ""
Write-Host "4. Проверка директории проекта..." -ForegroundColor Yellow
$dirCheck = Invoke-VPSCommand "if [ -d $VPS_PROJECT_PATH ]; then echo '✅ Директория существует'; ls -la $VPS_PROJECT_PATH | head -5; else echo '❌ Директория не существует'; fi"
Write-Host "   $dirCheck" -ForegroundColor Gray

Write-Host ""
Write-Host "5. Проверка Git репозитория..." -ForegroundColor Yellow
$repoCheck = Invoke-VPSCommand "if [ -d $VPS_PROJECT_PATH/.git ]; then echo '✅ Git репозиторий найден'; cd $VPS_PROJECT_PATH && git remote get-url origin 2>/dev/null || echo 'Remote не настроен'; else echo '❌ Git репозиторий не найден'; fi"
Write-Host "   $repoCheck" -ForegroundColor Gray

Write-Host ""
Write-Host "6. Проверка .env файла..." -ForegroundColor Yellow
$envCheck = Invoke-VPSCommand "if [ -f $VPS_PROJECT_PATH/.env ]; then echo '✅ .env файл существует'; grep -E '^ENVIRONMENT=' $VPS_PROJECT_PATH/.env 2>/dev/null || echo 'ENVIRONMENT не найден'; else echo '❌ .env файл не найден'; fi"
Write-Host "   $envCheck" -ForegroundColor Gray

Write-Host ""
Write-Host "7. Проверка docker-compose.yml..." -ForegroundColor Yellow
$composeFileCheck = Invoke-VPSCommand "if [ -f $VPS_PROJECT_PATH/docker-compose.yml ]; then echo '✅ docker-compose.yml найден'; else echo '❌ docker-compose.yml не найден'; fi"
Write-Host "   $composeFileCheck" -ForegroundColor Gray

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "✅ ПРОВЕРКА ЗАВЕРШЕНА" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📋 Если что-то не настроено, следуйте инструкциям в VPS_DEPLOY_SETUP.md" -ForegroundColor Yellow
Write-Host ""

