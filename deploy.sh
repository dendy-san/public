#!/usr/bin/env bash
# Деплой на сервере. Вызывается из GitHub Actions, но можно запустить и вручную:
#   IMAGE_TAG=sha-abc1234 /opt/genpost/deploy.sh
#
# Скрипт делает ровно четыре вещи: скачивает образы, поднимает стек,
# проверяет здоровье, при неудаче откатывается на предыдущий тег.
#
# Чего здесь сознательно нет:
#   - docker system prune --volumes: он удаляет том sqlite-data, а в нём
#     персональные данные клиентов;
#   - git reset --hard / git pull: на сервере нет репозитория, код приходит
#     в образах из GHCR;
#   - docker compose down перед up: пересоздание всех контейнеров обрывает
#     активные платежи и генерации. compose сам обновит изменившиеся.

set -euo pipefail

cd "$(dirname "$0")"

COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.prod.yml)
LOG_FILE="$PWD/deploy.log"
TAG_FILE="$PWD/.current_tag"

IMAGE_TAG="${IMAGE_TAG:-latest}"

log() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG_FILE"; }

# .env содержит ключи API, токен админки и пароль Redis. Если файла нет —
# поднимать стек нельзя: compose подставит пустые значения и приложение
# поедет без защиты.
if [ ! -f .env ]; then
  log "ОШИБКА: .env не найден в $(pwd). Скопируйте .env.example и заполните."
  exit 1
fi

# Обязательные для production значения. Проверяем до запуска, потому что
# пустой REDIS_PASSWORD означает Redis без пароля — ровно ту причину, по
# которой был заблокирован прошлый сервер.
for var in REDIS_PASSWORD ADMIN_TOKEN SITE_DOMAIN ADMIN_DOMAIN; do
  if ! grep -qE "^${var}=.+" .env; then
    log "ОШИБКА: ${var} пуст или отсутствует в .env"
    exit 1
  fi
done

# Пароль Redis подставляется в REDIS_URL (redis://:<пароль>@redis:6379/0), и
# redis-py разбирает это значение как URL: '/', ':' или '@' внутри пароля
# ломают разбор — приложение падает с "Port could not be cast to integer
# value as ...". Redis при этом отвечает, healthcheck проходит, и контейнеры
# выглядят здоровыми, а работа с параметрами, сессиями и лимитами молча
# не работает. Разрешаем только буквы и цифры: энтропия не страдает
# (openssl rand -hex 24 даёт те же 96 бит).
if ! grep -qE '^REDIS_PASSWORD=[A-Za-z0-9]{16,}$' .env; then
  log "ОШИБКА: REDIS_PASSWORD должен состоять только из латинских букв и цифр"
  log "и быть не короче 16 символов. Сгенерируйте новый: openssl rand -hex 24"
  exit 1
fi

PREVIOUS_TAG="$(cat "$TAG_FILE" 2>/dev/null || echo "")"
log "Деплой: тег ${IMAGE_TAG} (предыдущий: ${PREVIOUS_TAG:-нет})"

log "Скачивание образов..."
if ! "${COMPOSE[@]}" pull --quiet 2>&1 | tee -a "$LOG_FILE"; then
  log "ОШИБКА: не удалось скачать образы. Проверьте docker login ghcr.io."
  exit 1
fi

log "Запуск контейнеров..."
# --no-build: собирать на сервере с 1.9 ГБ ОЗУ нельзя, сборки делает CI.
if ! "${COMPOSE[@]}" up -d --no-build --remove-orphans 2>&1 | tee -a "$LOG_FILE"; then
  log "ОШИБКА: compose up завершился неудачей"
  if [ -n "$PREVIOUS_TAG" ]; then
    log "Откат на ${PREVIOUS_TAG}"
    IMAGE_TAG="$PREVIOUS_TAG" "${COMPOSE[@]}" up -d --no-build 2>&1 | tee -a "$LOG_FILE"
  fi
  exit 1
fi

log "Ожидание здоровых контейнеров..."
healthy=false
for i in $(seq 1 40); do
  # Требовать «все контейнеры healthy» нельзя: у caddy healthcheck не задан,
  # и его статус всегда выглядит как "Up 7 minutes" без пометки о здоровье.
  # Прежняя проверка («в каждой строке есть healthy или running») поэтому не
  # выполнялась никогда, и деплой падал по таймауту уже после того, как стек
  # успешно поднялся. Проверяем иначе: все контейнеры запущены (Up) и ни один
  # не в unhealthy или health: starting.
  statuses="$("${COMPOSE[@]}" ps --format '{{.Status}}' 2>/dev/null || true)"
  total="$(printf '%s\n' "$statuses" | grep -c . || true)"
  not_up="$(printf '%s\n' "$statuses" | grep -Evc '^Up' || true)"
  not_ready="$(printf '%s\n' "$statuses" | grep -Ec 'unhealthy|starting' || true)"
  if [ "${total:-0}" -ge 5 ] && [ "${not_up:-1}" -eq 0 ] && [ "${not_ready:-1}" -eq 0 ]; then
    healthy=true
    log "Все контейнеры здоровы (попытка $i)"
    break
  fi
  sleep 5
done

if [ "$healthy" != "true" ]; then
  log "ОШИБКА: контейнеры не стали здоровыми за 200 секунд"
  "${COMPOSE[@]}" ps 2>&1 | tee -a "$LOG_FILE"
  "${COMPOSE[@]}" logs --tail=40 backend 2>&1 | tee -a "$LOG_FILE"
  if [ -n "$PREVIOUS_TAG" ]; then
    log "Откат на ${PREVIOUS_TAG}"
    IMAGE_TAG="$PREVIOUS_TAG" "${COMPOSE[@]}" up -d --no-build 2>&1 | tee -a "$LOG_FILE"
  fi
  exit 1
fi

# Проверка API изнутри: Caddy отвечает наружу, но /health через него же
# подтверждает всю цепочку Caddy -> nginx frontend -> backend.
site="$(grep -E '^SITE_DOMAIN=' .env | cut -d= -f2- | tr -d '"')"
if [ -n "$site" ]; then
  code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 15 "https://${site}/health" || echo 000)"
  if [ "$code" = "200" ]; then
    log "https://${site}/health -> 200"
  else
    # Не считаем это фатальным: DNS или сертификат могут быть ещё не готовы
    # при первом деплое, а контейнеры при этом работают.
    log "ВНИМАНИЕ: https://${site}/health вернул ${code} — проверьте DNS и сертификат Caddy"
  fi
fi

echo "$IMAGE_TAG" > "$TAG_FILE"
log "Деплой завершён: ${IMAGE_TAG}"

# Чистим только висячие слои и старые образы старше недели.
# Без --volumes и без -a: базовые образы (redis, caddy) остаются, иначе
# следующий деплой качал бы их заново, а тома с данными остаются нетронутыми
# в любом случае.
docker image prune -f --filter "until=168h" >/dev/null 2>&1 || true
log "Очистка старых слоёв сборки выполнена"
