from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.user import User
from bot.keyboards.main_keyboard import get_main_keyboard
from bot.texts import texts

router = Router(name="start")


@router.message(CommandStart())
async def start_handler(message: Message, db_user: User) -> None:
    await message.answer(
        f"سلام <b>{message.from_user.first_name}</b> عزیز! 👋\n\n"
        "به <b>StudyBot Pro</b> خوش اومدی 🎓\n\n"
        "با این ربات می‌تونی:\n"
        "📝 مطالعه‌هات رو ثبت کنی\n"
        "📊 گزارش روزانه و هفتگی بگیری\n"
        "🤖 با هوش مصنوعی پیشرفتت رو تحلیل کنی\n"
        "📅 برنامه مطالعه هفتگی بسازی\n\n"
        "از منوی پایین شروع کن 👇",
        parse_mode="HTML",
        reply_markup=get_main_keyboard(),
    )


@router.message(Command("help"))
@router.message(F.text == texts.BTN_HELP)
async def help_handler(message: Message) -> None:
    await message.answer(
        "🆘 <b>راهنمای StudyBot Pro</b>\n\n"
        "<b>📝 ثبت مطالعه:</b>\n"
        "  درس و مدت مطالعه رو ثبت کن\n\n"
        "<b>📊 گزارش‌ها:</b>\n"
        "  گزارش روزانه و هفتگی با نمودار\n\n"
        "<b>🤖 هوش مصنوعی (پریمیوم):</b>\n"
        "  /analyze — تحلیل پیشرفت ۳۰ روز\n"
        "  /advisor — مشاوره تحصیلی\n"
        "  /plan — برنامه هفتگی هوشمند\n\n"
        "<b>⚙️ تنظیمات:</b>\n"
        "  /setgoal عدد — تغییر هدف روزانه\n"
        "  مثال: <code>/setgoal 90</code>\n\n"
        "<b>⏰ یادآور:</b>\n"
        "  تنظیم یادآور مطالعه روزانه\n\n"
        "<b>⭐ پریمیوم:</b>\n"
        "  /premium — خرید اشتراک",
        parse_mode="HTML",
        reply_markup=get_main_keyboard(),
    )


@router.message(Command("cancel"))
async def cancel_handler(message: Message) -> None:
    await message.answer(texts.CANCELLED, reply_markup=get_main_keyboard())


@router.message(F.text == texts.BTN_SETTINGS)
async def btn_settings(message: Message, db_user: User) -> None:
    goal_bar = "█" * min(int(db_user.daily_goal_minutes / 12), 10) + "░" * max(10 - int(db_user.daily_goal_minutes / 12), 0)
    await message.answer(
        f"⚙️ <b>تنظیمات حساب کاربری</b>\n\n"
        f"👤 نام: <b>{db_user.full_name or 'تنظیم نشده'}</b>\n"
        f"🆔 آیدی: <code>{db_user.telegram_id}</code>\n"
        f"🎯 هدف روزانه: <b>{db_user.daily_goal_minutes} دقیقه</b>\n"
        f"{goal_bar}\n\n"
        f"برای تغییر هدف:\n"
        f"<code>/setgoal 90</code>",
        parse_mode="HTML",
        reply_markup=get_main_keyboard(),
    )


@router.message(Command("setgoal"))
async def set_goal(message: Message, db_user: User, db: AsyncSession) -> None:
    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer(
            "❌ فرمت اشتباه.\n\n"
            "مثال: <code>/setgoal 90</code>",
            parse_mode="HTML",
        )
        return

    goal = int(parts[1])
    if not (10 <= goal <= 720):
        await message.answer(
            "❌ هدف باید بین <b>۱۰</b> تا <b>۷۲۰</b> دقیقه باشد.",
            parse_mode="HTML",
        )
        return

    db_user.daily_goal_minutes = goal
    await db.commit()

    hours = goal // 60
    mins = goal % 60
    time_text = f"{hours} ساعت و {mins} دقیقه" if hours else f"{mins} دقیقه"

    await message.answer(
        f"✅ هدف روزانه به <b>{goal} دقیقه</b> ({time_text}) تغییر کرد!\n\n"
        f"موفق باشی 💪",
        parse_mode="HTML",
        reply_markup=get_main_keyboard(),
    )