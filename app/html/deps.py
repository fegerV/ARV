from typing import AsyncGenerator
from fastapi import Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db, AsyncSessionLocal
from app.api.routes.auth import get_current_active_user, get_current_user_optional
from app.models.user import User

async def get_html_db() -> AsyncGenerator[AsyncSession, None]:
    """Генератор одной сессии для HTML-ручек (аналог get_db, но без цикла)."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

# для страниц, где нужен авторизованный пользователь
CurrentActiveUser = Depends(get_current_active_user)

# для страниц, где пользователь может быть гостем
OptionalUser = Depends(get_current_user_optional)