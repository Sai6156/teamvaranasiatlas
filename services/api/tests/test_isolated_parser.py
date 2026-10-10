import asyncio
import sys
import pytest
from atlas import isolated_parser


@pytest.mark.asyncio
async def test_disposable_parser_preserves_text_and_locations():
    chunks, note = await isolated_parser.prepare(
        b"Company policy\nAnnual leave is 18 days.", "handbook.txt", [0, 0]
    )
    assert "Annual leave is 18 days." in chunks[0].text
    assert chunks[0].location["kind"] == "lines"


@pytest.mark.asyncio
async def test_blocked_parser_does_not_block_parent_and_is_killed_on_cancel(
    monkeypatch,
):
    original = asyncio.create_subprocess_exec
    children = []

    async def blocked(*args, **kwargs):
        child = await original(
            sys.executable, "-c", "import time; time.sleep(60)", **kwargs
        )
        children.append(child)
        return child

    monkeypatch.setattr(asyncio, "create_subprocess_exec", blocked)
    task = asyncio.create_task(isolated_parser.prepare(b"text", "test.txt", [0, 0]))
    for _ in range(20):
        await asyncio.sleep(0.01)
    assert not task.done() and children
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert children[0].returncode is not None


@pytest.mark.asyncio
async def test_memory_guard_rejects_file_and_stops_parser(monkeypatch):
    monkeypatch.setattr(isolated_parser, "resident_mb", lambda pid: 1000)
    with pytest.raises(ValueError, match="extraction memory"):
        await isolated_parser.prepare(b"text", "test.txt", [0, 0])


def test_low_memory_pdf_preserves_every_page_and_aligned_values(monkeypatch):
    import pymupdf
    from atlas.pdf_extract import extract_pdf

    def forbidden(*args, **kwargs):
        raise AssertionError("Expensive geometric detection must be skipped")

    monkeypatch.setattr(pymupdf.Page, "find_tables", forbidden)
    document = pymupdf.open()
    for _ in range(3):
        page = document.new_page()
        page.insert_text((40, 40), "Region   Machines\nNational   8\nInternational   1")
    blocks, note = extract_pdf(document.tobytes(), detect_tables=False)
    document.close()
    assert {block.location["page"] for block in blocks} == {1, 2, 3}
    assert any(
        "National" in block.text
        and "8" in block.text
        and block.location.get("kind") == "table"
        for block in blocks
    )
    assert "native text and aligned columns" in note
