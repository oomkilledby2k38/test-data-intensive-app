# Архитектура проекта

## Обзор

Проект демонстрирует паттерн автоматической инвалидации кеша через события. При изменении данных в БД, кеш в Redis автоматически обновляется.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            PostgreSQL                                   │
│  ┌──────────┐    ┌─────────────────┐    ┌─────────────────────────────┐ │
│  │  city    │───→│  TRIGGER        │───→│  NOTIFY 'city_updates'      │ │
│  │  table   │    │  notify_city_   │    │  с кодом страны (BGR)       │ │
│  └──────────┘    │  update()       │    └─────────────────────────────┘ │
│                  └─────────────────┘                                       │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ↓ LISTEN/NOTIFY
┌─────────────────────────────────────────────────────────────────────────┐
│                       worker_pg.py (Async)                               │
│  • Подключается к PostgreSQL через psycopg.AsyncConnection              │
│  • LISTEN city_updates                                                    │
│  • Получает уведомления → отправляет в Kafka                             │
│  • Использует kafka_service.send_invalidation_event()                    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ↓ Kafka topic: city_updates
┌─────────────────────────────────────────────────────────────────────────┐
│                          Kafka                                           │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  Topic: city_updates                                            │   │
│  │  Message: {"action": "invalidate_cache", "code": "BGR"}        │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ↓ Consumer
┌─────────────────────────────────────────────────────────────────────────┐
│                    cleaner/worker.py (Async)                             │
│  • AIOKafkaConsumer слушает topic city_updates                           │
│  • Получает сообщение из Kafka                                            │
│  • Удаляет кеш из Redis: `r.delete(cities_BGR)`                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ↓ Redis DELETE
┌─────────────────────────────────────────────────────────────────────────┐
│                            Redis                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  Key: cities_BGR                                              │   │
│  │  Value: [{"name": "Dobric", "population": 111001}, ...]      │   │
│  │  Operation: DELETE                                            │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                           FastAPI (main.py)                              │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  GET /cities/BGR                                                │   │
│  │  1. Проверяет Redis: get_cache(cities_BGR)                      │   │
│  │     └─ Нет кеша → execute_query() в PostgreSQL                 │   │
│  │     └─ set_cache(cities_BGR, data, 320)                         │   │
│  │  2. Возвращает данные                                           │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  GET /image/{file_name}                                          │   │
│  │  • Загружает файл из MinIO через S3-compatible API               │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  GET /health                                                       │   │
│  │  • Проверка состояния сервиса                                      │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

## Поток данных

### При ручном обновлении БД:

1. **SQL UPDATE** в PostgreSQL
   ```sql
   UPDATE city SET population = 999999 WHERE name = 'Dobric';
   ```

2. **TRIGGER срабатывает** → `notify_city_update()`
   ```sql
   NOTIFY city_updates, 'BGR';
   ```

3. **worker_pg.py получает уведомление** → отправляет в Kafka
   ```python
   await kafka_service.send_invalidation_event('BGR')
   ```

4. **cleaner/worker.py получает сообщение** → удаляет кеш
   ```python
   r.delete('cities_BGR')
   ```

5. **Следующий GET /cities/BGR** → кеша нет → берет из PostgreSQL

## Компоненты

| Компонент | Файл | Роль |
|-----------|------|------|
| FastAPI | `main.py` | API сервер, кеширование |
| PostgreSQL | БД | Хранение данных + TRIGGER |
| Kafka | Мессенджер | Событийная шина |
| Redis | Кеш-сервер | Кеширование результатов |
| worker_pg.py | `database/worker_pg.py` | PostgreSQL → Kafka |
| worker.py | `cleaner/worker.py` | Kafka → Redis |
| docker-compose.yml | - | Оркестрация сервисов |

## API Endpoints

### GET /cities/{code}
Получает города по коду страны с кешированием.

```bash
curl http://localhost:8000/cities/BGR
```

Ответ:
```json
{
  "source": "cache",
  "data": [
    {"name": "Dobric", "population": 111001}
  ]
}
```

### GET /image/{file_name}
Загружает файл из MinIO.

```bash
curl http://localhost:8000/image/test.jpg
```

### GET /health
Проверка состояния сервиса.

```bash
curl http://localhost:8000/health
```

## Запуск

### 1. Запустить сервисы через docker-compose
```bash
docker-compose up -d
```

### 2. Применить триггер в PostgreSQL
```bash
psql postgresql://postgres:root@localhost:5432/tutorial -f app/database/trigger.sql
```

Или через docker:
```bash
docker exec postgres-tutorial psql -U postgres -d tutorial -c \
  "CREATE OR REPLACE FUNCTION notify_city_update() RETURNS TRIGGER AS \$\$ \
   BEGIN PERFORM pg_notify('city_updates', NEW.countrycode); RETURN NEW; END; \$\$ LANGUAGE plpgsql;"

docker exec postgres-tutorial psql -U postgres -d tutorial -c \
  "CREATE TRIGGER trigger_city_update AFTER UPDATE ON city FOR EACH ROW EXECUTE FUNCTION notify_city_update();"
```

### 3. Запустить FastAPI
```bash
cd app
export PYTHONPATH=$PYTHONPATH:$(pwd)
./venv/bin/uvicorn main:app --reload
```

### 4. Запустить worker для Kafka consumer
```bash
cd app
export PYTHONPATH=$PYTHONPATH:$(pwd)
./venv/bin/python cleaner/worker.py
```

### 5. Запустить worker для PostgreSQL → Kafka
```bash
cd app
export PYTHONPATH=$PYTHONPATH:$(pwd)
./venv/bin/python database/worker_pg.py
```

## Тестирование

1. Получить данные (кешируется):
   ```bash
   curl http://localhost:8000/cities/BGR
   ```

2. Изменить данные вручную в БД:
   ```bash
   psql postgresql://postgres:root@localhost:5432/tutorial -c \
     "UPDATE city SET population = 999999 WHERE name = 'Dobric';"
   ```

3. Снова получить данные (кеш автоматически инвалидирован):
   ```bash
   curl http://localhost:8000/cities/BGR
   ```



- **Автоматическая инвалидация кеша** при прямых изменениях в БД
-  **Минимальная нагрузка** (LISTEN/NOTIFY встроен в PostgreSQL)
-  **Kafka гарантирует доставку** сообщений
-  **Расширяемая архитектура** (можно добавить потребителей)
- **Connection pooling** для оптимизации подключений к БД
- **Единый конфиг** через .env файл





- `.env` файлы добавлены в `.gitignore` для безопасности
- Для локального тестирования используется MinIO как S3-совместимое хранилище
- PostgreSQL TRIGGER создается один раз при установке проекта
