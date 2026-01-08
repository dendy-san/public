#!/bin/bash
# Скрипт для диагностики SSH на VPS
# Выполните на VPS: bash diagnose-ssh-on-vps.sh

echo "🔍 Диагностика SSH настройки на VPS"
echo ""

# Проверка директории .ssh
echo "1. Проверка директории ~/.ssh:"
if [ -d ~/.ssh ]; then
    echo "   ✅ Директория существует"
    ls -la ~/.ssh/
    echo ""
    
    # Проверка прав
    DIR_PERMS=$(stat -c "%a" ~/.ssh 2>/dev/null || stat -f "%OLp" ~/.ssh 2>/dev/null)
    if [ "$DIR_PERMS" = "700" ]; then
        echo "   ✅ Права директории правильные: 700"
    else
        echo "   ❌ Права директории неправильные: $DIR_PERMS (должно быть 700)"
        echo "   🔧 Исправление: chmod 700 ~/.ssh"
        chmod 700 ~/.ssh
    fi
else
    echo "   ❌ Директория не существует"
    echo "   🔧 Создание: mkdir -p ~/.ssh && chmod 700 ~/.ssh"
    mkdir -p ~/.ssh
    chmod 700 ~/.ssh
fi
echo ""

# Проверка authorized_keys
echo "2. Проверка файла ~/.ssh/authorized_keys:"
if [ -f ~/.ssh/authorized_keys ]; then
    echo "   ✅ Файл существует"
    ls -la ~/.ssh/authorized_keys
    echo ""
    
    # Проверка прав
    FILE_PERMS=$(stat -c "%a" ~/.ssh/authorized_keys 2>/dev/null || stat -f "%OLp" ~/.ssh/authorized_keys 2>/dev/null)
    if [ "$FILE_PERMS" = "600" ]; then
        echo "   ✅ Права файла правильные: 600"
    else
        echo "   ❌ Права файла неправильные: $FILE_PERMS (должно быть 600)"
        echo "   🔧 Исправление: chmod 600 ~/.ssh/authorized_keys"
        chmod 600 ~/.ssh/authorized_keys
    fi
    echo ""
    
    # Проверка наличия ключа
    echo "3. Поиск ключа github-actions-deploy:"
    if grep -q "github-actions-deploy" ~/.ssh/authorized_keys; then
        echo "   ✅ Ключ найден:"
        grep "github-actions-deploy" ~/.ssh/authorized_keys
        echo ""
        
        # Проверка формата ключа
        KEY_LINE=$(grep "github-actions-deploy" ~/.ssh/authorized_keys)
        if echo "$KEY_LINE" | grep -q "^ssh-ed25519 "; then
            echo "   ✅ Формат ключа правильный"
        else
            echo "   ⚠️  Формат ключа может быть неправильным"
        fi
        
        # Проверка на переносы строк
        if echo "$KEY_LINE" | grep -q $'\n'; then
            echo "   ❌ Ключ содержит переносы строк (неправильно!)"
        else
            echo "   ✅ Ключ в одной строке (правильно)"
        fi
    else
        echo "   ❌ Ключ не найден!"
        echo "   🔧 Добавьте ключ:"
        echo "   echo 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOPImx/kOomSYQHi9jPjHbK9fGv/WpgSuLFX+FeRIrn+ github-actions-deploy' >> ~/.ssh/authorized_keys"
    fi
else
    echo "   ❌ Файл не существует"
    echo "   🔧 Создание файла:"
    echo "   touch ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
    touch ~/.ssh/authorized_keys
    chmod 600 ~/.ssh/authorized_keys
fi
echo ""

# Проверка конфигурации SSH сервера
echo "4. Проверка конфигурации SSH сервера:"
if [ -f /etc/ssh/sshd_config ]; then
    echo "   Проверка важных параметров:"
    grep -E "^PubkeyAuthentication|^AuthorizedKeysFile|^PasswordAuthentication" /etc/ssh/sshd_config | grep -v "^#" || echo "   (используются значения по умолчанию)"
fi
echo ""

echo "=========================================="
echo "✅ Диагностика завершена"
echo "=========================================="
echo ""
echo "Если проблемы остались, проверьте:"
echo "1. Права: ~/.ssh должен быть 700, authorized_keys - 600"
echo "2. Ключ должен быть в одной строке без переносов"
echo "3. Владелец файлов должен быть правильным пользователем"
echo ""

