from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool
from config.config import settings
import asyncio


engine = create_engine(
    settings.DATABASE_URL,
    poolclass=QueuePool,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_recycle=settings.DB_POOL_RECYCLE
)

def execute_query(query: str, params: dict = None):
    """
    Простейшая функция: открыл, выполнил, отдал результат.
    Пример: execute_query("SELECT * FROM city WHERE countrycode = :code", {"code": "NLD"})
    """
    with engine.connect() as conn:
        result = conn.execute(text(query), params or {})
        

        if result.returns_rows:
            return [dict(row._mapping) for row in result]
        

        conn.commit()
        return {"status": "ok", "count": result.rowcount}

async def listen_to_pg_notify():
    """
    Слушает уведомления PostgreSQL и отправляет в Kafka
    """
    import psycopg
    from kafka.kafka_service import send_update_event
    
    conn = await psycopg.AsyncConnection.connect(settings.DATABASE_URL)
    await conn.execute("LISTEN city_updates")
    
    async with conn.notifies():
        async for notify in conn.notifies():
            city_code = notify.payload
            await send_update_event(city_code)
            print(f" Получено уведомление из PG: {city_code}")

if __name__ == "__main__":
    res = execute_query("SELECT 1")
    print(f"Проверка связи с БД: {res}")