# Atlas public company demo library

The live application has ten read-only demo workspaces. Sign in at
https://atlas-varanasi.vercel.app/app and choose **Explore demo companies** in
the sidebar. A verified account with no private workspace opens the company
picker directly. Each account's chats are private, even in these shared demos.

Inside **Ask Atlas**, the **Demo company files** selector above the input also
lets a judge visit all ten companies in one visible chat. Four questions are
shuffled locally from a curated five-question set for the selected company.
Selecting companies, refreshing suggestions and filling a question make no
model requests. Earlier messages stay visible and carry company labels. Each
company keeps its own conversation context; another company's questions and
answers are not sent along with the next request. Source citations continue to
open their original documents. The combined visible journey lasts for the
current open chat; company conversations are individually stored privately.

| India | Global |
| --- | --- |
| Reliance Industries | Microsoft |
| TCS | Apple |
| Infosys | NVIDIA |
| Wipro | Amazon |
| HCLTech | Alphabet |

## Dataset and provenance

All 14 PDFs supplied in `demo/` were used. Twelve additional verified public
documents supplement them. There are **30 prepared source files**, **2,717 PDF
pages**, and **2,953 indexed passages**, plus full text from four HTML sources.
The prepared original files occupy about 152 MB in private Supabase Storage.

- TCS and Infosys each use three contiguous parts of their supplied annual
  report. These are clearly labelled parts, not three independent reports.
- Apple combines the three supplied FY2026 quarterly statements in one source
  and splits its 2025 environmental report into two contiguous parts.
- Alphabet uses its supplied Q1 2026 earnings release and two contiguous parts
  of the Google 2026 environmental report. That PDF is not an annual report.
- Other companies use their supplied annual report plus public results and
  conduct policies. NVIDIA's conduct policy specifically covers finance staff.
- Every prepared PDF page maps to its original filename and physical PDF page.
  Citations expose both the original reference and prepared PDF page when needed.
  Interactive PDF form/navigation controls are omitted from prepared copies.
  The user-supplied originals remain untouched on the PC.
- Financial periods differ across documents. The UI supplies questions naming
  explicit periods; answers must not treat quarterly and year-to-date figures
  as interchangeable or present historical figures as current market data.

`source-catalog.json` lists the final company/source selection.
`prepared-manifest.json` records file hashes, source URLs where verified,
reporting periods and page maps. The extracted text, original files and cached
embeddings are ignored by Git and excluded from Vercel deployments.

## Local preparation and indexing

Processing runs on this Windows PC; no demo ingestion jobs run on Render.
Supabase holds the source objects, document metadata, full-text search index
and 1536-dimensional vectors. Vercel serves the interface and Render handles
retrieval and answer generation.

Keep the existing Python environment, supplied `demo/` files and
`.runtime/tessdata/eng.traineddata`. The trained data is the official English
model from https://github.com/tesseract-ocr/tessdata_fast. API credentials stay
in ignored `secrets.env`; never upload that file to GitHub.

Run these commands from the repository root:

```powershell
.venv\Scripts\python.exe scripts/prepare_demo_library.py
.venv\Scripts\python.exe scripts/seed_demo_library.py
```

Preparation preserves complete page coverage and financial column alignment.
Indexing caches embeddings locally, uses deterministic document/chunk IDs and
resumes after interruptions. Existing source hashes must match; changed
published sources require a new dataset version. Workspaces become visible
only after all three documents are ready and their chunk counts match.

Embeddings use `openai/text-embedding-3-small`. Answer routing remains the
user-requested GLM → DeepSeek → GPT-6 Luna → Qwen priority. An OpenRouter key
limit or exhausted credit blocks AI requests; it is reported as an account
configuration issue rather than silently trying every provider.

## Verification

`acceptance-report.json` records live checks of all ten companies and all thirty
original-source URLs, anonymous access denial, mutation denial, private
company isolation and personal-chat isolation. UI checks cover actual sign-in,
the ten-card company picker, company switching, hidden write controls and
mobile overflow. Backend regression suite: 46 passing tests.

Temporary acceptance accounts are generated separately and removed after QA.
No judge account receives membership or administrator rights in shared demos.
Only server-side service-role seeding can publish the library.

The prebuilt index removes PDF-processing waits during judging. Free Render
hosting can still have a cold start after inactivity, and model/network latency
still affects answer time; this setup does not promise unlimited uploads or
zero-latency AI responses.
