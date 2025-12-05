from datetime import datetime, timedelta, time
import asyncio
from typing import Optional
import random

from app.tasks.celery_app import celery_app
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.project import Project
from app.models.ar_content import ARContent
from app.models.video import Video
from app.models.video_rotation_schedule import VideoRotationSchedule
from app.models.notification import Notification


def _now() -> datetime:
    return datetime.utcnow()


def _calculate_next_rotation_time(sched: VideoRotationSchedule) -> datetime:
    now = _now()
    if sched.rotation_type == "daily" and sched.time_of_day:
        target = datetime.combine(now.date(), sched.time_of_day)
        if target <= now:
            target = target + timedelta(days=1)
        return target
    if sched.rotation_type == "weekly" and sched.day_of_week:
        # day_of_week: 1..7 (Mon..Sun)
        dow = sched.day_of_week
        current_dow = (now.isoweekday())
        delta_days = (dow - current_dow) % 7 or 7
        base = now + timedelta(days=delta_days)
        t = sched.time_of_day or time(9, 0)
        return datetime.combine(base.date(), t)
    if sched.rotation_type == "monthly" and sched.day_of_month:
        dom = sched.day_of_month
        # naive monthly increment
        month = now.month + (1 if now.day >= dom else 0)
        year = now.year + (month - 1) // 12
        month = ((month - 1) % 12) + 1
        try:
            base = datetime(year, month, dom)
        except ValueError:
            # fallback to last day of month
            from calendar import monthrange
            last_dom = monthrange(year, month)[1]
            base = datetime(year, month, last_dom)
        t = sched.time_of_day or time(9, 0)
        return datetime.combine(base.date(), t)
    # custom/unknown: next 5 minutes
    return now + timedelta(minutes=5)


@celery_app.task(name="app.tasks.expiry_tasks.check_expiring_projects")
def check_expiring_projects():
    async def _run():
        async with AsyncSessionLocal() as db:
            warning_date = _now() + timedelta(days=7)
            stmt = select(Project).where(
                Project.expires_at != None,  # noqa: E711
                Project.expires_at.between(_now(), warning_date),
                Project.status == "active",
            )
            res = await db.execute(stmt)
            projects = res.scalars().all()
            for project in projects:
                # cooldown by notify_before_expiry_days
                if project.last_notification_sent_at:
                    days_since = (_now() - project.last_notification_sent_at).days
                    if days_since < (project.notify_before_expiry_days or 7):
                        continue
                # record notification
                n = Notification(
                    company_id=project.company_id,
                    project_id=project.id,
                    ar_content_id=None,
                    notification_type="expiry_warning",
                    subject=f"Проект {project.name} истекает через 7 дней",
                    message=f"Срок действия проекта истекает {project.expires_at}",
                    metadata={"expires_at": project.expires_at.isoformat() if project.expires_at else None},
                )
                db.add(n)
                project.last_notification_sent_at = _now()
            await db.commit()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_run())
    finally:
        loop.close()


@celery_app.task(name="app.tasks.expiry_tasks.deactivate_expired_content")
def deactivate_expired_content():
    async def _run():
        async with AsyncSessionLocal() as db:
            stmt = select(Project).where(
                Project.expires_at != None,  # noqa: E711
                Project.expires_at < _now(),
                Project.status == "active",
            )
            res = await db.execute(stmt)
            expired_projects = res.scalars().all()
            for project in expired_projects:
                project.status = "expired"
                # deactivate AR content under project
                stmt_content = select(ARContent).where(ARContent.project_id == project.id)
                res_content = await db.execute(stmt_content)
                for content in res_content.scalars().all():
                    content.is_active = False
                # optional: create notification
                n = Notification(
                    company_id=project.company_id,
                    project_id=project.id,
                    ar_content_id=None,
                    notification_type="expired",
                    subject=f"Проект {project.name} истёк",
                    message=f"Срок действия проекта истёк {project.expires_at}",
                )
                db.add(n)
            await db.commit()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_run())
    finally:
        loop.close()


@celery_app.task(name="app.tasks.expiry_tasks.rotate_scheduled_videos")
def rotate_scheduled_videos():
    async def _run():
        async with AsyncSessionLocal() as db:
            now = _now()
            stmt = select(VideoRotationSchedule).where(
                VideoRotationSchedule.is_active == 1,
                VideoRotationSchedule.next_rotation_at != None,  # noqa: E711
                VideoRotationSchedule.next_rotation_at <= now,
            )
            res = await db.execute(stmt)
            schedules = res.scalars().all()
            for schedule in schedules:
                seq = schedule.video_sequence or []
                if not seq:
                    continue
                current_idx = schedule.current_index or 0
                if getattr(schedule, "rotation_type", None) == "random":
                    candidates = [i for i in range(len(seq)) if i != current_idx]
                    next_idx = random.choice(candidates) if candidates else current_idx
                else:
                    next_idx = (current_idx + 1) % len(seq)
                next_video_id = seq[next_idx]
                # deactivate current active video
                stmt_cur = select(Video).where(
                    Video.ar_content_id == schedule.ar_content_id,
                    Video.is_active == True,
                )
                res_cur = await db.execute(stmt_cur)
                cur_video = res_cur.scalars().first()
                if cur_video:
                    cur_video.is_active = False
                # activate next
                next_video = await db.get(Video, next_video_id)
                if next_video:
                    next_video.is_active = True
                    # update AR content active_video_id
                    ac = await db.get(ARContent, next_video.ar_content_id)
                    if ac:
                        ac.active_video_id = next_video.id
                # update schedule times
                schedule.current_index = next_idx
                schedule.last_rotation_at = now
                schedule.next_rotation_at = _calculate_next_rotation_time(schedule)
            await db.commit()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_run())
    finally:
        loop.close()
