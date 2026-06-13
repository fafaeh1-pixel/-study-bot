from dataclasses import dataclass

@dataclass
class Plan:
    key: str
    label: str
    emoji: str
    months: int
    price_toman: int
    description: str

PLANS: dict[str, Plan] = {
    "monthly": Plan(
        key="monthly",
        label="ماهانه",
        emoji="📅",
        months=1,
        price_toman=50_000,
        description="دسترسی کامل به همه امکانات پریمیوم برای ۱ ماه",
    ),
    "quarterly": Plan(
        key="quarterly",
        label="سه‌ماهه",
        emoji="📆",
        months=3,
        price_toman=120_000,
        description="دسترسی کامل به همه امکانات پریمیوم برای ۳ ماه",
    ),
    "biannual": Plan(
        key="biannual",
        label="شش‌ماهه",
        emoji="🗓️",
        months=6,
        price_toman=270_000,
        description="دسترسی کامل به همه امکانات پریمیوم برای ۶ ماه",
    ),
    "yearly": Plan(
        key="yearly",
        label="سالانه",
        emoji="🏆",
        months=12,
        price_toman=550_000,
        description="دسترسی کامل به همه امکانات پریمیوم برای ۱ سال",
    ),
}

PREMIUM_FEATURES = [
    "⏰ یادآور نامحدود",
    "🎙️ ارسال ویس در تمام بخش‌ها",
    "📊 دریافت نمودار به صورت تصویر در تمام بخش‌ها",
]