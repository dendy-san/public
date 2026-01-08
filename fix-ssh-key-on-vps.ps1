# Скрипт для исправления проблем с SSH ключом на VPS
# Выполняет проверку и исправление прав доступа и формата ключа

Write-Host "🔧 Исправление SSH ключа на VPS" -ForegroundColor Cyan
Write-Host ""

$pubKeyPath = "$env:USERPROFILE\.ssh\github_actions_deploy.pub"
$publicKey = Get-Content $pubKeyPath -Raw
$publicKey = $publicKey.Trim()

Write-Host "📋 Публичный ключ:" -ForegroundColor Yellow
Write-Host $publicKey -ForegroundColor Gray
Write-Host ""

Write-Host "📝 Выполните следующие команды на VPS (подключитесь через ssh root@5.101.4.137):" -ForegroundColor Yellow
Write-Host ""

Write-Host "1. Проверка текущего состояния:" -ForegroundColor Cyan
Write-Host "   cat ~/.ssh/authorized_keys" -ForegroundColor White
Write-Host "   ls -la ~/.ssh/" -ForegroundColor White
Write-Host ""

Write-Host "2. Удаление старого ключа (если есть проблемы):" -ForegroundColor Cyan
Write-Host "   sed -i '/github-actions-deploy/d' ~/.ssh/authorized_keys" -ForegroundColor White
Write-Host ""

Write-Host "3. Добавление ключа правильным способом:" -ForegroundColor Cyan
Write-Host "   mkdir -p ~/.ssh" -ForegroundColor White
Write-Host "   chmod 700 ~/.ssh" -ForegroundColor White
Write-Host "   echo '$publicKey' >> ~/.ssh/authorized_keys" -ForegroundColor White
Write-Host "   chmod 600 ~/.ssh/authorized_keys" -ForegroundColor White
Write-Host ""

Write-Host "4. Проверка результата:" -ForegroundColor Cyan
Write-Host "   cat ~/.ssh/authorized_keys | grep github-actions-deploy" -ForegroundColor White
Write-Host "   ls -la ~/.ssh/authorized_keys" -ForegroundColor White
Write-Host ""

Write-Host "5. Или выполните всё одной командой:" -ForegroundColor Cyan
Write-Host "   mkdir -p ~/.ssh && chmod 700 ~/.ssh && sed -i '/github-actions-deploy/d' ~/.ssh/authorized_keys 2>/dev/null; echo '$publicKey' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys && echo '✅ Готово'" -ForegroundColor White
Write-Host ""

Write-Host "6. После выполнения команд на VPS, проверьте подключение:" -ForegroundColor Cyan
Write-Host "   ssh -i `"$env:USERPROFILE\.ssh\github_actions_deploy`" root@5.101.4.137 `"echo '✅ Работает!'`"" -ForegroundColor White
Write-Host ""

Write-Host "💡 ВАЖНО: Убедитесь, что:" -ForegroundColor Yellow
Write-Host "   - Файл ~/.ssh/authorized_keys имеет права 600" -ForegroundColor White
Write-Host "   - Директория ~/.ssh имеет права 700" -ForegroundColor White
Write-Host "   - Ключ добавлен в одну строку без переносов" -ForegroundColor White
Write-Host ""

