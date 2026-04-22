from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
from sqlalchemy import select
from src.core.database import async_session_factory
from src.models.all_models import Task
from src.core.logging import logger

async def check_reminders():
    logger.info("Checking for due reminders...")
    async with async_session_factory() as db:
        now = datetime.utcnow()
        result = await db.execute(
            select(Task).where(
                Task.due_date <= now,
                Task.reminder_sent == False
            )
        )
        tasks = result.scalars().all()
        
        for task in tasks:
            logger.info(f"REMINDER: Task '{task.title}' is due!")
            
            # US4: Send Slack notification
            if settings.SLACK_BOT_TOKEN:
                from slack_sdk.web.async_client import AsyncWebClient
                client = AsyncWebClient(token=settings.SLACK_BOT_TOKEN)
                try:
                    # In real app, we'd need the user's slack ID from the DB
                    # Mocking channel ID for demo
                    await client.chat_postMessage(channel="C0123456789", text=f"⏰ REMINDER: {task.title}")
                except Exception as e:
                    logger.error(f"Failed to send Slack reminder: {e}")
            
            task.reminder_sent = True
        
        await db.commit()

def start_reminder_worker():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_reminders, 'interval', minutes=1)
    scheduler.start()
    logger.info("Reminder worker started.")
