# Atlas — company knowledge, connected

Built by Team Varanasi for the TriCity AI Hackathon. Atlas is a secure company knowledge application: create an account, open a private workspace, invite employees, upload company documents, and ask questions with source evidence.

Live application: [atlas-varanasi.vercel.app](https://atlas-varanasi.vercel.app). API readiness: [atlas-varanasi-api.onrender.com/health/ready](https://atlas-varanasi-api.onrender.com/health/ready). See [release verification](docs/VERIFICATION.md) for measured checks and limits.

## Stack

Next.js App Router / React / TypeScript; Python FastAPI; Supabase Auth, PostgreSQL/pgvector, and private Storage; OpenRouter; Vercel frontend and Render API/worker.

## Local setup

Requirements: Node.js 22 or 24, Python 3.12+, a Supabase project, and an OpenRouter account with credit.

1. `npm ci`
2. `python -m venv .venv`
3. Activate the environment and `pip install -r services/api/requirements.txt`.
4. Copy `apps/web/.env.example` to `apps/web/.env.local`; set your Supabase URL/publishable key and API URL.
5. Copy `services/api/.env.example` to `services/api/.env`; supply your Supabase and OpenRouter server keys. Alternatively put private keys in a root `secrets.env`.
6. Apply SQL migrations in `supabase/migrations` in numerical order using the Supabase SQL editor or CLI.
7. Configure Supabase Auth site/redirect URLs and SMTP, as described below.
8. From `services/api`, run `python -m uvicorn atlas.main:app --host 127.0.0.1 --port 8000`.
9. In another terminal from `services/api`, run `python -m atlas.worker`.
10. From the root, run `npm run dev`; open `http://127.0.0.1:3000`.

Passwords are sent directly to Supabase Auth and are not stored in application tables. Never commit `secrets.env`, `.env`, service/secret keys, or generated test credentials. The browser receives only the public Supabase key and its own session token.

## Required authentication setup

Keep email confirmation enabled. Configure custom SMTP in Supabase Auth before opening signup to judges: the default mail service restricts recipients and is unsuitable for general external signup. Set the site URL to the deployed Vercel origin. Allow these redirects on the production origin and localhost for development:

- `/auth/callback` — signup verification
- `/reset-password` — password recovery

Use at least a 12-character password policy in Supabase Auth; enable compromised-password checks if the project's plan supports them. Frontend forms enforce the 12-character minimum for signup and reset, but the Supabase server policy is authoritative. Invitations are email-bound, single-use, and expire after seven days. Administrators share invitation links themselves; the app does not send invitation emails.

## Features

- Email signup, verification, login, recovery, signout, and workspace onboarding.
- Multiple organization workspaces with administrator/employee roles.
- Private library, named collections, file upload, indexing status, failure retry, source download, and deletion.
- Hybrid PostgreSQL full-text/pgvector retrieval and streamed grounded answers.
- Citation cards with exact passages and source locations; private per-user conversations.
- Workspace invitations and audit activity.
- Durable PostgreSQL jobs with leases, bounded retries, idempotent chunk indexing, and immediate removal from search on deletion.
- Per-workspace document/storage/question limits; authenticated API, RLS, and private Storage policies.

## Supported formats and limits

TXT, Markdown, logs, common programming/config files, JSON/YAML/TOML, SQL, HTML/XML, notebook source, PDF, DOCX, CSV/TSV, XLSX, PPTX, common images, and bounded ZIP archives. Linux deployment includes Tesseract and Poppler for OCR. PDF, paragraph, slide, row/sheet, and line references are preserved. ZIP members retain their paths and source locations; unsupported members are explicitly skipped. Nested/encrypted archives, unsafe paths, symbolic links, and excessive expansion are rejected.

Limits: 25 MB/file, 200 PDF pages, 40 scanned OCR pages, 100,000 spreadsheet/table rows, 2,000 chunks/file, 200 documents and 500 MB per workspace, and 200 questions/workspace/day. ZIP archives are limited to 100 files and 75 MB expanded content. Legacy Office formats, encrypted files, audio/video, executables, and arbitrary binary formats are not currently supported. Image-only content in Office documents is not OCR'd. XLSX uses saved values and does not recalculate formulas. RAG cannot provide exact totals over an entire spreadsheet from only retrieved row subsets; Atlas explicitly asks the model to disclose this limitation.

## AI routing

1. `z-ai/glm-5.3-flash`: open-inference → deepinfra → relace → streamlake → novita.
2. `deepseek/deepseek-v4.1-flash`: decart → morph → inference-net → sail-research → relace.
3. `openai/gpt-6-luna`: openai → azure.
4. `qwen/qwen3.8-flash`: automatic OpenRouter routing.

Each model gets its own ordered provider allowlist. Transient failures advance routes; invalid credentials/balance/configuration do not retry across all models. Interrupted partial output is marked incomplete rather than joined to another answer. Privacy policy defaults to disallow provider data collection. Optional strict ZDR may reduce route availability.

Embeddings: `openai/text-embedding-3-small`, fixed 1536 dimensions. The index and query use the same embedding space. Temporary embedding failure enables explicitly labeled keyword-only search; indexing retries without switching vector spaces.

## Deployment

Vercel project root: `apps/web`. Public environment variables: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`, `NEXT_PUBLIC_API_URL`. Set production branch to `main` and disable Vercel deployment protection for the public judging URL if it is enabled.

Render Docker context: `services/api`; Dockerfile: `services/api/Dockerfile`. API uses the image default command. Worker command: `python -m atlas.worker`. Set server secrets and `FRONTEND_URL`/`ALLOWED_ORIGINS` to the exact production origin. API liveness: `/health/live`; readiness: `/health/ready`. A `render.yaml` blueprint is provided when available; service plans must be selected with the account owner's budget approval. Free API instances have cold starts. Worker-only services require paid hosting.

Migrations must be deployed before the API/worker. Back up data before schema changes; deploy compatible changes first. Logs use job/request IDs, not keys or full uploaded documents. Supabase security-definer RPCs deliberately expose only validated membership/role operations; ingestion jobs have no user-access policies because they are server-only.

## Verification

`npm run typecheck` and `npm run build` check the frontend. From `services/api`, `python -m pytest tests -q` exercises parsers and authentication guards. `python scripts/live_verify.py [API_URL]` runs a live synthetic end-to-end test against the configured project, creates QA users/workspaces, and checks invitations, role restrictions, cross-tenant denial, four formats, duplicate uploads, signed sources, private conversations, and a multi-document answer. It uses API credit. Generated QA credentials stay in ignored `.runtime/`; remove synthetic QA accounts/workspaces after verification.

## Current scope and submission

This is a hackathon application, not a claim of enterprise security certification or guaranteed hallucination elimination. Review source evidence for important decisions. Billing, enterprise SSO, external knowledge connectors, table-wide deterministic analytics, and version comparison remain future scope.

Use a public repository and add every team member as a collaborator/contributor. Keep the submission ZIP at or below 10 MB, excluding dependencies/build output/secrets. Presentation and product links must be accessible to judges. Video recording is deferred, but its accessible link is still a required hackathon deliverable.
