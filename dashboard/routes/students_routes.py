from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func
from pathlib import Path

from dashboard.auth import get_current_user
from database.engine import AsyncSessionLocal
from database.models.user import User
from database.models.study_session import StudySession
from datetime import datetime, timedelta

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


def _auth(request: Request):
    try:
        return get_current_user(request)
    except Exception:
        return None


@router.get("/students", response_class=HTMLResponse)
async def students_list(request: Request, search: str = ""):
    if not _auth(request):
        return RedirectResponse(url="/login", status_code=302)

    async with AsyncSessionLocal() as session:
        query = select(User).order_by(User.created_at.desc())
        if search:
            query = query.where(User.full_name.ilike(f"%{search}%"))
        students = (await session.execute(query)).scalars().all()

    return templates.TemplateResponse(
        request=request,
        name="students.html",
        context={"students": students, "search": search},
    )


@router.get("/students/{telegram_id}", response_class=HTMLResponse)
async def student_detail(request: Request, telegram_id: int):
    if not _auth(request):
        return RedirectResponse(url="/login", status_code=302)

    month_ago = datetime.utcnow() - timedelta(days=30)

    async with AsyncSessionLocal() as session:
        student = (
            await session.execute(select(User).where(User.telegram_id == telegram_id))
        ).scalar_one_or_none()

        if not student:
            return RedirectResponse(url="/students", status_code=302)

        # ── جلسات ماه اخیر ──────────────────────────────────────────────
        sessions = (
            await session.execute(
                select(StudySession)
                .where(
                    StudySession.user_id == student.id,       # ✅ student.id نه telegram_id
                    StudySession.session_date >= month_ago,
                )
                .order_by(StudySession.session_date.desc())
            )
        ).scalars().all()

        # ── کل مطالعه (همیشه، نه فقط ماه اخیر) ─────────────────────────
        all_minutes = (
            await session.execute(
                select(func.sum(StudySession.duration_minutes))
                .where(StudySession.user_id == student.id)
            )
        ).scalar() or 0

    subject_stats: dict = {}
    for s in sessions:
        key = s.subject or "نامشخص"
        subject_stats[key] = subject_stats.get(key, 0) + s.duration_minutes

    month_minutes = sum(s.duration_minutes for s in sessions)

    return templates.TemplateResponse(
        request=request,
        name="student.html",
        context={
            "student":      student,
            "sessions":     sessions,
            "subject_stats": sorted(subject_stats.items(), key=lambda x: x[1], reverse=True),
            "total_minutes": all_minutes,
            "hours":         int(all_minutes) // 60,
            "mins":          int(all_minutes) % 60,
            "month_minutes": month_minutes,
            "month_hours":   month_minutes // 60,
            "month_mins":    month_minutes % 60,
        },
    )


@router.post("/students/{telegram_id}/edit")
async def student_edit(
    request: Request,
    telegram_id: int,
    full_name: str = Form(...),
    daily_goal_minutes: int = Form(...),
):
    if not _auth(request):
        return RedirectResponse(url="/login", status_code=302)

    async with AsyncSessionLocal() as session:
        student = (
            await session.execute(select(User).where(User.telegram_id == telegram_id))
        ).scalar_one_or_none()

        if student:
            student.full_name = full_name
            student.daily_goal_minutes = daily_goal_minutes
            await session.commit()

    return RedirectResponse(url=f"/students/{telegram_id}", status_code=302)


@router.post("/students/{telegram_id}/delete-session/{session_id}")
async def delete_session(request: Request, telegram_id: int, session_id: int):
    if not _auth(request):
        return RedirectResponse(url="/login", status_code=302)

    async with AsyncSessionLocal() as db:
        s = (
            await db.execute(select(StudySession).where(StudySession.id == session_id))
        ).scalar_one_or_none()

        if s:
            await db.delete(s)
            await db.commit()

    return RedirectResponse(url=f"/students/{telegram_id}", status_code=302)