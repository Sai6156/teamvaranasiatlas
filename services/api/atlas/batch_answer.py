"""Answer every requested question without one oversized reasoning context."""

import asyncio
from .llm import generate
from .retrieval import rank
from .grounding import disclosed_column_totals


async def answer_batch(system: str, queries: list[str], sources: list[dict]):
    gate = asyncio.Semaphore(3)
    tasks = []

    async def solve(query, index):
        relevant = [
            source for source in sources if str(index) in source.get("query_ranks", {})
        ]
        relevant.sort(key=lambda source: source["query_ranks"][str(index)])
        if not relevant:
            relevant = rank(query, sources)[:12]
        evidence = "\n\n".join(
            f"[{source['number']}] {source['document_name']} · {source['location'].get('label', 'Source')}\n{source['content']}"
            for source in relevant
        )
        prompt = [
            {
                "role": "system",
                "content": system + "\n\nAUTHORIZED EVIDENCE:\n" + evidence,
            },
            {
                "role": "user",
                "content": "Answer only the following subquestion completely. Include every requested field and any requested category totals. Keep the response concise.\n"
                + query,
            },
        ]
        text = ""
        model = None
        async with gate:
            async for item in generate(prompt, max_tokens=2200, timeout_seconds=90):
                if item["type"] == "token":
                    text += item["text"]
                elif item["type"] == "model":
                    model = item["model"]
        return disclosed_column_totals(text, query, relevant), model

    try:
        tasks = [
            asyncio.create_task(solve(query, index))
            for index, query in enumerate(queries)
        ]
        for index, task in enumerate(tasks):
            yield {
                "type": "status",
                "text": f"Answering question {index + 1} of {len(queries)}",
            }
            text, model = await task
            if model:
                yield {"type": "model", "model": model}
            yield {"type": "token", "text": f"\n\n### {index + 1}\n\n" + text.strip()}
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
