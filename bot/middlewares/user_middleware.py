from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update
from sqlalchemy.ext.asyncio import AsyncSession
from database.repositories.user_repository import UserRepository


class UserMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = None
        if isinstance(event, Update):
            if event.message:
                user = event.message.from_user
            elif event.callback_query:
                user = event.callback_query.from_user

        if user and not user.is_bot:
            session: AsyncSession = data.get("session")
            if session:
                repo = UserRepository(session)
                db_user = await repo.get_or_create(
                    telegram_id=user.id,
                    full_name=user.full_name or "کاربر",
                    username=user.username,
                )
                data["db_user"] = db_user

        return await handler(event, data)