from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func, Boolean
from sqlalchemy.orm import relationship
from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)

    links = relationship("Link", back_populates="owner")


class Link(Base):
    __tablename__ = "links"

    id = Column(Integer, primary_key=True, index=True)
    short_code = Column(String(12), unique=True, index=True, nullable=False)
    original_url = Column(String(2048), nullable=False)
    custom_alias = Column(String(30), unique=True, index=True, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime(timezone=False), nullable=True)  # ← timezone=False обязательно!
    clicks = Column(Integer, default=0)
    last_clicked = Column(DateTime, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    owner = relationship("User", back_populates="links")