from aiogram.fsm.state import State, StatesGroup


class StudyLogStates(StatesGroup):
    waiting_for_subject = State()
    waiting_for_duration = State()
    waiting_for_notes = State()


class ReminderStates(StatesGroup):
    waiting_for_time = State()


class AIAnalysisStates(StatesGroup):
    waiting_for_question = State()