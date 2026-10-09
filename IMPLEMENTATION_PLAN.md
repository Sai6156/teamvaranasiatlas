# Team Varanasi — end-to-end implementation plan

Planning baseline: October 9, 2026, Asia/Kolkata. No application code, infrastructure changes, paid API calls, or deployment performed during this planning task.

## 1. Product and success criteria

Build a company knowledge assistant: administrators upload internal files; employees ask questions and receive answers grounded in documents they are authorized to read, with citations that open the exact supporting passage.

The workspace currently contains the hackathon rules and secrets.env, with no application implementation. The five reference images confirm the locked problem and stack, submission requirements, and judging weights. Use Next.js, Python/FastAPI, Supabase PostgreSQL/pgvector, and Supabase Auth. Host the frontend on Vercel and API/worker on Render.

Prioritize the live upload → ingestion → search → answer → citation flow. Working MVP and meaningful AI account for 50% of judging; UI/UX and market potential add 30%. Differentiate with evidence previews, mixed-format questions, conflict detection, and dependable failover. Winning cannot be guaranteed; these choices maximize alignment with the rubric.

Core release: authentication, organizations and roles, broad supported file ingestion, durable status/retry, hybrid retrieval, grounded chat with streaming, source previews, document deletion, tenant isolation, seeded judge demo, and live deployment. Add multilingual evaluation and policy comparison once the core passes. Defer billing, enterprise SSO, Slack/Drive connectors, autonomous actions, and audio/video ingestion. Video recording is deferred as requested, but remains a mandatory submission deliverable.

## 2. Architecture and repository boundaries

- apps/web: Next.js App Router, TypeScript, Tailwind, accessible component library; chat, library, upload, evidence drawer, workspace settings.
- services/api: FastAPI, Pydantic schemas, Supabase JWT validation, upload authorization, retrieval, chat streaming, source access, document lifecycle.
- services/worker: the same Python project with a separate worker entrypoint; extraction, OCR, chunking, embedding, and cleanup jobs.
- supabase/migrations: schema, pgvector/full-text indexes, row-level security, storage policies, authorized retrieval functions, durable job claim functions.
- tests and fixtures: synthetic company documents and expected answers; API, isolation, routing, ingestion, and browser integration tests.
- docs: setup, architecture, deployment, support matrix, evaluation results, pitch content, and submission checklist.

Browser authenticates with Supabase. FastAPI validates the access token and derives organization membership server-side. Files upload directly into private Supabase Storage using narrowly scoped signed upload authorization. FastAPI registers the completed upload and enqueues a durable job. A Render background worker claims jobs from PostgreSQL. The worker produces source-aware chunks and embeddings; FastAPI retrieves authorized evidence and streams OpenRouter answers directly to the browser over SSE.

Keep document ingestion and model traffic off Vercel functions. Vercel serves the product interface; the browser talks to the Render API with an authenticated request and exact-origin CORS. PostgreSQL is the job source of truth; no Redis dependency is required for this MVP.

## 3. Company-file support

Do not promise literal support for every arbitrary binary format. Publish a tested support matrix. Use a parser registry and one common extraction contract: document/version ID, text blocks, headings, tables, original location, extraction method, and quality flags.

| Family | First-release support and source locations |
| --- | --- |
| TXT, Markdown, logs | Encoding detection; heading/line-range citations |
| PDF | Native text and tables with page citations; local OCR for scanned pages; low-quality extraction flags |
| DOCX | Paragraphs, headings, tables; section/paragraph locations because original pagination is not stable |
| CSV, TSV | Delimiter/encoding detection; preserve headers and row ranges |
| XLSX | Sheet names, cell ranges, stored values; do not execute macros or claim to recalculate formulas |
| PPTX | Slide text, notes, tables; slide-number citations |
| Code/config | Common source extensions, JSON, YAML, TOML, SQL; preserve paths, symbols where available, and line ranges |
| HTML/XML | Safe text extraction; discard active content and avoid fetching embedded remote resources |
| PNG/JPG/TIFF | OCR and optional routed vision extraction; retain image/page reference and label uncertain interpretation |
| ZIP | Bounded recursive extraction of supported files; reject traversal, symlinks, excessive expansion, depth, and file counts |
| Legacy Office, RTF, EML | Second pass, only after converter/parser fixtures pass; otherwise return an explicit unsupported-format explanation |
| Encrypted files, executables, databases, audio/video | Explain the limitation and request a supported export; do not silently index empty content |

