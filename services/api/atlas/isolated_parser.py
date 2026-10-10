"""Bounded extraction in a killable child, preserving API responsiveness."""

import asyncio
import json
import os
import signal
import sys
import tempfile
from pathlib import Path
from .config import settings
from .extraction import Block


def resident_mb(pid: int) -> float:
    try:
        for line in Path(f"/proc/{pid}/status").read_text().splitlines():
            if line.startswith("VmRSS:"):
                return int(line.split()[1]) / 1024
    except (OSError, ValueError):
        pass
    return 0  # /proc isn't available on Windows.


async def prepare(data: bytes, name: str, progress: list[int]):
    config = settings()
    with tempfile.TemporaryDirectory(prefix="atlas-parse-") as temporary:
        directory = Path(temporary)
        await asyncio.to_thread((directory / "input").write_bytes, data)
        (directory / "request.json").write_text(
            json.dumps({"name": name, "max_chunks": config.max_chunks})
        )
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            "atlas.parse_file",
            str(directory),
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
            cwd=str(Path(__file__).resolve().parent.parent),
            start_new_session=os.name != "nt",
        )
        waiter = asyncio.create_task(process.wait())
        try:
            async with asyncio.timeout(config.ingestion_timeout_seconds):
                while not waiter.done():
                    if resident_mb(process.pid) > config.parser_memory_limit_mb:
                        raise ValueError(
                            "This file needs more extraction memory than the current server allows. Split it into smaller files and retry."
                        )
                    try:
                        progress[:] = json.loads(
                            (directory / "progress.json").read_text()
                        )
                    except (OSError, ValueError):
                        pass
                    await asyncio.wait({waiter}, timeout=0.5)
            result_file = directory / "result.json"
            if not result_file.exists():
                raise RuntimeError("The extraction process exited unexpectedly.")
            if result_file.stat().st_size > 64 * 1024 * 1024:
                raise ValueError(
                    "Extracted content is too large. Split the file and retry."
                )
            result = await asyncio.to_thread(
                lambda: json.loads(result_file.read_text(encoding="utf-8"))
            )
            if "error" in result:
                error_type = ValueError if result.get("terminal") else RuntimeError
                raise error_type(result["error"])
            return [
                Block(row["text"], row["location"]) for row in result["chunks"]
            ], result["note"]
        finally:
            if process.returncode is None:
                try:
                    if os.name == "nt":
                        process.terminate()
                    else:
                        os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    await asyncio.wait_for(asyncio.shield(waiter), timeout=5)
                except TimeoutError:
                    if os.name == "nt":
                        process.kill()
                    else:
                        os.killpg(process.pid, signal.SIGKILL)
                    await waiter
            await waiter
