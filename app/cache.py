import redis.asyncio as redis
import json
from datetime import datetime
from app.config import settings



redis_client = redis.from_url(settings.redis_url, decode_responses=True)


async def get_cached_url(short_code: str) -> str | None:
    return await redis_client.get(f"url:{short_code}")


async def set_cached_url(short_code: str, original_url: str, ttl: int = 86400):
    await redis_client.setex(f"url:{short_code}", ttl, original_url)


async def invalidate_url_cache(short_code: str):
    await redis_client.delete(f"url:{short_code}")


async def get_cached_stats(short_code: str) -> dict | None:
    data = await redis_client.get(f"stats:{short_code}")
    if not data:
        return None
    
    stats = json.loads(data)
    # Опционально: верни datetime из строк (если нужно в коде)
    for key in ['created_at', 'last_clicked', 'expires_at']:
        if key in stats and stats[key]:
            stats[key] = datetime.fromisoformat(stats[key])
    
    return stats


async def set_cached_stats(short_code: str, stats: dict, ttl: int = 300):
    # Конвертируем все datetime в строки ISO
    serializable_stats = stats.copy()
    for key in ['created_at', 'last_clicked', 'expires_at']:
        if key in serializable_stats and isinstance(serializable_stats[key], datetime):
            serializable_stats[key] = serializable_stats[key].isoformat()

    await redis_client.setex(f"stats:{short_code}", ttl, json.dumps(serializable_stats))


async def invalidate_stats_cache(short_code: str):
    await redis_client.delete(f"stats:{short_code}")
    