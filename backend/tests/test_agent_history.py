from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from src.agent.history import (
    TOOL_OUTPUT_REPLAY_CHARS,
    assistant_blocks_to_messages,
    messages_to_langchain,
)
from src.models.all_models import Message, SenderEnum
from tests.agent_helpers import call, run_turn, use_script


def tc(call_id, name="list_tasks", **input):
    return {"type": "tool_call", "id": call_id, "name": name, "input": input}


def tr(call_id, name="list_tasks", output=None, status="ok", summary="ok"):
    return {
        "type": "tool_result",
        "id": call_id,
        "name": name,
        "status": status,
        "summary": summary,
        "output": output if output is not None else [],
    }


def test_tool_steps_replay_as_paired_messages():
    blocks = [
        {"type": "text", "text": "Let me check. "},
        tc("c1", overdue_only=True),
        tr("c1", output=[{"id": "t1"}]),
        tc("c2", name="update_task", task_id="t1", status="DONE"),
        tr("c2", name="update_task", output={"id": "t1"}),
        {"type": "text", "text": "Done."},
    ]

    messages = assistant_blocks_to_messages(blocks)

    assert [type(m) for m in messages] == [
        AIMessage,
        ToolMessage,
        AIMessage,
        ToolMessage,
        AIMessage,
    ]
    assert messages[0].content == "Let me check. "
    assert messages[0].tool_calls[0]["id"] == "c1"
    assert messages[0].tool_calls[0]["args"] == {"overdue_only": True}
    assert messages[1].tool_call_id == "c1"
    assert messages[2].tool_calls[0]["name"] == "update_task"
    assert messages[3].tool_call_id == "c2"
    assert messages[4].content == "Done."


def test_parallel_calls_stay_in_one_ai_message():
    blocks = [tc("a"), tc("b", name="search_documents"), tr("a"), tr("b", name="search_documents")]

    messages = assistant_blocks_to_messages(blocks)

    assert [type(m) for m in messages] == [AIMessage, ToolMessage, ToolMessage]
    assert [c["id"] for c in messages[0].tool_calls] == ["a", "b"]


def test_unpaired_tool_call_is_dropped():
    # e.g. the server died between the model step and the tool step
    blocks = [{"type": "text", "text": "Checking"}, tc("c1")]

    messages = assistant_blocks_to_messages(blocks)

    assert len(messages) == 1
    assert messages[0].content == "Checking"
    assert messages[0].tool_calls == []


def test_error_results_replay_as_error_tool_messages():
    messages = assistant_blocks_to_messages(
        [
            tc("c1"),
            tr("c1", status="error", summary="no task with id x"),
            {"type": "text", "text": "Hm."},
        ]
    )

    assert messages[1].status == "error"
    assert messages[1].content == "Error: no task with id x"


def test_long_tool_output_is_truncated():
    messages = assistant_blocks_to_messages([tc("c1"), tr("c1", output="x" * 5000)])

    assert len(messages[1].content) < TOOL_OUTPUT_REPLAY_CHARS + 20
    assert messages[1].content.endswith("[truncated]")


def test_ui_only_blocks_are_not_replayed():
    blocks = [
        {"type": "thinking", "thinking": "hmm"},
        {"type": "image", "url": "data:image/png;base64,AAAA", "alt": "cat"},
        {"type": "citation", "document_id": "d", "chunk_text": "c", "source_name": "s"},
        {"type": "text", "text": "Here you go."},
    ]

    messages = assistant_blocks_to_messages(blocks)

    assert len(messages) == 1
    assert messages[0].content == "Here you go."


def test_history_starts_with_a_user_turn():
    rows = [
        Message(
            sender=SenderEnum.ASSISTANT,
            text="older answer",
            content=[{"type": "text", "text": "older"}],
        ),
        Message(sender=SenderEnum.USER, text="question", content=[]),
        Message(
            sender=SenderEnum.ASSISTANT, text="answer", content=[{"type": "text", "text": "answer"}]
        ),
    ]

    messages = messages_to_langchain(rows)

    assert [type(m) for m in messages] == [HumanMessage, AIMessage]


async def test_follow_up_sees_previous_tool_step(owner, monkeypatch):
    use_script(
        monkeypatch, call("create_task", "c1", title="Pay rent"), AIMessage(content="Added.")
    )
    await run_turn(owner, "remind me to pay rent")

    model = use_script(monkeypatch, AIMessage(content="Sure."))
    await run_turn(owner, "push it to Monday")

    system, *seen = model.calls[0]
    assert isinstance(system, SystemMessage)
    assert [type(m) for m in seen] == [
        HumanMessage,
        AIMessage,
        ToolMessage,
        AIMessage,
        HumanMessage,
    ]
    assert seen[1].tool_calls[0]["id"] == "c1"
    assert '"title": "Pay rent"' in seen[2].content
    assert seen[-1].content == "push it to Monday"


async def test_history_is_shared_across_platforms(owner, monkeypatch):
    from src.models.all_models import PlatformEnum

    use_script(monkeypatch, AIMessage(content="Noted on the web."))
    await run_turn(owner, "hello from the web", PlatformEnum.WEB)

    model = use_script(monkeypatch, AIMessage(content="Hi from Slack."))
    await run_turn(owner, "hello from slack", PlatformEnum.SLACK)

    system, *seen = model.calls[0]
    assert "chatting from slack" in system.content
    assert [m.content for m in seen] == [
        "hello from the web",
        "Noted on the web.",
        "hello from slack",
    ]
