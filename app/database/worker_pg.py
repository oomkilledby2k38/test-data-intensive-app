import asyncio
import sys
import os
from dotenv import load_dotenv

# Явно загружаем .env из корневой директории проекта
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../..", ".env"))

import psycopg
from config.config import settings
from kafka.kafka_service import kafka_service

async def listen_to_pg_notify():
    """
    Слушает уведомления PostgreSQL и отправляет в Kafka
    """
    print(f"Connecting to: {settings.DATABASE_URL}")
    # В psycopg3 подключение делается через AsyncConnection
    conn = await psycopg.AsyncConnection.connect(settings.DATABASE_URL)
    
    # Для LISTEN/NOTIFY в psycopg3 важно, чтобы автокоммит был включен,
    # иначе уведомления могут "зависать" в транзакции
    await conn.set_autocommit(True)
    
    await conn.execute("LISTEN city_updates")
    print("LISTEN city_updates executed")
    
    await kafka_service.start()
    print("Worker listening for PostgreSQL notifications...")
    
    try:
        # В psycopg3 объект уведомлений находится прямо в подключении
        async for notify in conn.notifies():
            city_code = notify.payload
            await kafka_service.send_invalidation_event(city_code)
            print(f"Sent Kafka event for: {city_code}")
    except Exception as e:
        print(f"Error in listener: {e}")
    finally:
        await kafka_service.stop()
        await conn.close()

if __name__ == "__main__":
    try:
        asyncio.run(listen_to_pg_notify())
    except KeyboardInterrupt:
        print("\nWorker stopped by user")