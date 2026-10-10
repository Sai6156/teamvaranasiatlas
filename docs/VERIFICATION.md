# Release verification — October 10, 2026

Application: https://atlas-varanasi.vercel.app

API readiness: https://atlas-varanasi-api.onrender.com/health/ready

Repository: https://github.com/Sai6156/teamvaranasiatlas

## Email-code rollout — prepared, delivery setup pending

The email-code signup/reset screens and direct Brevo invitation delivery are implemented on `codex/brevo-email-codes`. They have not replaced production yet: Brevo rejects the provided API key from the development IP because that IP is not authorized. Sender discovery, delivery testing, and the final production rollout are pending that account configuration. The rate-limit migration is already applied and does not change existing login behavior.

The frontend production build and TypeScript checks pass, and 36 backend tests pass. A regression against the real Supabase project (capturing outbound email locally) verified: signup cannot log in before confirmation; invalid and reused codes fail; requesting another email within 60 seconds fails; an invitation cannot be accepted by another email or replayed; the correct invitee receives employee access; and recovery changes the password, rejecting the old one. All test accounts and the empty workspace were removed. This test does not establish Brevo inbox delivery. Supabase currently generates eight-digit email codes for this project.

New users follow invitation link → signup → email code → accept workspace. Existing verified users follow invitation link → password login → accept workspace. Invitations retain their email binding, seven-day expiry, and single-use behavior.

## Large-report and conversation update

The frontend changes are deployed on Vercel. Render is live on application commit `0f9790da6709ce3f28b25e3ff6e2ea8bbc556b96`.

Both original Reliance uploads were completely reindexed on the deployed worker: the BRSR has 51 physical PDF pages and 300 chunks; the integrated annual report has 146 physical pages and 1,340 chunks. Every physical page is represented. Double-page spreads retain their printed page labels. There is no combined 100-page cutoff. Native text and structured tables are extracted with PyMuPDF; scanned pages use OCR. Indexing progress is visible per document.

The deployed API was evaluated against isolated copies of both full reports, including every chunk and vector. Expected answers were used only as test oracles, never injected into retrieval or model prompts. All ten individual responses passed their requested-field checks. The combined ten-question response completed in 49.16 seconds with every requested substantive field, after manual source review:

| Question | Verified result |
|---|---|
| Largest product/service | Exact petroleum-product description; NIC 19201; 65.02% |
| Related parties | Purchases 40.77%; sales 57.02%; investments 64.87% |
| ESG investment | R&D 36.64%; capex 63.36% |
| Payables | FY2024-25: 101 days; FY2023-24: 100 days |
| Differently abled | Employees 13; workers 24; requested combined count 37; female 2 |
| Safety | Recordable injuries 14 employees / 31 workers; high-consequence injuries 0 / 0 |
| ESG committee | Hital R. Meswani, chairman/executive; P. M. S. Prasad, member/executive; Arundhati Bhattacharya, member/independent |
| Female turnover | Employees 18%, 19%, 20%; workers 25%, 21%, 12%, in the requested year order |
| Plastics and POY | Recycled 29,464 MT; safely disposed 33,400 MT; POY reclaimed 73% |
| Locations and exports | Plants 15 national + 0 international = 15; offices 62 + 2 = 64; 108 export countries |

Source-spelling caveat: the BRSR itself prints “Arundhati Bhattacharaya.” The combined answer faithfully uses that spelling; the standalone answer uses “Bhattacharya.” The original strict spelling oracle therefore scored the combined response 9/10. The documented source-supported spelling exception scores it 10/10 substantive responses; it does not modify production answers. This is a fixed ten-question regression, not a general accuracy guarantee. Individual complete-response times were 13.41–23.47 seconds in this run; free hosting cold starts and provider latency can add time.

Production browser checks used 22 conversations: every conversation was accessible through the scrollable sidebar and searchable history, and searching/selecting an older conversation worked. An 8,302-character, 90-line draft was preserved between the inline and expanded editors. Ctrl+Home/Ctrl+End navigated the complete draft, and clipboard readback exactly matched the full draft, including its final marker.

The updated production frontend build and TypeScript checks passed. All 32 backend tests passed, including per-question evidence preservation, bounded batch concurrency, complete PDF extraction, and source-verified category totals. Temporary verification workspaces and accounts are removed after retaining private local evidence. The original company workspace and both uploaded reports are preserved.

## Earlier release checks

- Production Next.js build and TypeScript checks passed; production frontend dependencies report zero known vulnerabilities in the npm audit performed for this release.
- 22 Python tests passed, covering supported format extraction, archive limits/traversal, authentication guards, model/provider failover, partial-stream failure, short-heading citation mismatch, and concise abstention.
- Live synthetic tests passed against the public Render API: authenticated workspace creation, email-bound invitation acceptance, employee upload denial, cross-organization document/source denial, duplicate detection, four indexed formats, authorized signed download, private conversations, and a two-document answer using GLM 5.3 Flash.
- The five-file fictional quickstart pack indexed successfully, including a PDF, DOCX, CSV, Markdown, and Python source. Live PNG OCR and image-only PDF OCR also passed with the local worker stopped, verifying the Render processing path. Last-admin removal and employee privilege escalation were denied.
- A real account was email-confirmed, a real user workspace was created, and its five example files reached ready status with no failures. User passwords and document contents were not printed for this check.
- Production browser QA confirmed login, workspace data, streaming responses, citation cards, and the exact PDF passage drawer.
- An observed multi-turn error linked a production-access claim to an onboarding heading. Historical assistant citation numbers are no longer reused as evidence; a conservative short-heading consistency guard was added. The live regression now cites the engineering passage, and an unsupported growth-rate question abstains without unrelated source cards.

Timing samples: the two-document query reported about 5.7 seconds for the server's question phase; the longer multi-turn citation regression reported about 9.5 seconds. These are small-sample measurements, not p95 results, end-to-end browser timings, or SLAs. Free Render hosting can introduce cold starts.

Current deployment runs the durable ingestion worker alongside FastAPI using RUN_WORKER=true. A separate paid worker and always-on API remain available as a scaling option. Public-repository Render deployments and Vercel CLI releases are currently deployed manually; installing the hosting GitHub integrations is required for automatic releases.

Supabase RLS and private Storage are enabled. The security advisor's signed-in SECURITY DEFINER warnings cover intentionally exposed RPCs with explicit membership/role checks. The ingestion job table intentionally has no user policies. Anonymous helper access was revoked. Compromised-password checking is not enabled on this project; this is distinct from password hashing, email verification, and workspace authorization.

The application does not guarantee semantic correctness from citation presence alone. Review evidence for important decisions. Exact whole-spreadsheet aggregation, Office embedded-image OCR, legacy Office formats, enterprise SSO, billing, and audio/video ingestion remain outside this release.
