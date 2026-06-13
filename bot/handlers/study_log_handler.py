from datetime import datetime
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.main_keyboard import get_cancel_keyboard, get_main_keyboard, get_skip_or_cancel_keyboard
from bot.states import StudyLogStates
from bot.texts import texts
from bot.texts_motivational import get_random_motivation, get_goal_message
from database.models.user import User
from database.repositories.study_session_repository import StudySessionRepository

router = Router(name="study_log")


@router.message(F.text == texts.BTN_LOG_STUDY)
async def start_study_log(message: Message, state: FSMContext) -> None:
    await state.set_state(StudyLogStates.waiting_for_subject)
    await message.answer(texts.ASK_SUBJECT, reply_markup=get_cancel_keyboard())


@router.message(StudyLogStates.waiting_for_subject)
async def got_subject(message: Message, state: FSMContext) -> None:
    if message.text == texts.BTN_CANCEL:
        await state.clear()
        await message.answer(texts.CANCELLED, reply_markup=get_main_keyboard())
        return

    await state.update_data(subject=message.text.strip())
    await state.set_state(StudyLogStates.waiting_for_duration)
    await message.answer(texts.ASK_DURATION, reply_markup=get_cancel_keyboard())


@router.message(StudyLogStates.waiting_for_duration)
async def got_duration(message: Message, state: FSMContext) -> None:
    if message.text == texts.BTN_CANCEL:
        await state.clear()
        await message.answer(texts.CANCELLED, reply_markup=get_main_keyboard())
        return

    try:
        duration = int(message.text.strip())
        if not (1 <= duration <= 600):
            raise ValueError
    except ValueError:
        await message.answer(texts.INVALID_DURATION)
        return

    await state.update_data(duration=duration)
    await state.set_state(StudyLogStates.waiting_for_notes)
    await message.answer(texts.ASK_NOTES, reply_markup=get_skip_or_cancel_keyboard())


@router.message(StudyLogStates.waiting_for_notes)
async def got_notes(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    db_user: User,
) -> None:
    if message.text == texts.BTN_CANCEL:
        await state.clear()
        await message.answer(texts.CANCELLED, reply_markup=get_main_keyboard())
        return

    notes = None if message.text in [texts.BTN_SKIP, "/skip"] else message.text.strip()
    data = await state.get_data()

    repo = StudySessionRepository(session)
    await repo.create(
        user_id=db_user.telegram_id,
        subject=data["subject"],
        duration_minutes=data["duration"],
        notes=notes,
        session_date=datetime.now(),
    )

    # محاسبه مجموع امروز و پیام انگیزشی
    total_today = await repo.get_total_minutes_today(db_user.telegram_id)
    motivation = get_random_motivation()
    extra = ""
    if total_today >= db_user.daily_goal_minutes:
        extra = f"\n\n{get_goal_message()}"

    await state.clear()
    await message.answer(
        texts.STUDY_SAVED.format(
            subject=data["subject"],
            duration=data["duration"],
        )
        + f"\n\n{motivation}{extra}",
        reply_markup=get_main_keyboard(),
    )