"""
Background tasks for the Vertex AR application.

This module contains background tasks that were previously handled by Celery.
"""

from fastapi import BackgroundTasks
from typing import Any, Callable, Dict, List, Optional, Union
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

# Global thread pool for CPU-bound tasks
thread_pool = ThreadPoolExecutor(max_workers=4)


def run_in_threadpool(func: Callable, *args, **kwargs) -> Any:
    """Run a function in a thread pool."""
    loop = asyncio.get_event_loop()
    return loop.run_in_executor(thread_pool, lambda: func(*args, **kwargs))


async def run_background_task(
    background_tasks: BackgroundTasks,
    func: Callable,
    *args,
    **kwargs
) -> None:
    """
    Run a function as a background task.
    
    Args:
        background_tasks: FastAPI BackgroundTasks instance
        func: The function to run in the background
        *args: Positional arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function
    """
    if asyncio.iscoroutinefunction(func):
        background_tasks.add_task(func, *args, **kwargs)
    else:
        background_tasks.add_task(run_in_threadpool, func, *args, **kwargs)


# Import task modules here
from . import email_tasks  # noqa: E402
from . import storage_tasks  # noqa: E402
from . import processing_tasks  # noqa: E402

__all__ = [
    'run_background_task',
    'run_in_threadpool',
    'email_tasks',
    'storage_tasks',
    'processing_tasks',
]
