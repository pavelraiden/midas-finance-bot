# 🚀 Midas Financial Bot - Deployment Guide

**Goal:** Развернуть бота за 10 минут с помощью Docker и Docker Compose.

## 1. Prerequisites

- **Сервер/VPS:** Ubuntu 22.04 или новее
- **Docker:** Установленный Docker и Docker Compose
- **Supabase:** Аккаунт Supabase для базы данных PostgreSQL
- **API Ключи:**
  - Telegram Bot Token
  - Anthropic (Claude) API Key

## 2. Установка Docker

Если Docker не установлен, выполните следующие команды:

```bash
# Обновить пакеты
sudo apt-get update

# Установить необходимые пакеты
sudo apt-get install ca-certificates curl gnupg

# Добавить GPG ключ Docker
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Добавить репозиторий Docker
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Установить Docker Engine
sudo apt-get update
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin -y
```

## 3. Настройка базы данных (Supabase)

1. Создайте новый проект в [Supabase](https://supabase.com/).
2. Перейдите в **Project Settings -> Database**.
3. Найдите **Connection string** и скопируйте параметры:
   - `Host`
   - `Database name`
   - `User`
   - `Password`
   - `Port`

## 4. Развертывание бота

### Шаг 1: Клонировать репозиторий

```bash
git clone https://github.com/pavelraiden/midas-finance-bot.git
cd midas-finance-bot
```

### Шаг 2: Настроить `.env` файл

Скопируйте шаблон и отредактируйте его:

```bash
cp .env.example .env
nano .env
```

Заполните все необходимые переменные:

```env
# Telegram
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
ADMIN_CHAT_IDS=your_admin_chat_id # ID вашего чата для уведомлений об ошибках

# Database (Supabase)
DB_USER=postgres
DB_PASSWORD=your_supabase_db_password
DB_HOST=your_supabase_db_host
DB_PORT=5432
DB_NAME=postgres

# AI
ANTHROPIC_API_KEY=your_claude_api_key

# Security
ENCRYPTION_KEY=your_32_byte_fernet_key

# Redis (оставьте по умолчанию, если не меняли в docker-compose.yml)
REDIS_HOST=redis
REDIS_PORT=6379
```

**Как сгенерировать `ENCRYPTION_KEY`:**

```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### Шаг 3: Запустить бота

Используйте Docker Compose для сборки и запуска контейнеров в фоновом режиме:

```bash
docker-compose up --build -d
```

### Шаг 4: Проверить статус

Проверьте логи, чтобы убедиться, что бот запустился без ошибок:

```bash
docker-compose logs -f bot
```

Вы должны увидеть сообщение о том, что бот успешно запущен.

## 5. Управление ботом

- **Остановить бота:**
  ```bash
  docker-compose down
  ```

- **Перезапустить бота:**
  ```bash
  docker-compose restart
  ```

- **Обновить бота до последней версии:**
  ```bash
  git pull
  docker-compose up --build -d
  ```

## 6. Резервное копирование

Данные хранятся в volume `postgres_data`. Для резервного копирования используйте стандартные инструменты `pg_dump` или создайте snapshot вашего сервера.

## 7. Устранение неполадок

- **Ошибка `permission denied` при запуске Docker:**
  - Добавьте вашего пользователя в группу `docker`:
    ```bash
    sudo usermod -aG docker $USER
    newgrp docker
    ```

- **Бот не отвечает:**
  - Проверьте логи: `docker-compose logs -f bot`
  - Убедитесь, что `TELEGRAM_BOT_TOKEN` правильный.
  - Проверьте сетевые настройки и доступность Telegram API.

- **Ошибки подключения к базе данных:**
  - Проверьте правильность `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_PORT`, `DB_NAME`.
  - Убедитесь, что IP вашего сервера добавлен в Whitelist в настройках Supabase (если включено).

Для других проблем, пожалуйста, откройте issue на GitHub.
