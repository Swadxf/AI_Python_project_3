from fastapi import Query
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete
import qrcode
import asyncio
import io
from datetime import datetime, timedelta

from app import models, schemas, crud, dependencies, cache
from app.database import get_db
from app.config import settings
from app.dependencies import get_current_active_user


router = APIRouter(tags=["links"])


@router.post("/links/shorten", response_model=schemas.LinkResponse)
async def shorten(
    data: schemas.LinkCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(dependencies.get_current_user_optional)
):
    user_id = current_user.id if current_user else None
    try:
        link = await crud.create_link(db, data, user_id)
        return schemas.LinkResponse(
            short_code=link.short_code,
            short_url=f"{settings.base_url}/{link.short_code}",
            original_url=link.original_url,
            expires_at=link.expires_at
        )
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/{short_code}")
async def redirect(short_code: str, db: AsyncSession = Depends(get_db)):
    link = await crud.get_link(db, short_code)
    
    if not link:
        await db.execute(
            delete(models.Link).where(models.Link.short_code == short_code)
        )
        await db.commit()
        raise HTTPException(404, "Ссылка не найдена или истекла")
    
    await crud.increment_click(db, short_code)
    return RedirectResponse(link.original_url, status_code=307)


@router.get("/links/{short_code}/stats", response_model=schemas.LinkStats)
async def get_stats(
    short_code: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(dependencies.get_current_active_user)
):
    # Сначала кэш
    cached = await cache.get_cached_stats(short_code)
    if cached:
        return cached

    link = await crud.get_link(db, short_code)
    if not link:
        raise HTTPException(404, "Ссылка не найдена")
    if link.owner_id != current_user.id:
        raise HTTPException(403, "Не ваша ссылка")

    stats = {
        "original_url": link.original_url,
        "short_code": link.short_code,
        "custom_alias": link.custom_alias,
        "created_at": link.created_at,
        "clicks": link.clicks,
        "last_clicked": link.last_clicked,
        "expires_at": link.expires_at
    }

    # Кэшируем на 5 минут
    await cache.set_cached_stats(short_code, stats)

    return stats


@router.put("/links/{short_code}", response_model=schemas.LinkResponse)
async def update_link(
    short_code: str,
    data: schemas.LinkUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(dependencies.get_current_active_user)
):
    updated = await crud.update_link(db, short_code, data, current_user.id)
    if not updated:
        raise HTTPException(404, "Ссылка не найдена или не ваша")
    return schemas.LinkResponse(
        short_code=updated.short_code,
        short_url=f"{settings.base_url}/{updated.short_code}",
        original_url=updated.original_url,
        expires_at=updated.expires_at
    )


@router.delete("/links/{short_code}")
async def delete_link(
    short_code: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(dependencies.get_current_active_user)
):
    success = await crud.delete_link(db, short_code, current_user.id)
    if not success:
        raise HTTPException(404, "Ссылка не найдена или не ваша")
    return {"message": "Ссылка удалена"}

@router.delete("/links/cleanup")
async def cleanup_links(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user),
    mode: str = Query("expired", description="expired (истёкшие) или inactive (неактивные)"),
    inactive_days: int = Query(30, description="Для inactive: сколько дней без кликов")
):
    if mode not in ["expired", "inactive"]:
        raise HTTPException(400, "mode должен быть 'expired' или 'inactive'")

    query = delete(models.Link).where(models.Link.owner_id == current_user.id)

    if mode == "expired":
        query = query.where(
            models.Link.expires_at.is_not(None),
            models.Link.expires_at < datetime.utcnow()
        )
    elif mode == "inactive":
        threshold = datetime.utcnow() - timedelta(days=inactive_days)
        query = query.where(
            models.Link.clicks == 0,
            models.Link.created_at < threshold
        )

    result = await db.execute(query)
    await db.commit()

    deleted_count = result.rowcount

    return {
        "deleted": deleted_count,
        "message": f"Удалено {deleted_count} ссылок ({mode})"
    }

@router.get("/links/{short_code}/qr", response_class=StreamingResponse)
async def get_qr_code(
    short_code: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    link = await crud.get_link(db, short_code)
    if not link:
        raise HTTPException(404, "Ссылка не найдена")
    if link.owner_id != current_user.id:
        raise HTTPException(403, "Не ваша ссылка")

    short_url = f"{settings.base_url}/{short_code}"

    # Генерация QR-кода
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(short_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    # Сохраняем в память
    img_io = io.BytesIO()
    img.save(img_io, "PNG")
    img_io.seek(0)

    return StreamingResponse(
        img_io,
        media_type="image/png",
        headers={"Content-Disposition": f"inline; filename=qr_{short_code}.png"}
    )