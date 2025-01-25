#!/bin/bash

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Фиксированные параметры репозитория
GIT_URL="https://github.com/Fen1xWAR/VideoServer"
GIT_BRANCH="master"
# Конфигурация по умолчанию
DEFAULT_APP_NAME="VideoServer"
DEFAULT_INSTALL_DIR="/opt/${DEFAULT_APP_NAME}"
DEFAULT_PORT=8000
DEFAULT_USER=$(id -un)

# Функции
check_port() {
    ss -tuln | grep -q ":${1} "
    return $?
}

find_free_port() {
    local port=$1
    while (( port <= 65535 )); do
        if ! check_port $port; then
            echo $port
            return 0
        fi
        ((port++))
    done
    echo "none"
    return 1
}

# Приветствие
clear
echo -e "${GREEN}"
echo "=== Установщик VideoServer ==="
echo -e "${NC}"
echo "Официальный репозиторий: ${CYAN}${GIT_URL}${NC}"
echo "Ветка: ${CYAN}${GIT_BRANCH}${NC}"
echo "-----------------------------------------"

# Ввод параметров
echo -e "${YELLOW}1. Основные настройки:${NC}"
read -p "   Имя приложения [${DEFAULT_APP_NAME}]: " APP_NAME
APP_NAME=${APP_NAME:-$DEFAULT_APP_NAME}

read -e -p "   Директория установки [${DEFAULT_INSTALL_DIR}]: " INSTALL_DIR
INSTALL_DIR=${INSTALL_DIR:-$DEFAULT_INSTALL_DIR}

while true; do
    read -p "   Порт приложения [${DEFAULT_PORT}]: " PORT
    PORT=${PORT:-$DEFAULT_PORT}

    if [[ ! $PORT =~ ^[0-9]+$ ]]; then
        echo -e "${RED}Ошибка: порт должен быть числом!${NC}"
        continue
    fi

    if (( PORT < 1 || PORT > 65535 )); then
        echo -e "${RED}Ошибка: недопустимый номер порта!${NC}"
        continue
    fi

    if check_port $PORT; then
        echo -e -n "${YELLOW}Порт ${PORT} занят!${NC} "
        read -p "Попробовать найти свободный порт? [Y/n]: " FIND_FREE
        FIND_FREE=${FIND_FREE:-Y}

        if [[ $FIND_FREE =~ ^[Yy] ]]; then
            NEW_PORT=$(find_free_port $PORT)
            if [[ $NEW_PORT == "none" ]]; then
                echo -e "${RED}Не удалось найти свободный порт!${NC}"
                exit 1
            fi
            echo -e "${GREEN}Найден свободный порт: ${NEW_PORT}${NC}"
            PORT=$NEW_PORT
            break
        else
            continue
        fi
    else
        break
    fi
done

echo -e "\n${YELLOW}2. Настройка сервиса:${NC}"
read -p "   Установить как systemd сервис? [y/N]: " INSTALL_SERVICE
INSTALL_SERVICE=${INSTALL_SERVICE:-"N"}

if [[ $INSTALL_SERVICE =~ ^[Yy] ]]; then
    read -p "   Пользователь для сервиса [${DEFAULT_USER}]: " SERVICE_USER
    SERVICE_USER=${SERVICE_USER:-$DEFAULT_USER}

    echo -e "\n${YELLOW}3. Дополнительные настройки:${NC}"
    read -p "   Открыть порт в firewall? [y/N]: " FIREWALL_SETUP
    FIREWALL_SETUP=${FIREWALL_SETUP:-"N"}
fi

# Подтверждение установки
echo -e "\n${YELLOW}=== Параметры установки ===${NC}"
echo -e "Репо:            ${CYAN}${GIT_URL}${NC}"
echo -e "Ветка:           ${CYAN}${GIT_BRANCH}${NC}"
echo -e "Имя приложения:  ${GREEN}${APP_NAME}${NC}"
echo -e "Директория:      ${GREEN}${INSTALL_DIR}${NC}"
echo -e "Порт:            ${GREEN}${PORT}${NC}"
echo -e "Установка сервиса: ${GREEN}$([[ $INSTALL_SERVICE =~ ^[Yy] ]] && echo "Да" || echo "Нет")${NC}"

if [[ $INSTALL_SERVICE =~ ^[Yy] ]]; then
    echo -e "Пользователь сервиса: ${GREEN}${SERVICE_USER}${NC}"
    echo -e "Настройка firewall:   ${GREEN}$([[ $FIREWALL_SETUP =~ ^[Yy] ]] && echo "Да" || echo "Нет")${NC}"
fi

