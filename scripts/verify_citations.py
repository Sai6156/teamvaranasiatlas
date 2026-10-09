"""Reproduce a multi-turn citation regression using the synthetic QA workspace."""

import asyncio
import json
from pathlib import Path
import sys
import httpx

ROOT = Path(__file__).resolve().parents[1]


async def main():
    saved = json.loads((ROOT / ".runtime/qa-session.json").read_text())
    user = saved["accounts"][2]
    org = saved["organizations"][0]
    base = (
        sys.argv[1] if len(sys.argv) > 1 else "https://atlas-varanasi-api.onrender.com"
    )
    headers = {"Authorization": "Bearer " + user["token"]}
    async with httpx.AsyncClient(timeout=90) as client:
        conversations = (
            await client.get(base + f"/workspaces/{org}/conversations", headers=headers)
        ).json()
        conversation = conversations[0]["id"]
        response = await client.post(
            base + f"/workspaces/{org}/chat",
            headers=headers,
            json={
                "question": "What should I do on my first day, when is security training due, and what is required before accessing production systems?",
                "conversation_id": conversation,
            },
        )
        response.raise_for_status()
        events = [
            json.loads(line[5:].strip())
            for line in response.text.splitlines()
            if line.startswith("data:")
        ]
        assert not [event for event in events if event["type"] == "error"], events[-1]
        done = next(event for event in events if event["type"] == "done")
        answer = ""
        for event in events:
            if event["type"] == "token":
                answer += event["text"]
            elif event["type"] == "reset":
                answer = event["text"]
        engineering = [
            citation
            for citation in done["citations"]
            if "production" in citation["content"].lower()
            and "team lead" in citation["content"].lower()
        ]
        assert engineering, "Production access must cite the engineering passage"
        assert "authentication" in answer.lower() and "five" in answer.lower(), answer
        refusal_response = await client.post(
            base + f"/workspaces/{org}/chat",
            headers=headers,
            json={
                "question": "What is this company's revenue growth rate?",
                "conversation_id": conversation,
            },
        )
        refusal_events = [
            json.loads(line[5:].strip())
            for line in refusal_response.text.splitlines()
            if line.startswith("data:")
        ]
        refusal_done = next(
            event for event in refusal_events if event["type"] == "done"
        )
        assert not refusal_done["citations"], (
            "An abstention must not attach unrelated source cards"
        )
        print(
            json.dumps(
                {
                    "multi_turn_citations_passed": True,
                    "production_source": engineering[0]["document_name"],
                    "unanswerable_question_abstained": True,
                    "duration_ms": done["duration_ms"],
                }
            )
        )


asyncio.run(main())
