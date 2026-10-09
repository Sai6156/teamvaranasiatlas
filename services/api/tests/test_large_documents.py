import pymupdf
import pytest
from atlas.extraction import extract, chunk_blocks, Block
from atlas.retrieval import focused_queries, lexical_query, rank, retrieve


def test_pdf_over_200_pages_keeps_the_last_page_and_progress():
    document = pymupdf.open()
    for index in range(250):
        page = document.new_page()
        page.insert_text(
            (40, 60), f"Report page {index + 1}. Deep source marker_{index + 1}."
        )
    progress = []
    blocks, note = extract(
        document.tobytes(),
        "large.pdf",
        lambda page, total: progress.append((page, total)),
    )
    assert len({block.location["page"] for block in blocks}) == 250
    assert any("marker_250" in block.text for block in blocks)
    assert progress[-1] == (250, 250)
    assert "All 250 PDF pages read" in note


def test_table_headers_are_not_lost_at_chunk_boundaries():
    prefix = "Metric | FY 2024-25 | FY 2023-24\n"
    rows = "\n".join(f"Metric {index} | {index} | {index + 1}" for index in range(1000))
    chunks = chunk_blocks(
        [
            Block(
                prefix + rows,
                {
                    "kind": "table",
                    "table_header": prefix,
                    "page": 3,
                    "label": "PDF page 3",
                },
            )
        ]
    )
    assert len(chunks) > 1
    assert all(chunk.text.startswith(prefix) for chunk in chunks)
    assert "Metric 999" in chunks[-1].text


def test_numbered_prompt_retrieves_all_ten_questions():
    prompt = "Read the report.\n" + "\n".join(
        f"Q{i}. What is metric {i} for the reporting year?" for i in range(1, 11)
    )
    queries = focused_queries(prompt)
    assert len(queries) == 10
    assert "metric 10" in queries[-1]


def test_a_short_new_topic_does_not_inherit_an_unrelated_previous_query():
    assert focused_queries(
        "What is the company growth rate?", "How many leave days?"
    ) == ["What is the company growth rate?"]
    assert (
        "How many leave days?"
        in focused_queries("When is it due?", "How many leave days?")[0]
    )


def test_keyword_query_uses_metric_anchors_and_safe_prefix_terms():
    query = lexical_query("What are related-party purchases and sales percentages?")
    assert "purchase:*" in query and "sale:*" in query
    assert "what" not in query
    assert ";" not in lexical_query("'); drop table public.chunks;--")


def test_exact_metric_table_outranks_rounded_promotional_callout():
    table = {
        "id": "table",
        "content": "Plastics recycled FY 2024-25 29,464 metric tonnes; safely disposed 33,400 metric tonnes.",
        "document_name": "Report.pdf",
        "location": {"structured": True},
        "score": 0.02,
    }
    teaser = {
        "id": "teaser",
        "content": "23,000+ metric tonnes. Recycling for a sustainable future.",
        "document_name": "Report.pdf",
        "location": {},
        "score": 0.025,
    }
    assert (
        rank(
            "What are the exact plastic recycled and safely disposed quantities?",
            [teaser, table],
        )[0]["id"]
        == "table"
    )


@pytest.mark.asyncio
async def test_evidence_budget_preserves_each_subquestion(monkeypatch):
    import atlas.retrieval as retrieval

    async def embeddings(queries):
        return [[i] for i, _ in enumerate(queries)]

    monkeypatch.setattr(retrieval, "embed", embeddings)

    class DB:
        async def rpc(self, name, payload):
            i = payload["query_embedding"][0]
            return [
                {
                    "id": f"evidence-{i}",
                    "content": f"Distinct metric {i} appears here with sufficient information.",
                    "document_name": "report",
                    "location": {},
                    "score": 0.02,
                }
            ]

    sources, queries = await retrieve(
        DB(), "org", "\n".join(f"{i}. What is metric {i}?" for i in range(1, 11))
    )
    assert len(queries) == 10 and len(sources) == 10
    assert {source["id"] for source in sources} == {f"evidence-{i}" for i in range(10)}
