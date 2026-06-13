from datetime import datetime
from database.models.user import User


def is_premium(user: User) -> bool:
    """بررسی می‌کنه کاربر پریمیوم فعال داره یا نه"""
    if not user.is_premium:
        return False
    if user.premium_expire and user.premium_expire < datetime.utcnow():
        return False
    return True


def premium_expired_soon(user: User, days: int = 3) -> bool:
    """۳ روز مونده به انقضا True برمی‌گردونه"""
    if not user.premium_expire:
        return False
    remaining = (user.premium_expire - datetime.utcnow()).days
    return 0 <= remaining <= days