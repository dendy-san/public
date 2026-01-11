#!/bin/bash
# Скрипт для проверки статуса деплоя на VPS

echo "🔍 Диагностика деплоя..."
echo ""

# Цвета для вывода
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Функция для проверки подключения
check_connection() {
    local host=$1
    local port=$2
    local service=$3
    
    echo -n "Проверка $service ($host:$port)... "
    if timeout 3 bash -c "cat < /dev/null > /dev/tcp/$host/$port" 2>/dev/null; then
        echo -e "${GREEN}✅ Порты открыты${NC}"
        return 0
    else
        echo -e "${RED}❌ Порты недоступны${NC}"
        return 1
    fi
}

# Проверка через curl
check_http() {
    local url=$1
    local service=$2
    
    echo -n "Проверка HTTP $service ($url)... "
    response=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$url" 2>/dev/null)
    if [ "$response" = "200" ] || [ "$response" = "301" ] || [ "$response" = "302" ]; then
        echo -e "${GREEN}✅ Отвечает (HTTP $response)${NC}"
        return 0
    else
        echo -e "${RED}❌ Не отвечает (HTTP $response)${NC}"
        return 1
    fi
}

# Получаем IP из GitHub Secrets (если запущено в GitHub Actions)
if [ -n "$VPS_HOST" ]; then
    VPS_IP=$VPS_HOST
else
    read -p "Введите IP адрес VPS: " VPS_IP
fi

if [ -z "$VPS_IP" ]; then
    echo -e "${RED}❌ IP адрес не указан${NC}"
    exit 1
fi

echo "🌐 Проверяем VPS: $VPS_IP"
echo ""

# Проверка доступности VPS
echo -n "Проверка доступности VPS... "
if ping -c 1 -W 3 "$VPS_IP" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ VPS доступен${NC}"
else
    echo -e "${RED}❌ VPS недоступен (ping)${NC}"
fi
echo ""

# Проверка портов
echo "📡 Проверка портов:"
check_connection "$VPS_IP" 8000 "Backend"
check_connection "$VPS_IP" 3000 "Frontend"
check_connection "$VPS_IP" 3001 "Admin Frontend"
echo ""

# Проверка HTTP сервисов
echo "🌐 Проверка HTTP сервисов:"
check_http "http://$VPS_IP:8000/health" "Backend Health"
check_http "http://$VPS_IP:8000" "Backend"
check_http "http://$VPS_IP:3000" "Frontend"
check_http "http://$VPS_IP:3001" "Admin Frontend"
echo ""

# Детальная проверка Backend
echo "🔍 Детальная проверка Backend:"
echo -n "  GET /health: "
health_response=$(curl -s --max-time 5 "http://$VPS_IP:8000/health" 2>/dev/null)
if [ -n "$health_response" ]; then
    echo -e "${GREEN}✅ $health_response${NC}"
else
    echo -e "${RED}❌ Нет ответа${NC}"
fi

echo -n "  GET /: "
root_response=$(curl -s --max-time 5 "http://$VPS_IP:8000/" 2>/dev/null)
if [ -n "$root_response" ]; then
    echo -e "${GREEN}✅ Отвечает${NC}"
    echo "  Ответ: $(echo "$root_response" | head -c 100)..."
else
    echo -e "${RED}❌ Нет ответа${NC}"
fi
echo ""

echo "📋 Следующие шаги для диагностики на VPS:"
echo "  1. Подключитесь к VPS: ssh -p ПОРТ ПОЛЬЗОВАТЕЛЬ@$VPS_IP"
echo "  2. Проверьте статус контейнеров: docker compose ps"
echo "  3. Проверьте логи: docker compose logs backend"
echo "  4. Проверьте порты: sudo netstat -tlnp | grep -E '3000|8000|3001'"
echo "  5. Проверьте firewall: sudo ufw status"
