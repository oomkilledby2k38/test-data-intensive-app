import json
from aiokafka import AIOKafkaProducer
from config.config import settings # Используем твои настройки

class KafkaService:
    def __init__(self):
        self.producer = None

    async def start(self):
        self.producer = AIOKafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS
        )
        await self.producer.start()
        print("Kafka Producer started")

    async def stop(self):
        if self.producer:
            await self.producer.stop()
            print("Kafka Producer stopped")

    async def send_invalidation_event(self, city_code: str):
        if not self.producer:
            await self.start()
            
        message = {
            "action": "invalidate_cache", 
            "code": city_code.upper()
        }
        
        await self.producer.send_and_wait(
            "city_updates", 
            json.dumps(message).encode('utf-8')
        )
        print(f"Kafka: Sent invalidation event for {city_code}")

# Создаем экземпляр сервиса
kafka_service = KafkaService()