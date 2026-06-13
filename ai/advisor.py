import json
from dataclasses import dataclass
from collections import defaultdict
from ai.client import get_gemini_client


@dataclass
class AdvisorInput:
    full_name: str
    sessions: list[dict]
    daily_goal_minutes: int
    days_active: int


@dataclass
class AdvisorReport:
    top_strengths: list[str]
    top_weaknesses: list[str]
    subject_recommendations: list[dict]
    motivational_message: str


def _calculate_subject_metrics(sessions: list[dict]) -> dict:
    data: dict = defaultdict(lambda: {"total_minutes": 0, "session_count": 0, "dates": set()})
    for s in sessions:
        subj = s["subject"]
        data[subj]["total_minutes"] += s["duration"]
        data[subj]["session_count"] += 1
        data[subj]["dates"].add(s["date"].strftime("%Y-%m-%d"))
    return {
        subj: {
            "total_minutes": d["total_minutes"],
            "session_count": d["session_count"],
            "unique_days": len(d["dates"]),
            "avg_per_session": round(d["total_minutes"] / max(d["session_count"], 1), 1),
        }
        for subj, d in data.items()
    }


async def get_advisor_report(inp: AdvisorInput) -> AdvisorReport:
    if not inp.sessions:
        return AdvisorReport(
            top_strengths=["برای تحلیل ابتدا جلسات مطالعه ثبت کن"],
            top_weaknesses=[],
            subject_recommendations=[],
            motivational_message="هنوز داده‌ای ثبت نشده. همین امروز شروع کن! 🚀",
        )
    metrics = _calculate_subject_metrics(inp.sessions)
    total = sum(d["total_minutes"] for d in metrics.values())
    avg_daily = round(total / max(inp.days_active, 1), 1)
    metrics_text = "\n".join(
        f"  - {s}: {d['total_minutes']} دقیقه | {d['session_count']} جلسه | میانگین: {d['avg_per_session']} دقیقه"
        for s, d in sorted(metrics.items(), key=lambda x: x[1]["total_minutes"], reverse=True)
    )
    prompt = f"""تو یک مشاور تحصیلی باتجربه هستی. گزارش مشاوره دقیق به فارسی بده.

اطلاعات:
- نام: {inp.full_name}
- کل مطالعه: {total} دقیقه | روزهای فعال: {inp.days_active}
- میانگین روزانه: {avg_daily} دقیقه | هدف: {inp.daily_goal_minutes} دقیقه
- تعداد دروس: {len(metrics)}

دروس:
{metrics_text}

خروجی JSON:
{{
  "top_strengths": ["قوت ۱", "قوت ۲", "قوت ۳"],
  "top_weaknesses": ["ضعف ۱", "ضعف ۲", "ضعف ۳"],
  "subject_recommendations": [{{"subject": "درس", "advice": "توصیه", "priority": "high/medium/low"}}],
  "motivational_message": "پیام انگیزشی شخصی‌سازی‌شده"
}}"""

    model = get_gemini_client()
    response = model.generate_content(prompt)
    raw = response.text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    parsed = json.loads(raw.strip())
    return AdvisorReport(
        top_strengths=parsed.get("top_strengths", []),
        top_weaknesses=parsed.get("top_weaknesses", []),
        subject_recommendations=parsed.get("subject_recommendations", []),
        motivational_message=parsed.get("motivational_message", ""),
    )


def format_advisor_message(report: AdvisorReport) -> str:
    p = {"high": "🔴", "medium": "🟡", "low": "🟢"}
    strengths = "\n".join(f"  ✅ {s}" for s in report.top_strengths)
    weaknesses = "\n".join(f"  ⚠️ {w}" for w in report.top_weaknesses)
    recs = ""
    if report.subject_recommendations:
        recs = "\n\n📖 <b>توصیه‌های درسی:</b>\n"
        for r in report.subject_recommendations:
            recs += f"  {p.get(r.get('priority','medium'), '🟡')} <b>{r['subject']}:</b> {r['advice']}\n"
    return (
        f"🎓 <b>گزارش مشاوره تحصیلی</b>\n\n"
        f"💪 <b>نقاط قوت:</b>\n{strengths}\n\n"
        f"📈 <b>فرصت‌های بهبود:</b>\n{weaknesses}"
        f"{recs}\n\n"
        f"💬 <b>پیام مشاور:</b>\n{report.motivational_message}"
    )