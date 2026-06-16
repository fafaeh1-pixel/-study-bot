from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.user import User
from database.repositories.study_session_repository import StudySessionRepository
from ai.analyzer import analyze_progress, format_analysis_message, StudyData
from ai.planner import generate_study_plan
from premium.checker import is_premium
from bot.texts import texts

router = Router(name="ai")

FREE_VOICE_LIMIT = 5
FREE_PLAN_LIMIT = 5

_usage_cache: dict[str, int] = {}


def _get_usage(telegram_id: int, feature: str) -> int:
    return _usage_cache.get(f"usage_{telegram_id}_{feature}", 0)


def _increment_usage(telegram_id: int, feature: str) -> int:
    key = f"usage_{telegram_id}_{feature}"
    _usage_cache[key] = _usage_cache.get(key, 0) + 1
    return _usage_cache[key]


def _build_study_data(sessions, user_name: str, daily_goal: int) -> StudyData:
    return StudyData(
        full_name=user_name,
        total_minutes=sum(s.duration_minutes for s in sessions),
        daily_goal_minutes=daily_goal,
        sessions=[
            {
                "subject": s.subject,
                "duration": s.duration_minutes,
                "date": s.session_date,
            }
            for s in sessions
        ],
    )


def _ai_keyboard(is_premium_user: bool, telegram_id: int) -> InlineKeyboardMarkup:
    voice_used = _get_usage(telegram_id, "voice")
    plan_used = _get_usage(telegram_id, "plan")

    if is_premium_user:
        voice_label = "🔊 دریافت ویس ⭐"
        plan_label = "📅 برنامه هفتگی ⭐"
    else:
        voice_remaining = max(0, FREE_VOICE_LIMIT - voice_used)
        plan_remaining = max(0, FREE_PLAN_LIMIT - plan_used)
        voice_label = f"🔊 دریافت ویس ({voice_remaining} باقی)"
        plan_label = f"📅 برنامه هفتگی ({plan_remaining} باقی)"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=plan_label, callback_data="ai_plan"),
                InlineKeyboardButton(text=voice_label, callback_data="ai_voice"),
            ],
            [InlineKeyboardButton(text="🔄 تحلیل مجدد", callback_data="ai_analyze")],
        ]
    )


@router.message(F.text == texts.BTN_AI_ANALYSIS)
async def ai_analysis_handler(message: Message, db: AsyncSession, db_user: User) -> None:
    premium = is_premium(db_user)

    await message.answer("⏳ در حال تحلیل داده‌های مطالعه‌ات هستم...")
    repo = StudySessionRepository(db)
    sessions = await repo.get_week_sessions(db_user.telegram_id)

    if not sessions:
        await message.answer("📭 هنوز که جلسه‌ای واسه مطالعه ثبت نکردی.\n\nابتدا چند جلسه مطالعه ثبت کن.")
        return

    data = _build_study_data(sessions, db_user.full_name, db_user.daily_goal_minutes)
    result = await analyze_progress(data)

    await message.answer(
        format_analysis_message(result),
        reply_markup=_ai_keyboard(premium, db_user.telegram_id),
        parse_mode="HTML",
    )


@router.message(Command("analyze"))
async def cmd_analyze(message: Message, db: AsyncSession, db_user: User) -> None:
    premium = is_premium(db_user)

    await message.answer("🔍 در حال تحلیل پیشرفت هفت روز اخیر...")
    repo = StudySessionRepository(db)
    sessions = await repo.get_week_sessions(db_user.telegram_id)

    if not sessions:
        await message.answer("📭 جلسه‌ای ثبت نشده. ابتدا مطالعه ثبت کن.")
        return

    data = _build_study_data(sessions, db_user.full_name, db_user.daily_goal_minutes)
    result = await analyze_progress(data)

    await message.answer(
        format_analysis_message(result),
        reply_markup=_ai_keyboard(premium, db_user.telegram_id),
        parse_mode="HTML",
    )


@router.message(Command("advisor"))
async def cmd_advisor(message: Message, db: AsyncSession, db_user: User) -> None:
    premium = is_premium(db_user)

    await message.answer("🎓 در حال تهیه گزارش مشاوره...")
    repo = StudySessionRepository(db)
    sessions = await repo.get_week_sessions(db_user.telegram_id)

    if not sessions:
        await message.answer("📭 جلسه‌ای ثبت نشده. ابتدا مطالعه ثبت کن.")
        return

    data = _build_study_data(sessions, db_user.full_name, db_user.daily_goal_minutes)
    result = await analyze_progress(data)

    await message.answer(
        format_analysis_message(result),
        reply_markup=_ai_keyboard(premium, db_user.telegram_id),
        parse_mode="HTML",
    )


