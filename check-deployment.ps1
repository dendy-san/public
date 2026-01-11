# PowerShell скрипт для проверки статуса деплоя на VPS

param(
    [string]$VPS_HOST = ""
)

Write-Host "🔍 Диагностика деплоя..." -ForegroundColor Cyan
Write-Host ""

# Получаем IP из параметра или запрашиваем
if ([string]::IsNullOrEmpty($VPS_HOST)) {
    $VPS_HOST = Read-Host "Введите IP адрес VPS"
}

if ([string]::IsNullOrEmpty($VPS_HOST)) {
    Write-Host "❌ IP адрес не указан" -ForegroundColor Red
    exit 1
}

Write-Host "🌐 Проверяем VPS: $VPS_HOST" -ForegroundColor Cyan
Write-Host ""

# Функция для проверки порта
function Test-Port {
    param(
        [string]$Computer,
        [int]$Port,
        [int]$Timeout = 3000
    )
    try {
        $tcpClient = New-Object System.Net.Sockets.TcpClient
        $connect = $tcpClient.BeginConnect($Computer, $Port, $null, $null)
        $wait = $connect.AsyncWaitHandle.WaitOne($Timeout, $false)
        if ($wait) {
            $tcpClient.EndConnect($connect)
            $tcpClient.Close()
            return $true
        } else {
            $tcpClient.Close()
            return $false
        }
    } catch {
        return $false
    }
}

# Функция для проверки HTTP
function Test-HttpService {
    param(
        [string]$Url,
        [string]$ServiceName
    )
    try {
        $response = Invoke-WebRequest -Uri $Url -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
        Write-Host "  ✅ $ServiceName откликается (HTTP $($response.StatusCode))" -ForegroundColor Green
        return $true
    } catch {
        $statusCode = $_.Exception.Response.StatusCode.value__
        if ($statusCode) {
            Write-Host "  ⚠️  $ServiceName отвечает, но с ошибкой (HTTP $statusCode)" -ForegroundColor Yellow
        } else {
            Write-Host "  ❌ $ServiceName не откликается" -ForegroundColor Red
        }
        return $false
    }
}

# Проверка доступности VPS
Write-Host "📡 Проверка доступности VPS..." -ForegroundColor Cyan
try {
    $ping = Test-Connection -ComputerName $VPS_HOST -Count 1 -Quiet -ErrorAction Stop
    if ($ping) {
        Write-Host "  ✅ VPS доступен (ping)" -ForegroundColor Green
    } else {
        Write-Host "  ❌ VPS недоступен (ping)" -ForegroundColor Red
    }
} catch {
    Write-Host "  ⚠️  Не удалось выполнить ping: $_" -ForegroundColor Yellow
}
Write-Host ""

# Проверка портов
Write-Host "📡 Проверка портов:" -ForegroundColor Cyan
$ports = @(
    @{Port = 8000; Name = "Backend"},
    @{Port = 3000; Name = "Frontend"},
    @{Port = 3001; Name = "Admin Frontend"}
)

foreach ($port in $ports) {
    Write-Host -NoNewline "  Проверка $($port.Name) ($VPS_HOST`:$($port.Port))... "
    if (Test-Port -Computer $VPS_HOST -Port $port.Port) {
        Write-Host "✅ Порты открыты" -ForegroundColor Green
    } else {
        Write-Host "❌ Порты недоступны" -ForegroundColor Red
    }
}
Write-Host ""

# Проверка HTTP сервисов
Write-Host "🌐 Проверка HTTP сервисов:" -ForegroundColor Cyan
Test-HttpService -Url "http://$VPS_HOST`:8000/health" -ServiceName "Backend Health"
Test-HttpService -Url "http://$VPS_HOST`:8000" -ServiceName "Backend"
Test-HttpService -Url "http://$VPS_HOST`:3000" -ServiceName "Frontend"
Test-HttpService -Url "http://$VPS_HOST`:3001" -ServiceName "Admin Frontend"
Write-Host ""

# Детальная проверка Backend
Write-Host "🔍 Детальная проверка Backend:" -ForegroundColor Cyan
try {
    $healthResponse = Invoke-RestMethod -Uri "http://$VPS_HOST`:8000/health" -TimeoutSec 5 -ErrorAction Stop
    Write-Host "  ✅ GET /health: $($healthResponse | ConvertTo-Json -Compress)" -ForegroundColor Green
} catch {
    Write-Host "  ❌ GET /health: Нет ответа - $_" -ForegroundColor Red
}

try {
    $rootResponse = Invoke-RestMethod -Uri "http://$VPS_HOST`:8000" -TimeoutSec 5 -ErrorAction Stop
    Write-Host "  ✅ GET /: Отвечает" -ForegroundColor Green
    Write-Host "  Ответ: $($rootResponse | ConvertTo-Json -Compress | Select-Object -First 100)..." -ForegroundColor Gray
} catch {
    Write-Host "  ❌ GET /: Нет ответа - $_" -ForegroundColor Red
}
Write-Host ""

Write-Host "📋 Следующие шаги для диагностики на VPS:" -ForegroundColor Yellow
Write-Host "  1. Подключитесь к VPS: ssh -p ПОРТ ПОЛЬЗОВАТЕЛЬ@$VPS_HOST" -ForegroundColor White
Write-Host "  2. Проверьте статус контейнеров: docker compose ps" -ForegroundColor White
Write-Host "  3. Проверьте логи: docker compose logs backend" -ForegroundColor White
Write-Host "  4. Проверьте порты: sudo netstat -tlnp | grep -E '3000|8000|3001'" -ForegroundColor White
Write-Host "  5. Проверьте firewall: sudo ufw status" -ForegroundColor White
