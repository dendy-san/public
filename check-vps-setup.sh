#!/bin/bash
# Скрипт для проверки готовности VPS к деплою
# Выполните на VPS: bash check-vps-setup.sh

set -e

echo "🔍 Проверка готовности VPS к деплою"
echo ""

# Цвета
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

PROJECT_PATH=${1:-~/public}
PROJECT_PATH=$(eval echo $PROJECT_PATH)

echo "📁 Путь к проекту: $PROJECT_PATH"
echo ""

# Проверка 1: Docker
echo -e "${YELLOW}1. Проверка Docker...${NC}"
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version)
    echo -e "${GREEN}✅ Docker установлен: $DOCKER_VERSION${NC}"
else
    echo -e "${RED}❌ Docker не установлен${NC}"
    echo "   Установите: curl -fsSL https://get.docker.com | sh"
    exit 1
fi

# Проверка 2: Docker Compose
echo ""
echo -e "${YELLOW}2. Проверка Docker Compose...${NC}"
if docker compose version &> /dev/null 2>&1; then
    COMPOSE_VERSION=$(docker compose version)
    echo -e "${GREEN}✅ Docker Compose установлен: $COMPOSE_VERSION${NC}"
elif command -v docker-compose &> /dev/null; then
    COMPOSE_VERSION=$(docker-compose --version)
    echo -e "${GREEN}✅ Docker Compose установлен: $COMPOSE_VERSION${NC}"
else
    echo -e "${RED}❌ Docker Compose не установлен${NC}"
    exit 1
fi

# Проверка 3: Git
echo ""
echo -e "${YELLOW}3. Проверка Git...${NC}"
if command -v git &> /dev/null; then
    GIT_VERSION=$(git --version)
    echo -e "${GREEN}✅ Git установлен: $GIT_VERSION${NC}"
else
    echo -e "${RED}❌ Git не установлен${NC}"
    exit 1
fi

# Проверка 4: Директория проекта
echo ""
echo -e "${YELLOW}4. Проверка директории проекта...${NC}"
if [ -d "$PROJECT_PATH" ]; then
    echo -e "${GREEN}✅ Директория существует: $PROJECT_PATH${NC}"
else
    echo -e "${YELLOW}⚠️  Директория не существует${NC}"
    echo "   Создайте: mkdir -p $PROJECT_PATH"
fi

# Проверка 5: Git репозиторий
echo ""
echo -e "${YELLOW}5. Проверка Git репозитория...${NC}"
if [ -d "$PROJECT_PATH/.git" ]; then
    echo -e "${GREEN}✅ Git репозиторий найден${NC}"
    cd "$PROJECT_PATH"
    REMOTE_URL=$(git remote get-url origin 2>/dev/null || echo "не настроен")
    echo "   Remote: $REMOTE_URL"
    CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "неизвестна")
    echo "   Ветка: $CURRENT_BRANCH"
else
    echo -e "${YELLOW}⚠️  Git репозиторий не найден${NC}"
    echo "   Клонируйте: cd $PROJECT_PATH && git clone https://github.com/dendy-san/public.git ."
fi

# Проверка 6: .env файл
echo ""
echo -e "${YELLOW}6. Проверка .env файла...${NC}"
ENV_FILE="$PROJECT_PATH/.env"
if [ -f "$ENV_FILE" ]; then
    echo -e "${GREEN}✅ .env файл существует${NC}"
    
    # Проверка ENVIRONMENT
    if grep -q "ENVIRONMENT=prod" "$ENV_FILE"; then
        echo -e "${GREEN}   ✅ ENVIRONMENT=prod установлен${NC}"
    else
        echo -e "${YELLOW}   ⚠️  ENVIRONMENT=prod не найден${NC}"
    fi
    
    # Проверка обязательных переменных
    if grep -q "API_KEY=" "$ENV_FILE" && ! grep -q "API_KEY=your_" "$ENV_FILE"; then
        echo -e "${GREEN}   ✅ API_KEY настроен${NC}"
    else
        echo -e "${YELLOW}   ⚠️  API_KEY не настроен или использует шаблон${NC}"
    fi
    
    if grep -q "REDIS_URL=" "$ENV_FILE"; then
        echo -e "${GREEN}   ✅ REDIS_URL настроен${NC}"
    else
        echo -e "${YELLOW}   ⚠️  REDIS_URL не найден${NC}"
    fi
else
    echo -e "${RED}❌ .env файл не найден${NC}"
    echo "   Создайте: nano $ENV_FILE"
    echo "   Минимальный .env должен содержать:"
    echo "   ENVIRONMENT=prod"
    echo "   REDIS_URL=redis://redis:6379"
    echo "   BASE_URL=https://api.deepseek.com/v1"
    echo "   API_KEY=ваш_ключ"
fi

# Проверка 7: docker-compose.yml
echo ""
echo -e "${YELLOW}7. Проверка docker-compose.yml...${NC}"
if [ -f "$PROJECT_PATH/docker-compose.yml" ]; then
    echo -e "${GREEN}✅ docker-compose.yml найден${NC}"
else
    echo -e "${RED}❌ docker-compose.yml не найден${NC}"
    echo "   Убедитесь, что проект клонирован полностью"
fi

# Итоговая сводка
echo ""
echo "=========================================="
echo -e "${GREEN}✅ ПРОВЕРКА ЗАВЕРШЕНА${NC}"
echo "=========================================="
echo ""
echo "📋 Следующие шаги:"
echo ""
echo "1. Если .env не настроен:"
echo "   nano $ENV_FILE"
echo ""
echo "2. Если проект не клонирован:"
echo "   cd $PROJECT_PATH"
echo "   git clone https://github.com/dendy-san/public.git ."
echo ""
echo "3. После настройки секретов в GitHub, деплой будет автоматическим"
echo ""