@router.message(Command("plan"))
async def cmd_plan(message: Message, db: AsyncSession, db_user: User) -> None:
    premium = is_premium(db_user)

    if not premium:
        used = _get_usage(db_user.telegram_id, "plan")
        if used >= FREE_PLAN_LIMIT:
            await message.answer(
                f"❌ سقف {FREE_PLAN_LIMIT} برنامه هفتگی رایگان تموم شد!\n\n"
                f"⭐ با پریمیوم برنامه نامحدود داری.\n/premium رو بزن 👇"
            )
            return
        _increment_usage(db_user.telegram_id, "plan")

    await message.answer("📅 در حال ساخت برنامه هفتگی هوشمند...")
    repo = StudySessionRepository(db)
    sessions = await repo.get_week_sessions(db_user.telegram_id)

    plan = await generate_study_plan(
        sessions=sessions,
        user_name=db_user.full_name,
        daily_goal=db_user.daily_goal_minutes,
    )
    await message.answer(plan, reply_markup=_ai_keyboard(premium, db_user.telegram_id))


@router.callback_query(F.data == "ai_analyze")
async def ai_reanalyze_callback(callback: CallbackQuery, db: AsyncSession, db_user: User) -> None:
    premium = is_premium(db_user)

    await callback.answer("در حال تحلیل...")
    repo = StudySessionRepository(db)
    sessions = await repo.get_week_sessions(db_user.telegram_id)

    if not sessions:
        await callback.message.answer("📭 جلسه‌ای ثبت نشده.")
        return

    data = _build_study_data(sessions, db_user.full_name, db_user.daily_goal_minutes)
    result = await analyze_progress(data)

    await callback.message.answer(
        format_analysis_message(result),
        reply_markup=_ai_keyboard(premium, db_user.telegram_id),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "ai_plan")
async def ai_plan_callback(callback: CallbackQuery, db: AsyncSession, db_user: User) -> None:
    premium = is_premium(db_user)

    if not premium:
        used = _get_usage(db_user.telegram_id, "plan")
        if used >= FREE_PLAN_LIMIT:
            await callback.answer(
                f"سقف {FREE_PLAN_LIMIT} برنامه رایگان تموم شد! /premium بزن.",
                show_alert=True,
            )
            return
        _increment_usage(db_user.telegram_id, "plan")

    await callback.answer("در حال ساخت برنامه...")
    repo = StudySessionRepository(db)
    sessions = await repo.get_week_sessions(db_user.telegram_id)

    plan = await generate_study_plan(
        sessions=sessions,
        user_name=db_user.full_name,
        daily_goal=db_user.daily_goal_minutes,
    )
    await callback.message.answer(
        plan,
        reply_markup=_ai_keyboard(premium, db_user.telegram_id),
    )


@router.callback_query(F.data == "ai_voice")
async def ai_voice_callback(callback: CallbackQuery, db: AsyncSession, db_user: User) -> None:
    premium = is_premium(db_user)

    if not premium:
        used = _get_usage(db_user.telegram_id, "voice")
        if used >= FREE_VOICE_LIMIT:
            await callback.answer(
                f"سقف {FREE_VOICE_LIMIT} ویس رایگان تموم شد! /premium بزن.",
                show_alert=True,
            )
            return
        _increment_usage(db_user.telegram_id, "voice")

    await callback.answer("در حال ساخت ویس...")
    repo = StudySessionRepository(db)
    sessions = await repo.get_week_sessions(db_user.telegram_id)
    data = _build_study_data(sessions, db_user.full_name, db_user.daily_goal_minutes)
    result = await analyze_progress(data)
    text = format_analysis_message(result)

    try:
        from voice.voice_generator import text_to_voice
        voice_buf = text_to_voice(text, gender="female")
        await callback.message.answer_voice(
            BufferedInputFile(voice_buf.read(), filename="analysis.ogg"),
            caption="🎙 ویس تحلیل هفتگی",
        )
    except Exception as e:
        await callback.message.answer(f"❌ خطا در ساخت ویس:\n<code>{e}</code>", parse_mode="HTML")