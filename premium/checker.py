from datetime import datetime, timedelta
from sqlalchemy import select
from database.engine import AsyncSessionLocal
from database.models.user import User


def is_premium(user: User) -> bool:
    """برگشت True اگه کاربر اشتراک فعال داشته باشه."""
    if not user.is_premium:
        return False
    if user.premium_expire is None:
        return False
    return user.premium_expire > datetime.utcnow()


async def get_premium_user(telegram_id: int) -> User | None:
    """کاربر رو از دیتابیس بگیر."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()


async def activate_premium(telegram_id: int, plan_key: str, months: int) -> None:
    """اشتراک کاربر رو فعال کن."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            return

        now = datetime.utcnow()
        base = user.premium_expire if (user.premium_expire and user.premium_expire > now) else now

        user.is_premium = True
        user.premium_expire = base + timedelta(days=months * 30)
        user.plan_type = plan_key
        await db.commit()