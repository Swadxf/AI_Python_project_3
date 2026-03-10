from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from app import crud, models
from app.database import get_db
from app.config import settings


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


async def get_current_user_optional(
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> models.User | None:
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        email: str = payload.get("sub")
        if email is None:
            return None
    except JWTError:
        return None
    return await crud.get_user_by_email(db, email)


async def get_current_active_user(
    current_user: models.User | None = Depends(get_current_user_optional)
) -> models.User:
    if current_user is None:
        raise HTTPException(status_code=401, detail="Требуется авторизация")
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Пользователь неактивен")
    return current_user