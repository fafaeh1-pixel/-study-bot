from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from datetime import datetime, timedelta
import re
import pytz

from bot.states import ReminderStates
from bot.keyboards.main_keyboard import get_main_keyboard, get_cancel_keyboard
from bot.texts import texts
from database.models.user import User
from premium.checker import is_premium
from reminders.scheduler import (
    add_once_reminder,
    get_user_reminder_count,
    list_user_reminders,
    remove_all_reminders,
    remove_reminder_by_index,
    MAX_REMINDERS_FREE,
)

router = Router(name="reminder")
MAX_REMINDERS_PREMIUM = 999
TEHRAN = pytz.timezone("Asia/Tehran")


# ─────────────────────────────────────────────
# پارس ورودی زمان
# ─────────────────────────────────────────────

def parse_datetime_input(text: str) -> datetime | None:
    """
    فرمت‌های پشتیبانی‌شده:
      فردا ۱۵:۳۰ / امروز ۲۰:۰۰
      ۲ ساعت دیگه / ۴۵ دقیقه دیگه
      ۲۰:۳۰ (امروز یا فردا اگه گذشته)
      8pm / 8:30am
    """
    now = datetime.now(TEHRAN)
    t = text.strip().lower()

    # فارسی → انگلیسی
    fa_map = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")
    t = t.translate(fa_map)

    # --- relative: X ساعت/دقیقه دیگه ---
    m = re.search(r'(\d+)\s*(ساعت|hour|h)\s*(دیگه|later)?', t)
    if m:
        return now + timedelta(hours=int(m.group(1)))

    m = re.search(r'(\d+)\s*(دقیقه|min|m)\s*(دیگه|later)?', t)
    if m:
        return now + timedelta(minutes=int(m.group(1)))

    # --- پیشوند روز ---
    day_offset = 0
    has_day = False
    if re.search(r'فردا|tomorrow', t):
        day_offset = 1
        has_day = True
    elif re.search(r'امروز|today', t):
        day_offset = 0
        has_day = True

    # --- پارس ساعت ---
    hour, minute = None, None

    m = re.search(r'(\d{1,2}):(\d{2})', t)
    if m:
        hour, minute = int(m.group(1)), int(m.group(2))

    if hour is None:
        m = re.search(r'(\d{1,2})\s*(pm|am)', t)
        if m:
            hour = int(m.group(1))
            minute = 0
            if m.group(2) == 'pm' and hour != 12:
                hour += 12
            elif m.group(2) == 'am' and hour == 12:
                hour = 0

    if hour is None:
        m = re.fullmatch(r'\s*(\d{1,2})\s*', t)
        if m:
            hour, minute = int(m.group(1)), 0

    if hour is None or not (0 <= hour <= 23) or not (0 <= (minute or 0) <= 59):
        return None

    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    target += timedelta(days=day_offset)

    # اگه روز مشخص نشده و ساعت گذشته، فردا حساب کن
    if not has_day and target <= now:
        target += timedelta(days=1)

    return target


# ─────────────────────────────────────────────
# شروع تنظیم یادآور
# ─────────────────────────────────────────────

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

    status = (
        f"⭐ پریمیوم — یادآور نامحدود\n📌 یادآورهای فعال: {count}\n\n"
        if premium
        else f"📌 یادآور فعال: {count} از {limit}\n\n"
    )

    await state.set_state(ReminderStates.waiting_for_time)
    await message.answer(
        f"⏰ <b>تنظیم یادآور</b>\n\n"
        f"{status}"
        f"زمان یادآور رو بگو:\n\n"
        f"<code>فردا ۱۵:۳۰</code>\n"
        f"<code>امروز ۲۰:۰۰</code>\n"
        f"<code>۲ ساعت دیگه</code>\n"
        f"<code>۴۵ دقیقه دیگه</code>\n"
        f"<code>۲۰:۳۰</code> — امروز یا فردا اگه گذشته باشه",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard(),
    )


# ─────────────────────────────────────────────
# دریافت زمان و ثبت یادآور
# ─────────────────────────────────────────────

