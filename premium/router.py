from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from premium.plans import PLANS, PREMIUM_FEATURES
from premium.zarinpal import create_payment, verify_payment
from premium.checker import is_premium, get_subscription_info
from config import settings

router = Router()


# ───────────────────────────── نمایش پلن‌ها ─────────────────────────────

@router.message(Command("premium"))
async def cmd_premium(message: Message):
    user_id = message.from_user.id

    info = await get_subscription_info(user_id)
    if info:
        days = info["days_left"]
        plan = PLANS.get(info["plan_key"])
        label = plan.label if plan else info["plan_key"]
        await message.answer(
            f"✅ <b>اشتراک فعال داری!</b>\n\n"
            f"📦 پلن: {label}\n"
            f"⏳ روزهای باقی‌مانده: <b>{days}</b> روز",
            parse_mode="HTML",
        )
        return

    features_text = "\n".join(PREMIUM_FEATURES)
    text = (
        f"⭐ <b>پرمیوم StudyBot</b>\n\n"
        f"<b>امکانات پریمیوم:</b>\n{features_text}\n\n"
        f"یه پلن انتخاب کن:"
    )

    builder = InlineKeyboardBuilder()
    for key, plan in PLANS.items():
        builder.button(
            text=f"{plan.emoji} {plan.label} — {plan.price_toman:,} تومان",
            callback_data=f"buy_plan:{key}",
        )
    builder.adjust(1)

    await message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")


# ───────────────────────────── انتخاب پلن ─────────────────────────────

@router.callback_query(F.data.startswith("buy_plan:"))
async def cb_buy_plan(callback: CallbackQuery):
    plan_key = callback.data.split(":")[1]
    plan = PLANS.get(plan_key)
    if not plan:
        await callback.answer("پلن نامعتبر!", show_alert=True)
        return

    await callback.answer()

    try:
        result = await create_payment(
            amount_toman=plan.price_toman,
            description=f"اشتراک {plan.label} StudyBot",
            callback_url=settings.PAYMENT_CALLBACK_URL,
            user_telegram_id=callback.from_user.id,
            plan_key=plan_key,
        )
    except Exception as e:
        await callback.message.answer(f"❌ خطا در اتصال به درگاه پرداخت:\n<code>{e}</code>", parse_mode="HTML")
        return

    builder = InlineKeyboardBuilder()
    builder.button(text="💳 پرداخت", url=result["url"])
    builder.button(text="✅ تأیید پرداخت", callback_data=f"verify:{result['authority']}:{plan_key}")
    builder.adjust(1)

    await callback.message.answer(
        f"🔗 لینک پرداخت برای پلن <b>{plan.label}</b> ({plan.price_toman:,} تومان) آماده شد.\n\n"
        f"بعد از پرداخت دکمه «تأیید پرداخت» رو بزن.",
        reply_markup=builder.as_markup(),
        parse_mode="HTML",
    )


# ───────────────────────────── تأیید پرداخت ─────────────────────────────

@router.callback_query(F.data.startswith("verify:"))
async def cb_verify(callback: CallbackQuery):
    _, authority, plan_key = callback.data.split(":")
    plan = PLANS.get(plan_key)
    if not plan:
        await callback.answer("پلن نامعتبر!", show_alert=True)
        return

    await callback.answer("در حال بررسی...")

    try:
        success = await verify_payment(authority=authority, amount_toman=plan.price_toman)
    except Exception as e:
        await callback.message.answer(f"❌ خطا در تأیید پرداخت:\n<code>{e}</code>", parse_mode="HTML")
        return

    if success:
        await _activate_subscription(
            user_id=callback.from_user.id,
            plan_key=plan_key,
            months=plan.months,
        )
        await callback.message.answer(
            f"🎉 <b>پرداخت موفق!</b>\n\n"
            f"اشتراک <b>{plan.label}</b> برای {plan.months} ماه فعال شد. ✅",
            parse_mode="HTML",
        )
    else:
        await callback.message.answer("❌ پرداخت تأیید نشد. اگه مشکل داری با پشتیبانی تماس بگیر.")


# ───────────────────────────── فعال‌سازی اشتراک ─────────────────────────────

async def _activate_subscription(user_id: int, plan_key: str, months: int):
    from datetime import datetime, timezone, timedelta
    from db import get_db
    from db.models import Subscription

    expires_at = datetime.now(timezone.utc) + timedelta(days=months * 30)

    async with get_db() as db:
        sub = Subscription(
            user_id=user_id,
            plan_key=plan_key,
            expires_at=expires_at,
        )
        db.add(sub)
        await db.commit()