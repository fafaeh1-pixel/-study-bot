from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from datetime import datetime, timedelta

from database.engine import AsyncSessionLocal
from database.models.user import User
from premium.zarinpal import verify_payment
from premium.plans import PLANS
from config import settings

router = APIRouter(prefix="/payment")


@router.get("/callback", response_class=HTMLResponse)
async def payment_callback(
    Authority: str = Query(...),
    Status:    str = Query(...),
):
    """زرین‌پال بعد از پرداخت اینجا ریدایرکت می‌کنه"""

    if Status != "OK":
        return _page("❌ پرداخت لغو شد", "متأسفانه پرداخت انجام نشد.", success=False)

    # اطلاعات پرداخت رو از دیتابیس بخون
    async with AsyncSessionLocal() as db:
        # پیدا کردن pending payment
        from database.models.payment import Payment
        payment = (
            await db.execute(
                select(Payment).where(Payment.authority == Authority)
            )
        ).scalar_one_or_none()

        if not payment:
            return _page("❌ خطا", "پرداخت پیدا نشد.", success=False)

        plan = PLANS.get(payment.plan_key)
        if not plan:
            return _page("❌ خطا", "پلن نامعتبر.", success=False)

        # تایید با زرین‌پال
        verified = await verify_payment(Authority, plan.price_toman)
        if not verified:
            return _page("❌ پرداخت تایید نشد", "لطفاً با پشتیبانی تماس بگیرید.", success=False)

        # آپدیت کاربر
        user = (
            await db.execute(select(User).where(User.telegram_id == payment.telegram_id))
        ).scalar_one_or_none()

        if user:
            now = datetime.utcnow()
            # اگه پریمیوم فعال داشت، از انقضا اضافه کن
            base = max(user.premium_expire or now, now)
            user.is_premium        = True
            user.premium_expire    = base + timedelta(days=plan.months * 30)
            user.plan_type         = plan.key
            payment.status         = "paid"
            await db.commit()

            # ارسال پیام تبریک به ربات
            await _notify_user(user.telegram_id, plan)

    return _page(
        "✅ پرداخت موفق",
        f"اشتراک {plan.label} شما فعال شد!\nبه ربات برگردید.",
        success=True,
    )


async def _notify_user(telegram_id: int, plan):
    """پیام تبریک به کاربر"""
    import httpx
    msg = (
        f"🎉 *تبریک! اشتراک پریمیوم فعال شد*\n\n"
        f"💎 پلن: {plan.label}\n"
        f"⏳ مدت: {plan.months} ماه\n\n"
        f"از همه امکانات پریمیوم لذت ببرید 🚀"
    )
    async with httpx.AsyncClient() as client:
        await client.post(
            f"https://api.telegram.org/bot{settings.BOT_TOKEN}/sendMessage",
            json={"chat_id": telegram_id, "text": msg, "parse_mode": "Markdown"},
        )


def _page(title: str, body: str, success: bool) -> str:
    color = "#10b981" if success else "#ef4444"
    icon  = "✅" if success else "❌"
    return f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{title}</title>
  <style>
    body {{ font-family: Tahoma,sans-serif; background:#0f172a; color:#f1f5f9;
            display:flex; align-items:center; justify-content:center; min-height:100vh; margin:0 }}
    .box {{ background:#1e293b; border:1px solid #334155; border-radius:16px;
            padding:2.5rem; text-align:center; max-width:400px; width:90% }}
    .icon {{ font-size:3rem; margin-bottom:1rem }}
    h1 {{ color:{color}; font-size:1.4rem; margin-bottom:0.75rem }}
    p  {{ color:#94a3b8; font-size:0.95rem; line-height:1.6 }}
    a  {{ display:inline-block; margin-top:1.5rem; background:{color};
          color:white; padding:0.6rem 1.5rem; border-radius:8px;
          text-decoration:none; font-weight:bold }}
  </style>
</head>
<body>
  <div class="box">
    <div class="icon">{icon}</div>
    <h1>{title}</h1>
    <p>{body}</p>
    <a href="https://t.me/{settings.BOT_USERNAME}">بازگشت به ربات</a>
  </div>
</body>
</html>"""