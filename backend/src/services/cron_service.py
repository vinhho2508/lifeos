from collections.abc import Callable
from dataclasses import dataclass

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from slack_sdk.web.async_client import AsyncWebClient

from src.core.database import settings
from src.core.logging import logger


@dataclass
class _JobDef:
    func: Callable
    cron_expr: str
    name: str


class CronService:
    """Simple in-process cron scheduler for code-defined jobs."""

    def __init__(self):
        self._jobs: list[_JobDef] = []
        self.scheduler: AsyncIOScheduler | None = None

    def register(self, cron_expr: str, name: str | None = None):
        """Decorator to register an async function as a cron job.

        Usage:
            @cron_service.register("0 * * * *", name="hourly_task_reminder")
            async def hourly_task_reminder():
                ...
        """

        def decorator(func: Callable) -> Callable:
            job_name = name or func.__name__
            self._jobs.append(_JobDef(func=func, cron_expr=cron_expr, name=job_name))
            logger.info(f"Registered cron job '{job_name}' with schedule '{cron_expr}'")
            return func

        return decorator

    def start(self):
        self.scheduler = AsyncIOScheduler()
        for job in self._jobs:
            self.scheduler.add_job(
                job.func,
                trigger="cron",
                **self._parse_cron(job.cron_expr),
                id=job.name,
                replace_existing=True,
                misfire_grace_time=3600,
            )
            logger.info(f"Scheduled job '{job.name}' -> {job.cron_expr}")
        self.scheduler.start()
        logger.info(f"Cron scheduler started with {len(self._jobs)} job(s).")

    def _parse_cron(self, expr: str) -> dict:
        """Parse standard 5-field cron expression into APScheduler kwargs."""
        parts = expr.split()
        if len(parts) != 5:
            raise ValueError(
                f"Invalid cron expression '{expr}': "
                "expected 5 fields (min hour day month dow)"
            )
        minute, hour, day, month, day_of_week = parts
        return {
            "minute": minute,
            "hour": hour,
            "day": day,
            "month": month,
            "day_of_week": day_of_week,
        }


cron_service = CronService()


async def send_slack_dm(text: str) -> None:
    """Send a direct message to the configured Slack user."""
    token = settings.SLACK_BOT_TOKEN
    user_id = getattr(settings, "SLACK_DM_USER_ID", None)
    if not token or not user_id:
        logger.warning("Slack DM skipped: SLACK_BOT_TOKEN or SLACK_DM_USER_ID not configured.")
        return

    client = AsyncWebClient(token=token)
    try:
        await client.chat_postMessage(channel=user_id, text=text)
        logger.info(f"Slack DM sent to {user_id}")
    except Exception as e:
        logger.error(f"Failed to send Slack DM: {e}")