Suggested parser starting points: pypdf/pdfplumber, python-docx, openpyxl, python-pptx, Python csv/JSON readers, safe HTML extraction, and Tesseract in the worker image. Benchmark extraction quality and memory before locking versions. Add heavyweight layout parsers only if the test corpus demonstrates a need.

Provisional limits: 25 MB per file, 200 PDF pages, 100 members per archive, bounded expanded size, worker timeout, and organization storage/quota limits. Tune against hosting resources. Big spreadsheets are indexed in bounded row groups; numerical totals require deterministic computation, not approximate RAG.

For table calculations, parse a validated operation specification for allowlisted filters/count/sum/average into Python operations over authorized uploaded tables. No model-generated Python or arbitrary SQL execution. Return the operation, sheet/row scope, units, and source citation. If this capability cannot pass tests, disclose the limitation and defer arithmetic questions.

## 4. Durable ingestion and lifecycle

States: uploaded → queued → extracting → chunking → embedding → ready, plus failed/deleting/deleted. Show stage, truthful progress where measurable, and an actionable retry/error message.

Validate membership, file signatures, size, and declared type before accepting processing. Store originals privately under organization/document/version paths. Record content hashes for within-organization deduplication. Never execute uploaded code or macros. Parse in resource-bounded subprocesses where practical; escape previews and serve unsafe originals as attachments.

Jobs use atomic claims, leases, attempt counters, delayed retries, and stale-lease recovery. Every stage is idempotent; retries cannot duplicate chunks or publish partial results. New versions become searchable only after complete indexing; switch the active version atomically. Retain previous versions only when needed for policy comparison, and exclude them from normal search by default.

Chunk by format: approximately 500–900 tokens for prose with modest overlap, function/section boundaries for code, and header-preserving row groups for tables. Preserve source locations and mark OCR content. Embed in bounded batches. Track parser, chunker, embedding model, dimensions, and pipeline version so changes can trigger controlled reindexing.

Deletion first removes search visibility and invalidates caches, then durably removes chunks and originals. In-flight jobs check document state/version before publishing, preventing deleted content from returning through a late worker result.

## 5. Data model and authorization

Tables: organizations, memberships, documents, document_versions, chunks, ingestion_jobs, conversations, messages, message_citations, usage_events, audit_events. Add collections/access rules only if department-level visibility is included in release scope.

Every tenant-owned row carries organization_id. Documents track uploader, access scope, status, active version, filename, MIME, storage path, size, and hash. Chunks carry content, full-text representation, vector, embedding identity, location metadata, and version ID. Citations reference actual retrieved chunks; filenames/links are resolved by the server rather than invented by the model.

Enable RLS across tenant data and private Storage. Retrieval must enforce membership and document visibility inside the database query, before vector/full-text candidate selection. User-facing database operations use the authenticated user's security context. Any privileged worker path explicitly checks organization/document scope; the service key never reaches the browser.

MVP roles: admin can upload/manage workspace documents; employee can read authorized documents and use chat. Conversation history is user-private by default. Source previews and downloads recheck access on every request. Use short-lived signed URLs and never let caches reuse results across users with different permissions.

## 6. Retrieval and grounded answers

Select one embedding model through OpenRouter's embeddings API during the initial configuration gate. Proposed default: openai/text-embedding-3-small if available for the account and suitable for the fixture corpus. Verify dimensions with a real response before creating the vector column/index. Generation model priorities do not replace the separate embedding requirement. Do not fail over embeddings into a different vector space; if unavailable, pause indexing and retry. Keep lexical search usable with a visible degraded-search indication.

Combine PostgreSQL full-text and pgvector similarity search using reciprocal-rank fusion. Start around 20 candidates from each, deduplicate, and select 6–10 diverse evidence chunks within a token budget. Adjust retrieval based on evaluation, especially policy identifiers, exact names, and code symbols. Supabase documents this hybrid-search architecture: https://supabase.com/docs/guides/ai/hybrid-search.

The answer prompt treats uploaded content as evidence, never as executable instructions. Answer from retrieved passages; abstain when support is missing; explain conflicts with effective dates when provided. Prior conversation helps resolve follow-up questions but does not replace source evidence.

Stream answer text with stable evidence IDs. Resolve those IDs to real citations and validate citation membership/access before finalizing. Validate important supported claims in a second pass when needed; suppress or qualify unsupported claims. This reduces hallucination but does not guarantee elimination. If no adequate evidence exists, return a clear abstention with useful search suggestions.

