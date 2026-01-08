# 🚀 Быстрый старт: Добавление секретов в GitHub

## 📋 Что уже готово

✅ SSH ключ создан: `C:\Users\I7 11700k\.ssh\github_actions_deploy`  
✅ Workflow файл готов: `.github/workflows/deploy.yml`  
✅ Репозиторий: `git@github.com:dendy-san/public.git`

## 🔑 Как получить приватный SSH ключ

**Самый простой способ:**

```powershell
.\show-ssh-key.ps1
```

Этот скрипт покажет приватный ключ, который нужно скопировать в GitHub Secrets.

**Альтернативный способ (вручную):**

Откройте файл: `C:\Users\I7 11700k\.ssh\github_actions_deploy`

Скопируйте **весь** содержимое файла (включая строки `-----BEGIN OPENSSH PRIVATE KEY-----` и `-----END OPENSSH PRIVATE KEY-----`).

## 🔑 Шаг 1: Получите приватный SSH ключ

**Самый простой способ:**

```powershell
.\show-ssh-key.ps1
```

Скрипт покажет приватный ключ для копирования. Также можно открыть файл напрямую:
`C:\Users\I7 11700k\.ssh\github_actions_deploy`

**Важно:** Скопируйте **весь** ключ, включая строки `-----BEGIN OPENSSH PRIVATE KEY-----` и `-----END OPENSSH PRIVATE KEY-----`

## 🔐 Шаг 2: Добавьте секреты в GitHub

**Откройте:** https://github.com/dendy-san/public/settings/secrets/actions

**Нажмите:** `New repository secret` и добавьте каждый секрет:

### Обязательные секреты:

1. **VPS_HOST**
   - Name: `VPS_HOST`
   - Value: `ваш_ip_или_домен` (например: `192.168.1.100` или `example.com`)

2. **VPS_USER**
   - Name: `VPS_USER`
   - Value: `ваш_пользователь` (например: `root` или `deploy`)

3. **VPS_SSH_KEY**
   - Name: `VPS_SSH_KEY`
   - Value: вставьте приватный ключ, полученный на шаге 1 (весь текст, включая BEGIN/END):

```
-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAACmFlczI1Ni1jdHIAAAAGYmNyeXB0AAAAGAAAABCvtSpDDC
nCVd7ZSvr8EhTmAAAAGAAAAAEAAAAzAAAAC3NzaC1lZDI1NTE5AAAAIOPImx/kOomSYQHi
9jPjHbK9fGv/WpgSuLFX+FeRIrn+AAAAoOgGIEr7NhvMqarjhKuu9w/gL2BBRTwgcxoxul
PI4WDn6mwcBdNkurRrRzNUXmPLOnkKAO65LnhaAma+hfZWnhXl99c8Kl9ig5hWehqzogwL
+pnQjNNbF3WgDFeQ6aQ2K+B93PEVc9EHpN95Tq5g+zdAX3uMQ7HX4rcXOE4stL1jHi/7UY
r2BqzFFmjzVR5Udylx2armtB/MtfHUosecKWA=
-----END OPENSSH PRIVATE KEY-----
```

### Опциональные секреты (только если нужны нестандартные значения):

4. **VPS_SSH_PORT** (по умолчанию: `22`)
5. **VPS_PROJECT_PATH** (по умолчанию: `~/public`)
6. **BACKEND_PORT** (по умолчанию: `8000`)
7. **FRONTEND_PORT** (по умолчанию: `3000`)
8. **ADMIN_FRONTEND_PORT** (по умолчанию: `3001`)
9. **TELEGRAM_BOT_TOKEN** (опционально, для уведомлений)
10. **TELEGRAM_CHAT_ID** (опционально, для уведомлений)

## 📤 Шаг 3: Добавьте публичный SSH ключ на VPS

**Публичный ключ:**
```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOPImx/kOomSYQHi9jPjHbK9fGv/WpgSuLFX+FeRIrn+ github-actions-deploy
```

### Вариант 1: Автоматически (если у вас уже настроен SSH доступ к VPS)

```powershell
# Замените user@your-vps-host на ваши данные
ssh-copy-id -i "$env:USERPROFILE\.ssh\github_actions_deploy.pub" user@your-vps-host
```

### Вариант 2: Вручную

1. Подключитесь к VPS:
   ```bash
   ssh user@your-vps-host
   ```

2. Выполните на VPS:
   ```bash
   mkdir -p ~/.ssh
   chmod 700 ~/.ssh
   echo "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOPImx/kOomSYQHi9jPjHbK9fGv/WpgSuLFX+FeRIrn+ github-actions-deploy" >> ~/.ssh/authorized_keys
   chmod 600 ~/.ssh/authorized_keys
   ```

## ✅ Шаг 4: Убедитесь, что проект настроен на VPS

1. Проект должен быть склонирован в нужную директорию (по умолчанию: `~/public`)
2. На VPS должен быть файл `.env` с `ENVIRONMENT=prod`
3. На VPS должны быть установлены Docker и Docker Compose

## 🧪 Шаг 5: Протестируйте деплой

### Вариант 1: Ручной запуск через GitHub UI

1. Перейдите: https://github.com/dendy-san/public/actions
2. Выберите workflow: **Deploy to VPS**
3. Нажмите: **Run workflow**
4. Выберите ветку: **main**
5. Нажмите: **Run workflow**

### Вариант 2: Push в main ветку

```bash
git add .
git commit -m "Test GitHub Actions deploy"
git push origin main
```

Затем проверьте статус в: https://github.com/dendy-san/public/actions

## 📖 Подробная документация

- Полная инструкция: `GITHUB_ACTIONS_SETUP.md`
- Файл с инструкциями (после запуска скрипта): `GITHUB_SECRETS_SETUP.txt`

## 🔧 Интерактивная настройка (опционально)

Если хотите заполнить все данные интерактивно:

```powershell
.\setup-github-secrets.ps1
```

Скрипт соберет все данные и создаст файл `GITHUB_SECRETS_SETUP.txt` с готовыми инструкциями.