@router.message(ReminderStates.waiting_for_time)
async def reminder_set(message: Message, state: FSMContext, db_user: User) -> None:
    if message.text == texts.BTN_CANCEL:
        await state.clear()
        await message.answer(texts.CANCELLED, reply_markup=get_main_keyboard())
        return

    target_dt = parse_datetime_input(message.text.strip())

    if target_dt is None:
        await message.answer(
            "❌ فرمت نادرست! مثال:\n"
            "<code>فردا ۱۵:۳۰</code> — <code>۲ ساعت دیگه</code> — <code>۲۰:۳۰</code>",
            parse_mode="HTML",
        )
        return

    premium = is_premium(db_user)

    success = add_once_reminder(
        telegram_id=db_user.telegram_id,
        run_at=target_dt,
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

    now = datetime.now(TEHRAN)
    dt_local = target_dt.astimezone(TEHRAN)
    diff = dt_local - now
    hours_left = int(diff.total_seconds() // 3600)
    mins_left  = int((diff.total_seconds() % 3600) // 60)

    if hours_left > 0:
        remaining = f"{hours_left} ساعت و {mins_left} دقیقه دیگه"
    else:
        remaining = f"{mins_left} دقیقه دیگه"

    weekdays = ["دوشنبه","سه‌شنبه","چهارشنبه","پنج‌شنبه","جمعه","شنبه","یکشنبه"]
    if dt_local.date() == now.date():
        day_label = "امروز"
    elif (dt_local.date() - now.date()).days == 1:
        day_label = "فردا"
    else:
        day_label = weekdays[dt_local.weekday()]

    await message.answer(
        f"✅ <b>یادآور ثبت شد!</b>\n\n"
        f"🗓 {day_label} — <b>{dt_local.strftime('%H:%M')}</b>\n"
        f"⏳ {remaining}\n\n"
        f"این یادآور فقط یه‌بار اجرا می‌شه 🔔",
        parse_mode="HTML",
        reply_markup=get_main_keyboard(),
    )


# ─────────────────────────────────────────────
# نمایش لیست یادآورها
# ─────────────────────────────────────────────

@router.message(F.text == texts.BTN_MY_REMINDERS)
async def show_reminders(message: Message, db_user: User) -> None:
    reminders = list_user_reminders(db_user.telegram_id)

    if not reminders:
        await message.answer(
            "📭 <b>هیچ یادآور فعالی نداری!</b>\n\n"
            "با دکمه ⏰ یادآور یه تا تنظیم کن.",
            parse_mode="HTML",
            reply_markup=get_main_keyboard(),
        )
        return

    now = datetime.now(TEHRAN)
    weekdays = ["دوشنبه","سه‌شنبه","چهارشنبه","پنج‌شنبه","جمعه","شنبه","یکشنبه"]

    lines = ["⏰ <b>یادآورهای فعال تو:</b>\n"]
    for i, dt in enumerate(reminders, 1):
        dt_local = dt.astimezone(TEHRAN)
        diff = dt_local - now

        if dt_local.date() == now.date():
            day_label = "امروز"
        elif (dt_local.date() - now.date()).days == 1:
            day_label = "فردا"
        else:
            day_label = weekdays[dt_local.weekday()]

        hours_left = int(diff.total_seconds() // 3600)
        mins_left  = int((diff.total_seconds() % 3600) // 60)

        if hours_left > 0:
            remaining = f"{hours_left} ساعت و {mins_left} دقیقه دیگه"
        else:
            remaining = f"{mins_left} دقیقه دیگه"

        lines.append(
            f"{i}. 🗓 <b>{day_label} {dt_local.strftime('%H:%M')}</b>\n"
            f"   ⏳ {remaining}"
        )

    lines.append(f"\n📌 مجموع: {len(reminders)} یادآور فعال")

    # دکمه‌های inline برای حذف
    buttons = []
    for i in range(len(reminders)):
        buttons.append(
            InlineKeyboardButton(
                text=f"🗑 حذف یادآور {i+1}",
                callback_data=f"del_reminder_{db_user.telegram_id}_{i}",
            )
        )
    buttons.append(
        InlineKeyboardButton(
            text="🗑 حذف همه",
            callback_data=f"del_all_reminders_{db_user.telegram_id}",
        )
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[[b] for b in buttons])

    await message.answer(
        "\n".join(lines),
        parse_mode="HTML",
        reply_markup=keyboard,
    )


# ─────────────────────────────────────────────
# حذف یادآور (callback)
# ─────────────────────────────────────────────

@router.callback_query(F.data.startswith("del_reminder_"))
async def delete_one_reminder(callback: CallbackQuery, db_user: User) -> None:
    parts = callback.data.split("_")
    # del_reminder_{telegram_id}_{index}
    index = int(parts[-1])
    tid = int(parts[-2])

    if tid != db_user.telegram_id:
        await callback.answer("❌ دسترسی نداری!", show_alert=True)
        return

    success = remove_reminder_by_index(db_user.telegram_id, index)
    if success:
        await callback.answer("✅ یادآور حذف شد!")
        reminders = list_user_reminders(db_user.telegram_id)
        if not reminders:
            await callback.message.edit_text("📭 هیچ یادآور فعالی نداری!")
        else:
            await callback.message.edit_text(
                f"✅ یادآور حذف شد.\n📌 {len(reminders)} یادآور باقی‌مونده."
            )
    else:
        await callback.answer("❌ یادآور پیدا نشد!", show_alert=True)


@router.callback_query(F.data.startswith("del_all_reminders_"))
async def delete_all_reminders(callback: CallbackQuery, db_user: User) -> None:
    tid = int(callback.data.split("_")[-1])

    if tid != db_user.telegram_id:
        await callback.answer("❌ دسترسی نداری!", show_alert=True)
        return

    count = remove_all_reminders(db_user.telegram_id)
    await callback.answer(f"✅ {count} یادآور حذف شد!")
    await callback.message.edit_text(f"🗑 {count} یادآور حذف شد.")