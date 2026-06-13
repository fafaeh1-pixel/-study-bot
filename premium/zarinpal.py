import httpx
from config import settings

ZARINPAL_REQUEST_URL = "https://api.zarinpal.com/pg/v4/payment/request.json"
ZARINPAL_VERIFY_URL  = "https://api.zarinpal.com/pg/v4/payment/verify.json"
ZARINPAL_GATEWAY     = "https://www.zarinpal.com/pg/StartPay/{authority}"


async def create_payment(
    amount_toman: int,
    description: str,
    callback_url: str,
    user_telegram_id: int,
    plan_key: str,
) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            ZARINPAL_REQUEST_URL,
            json={
                "merchant_id":  settings.ZARINPAL_MERCHANT_ID,
                "amount":       amount_toman * 10,
                "description":  description,
                "callback_url": callback_url,
                "metadata": {
                    "telegram_id": str(user_telegram_id),
                    "plan":        plan_key,
                },
            },
            timeout=15,
        )
        data = resp.json()

    if data.get("data", {}).get("code") == 100:
        authority = data["data"]["authority"]
        return {
            "url":       ZARINPAL_GATEWAY.format(authority=authority),
            "authority": authority,
        }
    raise ValueError(f"خطای زرین‌پال: {data}")


async def verify_payment(authority: str, amount_toman: int) -> bool:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            ZARINPAL_VERIFY_URL,
            json={
                "merchant_id": settings.ZARINPAL_MERCHANT_ID,
                "amount":      amount_toman * 10,
                "authority":   authority,
            },
            timeout=15,
        )
        data = resp.json()

    return data.get("data", {}).get("code") in (100, 101)