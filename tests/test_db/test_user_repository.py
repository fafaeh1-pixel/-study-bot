import pytest
from database.repositories.user_repository import UserRepository


@pytest.mark.asyncio
async def test_create_user(test_session):
    repo = UserRepository(test_session)
    user = await repo.get_or_create(
        telegram_id=123456789,
        full_name="تست کاربر",
        username="testuser",
    )
    assert user.telegram_id == 123456789
    assert user.full_name == "تست کاربر"


@pytest.mark.asyncio
async def test_get_or_create_existing_user(test_session):
    repo = UserRepository(test_session)
    user1 = await repo.get_or_create(telegram_id=987654321, full_name="کاربر اول")
    user2 = await repo.get_or_create(telegram_id=987654321, full_name="کاربر بروز شده")
    assert user1.telegram_id == user2.telegram_id
    assert user2.full_name == "کاربر بروز شده"