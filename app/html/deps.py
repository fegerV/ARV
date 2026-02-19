import asyncio
from typing import AsyncGenerator
from fastapi import Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IllegalStateChangeError
from app.core.database import get_db, AsyncSessionLocal
from app.api.routes.auth import get_current_active_user, get_current_user_optional
from app.models.user import User
import structlog

logger = structlog.get_logger(__name__)


async def get_html_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Генератор одной сессии для HTML-ручек.
    Сессия создаётся без async with, закрытие выполняется вручную с откатом
    и expire_all, чтобы снизить риск IllegalStateChangeError при гонке
    с _connection_for_bind (ленивая загрузка при рендере/очистке).
    """
    session = AsyncSessionLocal()
    try:
        yield session
    except Exception:
        await session.rollback()
        raise
    finally:
        try:
            await session.rollback()
        except Exception:
            pass
        try:
            session.expire_all()
        except Exception:
            pass
        await asyncio.sleep(0)
        try:
            await session.close()
        except IllegalStateChangeError as e:
            logger.warning(
                "html_db_session_close_skipped",
                error=str(e),
                message="Session close deferred due to in-progress connection use",
            )

            async def _close_later() -> None:
                await asyncio.sleep(1.0)
                try:
                    await session.close()
                except Exception as late_e:
                    logger.warning("html_db_session_close_later_failed", error=str(late_e))

            asyncio.create_task(_close_later())
        except Exception as e:
            logger.warning("html_db_session_close_failed", error=str(e))

# для страниц, где нужен авторизованный пользователь
CurrentActiveUser = Depends(get_current_active_user)

# для страниц, где пользователь может быть гостем
OptionalUser = Depends(get_current_user_optional)