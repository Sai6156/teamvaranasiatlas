import asyncio
import pytest
from atlas import batch_answer


@pytest.mark.asyncio
async def test_all_numbered_answers_are_returned_in_order_with_bounded_concurrency(
    monkeypatch,
):
    active = 0
    maximum = 0
    seen = []

    async def fake_generate(messages, **kwargs):
        nonlocal active, maximum
        active += 1
        maximum = max(maximum, active)
        seen.append(messages[-1]["content"])
        await asyncio.sleep(0.01)
        yield {"type": "model", "model": "test"}
        yield {"type": "token", "text": "Supported answer [1]"}
        active -= 1

    monkeypatch.setattr(batch_answer, "generate", fake_generate)
    sources = [
        {
            "id": "source",
            "number": 1,
            "content": "Complete table values and labels.",
            "document_name": "report.pdf",
            "location": {"label": "Page 1"},
            "score": 0.01,
        }
    ]
    events = [
        event
        async for event in batch_answer.answer_batch(
            "Ground answers.", [f"Question {index}" for index in range(1, 11)], sources
        )
    ]
    text = "".join(event["text"] for event in events if event["type"] == "token")
    assert all(f"### {index}\n" in text for index in range(1, 11))
    assert len(seen) == 10 and maximum <= 3
    assert text.index("### 1\n") < text.index("### 10\n")
