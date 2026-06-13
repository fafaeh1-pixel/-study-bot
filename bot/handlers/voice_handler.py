from aiogram import Router, F
from aiogram.types import Message, BufferedInputFile
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.user import User
from database.repositories.study_session_repository import StudySessionRepository
from premium.checker import is_premium

router = Router(name="voice")


@router.message(F.text == "🔊 ویس گزارش")
async def send_voice_report(
    message: Message,
    db: AsyncSession,
    db_user: User,
) -> None:
    if not is_premium(db_user):
        await message.answer(
            "⭐ <b>ویس گزارش مخصوص پریمیوم‌هاست!</b>\n\n"
            "با پریمیوم می‌تونی گزارش هفتگیت رو به صورت ویس فارسی دریافت کنی.\n\n"
            "برای خرید /premium رو بزن 👇",
            parse_mode="HTML",
        )
        return

    await message.answer("🎙 در حال آماده‌سازی ویس فارسی گزارش...")

    repo = StudySessionRepository(db)
    sessions = await repo.get_week_sessions(db_user.telegram_id)

    if not sessions:
        await message.answer("📭 این هفته جلسه‌ای ثبت نشده تا ویس بسازم!")
        return

    total_m = sum(s.duration_minutes for s in sessions)
    hours, mins = divmod(total_m, 60)

    subject_stats: dict = {}
    for s in sessions:
        subject_stats[s.subject] = subject_stats.get(s.subject, 0) + s.duration_minutes

    subject_lines = " ".join(
        f"{subj} {m} دقیقه،"
        for subj, m in sorted(subject_stats.items(), key=lambda x: x[1], reverse=True)
    )

    voice_text = (
        f"سلام {db_user.full_name or 'دوست عزیز'}. "
        f"گزارش هفتگی مطالعه شما آماده است. "
        f"این هفته مجموعاً {hours} ساعت و {mins} دقیقه مطالعه کردید. "
        f"تعداد جلسات {len(sessions)} جلسه بود. "
        f"آمار درس‌ها: {subject_lines} "
        f"آفرین! به تلاشت ادامه بده."
    )

    try:
        from voice.voice_generator import text_to_voice
        voice_buf = text_to_voice(voice_text, gender="female")
        await message.answer_voice(
            BufferedInputFile(voice_buf.read(), filename="report.ogg"),
            caption="🎙 ویس گزارش هفتگی — صدای فارسی",
        )
    except Exception as e:
        await message.answer(
            f"❌ خطا در ساخت ویس:\n<code>{e}</code>",
            parse_mode="HTML",
        )