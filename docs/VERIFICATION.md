# Verification

## Reproducible checks

```bash
python -m pytest
npm run build
npm run typecheck
```

The current baseline has 51 passing backend tests covering extraction, archive limits, isolated parsing, authorization, invitations/email codes, retrieval, grounding, and model/key routing. Frontend production build and TypeScript checks pass. CI repeats these checks without production credentials.

`scripts/live_verify.py` and `scripts/cleanup_qa.py` support explicit integration testing on a dedicated project. Live checks create accounts/workspaces and may send email or consume API credit; they are not part of CI.

## Observed live checks

- Ten public demo companies with three indexed files each and original-source links.
- Organization isolation, employee write denial, private conversations, and authenticated source access.
- Brevo signup/recovery codes and email-bound invitations.
- Desktop/mobile navigation, compact short-screen chat, evidence previews, and reduced-motion support.
- Separate-key free fallback with the primary key exhausted. Apodex returned answers; Nemotron could not route under the account's free-model data policy.

These checks are individual observations, not uptime or latency guarantees.

## Answer-quality review

A targeted 20-question review across all ten companies compared answers with returned passages and independently recomputed arithmetic. Every request completed without API errors on the free fallback: 10 passes, 8 partial results, and 2 material failures.

Partial results involved rounding, citation alignment, reporting-basis ambiguity, unsupported explanations, and contradictory statements about evidence. Material failures substituted the wrong HCLTech revenue classification and labeled Alphabet quarterly revenue as a full-year result.

This sample is not a general accuracy benchmark. Important financial or policy decisions require source review. Deterministic arithmetic and stronger claim-to-passage verification remain development priorities.
