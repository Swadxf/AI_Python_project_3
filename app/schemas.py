from pydantic import BaseModel, HttpUrl
from pydantic import field_validator
from datetime import datetime
from typing import Optional
from dateutil import parser


class UserCreate(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: int
    email: str

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class LinkCreate(BaseModel):
    original_url: HttpUrl
    custom_alias: Optional[str] = None
    expires_at: Optional[datetime] = None

    @field_validator('expires_at', mode='before')
    @classmethod
    def make_naive(cls, v):
        if v is None:
            return None
        
        # Если v — уже datetime (маловероятно, но на всякий случай)
        if isinstance(v, datetime):
            if v.tzinfo is not None:
                return v.replace(tzinfo=None)
            return v
        
        # Если v — строка (самый частый случай из JSON)
        if isinstance(v, str):
            try:
                dt = parser.isoparse(v)  # парсит ISO-строку (2026-03-09T23:59:59)
                if dt.tzinfo is not None:
                    return dt.replace(tzinfo=None)  # убираем таймзону
                return dt
            except ValueError as e:
                raise ValueError(f"Неверный формат даты: {v}. Ожидается ISO (YYYY-MM-DDTHH:MM:SS)")
        
        raise ValueError(f"expires_at должен быть строкой ISO или datetime, получено: {type(v)}")

class LinkResponse(BaseModel):
    short_code: str
    short_url: str
    original_url: str
    expires_at: Optional[datetime]


class LinkStats(BaseModel):
    original_url: str
    short_code: str
    custom_alias: Optional[str]
    created_at: datetime
    clicks: int
    last_clicked: Optional[datetime]
    expires_at: Optional[datetime]


class LinkUpdate(BaseModel):
    original_url: Optional[HttpUrl] = None
    expires_at: Optional[datetime] = None

    @field_validator('expires_at', mode='before')
    @classmethod
    def make_naive(cls, v):
        if v is None:
            return None

        if isinstance(v, datetime):
            if v.tzinfo is not None:
                return v.replace(tzinfo=None)
            return v

        if isinstance(v, str):
            dt = parser.isoparse(v)
            if dt.tzinfo is not None:
                return dt.replace(tzinfo=None)
            return dt

        raise ValueError("Invalid datetime format")