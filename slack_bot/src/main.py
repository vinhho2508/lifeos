import os
import time
import json
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


def deltas_to_text(lines: list[str]) -> str:
    """Parse NDJSON deltas and convert to plain text for Slack."""
    text_parts = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            delta = json.loads(line)
            delta_type = delta.get("type", "")
            if delta_type == "text":
                text_parts.append(delta.get("delta", ""))
            elif delta_type == "thinking":
                text_parts.append(f"\n💭 {delta.get('delta', '')}\n")
            elif delta_type == "image":
                url = delta.get("url", "")
                alt = delta.get("alt", "image")
                text_parts.append(f"\n🖼️ [{alt}]({url})\n")
            elif delta_type == "tool_call":
                name = delta.get("name", "tool")
                text_parts.append(f"\n🔧 Using tool: {name}\n")
            elif delta_type == "tool_result":
                output = delta.get("output", "")
                text_parts.append(f"\n✅ Result: {output}\n")
        except json.JSONDecodeError:
            # If it's not valid JSON, treat as raw text (backward compat)
            text_parts.append(line)
    return "".join(text_parts)


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

    accumulated_lines = []
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
                    accumulated_lines.append(chunk)
                    now = time.time()
                    if now - last_update >= 1.0:
                        full_text = deltas_to_text(accumulated_lines)
                        await client.chat_update(
                            channel=channel,
                            ts=ts,
                            text=full_text or "💭 ...",
                        )
                        last_update = now

        # Final update once the stream is complete
        full_text = deltas_to_text(accumulated_lines)
        await client.chat_update(
            channel=channel,
            ts=ts,
            text=full_text or "Done.",
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


async def main():
    handler = AsyncSocketModeHandler(app, SLACK_APP_TOKEN)
    await handler.start_async()


if __name__ == "__main__":
    asyncio.run(main())
