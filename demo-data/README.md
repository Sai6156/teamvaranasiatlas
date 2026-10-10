# Public company demo dataset

Verify an account, open Ask Atlas, and select **Demo company files**. Users retain private chats and company-specific context. Suggestions are curated and shuffled locally without model calls.

| India | Global |
| --- | --- |
| Reliance Industries | Microsoft |
| TCS | Apple |
| Infosys | NVIDIA |
| Wipro | Amazon |
| HCLTech | Alphabet |

## Dataset

Thirty prepared files cover 2,717 physical PDF pages and 2,953 indexed passages, including HTML text. Fourteen supplied PDFs and twelve supplemental public files contribute to the library.

The ZIP includes originals in `demo/`, prepared sources/extracted passages in `demo/prepared/`, and supplemental downloads in `demo-data/companies/`. Git tracks source catalogs and manifests rather than large binaries. Public embedding caches contain numeric vectors, not API credentials; they are not a database backup.

TCS and Infosys use three contiguous report parts. Apple combines quarterly statements and splits its environmental report. Alphabet includes its Q1 release and parts of Google's environmental report. NVIDIA's conduct policy covers finance staff. Reporting periods and document scopes differ and must remain explicit.

## Reproduction

With the Python environment active, run from the project root:

```bash
python scripts/download_demo_documents.py
python scripts/prepare_demo_library.py
python scripts/seed_demo_library.py --stage-only
# Inspect staged data, then publish:
python scripts/seed_demo_library.py
```

Preparation needs the supplied originals or packaged demo directory. Downloads require internet access. OCR uses system Tesseract or an explicitly configured `TESSDATA_PREFIX`.

Seeding writes to the configured Supabase project and may consume embedding credit if compatible cached vectors are absent. Use a dedicated project. It is resumable and publishes only ready demo documents.

A fresh installation does not automatically copy the deployed database. Fill credentials and seed explicitly. See `NOTICE.md` for publisher ownership.
