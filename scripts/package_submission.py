"""Build a source-and-public-demo submission without local credentials or builds."""
import argparse
import hashlib
import json
import shutil
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {".git", ".runtime", ".venv", "node_modules", ".next", "__pycache__", ".pytest_cache", ".ruff_cache", ".vercel"}


def allowed(relative):
    if any(part in EXCLUDED for part in relative.parts):
        return False
    if relative.name == "AGENTS.md" or relative.suffix in {".pyc", ".log", ".tsbuildinfo"}:
        return False
    if relative.name.startswith(".env") and relative.name != ".env.example":
        return False
    return relative.name != "secrets.env"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if output.is_relative_to(ROOT.resolve()):
        raise SystemExit("Choose an output directory outside the source checkout.")
    folder = output / "atlas-hackathon-codebase"
    archive = output / "atlas-hackathon-codebase.zip"
    if folder.exists() or archive.exists():
        raise SystemExit("Output exists. Choose a new directory to preserve earlier packages.")
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
    selected = {Path(name) for name in tracked if name and (ROOT / name).is_file() and allowed(Path(name))}
    for dataset in (ROOT / "demo", ROOT / "demo-data/companies"):
        if dataset.is_dir():
            selected.update(p.relative_to(ROOT) for p in dataset.rglob("*") if p.is_file() and allowed(p.relative_to(ROOT)))
    output.mkdir(parents=True, exist_ok=True)
    folder.mkdir()
    for relative in sorted(selected):
        source = ROOT / relative
        if source.is_symlink():
            raise SystemExit(f"Unexpected symlink: {relative}")
        target = folder / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    # This always comes from the blank template, never from the live secret file.
    shutil.copy2(ROOT / "secrets.env.example", folder / "secrets.env")
    (folder / "START-HERE.md").write_text("# Atlas submission\n\nStart with README.md and docs/SETUP.md. The server secrets.env is a blank template. Fill credentials locally.\n\nThe package includes source code, migrations, tests, deployment configuration, original public demo documents, prepared passages, and embedding caches. Dependencies and database contents are not bundled.\n", encoding="utf-8")
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    manifest = {"source_commit": commit, "files": {}}
    for p in sorted(folder.rglob("*")):
        if p.is_file():
            manifest["files"][p.relative_to(folder).as_posix()] = {"bytes": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
    (folder / "MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in sorted(folder.rglob("*")):
            if p.is_file():
                z.write(p, (Path(folder.name) / p.relative_to(folder)).as_posix())
    if archive.stat().st_size >= 900_000_000:
        raise SystemExit("Archive exceeds the requested 900 MB limit.")
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:
            raise SystemExit("ZIP integrity check failed.")
        assert z.read("atlas-hackathon-codebase/secrets.env") == (ROOT / "secrets.env.example").read_bytes()
    checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
    (output / "atlas-hackathon-codebase.zip.sha256").write_text(checksum + "  " + archive.name + "\n")
    print(json.dumps({"archive": str(archive), "folder": str(folder), "bytes": archive.stat().st_size, "files": len(manifest["files"]) + 1, "sha256": checksum, "source_commit": commit, "integrity": "passed"}))


if __name__ == "__main__":
    main()
