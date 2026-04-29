import random
from datetime import datetime

from sqlalchemy import select

from src.core.database import async_session_factory, settings
from src.core.logging import logger
from src.models.all_models import StatusEnum, Task, User
from src.services.cron_service import cron_service, send_slack_dm

_DUMMY_MESSAGES = [
    "🌟 Hey, you're doing great! Keep it up!",
    "💡 Pro tip: Take a 5-minute walk. Your brain will thank you.",
    "🎲 Random fact: Octopuses have three hearts.",
    "☕ Coffee break? You deserve it.",
    "🚀 Reminder: You're capable of amazing things.",
    "🌈 Did you know? Honey never spoils.",
    "✨ Small steps every day lead to big results.",
    "🐱 Meow. That is all.",
]


async def _get_user() -> User | None:
    async with async_session_factory() as db:
        result = await db.execute(select(User).where(User.email == settings.ALLOWED_USER_EMAIL))
        return result.scalar_one_or_none()


@cron_service.register("0 * * * *", name="hourly_task_reminder")
async def hourly_task_reminder() -> None:
    """Find overdue tasks and send a Slack DM for each."""
    logger.info("Running hourly_task_reminder...")
    async with async_session_factory() as db:
        now = datetime.utcnow()
        result = await db.execute(
            select(Task).where(
                Task.due_date <= now,
                Task.reminder_sent.is_(False),
            )
        )
        tasks = result.scalars().all()

        for task in tasks:
            await send_slack_dm(f"⏰ Reminder: *{task.title}* is due!")
            task.reminder_sent = True

        await db.commit()
        if tasks:
            logger.info(f"Sent {len(tasks)} reminder(s).")


@cron_service.register("0 9 * * *", name="daily_task_digest")
async def daily_task_digest() -> None:
    """Send a morning summary of TODO and WORKING tasks."""
    logger.info("Running daily_task_digest...")
    async with async_session_factory() as db:
        user = await db.execute(
            select(User).where(User.email == settings.ALLOWED_USER_EMAIL)
        )
        user = user.scalar_one_or_none()
        if not user:
            logger.warning("daily_task_digest: no user found.")
            return

        result = await db.execute(
            select(Task).where(
                Task.user_id == user.id,
                Task.status.in_([StatusEnum.TODO, StatusEnum.WORKING]),
            )
        )
        tasks = result.scalars().all()

        if not tasks:
            await send_slack_dm("🌅 Good morning! You have no pending tasks. Enjoy your day!")
            return

        lines = ["🌅 Good morning! Here are your pending tasks:"]
        for task in tasks:
            icon = "⬜" if task.status == StatusEnum.TODO else "🔄"
            lines.append(f"{icon} *{task.title}*")

        await send_slack_dm("\n".join(lines))
        logger.info(f"Sent daily digest with {len(tasks)} task(s).")


@cron_service.register("0 */6 * * *", name="dummy_news_update")
async def dummy_news_update() -> None:
    """Placeholder cron job. Sends a reminder to configure news sources."""
    logger.info("Running dummy_news_update...")
    await send_slack_dm(
        "📰 *News Update Placeholder*\n"
        "This is a demo cron job. Configure your news sources in "
        "`backend/src/services/cron_jobs.py` to make it useful!"
    )


@cron_service.register("* * * * *", name="random_message")
async def random_message() -> None:
    """Send a random fun message every minute."""
    message = random.choice(_DUMMY_MESSAGES)
    await send_slack_dm(message)
