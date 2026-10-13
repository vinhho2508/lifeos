import os
import time
from dotenv import load_dotenv, find_dotenv
from slack_bolt.app.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
import httpx
import asyncio

from stream_format import deltas_to_text

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
# Shared secret the backend accepts as X-Service-Token (set the same value in backend/.env).
SLACK_SERVICE_TOKEN = os.environ.get("SLACK_SERVICE_TOKEN", "")
# Agent runs can call several tools (image generation is slow).
STREAM_TIMEOUT = 180.0


@app.event("message")
@app.event("app_mention")
async def handle_message_events(body, logger, say, client):
    event = body["event"]

    # Skip bot messages to prevent self-response loops
    if event.get("subtype") == "bot_message":
        return

    event_type = event.get("type")

    # For plain message events (not app_mention), only respond to DMs
    if event_type == "message" and event.get("channel_type") != "im":
        return

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

    raw = ""
    last_update = time.time()

    try:
        async with httpx.AsyncClient() as http_client:
            async with http_client.stream(
                "POST",
                f"{BACKEND_URL}/chat/stream",
                json={"message": text, "platform": "SLACK"},
                headers={"X-Service-Token": SLACK_SERVICE_TOKEN},
                timeout=STREAM_TIMEOUT,
            ) as response:
                if response.status_code == 401:
                    await client.chat_update(
                        channel=channel,
                        ts=ts,
                        text="⚠️ The backend rejected me: check SLACK_SERVICE_TOKEN matches.",
                    )
                    return
                response.raise_for_status()
                async for chunk in response.aiter_text():
                    raw += chunk
                    now = time.time()
                    if now - last_update >= 1.0:
                        await client.chat_update(
                            channel=channel,
                            ts=ts,
                            text=deltas_to_text(raw) or "💭 ...",
                        )
                        last_update = now

        # Final update once the stream is complete
        await client.chat_update(
            channel=channel,
            ts=ts,
            text=deltas_to_text(raw if raw.endswith("\n") else raw + "\n") or "Done.",
        )
    except Exception as e:
        logger.error(f"Error calling backend stream: {e}")
        await client.chat_update(
            channel=channel,
            ts=ts,
            text="Sorry, I'm having trouble connecting to my brain.",
        )


@app.event("reaction_added")
async def handle_reaction_added(body, logger, client):
    event = body["event"]
    reaction = event.get("reaction")

    if reaction != "pushpin":
        return

    user_id = event.get("user")
    item = event.get("item", {})

    if item.get("type") != "message":
        return

    channel = item.get("channel")
    ts = item.get("ts")

    # Fetch the message that was reacted to
    try:
        result = await client.reactions_get(channel=channel, timestamp=ts)
        message_text = result.get("message", {}).get("text", "")
    except Exception as e:
        logger.error(f"Error fetching reacted message: {e}")
        try:
            await client.chat_postMessage(
                channel=user_id,
                text="Sorry, I couldn't read that message to create a task.",
            )
        except Exception:
            pass
        return

    if not message_text:
        try:
            await client.chat_postMessage(
                channel=user_id,
                text="That message doesn't have any text I can turn into a task.",
            )
        except Exception:
            pass
        return

    # Call backend to create a task from the message
    try:
        async with httpx.AsyncClient() as http_client:
            response = await http_client.post(
                f"{BACKEND_URL}/tasks/from-message",
                json={"message": message_text},
                timeout=30.0,
            )
            if response.status_code == 200:
                task = response.json()
                title = task.get("title", message_text[:100])
                await client.chat_postMessage(
                    channel=user_id,
                    text=f"📌 Created task: *{title}*",
                )
            else:
                await client.chat_postMessage(
                    channel=user_id,
                    text="Sorry, I couldn't create a task from that message.",
                )
    except Exception as e:
        logger.error(f"Error creating task from pin: {e}")
        try:
            await client.chat_postMessage(
                channel=user_id,
                text="Sorry, I'm having trouble connecting to my brain.",
            )
        except Exception:
            pass


async def _health(reader, writer):
    # Minimal HTTP 200 so Render's web-service port scan / health check passes.
    try:
        await reader.readuntil(b"\r\n\r\n")
    except Exception:
        pass
    writer.write(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\nok")
    try:
        await writer.drain()
    finally:
        writer.close()


async def main():
    # Socket Mode opens no inbound port; Render web services require one.
    port = os.environ.get("PORT")
    if port:
        await asyncio.start_server(_health, "0.0.0.0", int(port))
    handler = AsyncSocketModeHandler(app, SLACK_APP_TOKEN)
    await handler.start_async()


if __name__ == "__main__":
    asyncio.run(main())
