_handler
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, func
from datetime import datetime, timedelta

from database.engine import AsyncSessionLocal
from database.models.user import User
from database.models.payment import Payment
from premium.checker import activate_premium
from premium.plans import PLANS
from config import settings

router = Router(name="admin")


def is_admin(telegram_id: int) -> bool:
    return telegram_id == settings.ADMIN_ID


class AdminStates(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_plan = State()
    waiting_for_broadcast = State()


# ─────────────── فیلتر ادمین ───────────────

def admin_only(func):
    from functools import wraps
    @wraps(func)
    async def wrapper(message: Message, *args, **kwargs):
        if not is_admin(message.from_user.id):
            await message.answer("❌ دسترسی ندارید.")
            return
        return await func(message, *args, **kwargs)
    return wrapper


# ─────────────── منوی ادمین ───────────────

def admin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 کاربران پریمیوم", callback_data="admin_premium_list")],
        [InlineKeyboardButton(text="📊 آمار فروش", callback_data="admin_sales")],
        [InlineKeyboardButton(text="✅ فعال‌سازی دستی", callback_data="admin_activate")],
        [InlineKeyboardButton(text="📢 پیام همگانی", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="❌ بستن", callback_data="admin_close")],
    ])


@router.message(Command("admin"))
@admin_only
async def cmd_admin(message: Message):
    async with AsyncSessionLocal() as db:
        total_users = (await db.execute(func.count(User.id))).scalar() or 0
        premium_users = (await db.execute(
            select(func.count(User.id)).where(
                User.is_premium == True,
                User.premium_expire > datetime.utcnow()
            )
        )).scalar() or 0

    await message.answer(
        f"🛠 <b>پنل ادمین</b>\n\n"
        f"👤 کل کاربران: <b>{total_users}</b>\n"
        f"⭐ پریمیوم فعال: <b>{premium_users}</b>\n\n"
        f"یه گزینه انتخاب کن:",
        parse_mode="HTML",
        reply_markup=admin_keyboard(),
    )


# ─────────────── لیست پریمیوم ───────────────

@router.callback_query(F.data == "admin_premium_list")
async def admin_premium_list(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("❌ دسترسی ندارید.", show_alert=True)
        return

    await call.answer()

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(
                User.is_premium == True,
                User.premium_expire > datetime.utcnow()
            ).order_by(User.premium_expire.desc()).limit(20)
        )
        users = result.scalars().all()

    if not users:
        await call.message.answer("📭 هیچ کاربر پریمیومی وجود نداره.")
        return

    lines = []
    for u in users:
        days = (u.premium_expire - datetime.utcnow()).days + 1
        name = u.full_name or u.username or str(u.telegram_id)
        lines.append(
            f"👤 <b>{name}</b> | <code>{u.telegram_id}</code>\n"
            f"   📦 {u.plan_type or '—'} | ⏳ {days} روز مانده"
        )

    await call.message.answer(
        f"⭐ <b>کاربران پریمیوم فعال ({len(users)})</b>\n\n" + "\n\n".join(lines),
        parse_mode="HTML",
    )


# ─────────────── آمار فروش ───────────────

