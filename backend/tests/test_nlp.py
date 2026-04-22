import pytest
from src.services.nlp import extract_task_info

def test_extract_task_info_simple():
    # Mocking or using a basic version if no LLM key provided
    text = "Remind me to buy milk at 5 PM"
    info = extract_task_info(text)
    
    assert "buy milk" in info["title"].lower()
    # Depending on implementation, time extraction might vary
    assert info["due_date"] is not None
