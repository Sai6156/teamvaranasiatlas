# Release verification — October 9, 2026

Application: https://atlas-varanasi.vercel.app

API readiness: https://atlas-varanasi-api.onrender.com/health/ready

Repository: https://github.com/Sai6156/teamvaranasiatlas

- Production Next.js build and TypeScript checks passed; production frontend dependencies report zero known vulnerabilities in the npm audit performed for this release.
- 22 Python tests passed, covering supported format extraction, archive limits/traversal, authentication guards, model/provider failover, partial-stream failure, short-heading citation mismatch, and concise abstention.
- Live synthetic tests passed against the public Render API: authenticated workspace creation, email-bound invitation acceptance, employee upload denial, cross-organization document/source denial, duplicate detection, four indexed formats, authorized signed download, private conversations, and a two-document answer using GLM 5.3 Flash.
- The five-file fictional quickstart pack indexed successfully, including a PDF, DOCX, CSV, Markdown, and Python source. Last-admin removal and employee privilege escalation were denied.
- A real account was email-confirmed, a real user workspace was created, and its five example files reached ready status with no failures. User passwords and document contents were not printed for this check.
- Production browser QA confirmed login, workspace data, streaming responses, citation cards, and the exact PDF passage drawer.
- An observed multi-turn error linked a production-access claim to an onboarding heading. Historical assistant citation numbers are no longer reused as evidence; a conservative short-heading consistency guard was added. The live regression now cites the engineering passage, and an unsupported growth-rate question abstains without unrelated source cards.

Timing samples: the two-document query reported about 5.7 seconds for the server's question phase; the longer multi-turn citation regression reported about 9.5 seconds. These are small-sample measurements, not p95 results, end-to-end browser timings, or SLAs. Free Render hosting can introduce cold starts.

Current deployment runs the durable ingestion worker alongside FastAPI using RUN_WORKER=true. A separate paid worker and always-on API remain available as a scaling option. Public-repository Render deployments and Vercel CLI releases are currently deployed manually; installing the hosting GitHub integrations is required for automatic releases.

Supabase RLS and private Storage are enabled. The security advisor's signed-in SECURITY DEFINER warnings cover intentionally exposed RPCs with explicit membership/role checks. The ingestion job table intentionally has no user policies. Anonymous helper access was revoked. Compromised-password checking is not enabled on this project; this is distinct from password hashing, email verification, and workspace authorization.

The application does not guarantee semantic correctness from citation presence alone. Review evidence for important decisions. Exact whole-spreadsheet aggregation, Office embedded-image OCR, legacy Office formats, enterprise SSO, billing, and audio/video ingestion remain outside this release.
