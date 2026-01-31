import asyncio
import json
from aiokafka import AIOKafkaConsumer
from config.config import settings

async def consume():
    consumer = AIOKafkaConsumer(
        "city_updates",
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id="cache_cleaners",
        auto_offset_reset="earliest"
    )
    await consumer.start()
    print("Worker started and listening to Kafka...")
    
    try:
        async for msg in consumer:
            try:
                raw_data = msg.value.decode('utf-8')
                data = json.loads(raw_data)
                print(f"Received event: {data}")
                
                if data.get("action") == "invalidate_cache":
                    city_code = data.get("code", "").upper()
                    if city_code:
                        from database.cache_service import r
                        cache_key = f"cities_{city_code}"
                        r.delete(cache_key)
                        print(f"Cache deleted for key: {cache_key}")
            
            except json.JSONDecodeError:
                print(f"Error: Received message is not valid JSON: {msg.value}")
            except Exception as e:
                print(f"Error during message processing: {e}")
    finally:
        await consumer.stop()

if __name__ == "__main__":
    try:
        asyncio.run(consume())
    except KeyboardInterrupt:
        print("Worker stopped by user")