Evidence drawer: original filename/version, exact extract, highlighted passage, and page/slide/line/sheet locator, with authorized original access. Preview PDF pages where supported; DOCX uses paragraph references, CSV/XLSX show a table range, and code uses escaped text with line numbers. Show evidence coverage/quality labels; never present uncalibrated retrieval scores as a probability of correctness.

## 7. Exact OpenRouter routing

The public model catalog and endpoint lists were checked on October 9. All four requested IDs were listed; the requested providers were also listed. This is catalog verification, not account-level inference or latency verification. secrets.env exists; its contents were not displayed or used for a paid request.

| Priority | Model | Provider order |
| --- | --- | --- |
| 1 | z-ai/glm-5.3-flash | open-inference → deepinfra → relace → streamlake → novita |
| 2 | deepseek/deepseek-v4.1-flash | decart → morph → inference-net → sail-research → relace |
| 3 | openai/gpt-6-luna | openai → azure |
| 4 | qwen/qwen3.8-flash | OpenRouter automatic routing |

OpenInference's catalog endpoint uses the base slug open-inference, rather than openinference. Validate exact current provider/endpoint slugs at implementation startup.

Use an application routing adapter so each model receives its own provider policy. For the first three, use provider.order plus provider.only containing that model's requested list; keep within-list provider failover enabled. When eligible providers fail, advance to the next model. Do not use one shared provider policy across a multi-model fallback request. The final Qwen tier retains automatic routing subject to the organization's privacy settings. Reference: https://openrouter.ai/docs/guides/routing/provider-selection.

Apply modality and parameter eligibility checks before an attempt. Normalize parameters per model; omit unsupported temperature/reasoning/output controls. Verify DeepSeek image-to-text on actual selected endpoints during implementation. Use the same ordered chain for optional vision work, skipping endpoints incapable of accepting the request and logging why.

Fail over on transient network errors, rate limits, unavailable routes, and retryable upstream errors. Do not traverse the whole chain for an invalid key, exhausted account balance, malformed request, or insufficient source evidence. Bound each attempt and total request time, honor retry-after within that budget, and use a circuit breaker for repeatedly failing routes. Preserve configured priority among eligible healthy routes. No promise of sub-second failover.

Before output begins, an attempt can transparently switch models. After partial streaming, send a reset/error event and offer regeneration rather than concatenate different model answers. Record actual model/provider when available, latency, usage/cost, outcome, and fallback reason without logging secrets or full company documents.

Use OpenRouter privacy controls appropriate to the workspace, such as disallowing data collection and enforcing ZDR where required. These filters may remove preferred routes; show availability implications instead of silently relaxing privacy. Store the key only in Render's server secret settings. Exclude secrets.env from source control, ZIP, logs, and frontend bundles.

## 8. UI and judge demo

Build four focused screens: dashboard with useful suggested questions; document library with filters/status/retry; chat with streaming and clear evidence; workspace/team settings. Use readable typography, accessible focus/contrast, responsive layout, helpful empty states, and clear failure states. Dark/light themes follow after functional polish.

Provide a prominent Try Demo route backed by a public synthetic corpus and server-enforced read-only access. No judge signup is required. It cannot expose private organizations, mutate documents, or exhaust unrestricted inference budgets. Keep guest histories isolated by session and apply per-session/IP and global quotas.

Demo corpus: fictional HR PDF, travel-policy DOCX, expense CSV/XLSX, engineering Markdown, code sample, and scanned notice. Hero interaction: ask a question requiring two file formats, open exact evidence, compare conflicting policy versions, then ask an unsupported question to demonstrate abstention. The real admin flow also demonstrates uploading a fresh file and asking about it after ready status.

Pitch target: HR/IT/operations teams in growing companies. Describe measurable onboarding/search friction and the proposed SaaS pricing hypothesis. Measure timed tasks against manual document search; do not repeat the local rules file's unmeasured 80% reduction claim as a fact.

## 9. Deployment sequence

Supabase, Vercel, and Render MCP tools are not currently exposed in this session. Connect the authorized accounts during implementation and discover the actual capabilities then. Inventory the selected projects and deploy resources only within that scope. A GitHub repository and appropriate hosting permissions are also needed for the planned Git deployment flow.

