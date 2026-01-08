# Frontend Dockerfile для административной панели

# Стадия 1: Сборка приложения
FROM node:20-alpine AS builder

WORKDIR /app

# Копирование package.json и package-lock.json
COPY package*.json ./

# Установка зависимостей
RUN npm install

# Копирование исходного кода
COPY . .

# Сборка приложения для production
RUN npm run build

# Стадия 2: Production образ с nginx
FROM nginx:alpine

# Копирование собранного приложения из builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Открытие порта
EXPOSE 80

# Запуск nginx
CMD ["nginx", "-g", "daemon off;"]














































