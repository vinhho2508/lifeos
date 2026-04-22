from datetime import datetime, timedelta
from typing import Dict, Any, Optional
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
