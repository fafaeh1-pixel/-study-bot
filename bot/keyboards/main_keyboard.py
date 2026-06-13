from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from bot.texts import texts


def get_main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=texts.BTN_LOG_STUDY), KeyboardButton(text=texts.BTN_AI_ANALYSIS)],
            [KeyboardButton(text=texts.BTN_DAILY_REPORT), KeyboardButton(text=texts.BTN_WEEKLY_REPORT)],
            [KeyboardButton(text=texts.BTN_REMINDER), KeyboardButton(text=texts.BTN_SETTINGS)],
            [KeyboardButton(text=texts.BTN_PREMIUM), KeyboardButton(text=texts.BTN_HELP)],
        ],
        resize_keyboard=True,
        input_field_placeholder="یه گزینه انتخاب کن...",
    )


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=texts.BTN_CANCEL)]],
        resize_keyboard=True,
    )


def get_skip_or_cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=texts.BTN_SKIP)],
            [KeyboardButton(text=texts.BTN_CANCEL)],
        ],
        resize_keyboard=True,
    )


def get_report_inline_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 نمودار", callback_data="show_chart"),
            InlineKeyboardButton(text="📄 PDF", callback_data="show_pdf"),
        ],
        [InlineKeyboardButton(text="🔄 بروزرسانی", callback_data="refresh_report")],
    ])