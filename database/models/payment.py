from sqlalchemy import BigInteger, Integer, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from database.models.base import Base


class Payment(Base):
    __tablename__ = "payments"

    id:           Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id:  Mapped[int] = mapped_column(BigInteger, index=True)
    plan_key:     Mapped[str] = mapped_column(String(20))
    amount_toman: Mapped[int] = mapped_column(Integer)
    authority:    Mapped[str] = mapped_column(String(100), unique=True)
    status:       Mapped[str] = mapped_column(String(20), default="pending")
    created_at:   Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)