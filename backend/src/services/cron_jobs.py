import random
from datetime import datetime

import httpx
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


# @cron_service.register("0 */6 * * *", name="crypto_price_update")
@cron_service.register("* * * * *", name="crypto_price_update")
async def crypto_price_update() -> None:
    """Fetch top 10 crypto prices and send a Slack DM every 6 hours."""
    logger.info("Running crypto_price_update...")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                "https://api.coingecko.com/api/v3/coins/markets",
                params={
                    "vs_currency": "usd",
                    "order": "market_cap_desc",
                    "per_page": 10,
                    "page": 1,
                },
                timeout=30.0,
            )
            response.raise_for_status()
            coins = response.json()
        except Exception as e:
            logger.error(f"Failed to fetch crypto prices: {e}")
            await send_slack_dm("⚠️ Could not fetch crypto prices right now. Try again later!")
            return

    lines = ["📊 *Crypto Update (Top 10)*"]
    for i, coin in enumerate(coins, 1):
        symbol = coin["symbol"].upper()
        price = coin["current_price"]
        change = coin["price_change_percentage_24h"]
        change_str = f"{change:+.2f}%" if change is not None else "N/A"
        if change is not None and change > 0:
            emoji = "🟢"
        elif change is not None and change < 0:
            emoji = "🔴"
        else:
            emoji = "⚪"
        lines.append(
            f"{i}. {coin['name']} ({symbol}): ${price:,.2f} {emoji} {change_str}"
        )

    await send_slack_dm("\n".join(lines))
    logger.info(f"Sent crypto update with {len(coins)} coin(s).")


# @cron_service.register("* * * * *", name="random_message")
# async def random_message() -> None:
#     """Send a random fun message every minute."""
#     message = random.choice(_DUMMY_MESSAGES)
#     await send_slack_dm(message)
