"""
premium/guard.py — دکوراتور و تابع چک پریمیوم
استفاده:
    from premium.guard import premium_required, check_premium

    @router.message(...)
    @premium_required
    async def my_handler(message, db_user, ...): ...
"""
from functools import wraps
from aiogram.types import Message
from premium.checker import is_premium


UPGRADE_TEXT = (
    "⭐ <b>این امکان مخصوص کاربران پریمیوم هست!</b>\n\n"
    "با پریمیوم می‌تونی از این قابلیت‌ها استفاده کنی:\n"
    "⏰ یادآور نامحدود\n"
    "🎙️ ارسال ویس گزارش\n"
    "📊 نمودار تصویری\n\n"
    "برای خرید اشتراک دستور /premium رو بزن 👇"
)


def premium_required(func):
    """دکوراتور — هندلر رو فقط برای پریمیوم‌ها فعال می‌کنه."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # پیدا کردن message و db_user از args/kwargs
        message = next((a for a in args if isinstance(a, Message)), None)
        db_user = kwargs.get("db_user")

        if message and db_user and not is_premium(db_user):
            await message.answer(UPGRADE_TEXT, parse_mode="HTML")
            return

        return await func(*args, **kwargs)
    return wrapper


async def check_premium_and_reply(message: Message, db_user) -> bool:
    """
    برگشت True اگه پریمیوم باشه، False اگه نباشه + پیام می‌فرسته.
    استفاده داخل هندلر:
        if not await check_premium_and_reply(message, db_user):
            return
    """
    if is_premium(db_user):
        return True
    await message.answer(UPGRADE_TEXT, parse_mode="HTML")
    return False