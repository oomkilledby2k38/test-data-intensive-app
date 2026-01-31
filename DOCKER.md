# Docker Deployment

## Multi-Stage Dockerfile

Проект использует multi-stage Dockerfile для оптимизации размера образа:

**Stage 1: Builder**
- Устанавливает gcc для сборки зависимостей
- Создает виртуальное окружение
- Устанавливает все зависимости из requirements.txt

**Stage 2: Runtime**
- Копирует только venv из builder
- Устанавливает Supervisor для управления тремя процессами
- Минимальный размер образа

## Решение проблемы с тремя процессами

Для запуска трех процессов в одном контейнере используется **Supervisor**:

```
┌─────────────────────────────────────────────────────────┐
│                    Docker Container                      │
│                                                          │
│  ┌───────────────────────────────────────────────────┐ │
│  │              Supervisor (PID 1)                    │ │
│  │                                                     │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │ │
│  │  │  FastAPI    │  │  Kafka      │  │  Postgres │ │ │
│  │  │  uvicorn    │  │  Consumer   │  │  Worker   │ │ │
│  │  │  :8000      │  │  worker.py  │  │  worker_  │ │ │
│  │  └─────────────┘  └─────────────┘  │  pg.py     │ │ │
│  │                                     └────────────┘ │ │
│  └───────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### Supervisor конфигурация (`supervisord.conf`)

Три программы управляются Supervisor:
- **fastapi**: FastAPI сервер на порту 8000
- **kafka_consumer**: Потребитель Kafka (cleaner/worker.py)
- **pg_notify_worker**: PostgreSQL → Kafka bridge (database/worker_pg.py)

### Преимущества подхода

✅ **Один контейнер** - все процессы в одном месте
✅ **Минимальный overhead** - одна база Python, одни зависимости
✅ **Автоматический restart** - если процесс упадет, Supervisor перезапустит
✅ **Единое логирование** - все логи идут в stdout/stderr
✅ **Multi-stage** - оптимизированный размер образа

## Быстрый запуск

### Сборка и запуск через docker-compose

```bash
# Запуск всех сервисов
docker-compose up -d

# Проверка статуса
docker-compose ps

# Просмотр логов
docker-compose logs -f app

# Остановка
docker-compose down
```

### Тестирование

```bash
# Проверка FastAPI
curl http://localhost:8000/health

# Получение городов (кешируется)
curl http://localhost:8000/cities/BGR

# Обновление данных в PostgreSQL (триггер автоматически инвалидирован кеш)
docker exec postgres-tutorial psql -U postgres -d tutorial -c \
  "UPDATE city SET population = 999999 WHERE name = 'Dobric';"

# Снова получаем - данные новые!
curl http://localhost:8000/cities/BGR
```

## Команды для работы с Docker

### Сборка образа

```bash
docker build -t cities-cache-app ./app
```

### Запуск контейнера

```bash
docker run -p 8000:8000 \
  -e MINIO_ENDPOINT=http://minio-test:9000 \
  -e DB_HOST=postgres-tutorial \
  -e REDIS_HOST=redis-for-cache \
  -e KAFKA_BOOTSTRAP_SERVERS=kafka-test:9092 \
  cities-cache-app
```

### Просмотр логов отдельных процессов

```bash
# Все логи
docker logs -f cities-cache-app

# Только FastAPI
docker exec cities-cache-app supervisorctl tail -f fastapi

# Только Kafka consumer
docker exec cities-cache-app supervisorctl tail -f kafka_consumer

# Только PostgreSQL worker
docker exec cities-cache-app supervisorctl tail -f pg_notify_worker
```

### Управление процессами

```bash
docker exec cities-cache-app supervisorctl status
docker exec cities-cache-app supervisorctl stop fastapi
docker exec cities-cache-app supervisorctl start fastapi
docker exec cities-cache-app supervisorctl restart kafka_consumer
```

## Dockerfile структура

```
# Stage 1: Builder
FROM python:3.14-slim as builder
- Установка gcc
- Копирование requirements.txt
- Создание venv
- Установка зависимостей

# Stage 2: Runtime
FROM python:3.14-slim
- Установка supervisor
- Копирование venv из builder
- Копирование приложения
- Запуск supervisor
```

## docker-compose.yml

Сервис `app` в docker-compose.yml:
- Билдится из `app/Dockerfile`
- Зависит от postgres, kafka, redis
- Передает все необходимые переменные окружения
- Подключен к сети tutorial_network

## Переменные окружения для Docker

При запуске через docker-compose используются контейнерные имена:
- `DB_HOST=postgres-tutorial`
- `REDIS_HOST=redis-for-cache`
- `KAFKA_BOOTSTRAP_SERVERS=kafka-test:9092`

Для локального запуска (не через docker-compose):
- `DB_HOST=localhost`
- `REDIS_HOST=localhost`
- `KAFKA_BOOTSTRAP_SERVERS=localhost:9092`
