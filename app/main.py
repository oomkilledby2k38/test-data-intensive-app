from fastapi import FastAPI, Response, HTTPException
from storage.s3_service import s3_service
from database.db_service import execute_query
from database.cache_service import get_cache, set_cache

app = FastAPI(title="Cities Cache API")

@app.get("/image/{file_name}")
async def get_image(file_name: str):
    image_data = s3_service.get_file(file_name)
    if image_data is None:
        raise HTTPException(status_code=404, detail="Файл не найден")
    return Response(content=image_data, media_type="image/jpeg")

@app.get("/cities/{code}")
def get_cities(code: str):
    cache_key = f"cities_{code.upper()}"
    cached_data = get_cache(cache_key)
    if cached_data:
        print("REDIS")
        return {"source": "cache", "data": cached_data}
    print(" POSTGRES")
    query = "SELECT name , population FROM city WHERE countrycode = :code"
    db_data = execute_query(query, {"code": code.upper()})
    set_cache(cache_key, db_data, expire=320)
    return {"source": "database", "data": db_data}

@app.get("/health")
def health_check():
    return {"status": "ok"}
