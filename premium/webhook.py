"""
webhook.py — تأیید پرداخت زرین‌پال
این فایل رو داخل پوشه premium/ بذار.

اگه از FastAPI/aiohttp استفاده نمی‌کنی، می‌تونی verify رو
مستقیم از طریق دکمه تلگرام (روش دوم) انجام بدی — روش دوم رو
در premium_handler.py داریم.
"""
from fastapi import APIRouter, Request
from sqlalchemy import select

from database.engine import AsyncSessionLocal
from database.models.payment import Payment
from premium.zarinpal import verify_payment
from premium.checker import activate_premium
from premium.plans import PLANS

webhook_router = APIRouter()


@webhook_router.get("/payment/callback")
async def payment_callback(request: Request):
    params = dict(request.query_params)
    authority = params.get("Authority", "")
    status = params.get("Status", "")

    if status != "OK":
        return {"result": "cancelled"}

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Payment).where(Payment.authority == authority)
        )
        payment = result.scalar_one_or_none()

    if not payment:
        return {"result": "not_found"}

    plan = PLANS.get(payment.plan_key)
    if not plan:
        return {"result": "invalid_plan"}

    success = await verify_payment(authority=authority, amount_toman=payment.amount_toman)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Payment).where(Payment.authority == authority)
        )
        pay = result.scalar_one_or_none()
        if pay:
            pay.status = "paid" if success else "failed"
            await db.commit()

    if success:
        await activate_premium(
            telegram_id=payment.telegram_id,
            plan_key=payment.plan_key,
            months=plan.months,
        )
        return {"result": "success"}

    return {"result": "failed"}