from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.states import ReminderStates
from bot.keyboards.main_keyboard import get_main_keyboard, get_cancel_keyboard
from bot.texts import texts
from database.models.user import User
from premium.checker import is_premium
from reminders.scheduler import (
    add_daily_reminder,
    get_user_reminder_count,
    parse_time_input,
    MAX_REMINDERS_FREE,
)

router = Router(name="reminder")

MAX_REMINDERS_PREMIUM = 999


@router.message(F.text == texts.BTN_REMINDER)
async def reminder_start(message: Message, state: FSMContext, db_user: User) -> None:
    count = get_user_reminder_count(db_user.telegram_id)
    premium = is_premium(db_user)
    limit = MAX_REMINDERS_PREMIUM if premium else MAX_REMINDERS_FREE

    if not premium and count >= MAX_REMINDERS_FREE:
        await message.answer(
            f"⏰ <b>یادآور</b>\n\n"
            f"کاربران رایگان فقط می‌تونن <b>{MAX_REMINDERS_FREE} یادآور</b> فعال داشته باشن.\n\n"
            f"⭐ با پریمیوم یادآور نامحدود داری!\n"
            f"برای خرید /premium رو بزن 👇",
            parse_mode="HTML",
            reply_markup=get_main_keyboard(),
        )
        return

    if premium:
        status = f"⭐ پریمیوم — یادآور نامحدود\n📌 یادآورهای فعال: {count}\n\n"
    else:
        status = f"📌 یادآور فعال: {count} از {MAX_REMINDERS_FREE}\n\n"

    await state.set_state(ReminderStates.waiting_for_time)
    await message.answer(
        f"⏰ <b>تنظیم یادآور مطالعه</b>\n\n"
        f"{status}"
        f"ساعت یادآور رو وارد کن — فرمت‌های قابل قبول:\n"
        f"<code>20:30</code> یا <code>08:00</code>\n"
        f"<code>8pm</code> یا <code>8:30am</code>\n"
        f"<code>20</code> (فقط ساعت، بدون دقیقه)",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard(),
    )


@router.message(ReminderStates.waiting_for_time)
async def reminder_set(message: Message, state: FSMContext, db_user: User) -> None:
    if message.text == texts.BTN_CANCEL:
        await state.clear()
        await message.answer(texts.CANCELLED, reply_markup=get_main_keyboard())
        return

    parsed = parse_time_input(message.text.strip())
    if parsed is None:
        await message.answer(
            "❌ فرمت نادرست! مثال‌های قابل قبول:\n"
            "<code>20:30</code> — <code>8pm</code> — <code>8:30am</code> — <code>20</code>",
            parse_mode="HTML",
        )
        return

    hour, minute = parsed
    premium = is_premium(db_user)

    success = add_daily_reminder(
        telegram_id=db_user.telegram_id,
        hour=hour,
        minute=minute,
        bot=message.bot,
        is_premium=premium,
    )

    await state.clear()

    if not success:
        limit = MAX_REMINDERS_PREMIUM if premium else MAX_REMINDERS_FREE
        await message.answer(
            f"❌ به سقف {limit} یادآور رسیدی!\n\n"
            f"⭐ با پریمیوم یادآور نامحدود داری.\n"
            f"برای خرید /premium رو بزن 👇",
            parse_mode="HTML",
            reply_markup=get_main_keyboard(),
        )
        return

    # نمایش ساعت به فرمت ۱۲ ساعته
    period = "بعدازظهر" if hour >= 12 else "صبح"
    h12 = hour % 12 or 12

    await message.answer(
        f"✅ یادآور برای ساعت <b>{hour:02d}:{minute:02d}</b> ({h12}:{minute:02d} {period}) تنظیم شد!\n\n"
        f"هر روز این ساعت بهت یادآوری می‌کنم 🔔",
        parse_mode="HTML",
        reply_markup=get_main_keyboard(),
    )