from src.services.nlp import extract_task_info


async def test_extract_task_info_without_api_key_falls_back_to_text():
    info = await extract_task_info("Remind me to buy milk at 5 PM")

    assert "buy milk" in info["title"].lower()
    assert info["due_date"] is None
