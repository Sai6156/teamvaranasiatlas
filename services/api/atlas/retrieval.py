"""Focused hybrid retrieval: separate questions keep separate evidence budgets."""

import asyncio
import math
import re
from collections import Counter
from .llm import embed

STOP = set(
    "a an the of on in at to from for with and or is are was were be have has had what which who how when where why give provide list extract please show tell report company industries reliance financial year fy current previous reported following details exact total per as its their under according also".split()
)
ALIASES = {
    "r&d": "research development",
    "rpt": "related party transactions",
    "capex": "capex capital expenditure",
    "attrition": "turnover",
    "reclamation": "reclaimed",
    "injuries": "injury",
}


def stem(word: str) -> str:
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    if word.endswith("s") and len(word) > 4:
        return word[:-1]
    return word


def tokens(text: str) -> list[str]:
    text = text.lower()
    for term, replacement in ALIASES.items():
        text = re.sub(r"\b" + re.escape(term) + r"\b", replacement, text)
    return [
        stem(term)
        for term in re.findall(r"[a-z0-9]+", text)
        if len(term) > 2 and term not in STOP
    ]


def focused_queries(question: str, previous: str = "") -> list[str]:
    parts = re.split(
        r"(?m)^\s*(?:[-*]\s*)?(?:q(?:uestion)?\s*)?\d{1,2}[).:\-]\s*",
        question,
        flags=re.I,
    )
    if len(parts) > 2:
        context = parts[0].strip()[:700]
        queries = [
            (context + "\n" if context else "") + part.strip()
            for part in parts[1:]
            if len(part.strip()) > 5
        ]
    else:
        queries = [
            part.strip() + "?"
            for part in re.split(r"\?\s*", question)
            if len(part.strip()) > 8
        ]
    if not queries:
        queries = [question]
    # Context is used only for genuinely referential follow-ups, not every short question.
    if (
        len(queries) == 1
        and previous
        and re.search(
            r"\b(it|that|those|these|they|them)\b|^(and|also|what about|how about)\b",
            question,
            re.I,
        )
    ):
        queries = [previous[:1500] + "\n" + question]
    return list(dict.fromkeys(query[:3500] for query in queries))[:24]


def lexical_query(text: str) -> str:
    return " | ".join(
        term + ":*"
        for term in dict.fromkeys(tokens(text))
        if re.fullmatch(r"[a-z0-9]+", term)
    )[:1800]


def rank(query: str, candidates: list[dict]) -> list[dict]:
    terms = set(tokens(query))
    frequencies = [
        Counter(tokens(source["content"] + " " + source.get("document_name", "")))
        for source in candidates
    ]
    lengths = [sum(words.values()) for words in frequencies]
    average = sum(lengths) / max(len(lengths), 1)
    document_frequency = {
        term: sum(term in words for words in frequencies) for term in terms
    }
    numerical = bool(
        re.search(
            r"percentage|percent|how many|number|rate|amount|quantity|days|headcount|capex|r&d|recycl|reclaim|dispos|injur",
            query,
            re.I,
        )
    )
    output = []
    for source, words, length in zip(candidates, frequencies, lengths):
        score = 0.0
        for term in terms:
            count = words.get(term, 0)
            if not count:
                continue
            inverse = math.log(
                1
                + (len(candidates) - document_frequency[term] + 0.5)
                / (document_frequency[term] + 0.5)
            )
            score += (
                inverse
                * count
                * 2.2
                / (count + 1.2 * (0.25 + 0.75 * length / max(average, 1)))
            )
        coverage = len(terms & words.keys()) / max(len(terms), 1)
        score += coverage * 4 + float(source.get("score") or 0) * 20
        if numerical and source["location"].get("structured") and coverage > 0.15:
            score *= 1.35
        output.append({**source, "retrieval_score": score})
    return sorted(output, key=lambda source: source["retrieval_score"], reverse=True)


async def retrieve(
    db, org: str, question: str, previous: str = "", folder: str | None = None
):
    queries = focused_queries(question, previous)
    vectors = await embed(queries)
    gate = asyncio.Semaphore(4)

    async def search(query, vector):
        async with gate:
            rows = await db.rpc(
                "search_chunks_v2",
                {
                    "org": org,
                    "lexical_query": lexical_query(query),
                    "query_embedding": vector,
                    "result_limit": 32,
                    "folder": folder,
                },
            )
            return rank(query, rows)

    ranked = await asyncio.gather(
        *(search(query, vector) for query, vector in zip(queries, vectors))
    )
    selected = {}
    if len(queries) > 3:
        for query_index, rows in enumerate(ranked):
            characters = 0
            for position, source in enumerate(rows[:12]):
                if position >= 8 and characters + len(source["content"]) > 65000:
                    continue
                characters += len(source["content"])
                if source["id"] not in selected:
                    selected[source["id"]] = {**source, "query_ranks": {}}
                selected[source["id"]]["query_ranks"][str(query_index)] = position
        sources = list(selected.values())
        for index, source in enumerate(sources):
            source["number"] = index + 1
            source["location"] = {
                key: value
                for key, value in source["location"].items()
                if key != "table_header"
            }
        return sources, queries
    protected = []
    # Reserve evidence for every requested subquestion before global ranking.
    minimum = 6 if len(queries) > 3 else 2 if len(queries) > 1 else 8
    for rows in ranked:
        for source in rows[:minimum]:
            if source["id"] not in selected:
                selected[source["id"]] = source
                protected.append(source["id"])
    remaining = sorted(
        (source for rows in ranked for source in rows),
        key=lambda source: source["retrieval_score"],
        reverse=True,
    )
    limit = min(40, max(12, len(queries) * 4))
    budget = 115000 if len(queries) > 3 else 65000
    characters = sum(len(source["content"]) for source in selected.values())
    for source in remaining:
        if len(selected) >= limit:
            break
        if source["id"] in selected:
            continue
        if characters + len(source["content"]) > budget:
            continue
        selected[source["id"]] = source
        characters += len(source["content"])
    sources = list(selected.values())
    for index, source in enumerate(sources):
        source["number"] = index + 1
        source["location"] = {
            key: value
            for key, value in source["location"].items()
            if key != "table_header"
        }
    return sources, queries
