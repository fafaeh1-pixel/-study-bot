from dataclasses import dataclass
from collections import defaultdict
import google.generativeai as genai
import json


@dataclass
class StudyData:
    full_name: str
    total_minutes: int
    daily_goal_minutes: int
    sessions: list


@dataclass
class AnalysisResult:
    summary: str
    strengths: list
    weaknesses: list
    consistency_score: int
    goal_achievement: float


def _build_stats(data):
    subject_minutes = defaultdict(int)
    daily_minutes = defaultdict(int)
    for s in data.sessions:
        subject_minutes[s["subject"]] += s["duration"]
        day_key = s["date"].strftime("%Y-%m-%d")
        daily_minutes[day_key] += s["duration"]
    days_with_study = len(daily_minutes)
    consistency = int((days_with_study / 30) * 100)
    avg_daily = data.total_minutes / max(days_with_study, 1)
    goal_pct = (avg_daily / data.daily_goal_minutes * 100) if data.daily_goal_minutes else 0
    top_subject = max(subject_minutes, key=subject_minutes.get) if subject_minutes else "-"
    weak_subject = min(subject_minutes, key=subject_minutes.get) if len(subject_minutes) > 1 else "-"
    return {
        "subject_minutes": dict(subject_minutes),
        "daily_minutes": dict(daily_minutes),
        "days_with_study": days_with_study,
        "consistency": consistency,
        "avg_daily_minutes": round(avg_daily, 1),
        "goal_achievement_pct": round(min(goal_pct, 100), 1),
        "top_subject": top_subject,
        "weak_subject": weak_subject,
        "total_sessions": len(data.sessions),
    }


def _build_prompt(data, stats):
    subjects_text = "\n".join(
        f"  - {subj}: {mins} دقیقه"
        for subj, mins in sorted(stats["subject_minutes"].items(), key=lambda x: x[1], reverse=True)
    )
    return f"""تو یک مشاور تحصیلی حرفه‌ای هستی. بر اساس داده‌های زیر، یک تحلیل کامل به فارسی ارائه بده.

اطلاعات دانشجو:
- نام: {data.full_name}
- هدف روزانه: {data.daily_goal_minutes} دقیقه
- کل مطالعه ۳۰ روز اخیر: {data.total_minutes} دقیقه
- تعداد روزهای مطالعه: {stats['days_with_study']} از ۳۰ روز
- میانگین روزانه: {stats['avg_daily_minutes']} دقیقه
- درصد رسیدن به هدف: {stats['goal_achievement_pct']}٪

توزیع دروس:
{subjects_text}

خروجی را دقیقاً در این قالب JSON بده:
{{
  "summary": "یک پاراگراف ۳-۴ جمله‌ای درباره وضعیت کلی",
  "strengths": ["نقطه قوت ۱", "نقطه قوت ۲", "نقطه قوت ۳"],
  "weaknesses": ["نقطه ضعف ۱", "نقطه ضعف ۲", "نقطه ضعف ۳"],
  "advice": "یک توصیه کلیدی و عملی برای هفته آینده"
}}"""


async def analyze_progress(data):
    stats = _build_stats(data)
    raw = await async_generate(_build_prompt(data, stats))
    if "```" in raw:
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    parsed = json.loads(raw.strip())
    return AnalysisResult(
        summary=parsed.get("summary", ""),
        strengths=parsed.get("strengths", []),
        weaknesses=parsed.get("weaknesses", []),
        consistency_score=stats["consistency"],
        goal_achievement=stats["goal_achievement_pct"],
    )


def format_analysis_message(result):
    strengths = "\n".join(f"  ✅ {s}" for s in result.strengths)
    weaknesses = "\n".join(f"  ⚠️ {w}" for w in result.weaknesses)
    def bar(v): return "█" * int(v / 10) + "░" * (10 - int(v / 10)) + f" {v:.0f}٪"
    return (
        f"📊 <b>تحلیل پیشرفت مطالعه</b>\n\n"
        f"📝 <b>خلاصه وضعیت:</b>\n{result.summary}\n\n"
        f"💪 <b>نقاط قوت:</b>\n{strengths}\n\n"
        f"📈 <b>نقاط ضعف:</b>\n{weaknesses}\n\n"
        f"🎯 <b>رسیدن به هدف:</b>\n{bar(result.goal_achievement)}\n\n"
        f"📅 <b>ثبات مطالعه:</b>\n{bar(result.consistency_score)}"
    )