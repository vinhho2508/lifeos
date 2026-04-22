import os
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
async def handle_message_events(body, logger, say):
    event = body["event"]
    user_id = event.get("user")
    text = event.get("text")
    thread_ts = event.get("thread_ts") or event.get("ts")
    
    if not text:
        return

    # Forward to backend /chat
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{BACKEND_URL}/chat/", 
                json={"message": text, "platform": "SLACK"}
            )
            data = response.json()
            # Reply in the same thread
            await say(text=data["reply"], thread_ts=thread_ts)
        except Exception as e:
            logger.error(f"Error calling backend: {e}")
            await say(text="Sorry, I'm having trouble connecting to my brain.", thread_ts=thread_ts)

async def main():
    handler = AsyncSocketModeHandler(app, SLACK_APP_TOKEN)
    await handler.start_async()

if __name__ == "__main__":
    asyncio.run(main())
