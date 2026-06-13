from google import genai
from config import settings
import jdatetime
import random
import json
import asyncio
from dataclasses import dataclass
from datetime import datetime


@dataclass
class PlanRequest:
    full_name: str
    subjects: list[str]
    daily_goal_minutes: int
    weak_subjects: list[str]
    exam_date: datetime | None
    days_to_plan: int = 7


@dataclass
class DayPlan:
    day_name: str
    sessions: list[dict]
    total_minutes: int


@dataclass
class StudyPlan:
    overview: str
    days: list[DayPlan]
    weekly_tips: list[str]


def _build_plan_prompt(sessions: list, user_name: str, daily_goal: int, subjects: list[str]) -> str:
    subject_stats: dict = {}
    for s in sessions:
        subject_stats[s.subject] = subject_stats.get(s.subject, 0) + s.duration_minutes

    sorted_subjects = sorted(subject_stats.items(), key=lambda x: x[1])
    weak = sorted_subjects[0][0] if sorted_subjects else ""
    strong = sorted_subjects[-1][0] if sorted_subjects else ""
    subjects_text = ", ".join(subjects)
    today = jdatetime.date.today().strftime("%Y/%m/%d")

    return f"""
تو یک مشاور تحصیلی حرفه‌ای هستی. یک برنامه مطالعه هفتگی شخصی‌سازی‌شده بساز.

کاربر: {user_name}
تاریخ امروز: {today}
هدف روزانه: {daily_goal} دقیقه
درس‌ها: {subjects_text}
ضعیف‌ترین درس: {weak}
قوی‌ترین درس: {strong}

قوانین:
- 7 روز (شنبه تا جمعه) هر روز جداگانه
- هر روز ترکیب متفاوتی از درس‌ها
- روزهای اول هفته تمرکز بیشتر روی درس ضعیف
- جمعه روز مرور کلی و استراحت
- زمان هر درس دقیقاً مشخص باشد
- مجموع هر روز برابر {daily_goal} دقیقه
- یک نکته انگیزشی در پایان
- از ایموجی‌های متنوع استفاده کن
- حداکثر 200 کلمه، کاملاً فارسی
""".strip()


def _build_planner_prompt(req: PlanRequest) -> str:
    exam_info = (
        f"تاریخ امتحان: {req.exam_date.strftime('%Y/%m/%d')} "
        f"({(req.exam_date - datetime.now()).days} روز دیگر)"
        if req.exam_date else "امتحانی در پیش رو نیست"
    )
    days = ["شنبه", "یک‌شنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنج‌شنبه", "جمعه"]

    return f"""تو یک مشاور تحصیلی متخصص هستی. یک برنامه مطالعه هفتگی دقیق بساز.

اطلاعات:
- نام: {req.full_name}
- دروس: {', '.join(req.subjects)}
- دروس ضعیف: {', '.join(req.weak_subjects) if req.weak_subjects else 'مشخص نشده'}
- هدف روزانه: {req.daily_goal_minutes} دقیقه
- {exam_info}
- روزها: {', '.join(days[:req.days_to_plan])}

قوانین: دروس ضعیف ۴۰٪ بیشتر وقت بگیرند. هر جلسه ۳۰-۹۰ دقیقه. جمعه سبک‌تر.

خروجی را دقیقاً در این قالب JSON بده (بدون هیچ متن اضافه‌ای):
{{
  "overview": "خلاصه برنامه",
  "days": [
    {{"day": "شنبه", "sessions": [{{"subject": "درس", "minutes": 60, "tip": "نکته"}}]}}
  ],
  "weekly_tips": ["نکته ۱", "نکته ۲", "نکته ۳"]
}}"""


def _sync_generate_plan(prompt: str) -> str:
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
    )
    return response.text.strip()


async def generate_study_plan(
    sessions: list,
    user_name: str,
    daily_goal: int,
    subjects: list[str] | None = None,
) -> str:
    if subjects is None:
        subject_stats: dict = {}
        for s in sessions:
            subject_stats[s.subject] = subject_stats.get(s.subject, 0) + s.duration_minutes
        subjects = list(subject_stats.keys())

    if not subjects:
        return (
            f"سلام {user_name} عزیز!\n\n"
            "برای ساخت برنامه مطالعه، ابتدا چند جلسه مطالعه ثبت کن "
            "تا درس‌هایت شناسایی بشن."
        )

    if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY == "your_key_here":
        return _smart_local_plan(sessions, user_name, daily_goal, subjects)

    try:
        prompt = _build_plan_prompt(sessions, user_name, daily_goal, subjects)
        return await asyncio.to_thread(_sync_generate_plan, prompt)
    except Exception:
        return _smart_local_plan(sessions, user_name, daily_goal, subjects)


