import os
import time
from dotenv import load_dotenv, find_dotenv
from slack_bolt.app.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
import httpx
import asyncio

# Load environment variables
load_dotenv(find_dotenv())

# Verify tokens
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN")
if not SLACK_BOT_TOKEN or not SLACK_APP_TOKEN:
    raise ValueError("SLACK_BOT_TOKEN or SLACK_APP_TOKEN not found in environment.")

# Setup Async Bolt App
app = AsyncApp(token=SLACK_BOT_TOKEN)
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")


@app.event("message")
@app.event("app_mention")
async def handle_message_events(body, logger, say, client):
    event = body["event"]
    user_id = event.get("user")
    text = event.get("text")
    thread_ts = event.get("thread_ts") or event.get("ts")

    if not text:
        return

    # Post a placeholder message that we'll update as the stream arrives
    try:
        placeholder = await say(text="💭 ...", thread_ts=thread_ts)
        channel = placeholder["channel"]
        ts = placeholder["ts"]
    except Exception as e:
        logger.error(f"Error posting placeholder: {e}")
        return

    accumulated = ""
    last_update = time.time()

    try:
        async with httpx.AsyncClient() as http_client:
            async with http_client.stream(
                "POST",
                f"{BACKEND_URL}/chat/stream",
                json={"message": text, "platform": "SLACK"},
                timeout=60.0,
            ) as response:
                async for chunk in response.aiter_text():
                    accumulated += chunk
                    now = time.time()
                    if now - last_update >= 1.0:
                        await client.chat_update(
                            channel=channel,
                            ts=ts,
                            text=accumulated or "💭 ...",
                        )
                        last_update = now

        # Final update once the stream is complete
        await client.chat_update(
            channel=channel,
            ts=ts,
            text=accumulated or "Done.",
        )
    except Exception as e:
        logger.error(f"Error calling backend stream: {e}")
        await client.chat_update(
            channel=channel,
            ts=ts,
            text="Sorry, I'm having trouble connecting to my brain.",
        )


async def main():
    handler = AsyncSocketModeHandler(app, SLACK_APP_TOKEN)
    await handler.start_async()


if __name__ == "__main__":
    asyncio.run(main())
