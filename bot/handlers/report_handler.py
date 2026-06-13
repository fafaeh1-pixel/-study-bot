from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.main_keyboard import get_report_inline_keyboard
from bot.texts import texts
from database.models.user import User
from database.repositories.study_session_repository import StudySessionRepository
from premium.checker import is_premium
import jdatetime

router = Router(name="report")

FREE_CHART_LIMIT = 10
FREE_PDF_LIMIT = 10

_usage_cache: dict[str, int] = {}


def _get_usage(telegram_id: int, feature: str) -> int:
    return _usage_cache.get(f"{telegram_id}_{feature}", 0)


def _increment_usage(telegram_id: int, feature: str) -> int:
    key = f"{telegram_id}_{feature}"
    _usage_cache[key] = _usage_cache.get(key, 0) + 1
    return _usage_cache[key]


@router.message(F.text == texts.BTN_DAILY_REPORT)
async def daily_report(message: Message, session: AsyncSession, db_user: User) -> None:
    repo = StudySessionRepository(session)
    sessions = await repo.get_today_sessions(db_user.telegram_id)

    if not sessions:
        await message.answer(texts.NO_SESSIONS_TODAY)
        return

    today_jalali = jdatetime.date.today().strftime("%Y/%m/%d")
    total_minutes = sum(s.duration_minutes for s in sessions)
    hours, mins = divmod(total_minutes, 60)

    lines = [
        f"گزارش امروز - {today_jalali}",
        "",
        f"مجموع: {hours} ساعت و {mins} دقیقه",
        f"تعداد جلسات: {len(sessions)}",
        "",
        "جزئیات:",
    ]
    for s in sessions:
        lines.append(f"  - {s.subject}: {s.duration_minutes} دقیقه")

    await message.answer("\n".join(lines), reply_markup=get_report_inline_keyboard())


@router.message(F.text == texts.BTN_WEEKLY_REPORT)
async def weekly_report(message: Message, session: AsyncSession, db_user: User) -> None:
    repo = StudySessionRepository(session)
    sessions = await repo.get_week_sessions(db_user.telegram_id)

    if not sessions:
        await message.answer(texts.NO_SESSIONS_WEEK)
        return

    total_minutes = sum(s.duration_minutes for s in sessions)
    hours, mins = divmod(total_minutes, 60)
    week_num = jdatetime.date.today().isocalendar()[1]

    subject_stats: dict = {}
    for s in sessions:
        subject_stats[s.subject] = subject_stats.get(s.subject, 0) + s.duration_minutes

    lines = [
        f"گزارش هفتگی - هفته {week_num}",
        "",
        f"مجموع: {hours} ساعت و {mins} دقیقه",
        f"تعداد جلسات: {len(sessions)}",
        "",
        "آمار درس‌ها:",
    ]
    for subject, m in sorted(subject_stats.items(), key=lambda x: x[1], reverse=True):
        h, mn = divmod(m, 60)
        lines.append(f"  - {subject}: {h}h {mn}m")

    await message.answer("\n".join(lines), reply_markup=get_report_inline_keyboard())


@router.callback_query(F.data == "show_chart")
async def show_chart_callback(callback: CallbackQuery, session: AsyncSession, db_user: User) -> None:
    premium = is_premium(db_user)

    if not premium:
        used = _get_usage(db_user.telegram_id, "chart")
        if used >= FREE_CHART_LIMIT:
            await callback.answer(
                f"سقف {FREE_CHART_LIMIT} نمودار رایگان تموم شد!\n⭐ /premium بزن برای نامحدود.",
                show_alert=True,
            )
            return
        _increment_usage(db_user.telegram_id, "chart")

    await callback.answer("در حال تهیه نمودار...")
    repo = StudySessionRepository(session)
    sessions = await repo.get_week_sessions(db_user.telegram_id)

    if not sessions:
        await callback.message.answer("داده‌ای برای نمایش وجود ندارد.")
        return

    try:
        from charts.study_chart import generate_weekly_bar_chart, generate_subject_pie_chart

        remaining = FREE_CHART_LIMIT - _get_usage(db_user.telegram_id, "chart")
        if premium:
            chart_caption = "نمودار مطالعه هفتگی ⭐"
        else:
            chart_caption = f"نمودار مطالعه هفتگی ({remaining} باقی‌مانده)"

        bar_buf = generate_weekly_bar_chart(sessions, db_user.full_name)
        await callback.message.answer_photo(
            BufferedInputFile(bar_buf.read(), filename="weekly_chart.png"),
            caption=chart_caption,
        )

        pie_buf = generate_subject_pie_chart(sessions, db_user.full_name)
        if pie_buf:
            await callback.message.answer_photo(
                BufferedInputFile(pie_buf.read(), filename="subject_chart.png"),
                caption="توزیع درس‌ها",
            )
    except Exception as e:
        await callback.message.answer(f"خطا در تهیه نمودار: {e}")


@router.callback_query(F.data == "show_pdf")
async def show_pdf_callback(callback: CallbackQuery, session: AsyncSession, db_user: User) -> None:
    premium = is_premium(db_user)

    if not premium:
        used = _get_usage(db_user.telegram_id, "pdf")
        if used >= FREE_PDF_LIMIT:
            await callback.answer(
                f"سقف {FREE_PDF_LIMIT} PDF رایگان تموم شد!\n⭐ /premium بزن برای نامحدود.",
                show_alert=True,
            )
            return
        _increment_usage(db_user.telegram_id, "pdf")

    await callback.answer("در حال تهیه PDF...")
    repo = StudySessionRepository(session)
    sessions = await repo.get_week_sessions(db_user.telegram_id)

    remaining = FREE_PDF_LIMIT - _get_usage(db_user.telegram_id, "pdf")
    if premium:
        pdf_caption = "گزارش هفتگی PDF ⭐"
    else:
        pdf_caption = f"گزارش هفتگی PDF ({remaining} باقی‌مانده)"

    try:
        from reports.pdf_report import generate_weekly_pdf
        pdf_buf = generate_weekly_pdf(sessions, db_user.full_name)
        await callback.message.answer_document(
            BufferedInputFile(pdf_buf.read(), filename="weekly_report.pdf"),
            caption=pdf_caption,
        )
    except Exception as e:
        await callback.message.answer(f"خطا در تهیه PDF: {e}")


@router.callback_query(F.data == "refresh_report")
async def refresh_report_callback(callback: CallbackQuery) -> None:
    await callback.answer("بروزرسانی شد")