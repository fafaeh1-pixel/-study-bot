from sqlalchemy import BigInteger, Boolean, Integer, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from database.models.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id:                 Mapped[int]            = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id:        Mapped[int]            = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    username:           Mapped[str | None]     = mapped_column(String(64), nullable=True)
    full_name:          Mapped[str]            = mapped_column(String(128), nullable=False)
    is_active:          Mapped[bool]           = mapped_column(Boolean, default=True)
    is_premium:         Mapped[bool]           = mapped_column(Boolean, default=False)
    premium_expire:     Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None)
    plan_type:          Mapped[str | None]     = mapped_column(String(20), nullable=True, default=None)
    daily_goal_minutes: Mapped[int]            = mapped_column(Integer, default=60)

    study_sessions = relationship("StudySession", back_populates="user", cascade="all, delete-orphan")
    reminders      = relationship("Reminder",      back_populates="user", cascade="all, delete-orphan")