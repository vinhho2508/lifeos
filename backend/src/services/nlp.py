import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, AsyncIterator
import json
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from src.core.database import settings


def extract_task_info(text: str) -> Dict[str, Any]:
    # In a real scenario, use ChatOpenAI.
    # For now, a fallback or mock if no key is present.
    if not settings.OPENAI_API_KEY:
        # Simple heuristic if no key
        return {
            "title": text.replace("Remind me to ", ""),
            "description": None,
            "due_date": datetime.utcnow() + timedelta(hours=1)
        }

    llm = ChatOpenAI(openai_api_key=settings.OPENAI_API_KEY, model="gpt-5.4-2026-03-05")
    prompt = ChatPromptTemplate.from_template(
        "Extract task information from this message: {message}. "
        "Return JSON with 'title', 'description', and 'due_date' (ISO format). "
        "Current time is {now}."
    )

    chain = prompt | llm
    response = chain.invoke({"message": text, "now": datetime.utcnow().isoformat()})

    try:
        data = json.loads(response.content)
        if data.get("due_date"):
            data["due_date"] = datetime.fromisoformat(data["due_date"])
        return data
    except:
        return {"title": text, "description": None, "due_date": None}


async def stream_reply(message: str, context: str, task_info: Optional[Dict[str, Any]]) -> AsyncIterator[str]:
    """Yield reply tokens incrementally."""
    if not settings.OPENAI_API_KEY:
        # Mock streaming: yield word-by-word
        if context:
            reply = f"Based on your documents, here's what I found regarding {task_info['title'] if task_info else 'that'}."
        elif task_info:
            reply = f"I've noted your task: {task_info['title']}."
        else:
            reply = f"I received your message: {message}."

        words = reply.split()
        for i, word in enumerate(words):
            suffix = " " if i < len(words) - 1 else ""
            yield word + suffix
            await asyncio.sleep(0.05)
        return

    llm = ChatOpenAI(
        openai_api_key=settings.OPENAI_API_KEY,
        model="gpt-5.4-2026-03-05",
        streaming=True,
    )
    prompt = ChatPromptTemplate.from_template(
        "You are a helpful personal assistant.\n"
        "User message: {message}\n"
        "Document context: {context}\n"
        "Task info: {task_info}\n"
        "Provide a concise, conversational response."
    )
    chain = prompt | llm
    task_info_str = json.dumps(task_info, default=str) if task_info else "None"
    async for chunk in chain.astream({
        "message": message,
        "context": context or "None",
        "task_info": task_info_str,
    }):
        yield chunk.content
