import os
from dotenv import load_dotenv
import boto3
from botocore.client import Config
from sqlalchemy.pool import QueuePool

load_dotenv()

class Settings:
    MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT")
    ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
    SECRET_KEY = os.getenv("MINIO_SECRET_KEY")
    BUCKET_NAME = os.getenv("MINIO_BUCKET")

    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    DB_HOST = os.getenv("DB_HOST")
    DB_PORT = os.getenv("DB_PORT")
    DB_NAME = os.getenv("DB_NAME")
    DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", 10))
    DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", 20))
    DB_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", 3600))
    
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    
    REDIS_HOST = os.getenv("REDIS_HOST")
    REDIS_PORT = os.getenv("REDIS_PORT")
    
    KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

settings = Settings()


s3_client = boto3.client(
    's3',
    endpoint_url=settings.MINIO_ENDPOINT,
    aws_access_key_id=settings.ACCESS_KEY,
    aws_secret_access_key=settings.SECRET_KEY,
    config=Config(signature_version='s3v4')
)
