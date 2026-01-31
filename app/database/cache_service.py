import redis
import json
from config.config import settings


r = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0)

def get_cache(key: str):
    data = r.get(key)
    return json.loads(data) if data else None

def set_cache(key: str, value: any, expire=60):
    r.setex(key, expire, json.dumps(value))