async def generate_study_plan_structured(req: PlanRequest) -> StudyPlan:
    if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY == "your_key_here":
        return _fallback_structured_plan(req)

    try:
        raw = await asyncio.to_thread(_sync_generate_plan, _build_planner_prompt(req))
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        parsed = json.loads(raw.strip())

        days = []
        for d in parsed.get("days", []):
            sessions = d.get("sessions", [])
            days.append(DayPlan(
                day_name=d.get("day", ""),
                sessions=sessions,
                total_minutes=sum(s.get("minutes", 0) for s in sessions),
            ))
        return StudyPlan(
            overview=parsed.get("overview", ""),
            days=days,
            weekly_tips=parsed.get("weekly_tips", []),
        )
    except Exception:
        return _fallback_structured_plan(req)


def _fallback_structured_plan(req: PlanRequest) -> StudyPlan:
    day_names = ["شنبه", "یک‌شنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنج‌شنبه", "جمعه"]
    days = []

    for i, day_name in enumerate(day_names[:req.days_to_plan]):
        if day_name == "جمعه":
            sessions = [{"subject": "مرور کلی", "minutes": req.daily_goal_minutes // 2, "tip": "روز استراحت و مرور"}]
        else:
            sessions = []
            subjects = req.weak_subjects + [s for s in req.subjects if s not in req.weak_subjects]
            if not subjects:
                subjects = req.subjects
            per = req.daily_goal_minutes // max(len(subjects[:2]), 1)
            for j, subj in enumerate(subjects[:2]):
                minutes = per + (10 if subj in req.weak_subjects else 0)
                sessions.append({"subject": subj, "minutes": minutes, "tip": ""})

        days.append(DayPlan(
            day_name=day_name,
            sessions=sessions,
            total_minutes=sum(s["minutes"] for s in sessions),
        ))

    return StudyPlan(
        overview=f"برنامه هفتگی {req.full_name} — {req.daily_goal_minutes} دقیقه در روز",
        days=days,
        weekly_tips=["منظم بخوان", "بعد از هر ۵۰ دقیقه استراحت کن", "دروس ضعیف رو اول بخوان"],
    )


def _smart_local_plan(sessions: list, user_name: str, daily_goal: int, subjects: list[str]) -> str:
    subject_stats: dict = {}
    for s in sessions:
        subject_stats[s.subject] = subject_stats.get(s.subject, 0) + s.duration_minutes

    sorted_by_need = sorted(subjects, key=lambda x: subject_stats.get(x, 0))

    days_config = [
        ("شنبه",     "📚", 0.6),
        ("یکشنبه",   "✏️", 0.5),
        ("دوشنبه",   "🔬", 0.5),
        ("سه‌شنبه",  "📐", 0.4),
        ("چهارشنبه", "📖", 0.6),
        ("پنجشنبه",  "🧠", 0.3),
        ("جمعه",     "😴", 0.0),
    ]

    motivational = [
        "هر روز یه قدم کوچیک، یه فردای بزرگ میسازه!",
        "تو می‌تونی! فقط شروع کن.",
        "مطالعه منظم، کلید موفقیته.",
        "به خودت ایمان داشته باش!",
        "امروزت رو بساز، فردات رو بدرخش!",
    ]

    lines = [f"برنامه مطالعه هفتگی — {user_name}\n"]

    for i, (day, emoji, weak_ratio) in enumerate(days_config):
        if day == "جمعه":
            lines.append(f"{emoji} جمعه: مرور کلی + استراحت")
            continue

        if len(sorted_by_need) == 1:
            subj = sorted_by_need[0]
            lines.append(f"{emoji} {day}: {subj} — ({daily_goal} دق)")
        elif len(sorted_by_need) == 2:
            s1, s2 = sorted_by_need[0], sorted_by_need[1]
            t1 = round(daily_goal * (0.6 if i % 2 == 0 else 0.4) / 5) * 5
            t1 = max(20, min(t1, daily_goal - 20))
            t2 = daily_goal - t1
            lines.append(f"{emoji} {day}: {s1} ({t1} دق) + {s2} ({t2} دق)")
        else:
            chosen_main = sorted_by_need[0]
            rest = sorted_by_need[1:]
            chosen_second = rest[i % len(rest)]
            t1 = round(daily_goal * 0.55 / 5) * 5
            t2 = daily_goal - t1
            lines.append(f"{emoji} {day}: {chosen_main} ({t1} دق) + {chosen_second} ({t2} دق)")

    lines.append(f"\nمجموع روزانه: {daily_goal} دقیقه")
    lines.append(f"\n{random.choice(motivational)}")
    return "\n".join(lines)


def format_plan_message(plan: StudyPlan) -> str:
    lines = [f"📅 <b>برنامه مطالعه هوشمند</b>\n\n📌 {plan.overview}\n"]
    for day in plan.days:
        lines.append(f"\n<b>━━ {day.day_name} ({day.total_minutes} دقیقه) ━━</b>")
        for s in day.sessions:
            lines.append(f"  📚 {s['subject']} — {s['minutes']} دقیقه")
            if s.get("tip"):
                lines.append(f"     💡 {s['tip']}")
    if plan.weekly_tips:
        lines.append("\n\n🌟 <b>نکات هفتگی:</b>")
        for tip in plan.weekly_tips:
            lines.append(f"  • {tip}")
    return "\n".join(lines)