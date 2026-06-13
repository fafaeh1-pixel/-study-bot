from datetime import datetime, timedelta
from typing import List
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from database.models.study_session import StudySession
from database.repositories.base_repository import BaseRepository


class StudySessionRepository(BaseRepository[StudySession]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, StudySession)

    async def get_today_sessions(self, user_id: int) -> List[StudySession]:
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)
        result = await self.session.execute(
            select(StudySession)
            .where(StudySession.user_id == user_id)
            .where(StudySession.session_date >= today)
            .where(StudySession.session_date < tomorrow)
            .order_by(StudySession.session_date.desc())
        )
        return list(result.scalars().all())

    async def get_week_sessions(self, user_id: int) -> List[StudySession]:
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today - timedelta(days=today.weekday())
        result = await self.session.execute(
            select(StudySession)
            .where(StudySession.user_id == user_id)
            .where(StudySession.session_date >= week_start)
            .order_by(StudySession.session_date.desc())
        )
        return list(result.scalars().all())

    async def get_total_minutes_today(self, user_id: int) -> int:
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)
        result = await self.session.execute(
            select(func.sum(StudySession.duration_minutes))
            .where(StudySession.user_id == user_id)
            .where(StudySession.session_date >= today)
            .where(StudySession.session_date < tomorrow)
        )
        return result.scalar() or 0