@router.callback_query(F.data == "admin_sales")
async def admin_sales(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("❌ دسترسی ندارید.", show_alert=True)
        return

    await call.answer()

    async with AsyncSessionLocal() as db:
        # کل پرداخت‌های موفق
        result = await db.execute(
            select(Payment).where(Payment.status == "paid")
        )
        payments = result.scalars().all()

        # پرداخت‌های ۳۰ روز اخیر
        month_ago = datetime.utcnow() - timedelta(days=30)
        result_month = await db.execute(
            select(Payment).where(
                Payment.status == "paid",
                Payment.created_at >= month_ago,
            )
        )
        monthly = result_month.scalars().all()

    total_income = sum(p.amount_toman for p in payments)
    monthly_income = sum(p.amount_toman for p in monthly)

    # آمار به تفکیک پلن
    plan_stats = {}
    for p in payments:
        plan_stats[p.plan_key] = plan_stats.get(p.plan_key, 0) + 1

    plan_lines = []
    for key, count in plan_stats.items():
        plan = PLANS.get(key)
        label = plan.label if plan else key
        plan_lines.append(f"  • {label}: {count} فروش")

    await call.message.answer(
        f"📊 <b>آمار فروش</b>\n\n"
        f"💰 درآمد کل: <b>{total_income:,} تومان</b>\n"
        f"📅 درآمد ۳۰ روز اخیر: <b>{monthly_income:,} تومان</b>\n"
        f"🧾 کل تراکنش موفق: <b>{len(payments)}</b>\n\n"
        f"<b>به تفکیک پلن:</b>\n" + ("\n".join(plan_lines) or "  —"),
        parse_mode="HTML",
    )


# ─────────────── فعال‌سازی دستی ───────────────

@router.callback_query(F.data == "admin_activate")
async def admin_activate_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        await call.answer("❌ دسترسی ندارید.", show_alert=True)
        return

    await call.answer()
    await state.set_state(AdminStates.waiting_for_user_id)
    await call.message.answer(
        "✅ <b>فعال‌سازی دستی پریمیوم</b>\n\n"
        "آیدی عددی تلگرام کاربر رو بفرست:",
        parse_mode="HTML",
    )


@router.message(AdminStates.waiting_for_user_id)
async def admin_get_user_id(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    if not message.text.isdigit():
        await message.answer("❌ آیدی باید عدد باشه!")
        return

    await state.update_data(target_id=int(message.text))
    await state.set_state(AdminStates.waiting_for_plan)

    plan_buttons = [
        [InlineKeyboardButton(
            text=f"{p.emoji} {p.label} ({p.months} ماه)",
            callback_data=f"admin_plan_{key}"
        )]
        for key, p in PLANS.items()
    ]
    await message.answer(
        "📦 پلن رو انتخاب کن:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=plan_buttons),
    )


@router.callback_query(F.data.startswith("admin_plan_"))
async def admin_set_plan(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        await call.answer("❌", show_alert=True)
        return

    plan_key = call.data.split("_", 2)[2]
    plan = PLANS.get(plan_key)
    data = await state.get_data()
    target_id = data.get("target_id")

    await state.clear()
    await call.answer()

    if not plan or not target_id:
        await call.message.answer("❌ خطا!")
        return

    await activate_premium(
        telegram_id=target_id,
        plan_key=plan_key,
        months=plan.months,
    )

    await call.message.answer(
        f"✅ <b>پریمیوم فعال شد!</b>\n\n"
        f"👤 کاربر: <code>{target_id}</code>\n"
        f"📦 پلن: {plan.label} ({plan.months} ماه)",
        parse_mode="HTML",
    )

    # اطلاع به کاربر
    try:
        await call.bot.send_message(
            chat_id=target_id,
            text=f"🎉 <b>اشتراک پریمیوم شما فعال شد!</b>\n\n"
                 f"📦 پلن: {plan.label}\n"
                 f"⏳ مدت: {plan.months} ماه\n\n"
                 f"از امکانات پریمیوم لذت ببر! ⭐",
            parse_mode="HTML",
        )
    except Exception:
        pass


# ─────────────── پیام همگانی ───────────────

@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        await call.answer("❌", show_alert=True)
        return

    await call.answer()
    await state.set_state(AdminStates.waiting_for_broadcast)
    await call.message.answer(
        "📢 <b>پیام همگانی</b>\n\n"
        "متن پیام رو بفرست — به همه کاربران ارسال می‌شه:\n\n"
        "برای لغو /cancel بزن",
        parse_mode="HTML",
    )


@router.message(AdminStates.waiting_for_broadcast)
async def admin_do_broadcast(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    await state.clear()

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.is_active == True)
        )
        users = result.scalars().all()

    sent, failed = 0, 0
    for user in users:
        try:
            await message.bot.send_message(
                chat_id=user.telegram_id,
                text=f"📢 <b>پیام از طرف مدیریت:</b>\n\n{message.text}",
                parse_mode="HTML",
            )
            sent += 1
        except Exception:
            failed += 1

    await message.answer(
        f"📢 <b>پیام همگانی ارسال شد</b>\n\n"
        f"✅ موفق: {sent}\n"
        f"❌ ناموفق: {failed}",
        parse_mode="HTML",
    )


# ─────────────── بستن ───────────────

@router.callback_query(F.data == "admin_close")
async def admin_close(call: CallbackQuery):
    await call.m