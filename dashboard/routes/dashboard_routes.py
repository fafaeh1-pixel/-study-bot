from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from datetime import datetime, timedelta
import logging

from database.engine import AsyncSessionFactory
from database.models import User, StudySession
from sqlalchemy import func, select

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


# ─── helpers ────────────────────────────────────────────────────────────────

def _require_auth(request: Request):
    if not request.cookies.get("access_token"):
        return RedirectResponse(url="/login", status_code=302)
    return None


PERSIAN_DAYS = {
    0: "دوشنبه", 1: "سه‌شنبه", 2: "چهارشنبه",
    3: "پنجشنبه", 4: "جمعه",   5: "شنبه",     6: "یکشنبه",
}


# ─── routes ─────────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def root(request: Request):
    if redirect := _require_auth(request):
        return redirect
    return RedirectResponse(url="/dashboard", status_code=302)


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    if redirect := _require_auth(request):
        return redirect

    now_utc  = datetime.utcnow()
    week_ago = now_utc - timedelta(days=7)
    today    = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)

    try:
        async with AsyncSessionFactory() as db:

            total_users: int = (
                await db.execute(select(func.count(User.id)))
            ).scalar() or 0

            active_users: int = (
                await db.execute(
                    select(func.count(func.distinct(StudySession.user_id)))
                    .where(StudySession.session_date >= week_ago)
                )
            ).scalar() or 0

            total_minutes = (
                await db.execute(
                    select(func.sum(StudySession.duration_minutes))
                    .where(StudySession.session_date >= week_ago)
                )
            ).scalar() or 0
            hours = int(total_minutes) // 60
            mins  = int(total_minutes) % 60

            total_sessions: int = (
                await db.execute(
                    select(func.count(StudySession.id))
                    .where(StudySession.session_date >= week_ago)
                )
            ).scalar() or 0

            top_raw = (
                await db.execute(
                    select(
                        User.full_name,
                        func.sum(StudySession.duration_minutes).label("total"),
                    )
                    .join(StudySession, StudySession.user_id == User.telegram_id)
                    .where(StudySession.session_date >= week_ago)
                    .group_by(User.id)
                    .order_by(func.sum(StudySession.duration_minutes).desc())
                    .limit(5)
                )
            ).all()
            top_users = [
                (row.full_name or "بی‌نام", int(row.total or 0))
                for row in top_raw
            ]

            recent_users = (
                await db.execute(
                    select(User).order_by(User.created_at.desc()).limit(8)
                )
            ).scalars().all()

            daily_stats = []
            for i in range(6, -1, -1):
                day_start = today - timedelta(days=i)
                day_end   = day_start + timedelta(days=1)

                day_minutes = (
                    await db.execute(
                        select(func.sum(StudySession.duration_minutes))
                        .where(
                            StudySession.session_date >= day_start,
                            StudySession.session_date <  day_end,
                        )
                    )
                ).scalar() or 0

                daily_stats.append({
                    "day":     PERSIAN_DAYS.get(day_start.weekday(), "؟"),
                    "minutes": int(day_minutes),
                })

    except Exception as exc:
        logger.exception("خطا در بارگذاری داشبورد: %s", exc)
        return templates.TemplateResponse(
            request=request,
            name="error.html",
            context={"message": "خطا در بارگذاری اطلاعات. لطفاً دوباره تلاش کنید."},
            status_code=500,
        )

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "total_users":    total_users,
            "active_users":   active_users,
            "hours":          hours,
            "mins":           mins,
            "total_sessions": total_sessions,
            "top_users":      top_users,
            "recent_users":   recent_users,
            "daily_stats":    daily_stats,
            "now":            now_utc.strftime("%Y/%m/%d %H:%M"),
        },
    )