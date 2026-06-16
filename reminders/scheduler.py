from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from aiogram import Bot
from datetime import datetime
from logger import logger
import pytz


TEHRAN = pytz.timezone("Asia/Tehran")
scheduler = AsyncIOScheduler(timezone=TEHRAN)

MAX_REMINDERS_FREE = 10
MAX_REMINDERS_PREMIUM = 999


# ─────────────────────────────────────────────
# راه‌اندازی و توقف
# ─────────────────────────────────────────────

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


# ─────────────────────────────────────────────
# مدیریت یادآورها
# ─────────────────────────────────────────────

def get_user_reminder_count(telegram_id: int) -> int:
    """تعداد یادآورهای فعال (هنوز اجرا نشده) کاربر"""
    jobs = [
        j for j in scheduler.get_jobs()
        if j.id.startswith(f"reminder_{telegram_id}_")
    ]
    return len(jobs)


def add_once_reminder(
    telegram_id: int,
    run_at: datetime,
    bot: Bot,
    is_premium: bool = False,
) -> bool:
    """
    یادآور یه‌باره در تاریخ و ساعت دقیق.
    بعد از اجرا خودکار حذف می‌شه.
    """
    current_count = get_user_reminder_count(telegram_id)
    limit = MAX_REMINDERS_PREMIUM if is_premium else MAX_REMINDERS_FREE

    if current_count >= limit:
        return False

    # اطمینان از timezone-aware بودن
    if run_at.tzinfo is None:
        run_at = TEHRAN.localize(run_at)

    job_id = f"reminder_{telegram_id}_{int(run_at.timestamp())}"

    async def send_reminder():
        try:
            from bot.texts_motivational import get_random_motivation
            await bot.send_message(
                chat_id=telegram_id,
                text=(
                    f"⏰ <b>یادآور مطالعه!</b>\n\n"
                    f"{get_random_motivation()}\n\n"
                    f"📚 وقتشه مطالعه کنی!"
                ),
                parse_mode="HTML",
            )
            logger.info(f"✅ یادآور {job_id} ارسال شد")
        except Exception as e:
            logger.error(f"خطا در ارسال یادآور به {telegram_id}: {e}")

    scheduler.add_job(
        send_reminder,
        trigger=DateTrigger(run_date=run_at, timezone=TEHRAN),
        id=job_id,
        replace_existing=False,
        misfire_grace_time=300,
    )
    logger.info(f"⏰ یادآور یه‌باره برای {telegram_id} در {run_at.strftime('%Y-%m-%d %H:%M')} ثبت شد")
    return True


def remove_reminder_by_index(telegram_id: int, index: int) -> bool:
    """حذف یادآور بر اساس شماره (از لیست مرتب‌شده)"""
    jobs = sorted(
        [j for j in scheduler.get_jobs() if j.id.startswith(f"reminder_{telegram_id}_")],
        key=lambda j: j.next_run_time,
    )
    if 0 <= index < len(jobs):
        scheduler.remove_job(jobs[index].id)
        logger.info(f"🗑 یادآور {jobs[index].id} حذف شد")
        return True
    return False


def remove_all_reminders(telegram_id: int) -> int:
    """حذف همه یادآورهای فعال کاربر"""
    jobs = [
        j for j in scheduler.get_jobs()
        if j.id.startswith(f"reminder_{telegram_id}_")
    ]
    for j in jobs:
        scheduler.remove_job(j.id)
    logger.info(f"🗑 {len(jobs)} یادآور برای {telegram_id} حذف شد")
    return len(jobs)


def list_user_reminders(telegram_id: int) -> list[datetime]:
    """لیست زمان یادآورهای فعال کاربر (مرتب‌شده)"""
    jobs = [
        j for j in scheduler.get_jobs()
        if j.id.startswith(f"reminder_{telegram_id}_")
    ]
    return sorted([j.next_run_time for j in jobs if j.next_run_time])


# ─────────────────────────────────────────────
# چک انقضای اشتراک
# ─────────────────────────────────────────────

async def _check_expiring_subscriptions(bot: Bot) -> None:
    from datetime import timedelta
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