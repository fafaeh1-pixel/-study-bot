from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from aiogram import Bot
from logger import logger
import pytz

TEHRAN = pytz.timezone("Asia/Tehran")
scheduler = AsyncIOScheduler(timezone=TEHRAN)


MAX_REMINDERS_FREE = 10
MAX_REMINDERS_PREMIUM = 999



def start_scheduler(bot: Bot) -> None:
    scheduler.start()
    scheduler.add_job(
        _check_expiring_subscriptions,
        trigger=CronTrigger(hour=10, minute=0, timezone=TEHRAN),
        id="expiry_check",
        replace_existing=True,
        args=[bot],
    )
    logger.info("⏰ Scheduler راه‌اندازی شد")



def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown()
        logger.info("⏰ Scheduler متوقف شد")



def get_user_reminder_count(telegram_id: int) -> int:
    jobs = [j for j in scheduler.get_jobs() if j.id.startswith(f"reminder_{telegram_id}_")]
    return len(jobs)



def parse_time_input(time_str: str) -> tuple[int, int] | None:
    import re
    time_str = time_str.strip().lower().replace(".", ":")

    match = re.fullmatch(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)", time_str)
    if match:
        h = int(match.group(1))
        m = int(match.group(2)) if match.group(2) else 0
        period = match.group(3)
        if period == "pm" and h != 12:
            h += 12
        if period == "am" and h == 12:
            h = 0
        if 0 <= h <= 23 and 0 <= m <= 59:
            return h, m
        return None

    match = re.fullmatch(r"(\d{1,2}):(\d{2})", time_str)
    if match:
        h, m = int(match.group(1)), int(match.group(2))
        if 0 <= h <= 23 and 0 <= m <= 59:
            return h, m
        return None

    match = re.fullmatch(r"(\d{1,2})", time_str)
    if match:
        h = int(match.group(1))
        if 0 <= h <= 23:
            return h, 0
        return None

    return None



def add_daily_reminder(telegram_id: int, hour: int, minute: int, bot: Bot, is_premium: bool = False) -> bool:
    current_count = get_user_reminder_count(telegram_id)
    limit = MAX_REMINDERS_PREMIUM if is_premium else MAX_REMINDERS_FREE

    if current_count >= limit:
        return False

    job_id = f"reminder_{telegram_id}_{hour:02d}{minute:02d}"

    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)

    async def send_reminder():
        try:
            from bot.texts_motivational import get_random_motivation
            await bot.send_message(
                chat_id=telegram_id,
                text=f"⏰ یادآور مطالعه!\n\n{get_random_motivation()}\n\n📚 وقتشه مطالعه کنی!",
            )
        except Exception as e:
            logger.error(f"خطا در ارسال یادآور به {telegram_id}: {e}")

    scheduler.add_job(
        send_reminder,
        trigger=CronTrigger(hour=hour, minute=minute, timezone=TEHRAN),
        id=job_id,
        replace_existing=True,
    )
    logger.info(f"⏰ یادآور برای {telegram_id} در {hour:02d}:{minute:02d} ثبت شد")
    return True



def remove_all_reminders(telegram_id: int) -> int:
    jobs = [j for j in scheduler.get_jobs() if j.id.startswith(f"reminder_{telegram_id}_")]
    for j in jobs:
        scheduler.remove_job(j.id)
    return len(jobs)



async def _check_expiring_subscriptions(bot: Bot) -> None:
    from datetime import datetime, timedelta
    from sqlalchemy import select
    from database.engine import AsyncSessionLocal
    from database.models.user import User

    now_tehran = datetime.now(TEHRAN).replace(tzinfo=None)
    three_days_later = now_tehran + timedelta(days=3)
    tomorrow = now_tehran + timedelta(days=1)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(
                User.is_premium == True,
                User.premium_expire >= tomorrow,
                User.premium_expire <= three_days_later,
            )
        )
        users = result.scalars().all()

    for user in users:
        days_left = (user.premium_expire - now_tehran).days + 1
        try:
            await bot.send_message(
                chat_id=user.telegram_id,
                text=(
                    f"⚠️ <b>اشتراک پریمیومت داره تموم می‌شه!</b>\n\n"
                    f"⏳ {days_left} روز دیگه اشتراکت منقضی می‌شه.\n\n"
                    f"برای تمدید /premium رو بزن 👇"
                ),
                parse_mode="HTML",
            )
            logger.info(f"📨 پیام انقضا برای {user.telegram_id} ارسال شد ({days_left} روز)")
        except Exception as e:
            logger.error(f"خطا در ارسال پیام انقضا به {user.telegram_id}: {e}")