#!/bin/bash
# Скрипт для автоматической настройки VPS для деплоя
# Выполните на VPS: bash <(curl -s https://raw.githubusercontent.com/your-repo/setup-vps.sh)
# Или скопируйте и выполните локально

set -e

echo "🚀 Настройка VPS для автоматического деплоя"
echo ""

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Проверка прав root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${YELLOW}⚠️  Рекомендуется выполнять от root или с sudo${NC}"
fi

# Шаг 1: Проверка и установка Docker
echo -e "${YELLOW}📦 Шаг 1: Проверка Docker...${NC}"
if ! command -v docker &> /dev/null; then
    echo "Установка Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
    echo -e "${GREEN}✅ Docker установлен${NC}"
else
    echo -e "${GREEN}✅ Docker уже установлен${NC}"
fi

# Шаг 2: Проверка и установка Docker Compose
echo ""
echo -e "${YELLOW}📦 Шаг 2: Проверка Docker Compose...${NC}"
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "Установка Docker Compose..."
    # Для Docker Compose V2 (встроен в Docker)
    if docker compose version &> /dev/null; then
        echo -e "${GREEN}✅ Docker Compose V2 доступен${NC}"
    else
        # Установка Docker Compose V1 (legacy)
        curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        chmod +x /usr/local/bin/docker-compose
        echo -e "${GREEN}✅ Docker Compose установлен${NC}"
    fi
else
    echo -e "${GREEN}✅ Docker Compose уже установлен${NC}"
fi

# Шаг 3: Проверка и установка Git
echo ""
echo -e "${YELLOW}📦 Шаг 3: Проверка Git...${NC}"
if ! command -v git &> /dev/null; then
    echo "Установка Git..."
    if [ -f /etc/debian_version ]; then
        apt-get update
        apt-get install -y git
    elif [ -f /etc/redhat-release ]; then
        yum install -y git
    fi
    echo -e "${GREEN}✅ Git установлен${NC}"
else
    echo -e "${GREEN}✅ Git уже установлен${NC}"
fi

# Шаг 4: Создание директории для проекта
echo ""
echo -e "${YELLOW}📁 Шаг 4: Настройка директории проекта...${NC}"
read -p "Введите путь к проекту (по умолчанию: ~/public): " PROJECT_PATH
PROJECT_PATH=${PROJECT_PATH:-~/public}
PROJECT_PATH=$(eval echo $PROJECT_PATH)  # Разворачиваем ~

if [ ! -d "$PROJECT_PATH" ]; then
    echo "Создание директории: $PROJECT_PATH"
    mkdir -p "$PROJECT_PATH"
    echo -e "${GREEN}✅ Директория создана${NC}"
else
    echo -e "${GREEN}✅ Директория уже существует${NC}"
fi

# Шаг 5: Клонирование репозитория (если нужно)
echo ""
echo -e "${YELLOW}📥 Шаг 5: Настройка Git репозитория...${NC}"
if [ ! -d "$PROJECT_PATH/.git" ]; then
    read -p "Введите URL репозитория GitHub (или нажмите Enter, чтобы пропустить): " REPO_URL
    if [ -n "$REPO_URL" ]; then
        echo "Клонирование репозитория..."
        cd "$PROJECT_PATH"
        git clone "$REPO_URL" .
        echo -e "${GREEN}✅ Репозиторий склонирован${NC}"
    else
        echo -e "${YELLOW}⚠️  Репозиторий не клонирован. Сделайте это вручную:${NC}"
        echo "   cd $PROJECT_PATH"
        echo "   git clone https://github.com/your-username/your-repo.git ."
    fi
else
    echo -e "${GREEN}✅ Git репозиторий уже настроен${NC}"
fi

# Шаг 6: Создание .env файла (если нужно)
echo ""
echo -e "${YELLOW}📝 Шаг 6: Настройка .env файла...${NC}"
ENV_FILE="$PROJECT_PATH/.env"
if [ ! -f "$ENV_FILE" ]; then
    echo "Создание .env файла..."
    cat > "$ENV_FILE" << EOF
# Режим работы (prod для production)
ENVIRONMENT=prod

# Redis
REDIS_URL=redis://redis:6379

# DeepSeek API
BASE_URL=https://api.deepseek.com/v1
API_KEY=your_deepseek_api_key_here

# GPT-4o через ProxyAPI (опционально)
OPENAI_BASE_URL=https://api.proxyapi.ru/openai/v1
OPENAI_API_KEY=your_proxyapi_key_here

# YooKassa
SHOP_ID=your_shop_id_here
YOOKASSA_API_KEY=your_yookassa_api_key_here

# Параметры (будут загружены в Redis при первом запуске)
W=60
Price=100
EOF
    echo -e "${GREEN}✅ .env файл создан: $ENV_FILE${NC}"
    echo -e "${YELLOW}⚠️  ВАЖНО: Отредактируйте .env файл и заполните все необходимые переменные!${NC}"
else
    echo -e "${GREEN}✅ .env файл уже существует${NC}"
fi

# Шаг 7: Настройка прав доступа
echo ""
echo -e "${YELLOW}🔐 Шаг 7: Настройка прав доступа...${NC}"
if [ -n "$SUDO_USER" ]; then
    chown -R "$SUDO_USER:$SUDO_USER" "$PROJECT_PATH"
    echo -e "${GREEN}✅ Права доступа настроены${NC}"
fi

# Итоговая информация
echo ""
echo "=========================================="
echo -e "${GREEN}✅ НАСТРОЙКА VPS ЗАВЕРШЕНА!${NC}"
echo "=========================================="
echo ""
echo -e "${YELLOW}📋 СЛЕДУЮЩИЕ ШАГИ:${NC}"
echo ""
echo "1. Отредактируйте .env файл:"
echo "   nano $ENV_FILE"
echo ""
echo "2. Убедитесь, что публичный SSH ключ добавлен в ~/.ssh/authorized_keys"
echo ""
echo "3. Проверьте, что проект клонирован и настроен:"
echo "   cd $PROJECT_PATH"
echo "   ls -la"
echo ""
echo "4. После настройки секретов в GitHub, деплой будет выполняться автоматически"
echo ""