1. Repository setup: ignore secrets.env before the first commit; secret scan; create example environment file; pin dependencies and Docker worker requirements.
2. Supabase: apply migrations, enable pgvector, create private bucket, deploy RLS/storage/retrieval/job functions, set Auth callback URLs, and seed the synthetic demo organization.
3. Render: deploy Docker-based FastAPI web service and background worker with database/OpenRouter secrets. Expose liveness and readiness endpoints; validate durable jobs across restarts and verify outbound API connectivity. Use a plan supporting the worker and sufficient OCR memory.
4. Vercel: deploy Next.js with only intended public Supabase URL/publishable key and API URL; configure production routing and final Auth redirects/CORS. No server secret gets a NEXT_PUBLIC name.
5. Live smoke test: login, upload, readiness, query, evidence, deletion, cross-tenant denial, fallback, and read-only demo in an incognito session.
6. Operations: capture request/job IDs, error rates, queue depth, indexing latency, model cost, and deployment version. Set daily spend/storage limits. Keep previous deployment and backward-compatible migration rollback/recovery notes.

For the judging period, choose an always-on API tier if budget permits. Render's free web service sleeps after 15 minutes idle and may take about a minute to resume: https://render.com/docs/free. Background workers are a separate service: https://render.com/docs/background-workers. Confirm account limits and costs before provisioning the chosen resources.

## 10. Delivery order and acceptance gates

Time estimates are engineering targets, dependent on staffing, access, and parser issues. Plan for October 9–10 implementation and verification, with a protected submission buffer on October 11. The screenshot says submissions are locked until October 11 while the local notes call October 11 the deadline; verify the actual opening/closing time and timezone. Do not assume midnight.

| Phase | Indicative effort | Exit gate |
| --- | --- | --- |
| Configuration and schema | 2–3 hours | Keys/account eligibility, auth, organization isolation, DB/storage/worker path verified |
| First deployed vertical slice | 4–6 hours | Live TXT/PDF upload → ready → answer → valid evidence on Vercel/Render |
| Broad ingestion and resilience | 5–7 hours | DOCX/CSV/XLSX/PPTX/code/image fixtures pass; worker retry/restart works |
| Retrieval, routing, evidence | 4–6 hours | Hybrid search, abstention, table calculations if included, per-model/provider failover verified |
| Product polish and demo | 3–4 hours | Read-only judge experience, upload errors, accessible UI, source drawer |
| Evaluation and submission artifacts | 3–4 hours | Live checks pass; public code, README, ZIP, pitch links verified |

Deploy the first working slice early; continue incremental deployments as capabilities pass gates. If time tightens, cut optional features before tenant isolation, accurate citations, durable ingestion, or the live core flow.

Proposed measured release gates:

- Fixture extraction tests cover every advertised format; corrupt/encrypted/unsupported files fail clearly; scanned OCR is validated against known text.
- At least 30 curated answerable questions, 10 unanswerable questions, plus conflict and table-calculation cases. Target ≥90% expected evidence retrieval and ≥90% correct abstention on this small corpus; report actual results and sample size.
- Every displayed citation resolves to a real accessible source location. Manually review groundedness; citation existence alone is insufficient.
- Automated cross-organization document, storage, search, source, cache, conversation, and download tests pass. Prompt-injection fixtures cannot expand access or execute tools.
- Routing tests inject 429/5xx/no-route failures and partial stream failures, verify order and reset semantics, and confirm unavailable privacy-compatible routes fail clearly. These tests do not require forcing real outages.
- Duplicate upload, worker termination, stale lease, reupload, and deletion-during-indexing tests pass.
- On representative small demo files, aim for text indexing under 60 seconds, first answer token under 5 seconds on a healthy preferred route, and normal answer completion under 20 seconds. Measure p50/p95; OCR and failover have separate published limits.
- Live smoke tests pass from an incognito browser; no secrets in bundle/logs/repository/ZIP; judge demo works without access requests.

## 11. Submission completion

Prepare a public GitHub repository with setup/architecture instructions, environment variable names, support matrix, known limits, deployment URLs, measured evaluation, and team contributions. Add all team collaborators/contributors. Create a project ZIP at or below 10 MB excluding dependencies, build artifacts, caches, .git, secrets, and real company documents. Upload it to Drive with anyone-with-link view permission.

Prepare a concise presentation covering problem, target customer, product flow, architecture, supported formats, trust/security, evidence-based differentiation, measured evaluation, market hypothesis, and roadmap. Publish with accessible permissions. Check repository, ZIP, presentation, and live app links in incognito. Leave video recording for later, as requested; submission is not fully complete until its mandatory accessible link is supplied.

Final definition of done: a judge can open the deployed demo, ask a cross-document question, inspect exact supporting evidence, observe an honest unsupported-answer response, and understand the business value; an administrator can upload new supported files and employees can securely query them end to end.
