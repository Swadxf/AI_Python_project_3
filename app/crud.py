from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app import models, schemas, utils
from app.cache import (
    get_cached_url, set_cached_url, invalidate_url_cache,
    get_cached_stats, set_cached_stats, invalidate_stats_cache
)
from datetime import datetime


async def create_user(db: AsyncSession, user: schemas.UserCreate):
    hashed = utils.hash_password(user.password)
    db_user = models.User(email=user.email, hashed_password=hashed)
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


async def get_user_by_email(db: AsyncSession, email: str):
    result = await db.execute(select(models.User).where(models.User.email == email))
    return result.scalar_one_or_none()


async def create_link(db: AsyncSession, link: schemas.LinkCreate, user_id: int | None = None):
    short_code = link.custom_alias or utils.generate_short_code()

    if link.custom_alias:
        exists = await db.execute(select(models.Link).where(models.Link.short_code == short_code))
        if exists.scalar_one_or_none():
            raise ValueError("Alias уже занят")

    db_link = models.Link(
        short_code=short_code,
        original_url=str(link.original_url),
        custom_alias=link.custom_alias,
        expires_at=link.expires_at.replace(tzinfo=None) if link.expires_at else None,
        owner_id=user_id
    )
    db.add(db_link)
    await db.commit()
    await db.refresh(db_link)

    # Кэшируем URL сразу
    await set_cached_url(short_code, db_link.original_url)

    return db_link


async def get_link(db: AsyncSession, short_code: str) -> models.Link | None:
    # Сначала Redis (только для URL, но объект берём из БД)
    cached_url = await get_cached_url(short_code)
    if cached_url:
        # Всё равно берём полный объект из БД для owner_id и stats
        result = await db.execute(select(models.Link).where(models.Link.short_code == short_code))
        link = result.scalar_one_or_none()
        if link:
            return link  # ← полный объект с owner_id
        return None

    # Обычный путь
    result = await db.execute(select(models.Link).where(models.Link.short_code == short_code))
    link = result.scalar_one_or_none()

    if not link:
        return None

    if link.expires_at and link.expires_at < datetime.utcnow():
        return None

    await set_cached_url(short_code, link.original_url)
    return link


async def increment_click(db: AsyncSession, short_code: str):
    await db.execute(
        update(models.Link)
        .where(models.Link.short_code == short_code)
        .values(clicks=models.Link.clicks + 1, last_clicked=datetime.utcnow())
    )
    await db.commit()

    # Инвалидируем статистику
    await invalidate_stats_cache(short_code)


async def update_link(db: AsyncSession, short_code: str, data: schemas.LinkUpdate, user_id: int):
    link = await get_link(db, short_code)
    if not link or link.owner_id != user_id:
        return None

    if data.original_url:
        link.original_url = str(data.original_url)
    if data.expires_at is not None:
        link.expires_at = data.expires_at

    await db.commit()
    await db.refresh(link)

    # Очистка кэша
    await invalidate_url_cache(short_code)
    await invalidate_stats_cache(short_code)

    return link


async def delete_link(db: AsyncSession, short_code: str, user_id: int) -> bool:
    link = await get_link(db, short_code)
    if not link or link.owner_id != user_id:
        return False

    await db.delete(link)
    await db.commit()

    # Очистка кэша
    await invalidate_url_cache(short_code)
    await invalidate_stats_cache(short_code)

    return True