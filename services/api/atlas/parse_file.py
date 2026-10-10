"""Disposable parser process: native PDF work must never hold the API's GIL."""

import json
import os
import sys
from pathlib import Path
from .extraction import extract, chunk_blocks


def main(directory: Path):
    if hasattr(os, "nice"):
        os.nice(10)  # Prefer serving interactive requests on a shared CPU.
    request = json.loads((directory / "request.json").read_text())
    output = directory / "result.json"

    def progress(done, total):
        pending = directory / "progress.tmp"
        pending.write_text(json.dumps([done, total]))
        pending.replace(directory / "progress.json")

    try:
        blocks, note = extract(
            (directory / "input").read_bytes(), request["name"], progress
        )
        chunks = chunk_blocks(blocks)
        if len(chunks) > request["max_chunks"]:
            raise ValueError(
                "Document is too large to index. Split it into smaller files."
            )
        result = {
            "chunks": [
                {"text": block.text, "location": block.location} for block in chunks
            ],
            "note": note,
        }
        output.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    except Exception as error:
        message = (
            str(error)[:240]
            if isinstance(error, ValueError)
            else "File extraction failed. Please retry this document."
        )
        output.write_text(
            json.dumps(
                {
                    "error": message,
                    "terminal": isinstance(error, (ValueError, MemoryError)),
                }
            ),
            encoding="utf-8",
        )
        sys.exit(1)


if __name__ == "__main__":
    main(Path(sys.argv[1]))