read -p "Выполнить установку? [y/N]: " CONFIRM
if [[ ! $CONFIRM =~ ^[Yy] ]]; then
    echo -e "${RED}Установка отменена!${NC}"
    exit 0
fi

# ========= Начало установки =========
echo -e "\n${GREEN}=== Начало установки ===${NC}"

# Проверка прав
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Ошибка: скрипт должен быть запущен с правами root!${NC}"
    exit 1
fi

# Установка системных зависимостей
echo -n "1. Установка системных пакетов... "
apt-get update > /dev/null
apt-get install -y python3 python3-pip python3-venv git > /dev/null
echo -e "${GREEN}OK${NC}"

# Подготовка директории
echo -n "2. Подготовка директории... "
if [[ -d "${INSTALL_DIR}" ]]; then
    TIMESTAMP=$(date +%Y%m%d%H%M%S)
    mv "${INSTALL_DIR}" "${INSTALL_DIR}.bak-${TIMESTAMP}" > /dev/null
    echo -n "(резервная копия создана)... "
fi

mkdir -p "${INSTALL_DIR}" > /dev/null

# Клонирование репозитория
echo -n "3. Клонирование репозитория... "
git clone --branch "${GIT_BRANCH}" "${GIT_URL}" "${INSTALL_DIR}" > /dev/null

if [[ -n "$REPO_SUBDIR" ]]; then
    mv "${INSTALL_DIR}/${REPO_SUBDIR}"/* "${INSTALL_DIR}"/
    rm -rf "${INSTALL_DIR}/${REPO_SUBDIR}"
fi
echo -e "${GREEN}OK${NC}"

# Проверка необходимых файлов
echo -n "4. Проверка структуры проекта... "
if [[ ! -f "${INSTALL_DIR}/requirements.txt" ]]; then
    echo -e "${RED}Ошибка: файл requirements.txt не найден!${NC}"
    exit 1
fi

if [[ ! -f "${INSTALL_DIR}/main.py" ]]; then
    echo -e "${RED}Ошибка: файл main.py не найден!${NC}"
    exit 1
fi
echo -e "${GREEN}OK${NC}"

# Настройка виртуального окружения
echo -n "5. Настройка Python окружения... "
python3 -m venv "${INSTALL_DIR}/venv" > /dev/null
"${INSTALL_DIR}/venv/bin/pip" install --upgrade pip > /dev/null
"${INSTALL_DIR}/venv/bin/pip" install -r "${INSTALL_DIR}/requirements.txt" > /dev/null
echo -e "${GREEN}OK${NC}"

# Настройка systemd сервиса
if [[ $INSTALL_SERVICE =~ ^[Yy] ]]; then
    echo -n "6. Настройка systemd сервиса... "

    SERVICE_FILE="/etc/systemd/system/${APP_NAME}.service"

    # Создание файла сервиса
    cat > "${SERVICE_FILE}" << EOF
[Unit]
Description=${APP_NAME} Service
After=network.target

[Service]
User=${SERVICE_USER}
WorkingDirectory=${INSTALL_DIR}
ExecStart=${INSTALL_DIR}/venv/bin/uvicorn main:app --host 0.0.0.0 --port ${PORT}
Restart=always
Environment="PATH=${INSTALL_DIR}/venv/bin:\$PATH"

[Install]
WantedBy=multi-user.target
EOF

    # Настройка прав
    chown -R "${SERVICE_USER}" "${INSTALL_DIR}"
    systemctl daemon-reload > /dev/null
    systemctl enable "${APP_NAME}" > /dev/null
    systemctl start "${APP_NAME}" > /dev/null
    echo -e "${GREEN}OK${NC}"

    # Настройка firewall
    if [[ $FIREWALL_SETUP =~ ^[Yy] ]]; then
        echo -n "7. Настройка firewall... "
        ufw allow ${PORT}/tcp > /dev/null
        echo -e "${GREEN}OK${NC}"
    fi
fi

# Завершение установки
echo -e "\n${GREEN}=== Установка завершена успешно! ===${NC}"
echo -e "Доступные команды:"
[[ $INSTALL_SERVICE =~ ^[Yy] ]] && echo -e "  Проверить статус: ${YELLOW}systemctl status ${APP_NAME}${NC}"
echo -e "  Тестовый запрос: ${YELLOW}curl http://localhost:${PORT}${NC}"
echo -e "  Логи приложения: ${YELLOW}journalctl -u ${APP_NAME} -f${NC}"
[[ $FIREWALL_SETUP =~ ^[Yy] ]] && echo -e "  Открытый порт:    ${YELLOW}${PORT}/tcp${NC}"
echo -e "\n${GREEN}Приложение доступно по адресу: http://ваш-сервер:${PORT}${NC}"