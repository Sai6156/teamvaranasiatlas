# TriCity AI Hackathon — Official Rules, Guidelines & Evaluation Criteria

> **Event**: TriCity AI Hackathon  
> **Team**: Team Varanasi  
> **Submission Deadline Lock**: October 11th  

---

## 📌 1. Problem Statement & Idea (Locked)

### Problem Statement
> **"Let companies upload internal documents and allow employees to ask questions across the knowledge base."**

### Proposed Idea *(Visible to Judges)*
> *"We want to build a simple AI assistant that helps employees quickly find information in company documents. Companies can upload PDFs, policies, manuals, and other files, and employees can ask questions in plain English to get relevant answers with links to the original sources. The goal is to save time, reduce the effort of searching through documents, and make company information easier to access securely."*

### Approved Tech Stack *(Locked)*
* **Frontend**: Next.js
* **Backend**: Python (FastAPI)
* **Database**: Supabase DB (PostgreSQL + pgvector)
* **Auth**: Supabase Auth

---

## 🏆 2. Evaluation Criteria & Judging Rubric (100% Total)

Your project will be evaluated across six weighted areas. Every aspect of the build must map to these criteria:

| # | Criterion | Weight | Organizers' Description | Strategic Action for Team Varanasi |
| :---: | :--- | :---: | :--- | :--- |
| **01** | **Working MVP** | **30%** | *"The core flow must work live."* | Complete live end-to-end pipeline: Document upload $\rightarrow$ Text chunking & Vector indexing $\rightarrow$ Querying $\rightarrow$ Streaming response with source citations. |
| **02** | **AI/SaaS Relevance** | **20%** | *"AI must meaningfully improve the solution."* | RAG grounded strictly in uploaded documents to eliminate hallucinations; real-world B2B SaaS architecture. |
| **03** | **UI/UX** | **15%** | *"The product should be clear and demo-friendly."* | High-end Next.js UI, dark/light theme, drag-and-drop file upload, real-time status badges, interactive citation cards. |
| **04** | **Market Potential** | **15%** | *"Clear target user and business value."* | Solves corporate knowledge fragmentation; reduces employee onboarding & HR/IT policy search time by 80%. |
| **05** | **Innovation** | **10%** | *"Fresh thinking or strong execution."* | Clickable page citations with drawer preview of exact text; query confidence scores; multi-provider sub-second failover. |
| **06** | **Demo & Pitch** | **10%** | *"Clear explanation of problem, solution and future scope."* | High-energy 2-minute demo video and clear 10-slide deck explaining the business value and future roadmap. |

---

## 📦 3. Required Deliverables & Submission Rules

> [!CAUTION]
> **CRITICAL SUBMISSION WARNING**:  
> *"If judges cannot access your links, your team will receive a score of zero. Make sure links are accessible to anyone with the link. Judges cannot access private files."*

### Deliverables Checklist

#### 1. Source Code (GitHub URL) — Mandatory
* **Public Visibility**: The repository **MUST be set to Public**.
* **Team Collaborators**: All team members **MUST** be added as collaborators or contributors to verify individual participation.
* **Detailed `README.md`**: Must explain how to install dependencies and run the project locally.

#### 2. Project ZIP (Google Drive Link) — Mandatory
* **Size Limit**: Keep the ZIP **at or below 10 MB**.
* **Clean Codebase**: Strictly exclude bulky dependencies and generated folders:
  * Exclude `node_modules/`, `.next/`, `venv/`, `.venv/`, `__pycache__/`, `.git/`.
* **Permissions**: Google Drive sharing permissions **MUST** be set to:  
  👉 **"Anyone with the link can view"** (Verify in an Incognito window!).

#### 3. Presentation (Link) — Mandatory
* Link to Google Slides, Canva, or hosted PDF.
* Permissions **MUST** be set to:  
  👉 **"Anyone with the link can view"**.

#### 4. 2-Minute Demo Video (Link) — Mandatory
* Uploaded to **YouTube** or **Loom** (or Google Drive).
* Privacy setting: **Public** or **Unlisted** (Private videos will receive a zero).
* **Length Rule**: Concise demo; **MUST NOT exceed 4 minutes** (target is ~2 minutes).

#### 5. Live Product Deployment (Link) — Highly Recommended
* *"While not strictly mandatory, deploying your project live (via Vercel, Render, Netlify, etc.) is highly recommended and carries extra weight during evaluation."*
* **Frontend**: Vercel (`https://your-project.vercel.app`)
* **Backend**: Render (`https://your-backend.onrender.com`)

---

## 📜 4. General Hackathon Rules

1. **Fresh Code**:
   * All core code, design, and assets must be created during the hackathon.
   * Using open-source boilerplates and APIs is permitted, but the main logic must be original.
2. **Strict Deadlines**:
   * The submission portal will lock exactly at the deadline (October 11th).
   * Late submissions will not be evaluated under any circumstances.
3. **Originality**:
   * Plagiarism will lead to immediate disqualification. Build something original that solves the problem statement uniquely.
4. **Team Conduct**:
   * Treat everyone with respect. Harassment of any kind towards participants, mentors, or judges will result in immediate disqualification.
5. **Equipment Responsibility**:
   * Take care of laptops, chargers, and personal belongings. Organizers are not responsible for lost or damaged items.

---

## 🛡️ 5. Event Code of Conduct

### ✅ Do's for Students
* Carry your valid ID and keep your participant QR ready at all times.
* Use only approved hackathon zones and follow volunteer instructions immediately.
* Maintain discipline during coding hours, mentor sessions, and overnight slots.
* Keep your workspace clean and use campus infrastructure responsibly.
* Report safety issues, health concerns, or suspicious activity to organizers without delay.
* Respect fellow teams, jury members, and campus residents in words and actions.

### ❌ Don'ts for Students
* Do not enter hostels, labs, offices, or any restricted areas.
* Do not share, forge, or misuse participant credentials or QR cards.
* Do not create noise, disruptions, or behavior that disturbs the campus environment.
* Do not litter, damage furniture/equipment, or misuse common facilities.
* Do not bypass check-in, verification, or security processes at any point.
* Do not engage in misconduct, harassment, or any non-compliant activity.

---

## 🔍 6. Pre-Submission Verification Checklist

Before clicking **Final Submit**:
- [ ] Open an **Incognito / Private browser window** and open:
  - [ ] GitHub repository URL (is it public? are all files visible?)
  - [ ] Google Drive ZIP link (downloads without login?)
  - [ ] Presentation link (opens without requesting access?)
  - [ ] Video link (plays cleanly without login?)
  - [ ] Live Vercel frontend URL (loads and can test a query?)
- [ ] Check video duration (under 4 minutes, ideally 2 minutes).
- [ ] Check ZIP file size (strictly under 10 MB).
