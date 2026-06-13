from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from sqlalchemy import select

from database.engine import AsyncSessionLocal
from database.models.user import User
from database.models.payment import Payment
from premium.plans import PLANS, PREMIUM_FEATURES
from premium.zarinpal import create_payment, verify_payment
from premium.checker import is_premium, activate_premium
from bot.texts import texts
from config import settings


router = Router()

CALLBACK_URL = f"{settings.WEBAPP_URL}/payment/callback"


def premium_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    for plan in PLANS.values():
        price_fmt = f"{plan.price_toman:,}".replace(",", "،")
        buttons.append([
            InlineKeyboardButton(
                text=f"💎 {plan.label} — {price_fmt} تومان",
                callback_data=f"buy_{plan.key}",
            )
        ])
    buttons.append([InlineKeyboardButton(text="❌ بستن", callback_data="close")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(Command("premium"))
@router.message(F.text == texts.BTN_PREMIUM)
async def show_premium(message: Message):
    async with AsyncSessionLocal() as db:
        user = (
            await db.execute(select(User).where(User.telegram_id == message.from_user.id))
        ).scalar_one_or_none()

    if user and is_premium(user):
        expire = user.premium_expire.strftime("%Y/%m/%d") if user.premium_expire else "—"
        await message.answer(
            f"✅ <b>اشتراک پریمیوم شما فعاله</b>\n\n"
            f"📅 تاریخ انقضا: <code>{expire}</code>\n"
            f"💼 پلن: {user.plan_type or '—'}",
            parse_mode="HTML",
        )
        return

    features_text = "\n".join(PREMIUM_FEATURES)
    await message.answer(
        f"⭐ <b>اشتراک پریمیوم StudyBot Pro</b>\n\n"
        f"با پریمیوم به این امکانات دسترسی داری:\n"
        f"{features_text}\n\n"
        f"یه پلن انتخاب کن:",
        parse_mode="HTML",
        reply_markup=premium_keyboard(),
    )


@router.callback_query(F.data.startswith("buy_"))
async def handle_buy(call: CallbackQuery):
    plan_key = call.data.split("_", 1)[1]
    plan = PLANS.get(plan_key)
    if not plan:
        await call.answer("پلن نامعتبر!", show_alert=True)
        return

    await call.answer()

    try:
        result = await create_payment(
            amount_toman=plan.price_toman,
            description=f"اشتراک {plan.label} StudyBot Pro",
            callback_url=CALLBACK_URL,
            user_telegram_id=call.from_user.id,
            plan_key=plan.key,
        )

        async with AsyncSessionLocal() as db:
            db.add(Payment(
                telegram_id=call.from_user.id,
                plan_key=plan.key,
                amount_toman=plan.price_toman,
                authority=result["authority"],
                status="pending",
            ))
            await db.commit()

        price_fmt = f"{plan.price_toman:,}".replace(",", "،")
        await call.message.answer(
            f"💳 <b>لینک پرداخت آماده‌ست</b>\n\n"
            f"💎 پلن: {plan.label}\n"
            f"💰 مبلغ: {price_fmt} تومان\n\n"
            f"بعد از پرداخت دکمه تأیید رو بزن 👇",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💳 پرداخت", url=result["url"])],
                [InlineKeyboardButton(
                    text="✅ تأیید پرداخت",
                    callback_data=f"verify_{result['authority']}_{plan.key}"
                )],
            ]),
        )
    except Exception:
        await call.message.answer("❌ خطا در ساخت لینک پرداخت. دوباره تلاش کن.")


@router.callback_query(F.data.startswith("verify_"))
async def handle_verify(call: CallbackQuery):
    parts = call.data.split("_", 2)
    if len(parts) != 3:
        await call.answer("خطا!", show_alert=True)
        return

    _, authority, plan_key = parts
    plan = PLANS.get(plan_key)
    if not plan:
        await call.answer("پلن نامعتبر!", show_alert=True)
        return

    await call.answer("در حال بررسی...")

    try:
        success = await verify_payment(authority=authority, amount_toman=plan.price_toman)
    except Exception:
        await call.message.answer("❌ خطا در تأیید پرداخت.")
        return

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Payment).where(Payment.authority == authority))
        payment = result.scalar_one_or_none()
        if payment:
            payment.status = "paid" if success else "failed"
            await db.commit()

    if success:
        await activate_premium(
            telegram_id=call.from_user.id,
            plan_key=plan_key,
            months=plan.months,
        )
        await call.message.answer(
            f"🎉 <b>پرداخت موفق!</b>\n\n"
            f"اشتراک <b>{plan.label}</b> برای {plan.months} ماه فعال شد ✅",
            parse_mode="HTML",
        )
    else:
        await call.message.answer("❌ پرداخت تأیید نشد. اگه مشکل داری با پشتیبانی تماس بگیر.")


@router.callback_query(F.data == "close")
async def close_menu(call: CallbackQuery):
    await call.message.delete()