# Setup and operations

## Requirements

Node.js 24, Python 3.12, Git, a dedicated Supabase project, OpenRouter credentials, and a Brevo API key with a verified sender. OCR additionally requires Tesseract and Poppler; the Docker image installs them.

## Windows Command Prompt

Extract the ZIP and open Command Prompt in `atlas-hackathon-codebase`.

```cmd
npm ci
py -3.12 -m venv .venv
.venv\Scripts\activate
python -m pip install -r services\api\requirements.txt
copy apps\web\.env.example apps\web\.env.local
```

The archive supplies a blank `secrets.env`. Fill it locally. For a Git clone, first run `copy secrets.env.example secrets.env`.

Terminal 1:

```cmd
.venv\Scripts\activate
cd services\api
python -m uvicorn atlas.main:app --host 127.0.0.1 --port 8000
```

Terminal 2, from the project root:

```cmd
.venv\Scripts\activate
cd services\api
python -m atlas.worker
```

Terminal 3, from the project root:

```cmd
npm run dev
```

Open http://localhost:3000. API documentation is at http://127.0.0.1:8000/docs.

## macOS and Linux

```bash
npm ci
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r services/api/requirements.txt
cp apps/web/.env.example apps/web/.env.local
# For a Git clone only:
cp secrets.env.example secrets.env
```

Use the same API, worker, and frontend start commands. Activate `.venv` in both Python terminals. Do not start a separate worker when `RUN_WORKER=true` already starts one in the API process.

## Configuration

Set the browser's `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`, and `NEXT_PUBLIC_API_URL` in `apps/web/.env.local`. The local API URL is http://127.0.0.1:8000.

Set server configuration in root `secrets.env` or `services/api/.env`. Start the API from `services/api` so its configuration loader can find the root file. Never put `SUPABASE_SECRET_KEY`, OpenRouter keys, or `BREVO_API_KEY` in public frontend settings.

The primary OpenRouter key handles embeddings and paid answers. `OPENROUTER_FREE_API_KEY` serves only zero-price free-model answer routes. Both accounts remain subject to provider availability, privacy settings, and quotas.

## Supabase bootstrap

For a new project, apply all files in `supabase/migrations` in filename order, beginning with `001_atlas.sql`. The initial migration creates the `company-documents` private bucket and database objects. Verify each migration succeeds before continuing. Do not reapply migrations to the deployed project.

Keep email confirmation enabled and set the minimum password length to 12. Set the Auth Site URL to http://localhost:3000. Allow:

```text
http://localhost:3000/auth/callback
http://localhost:3000/reset-password
```

Use equivalent production-origin URLs for deployment. Configure `BREVO_API_KEY`, a verified `BREVO_SENDER_EMAIL`, and `BREVO_SENDER_NAME`. Atlas delivers Supabase-generated signup/recovery codes through Brevo. Authorize the server's outbound IPs if your Brevo account restricts API access. Supabase custom SMTP can still serve other native Auth email flows.

## Deployment

Vercel uses root `apps/web` and the public frontend variables. Render uses `services/api/Dockerfile`, with Docker context `services/api`. `render.yaml` contains environment-variable names without secret values. `RUN_WORKER=true` runs ingestion inside the API service for the current small deployment.

Set `FRONTEND_URL` and `ALLOWED_ORIGINS` to the exact frontend origin. API liveness is `/health/live`; readiness is `/health/ready`. Apply compatible migrations before deploying the backend.

## Default limits

25 MB/file; 1,500 PDF pages; 200 OCR pages; 100,000 spreadsheet/table rows; 8,000 chunks/file; 200 documents and 500 MB/workspace; 200 questions/workspace/day. ZIP uploads allow 100 members and 75 MB expanded content. Nested/encrypted archives, unsafe paths, and executable formats are rejected. XLSX reads saved values instead of recalculating formulas.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Configuration screen | Frontend/server environment files; restart after editing |
| Email code missing | Brevo key, verified sender, and authorized outbound IPs |
| Upload stays queued | Worker process or `RUN_WORKER` |
| Paid key is exhausted | Dedicated free key; existing documents can use keyword search |
| Free route fails | OpenRouter privacy policy, quotas, and provider capacity |
| Demo list empty | Seed this Supabase project; see `demo-data/README.md` |
| Original link expired | Request a fresh source link in Atlas |
