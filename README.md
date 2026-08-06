# AdaptOBE

**An Intelligent Outcome-Based Education (OBE) Attainment & Adaptive Learning Platform.**

AdaptOBE automates three things academic departments normally do by hand: matching Course Learning Outcomes to Programme Learning Outcomes with AI, calculating direct attainment from assessment scores, and giving faculty a real-time, live-updating view of how their class is actually performing against those outcomes.

Built as a Final Year Project for the Department of Computer Science, UBIT (Umaer Basha Institute of Information Technology).

---

## What it does

- **AI-powered CLO → PLO mapping.** CLO and PLO descriptions are embedded with a sentence-transformer model; matches are ranked by cosine similarity instead of manual, subjective judgment. Faculty confirm every AI suggestion — the system never maps outcomes on its own.
- **Direct attainment engine.** Turns raw scores into CLO/PLO attainment percentages, with every edge case handled explicitly: absent students count as zero (not excluded), zero-denominator CLOs return 0.00% instead of crashing, and every score edit triggers an automatic recalculation.
- **Real-time faculty dashboard.** A CLO × PLO heatmap that updates live over WebSockets — enter a score in one tab, watch the dashboard update in another with no refresh.
- **One-click reporting.** PDF and Excel export of the full attainment report, styled to match the dashboard.
- **Role-based access control** end to end — Admin, Faculty, and Student scopes enforced on every API endpoint, not just hidden in the UI.

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+, FastAPI (fully async) |
| Database | PostgreSQL 18 + [pgvector](https://github.com/pgvector/pgvector) |
| ORM / Migrations | SQLAlchemy 2.0 (AsyncSession) + Alembic |
| Auth | JWT (`python-jose`) + bcrypt |
| AI / ML | PyTorch + `sentence-transformers` (`all-MiniLM-L6-v2`) |
| Frontend | React.js (JavaScript, no TypeScript) + TailwindCSS v4 |
| Real-time | Native FastAPI WebSockets |
| Reporting | ReportLab (PDF), openpyxl (Excel) |
| Testing | pytest, pytest-asyncio, httpx — 165 automated backend tests |

## Project status

Modules 0–4 are implemented, tested, and demo-verified: auth/RBAC, institutional data management, course/CLO/PLO management with AI mapping, assessments and the attainment engine, and the real-time dashboard. ML-based risk prediction (Module 5), the student portal (Module 6), and containerized deployment (Module 7) are planned next.

For the full breakdown of what's built vs. what's left, see **[HANDOFF.md](HANDOFF.md)**.

---

## Quick Start

### Prerequisites
- PostgreSQL 18, running locally
- **pgvector extension.** There's no official Windows binary — on Windows it has to be built from source with MSVC (Visual Studio Build Tools, C++ workload). See [HANDOFF.md §3](HANDOFF.md#3-local-development-setup) for the full walkthrough if you're setting this up on a new machine.
- Python 3.11+ and Node.js 18+

### 1. Clone and configure environment variables

```bash
git clone https://github.com/zawadAli/AdaptOBE.git
cd AdaptOBE
```

**Neither `backend/.env` nor `frontend/.env` is committed to this repo** — they contain real database credentials and secrets, so they're gitignored on purpose. Before anything will run, copy the example files and fill in your own values:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

In `backend/.env`, set:
- `DATABASE_URL` — your local Postgres connection string, e.g. `postgresql+asyncpg://adaptobe_user:<password>@localhost:5432/adaptobe`
- `JWT_SECRET_KEY` — generate a fresh one, don't reuse an example value:
  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(48))"
  ```

`frontend/.env` just needs `VITE_API_BASE_URL` pointed at your backend (defaults to `http://localhost:8000`, fine for local dev as-is).

### 2. Set up the database

```sql
CREATE ROLE adaptobe_user WITH LOGIN PASSWORD '<pick one>';
CREATE DATABASE adaptobe OWNER adaptobe_user;
```

### 3. Backend

```bash
cd backend
python -m venv venv
venv\Scripts\Activate.ps1        # Windows PowerShell
# source venv/bin/activate       # macOS/Linux

pip install -r requirements.txt
alembic upgrade head             # builds the schema, including CREATE EXTENSION vector

python scripts/seed_admin.py --email admin@yourdomain.edu --password YourPass123 --full-name "Admin"
python scripts/seed_ubit_data.py # seeds the department, 4 programmes, 40 PLOs with real embeddings

uvicorn app.main:app --reload --port 8000
```

API docs: `http://localhost:8000/docs`. Health check: `http://localhost:8000/api/v1/health/db` should return `{"pgvector_enabled": true}`.

### 4. Frontend

```bash
cd frontend
npm install
npm run dev
```

Runs at `http://localhost:5173`, logs in against the backend above.

---

## Running tests

```bash
cd backend
pytest -v
```

165 tests across three tiers: pure math unit tests (the attainment formulas, no database), service/engine integration tests (real but transactionally-rolled-back Postgres), and full API/RBAC tests. All must pass before a module is considered done — see [HANDOFF.md §8](HANDOFF.md#8-testing).

## Project structure

```
backend/
  app/
    models/      SQLAlchemy ORM models
    schemas/     Pydantic v2 request/response schemas
    routers/     FastAPI route handlers (thin — no business logic)
    services/    Business logic: attainment math, AI mapping, RBAC-aware CRUD
    ml/          Embedding generation (sentence-transformers)
    core/        Config, JWT/security, dependencies, institutional constants
  alembic/       Database migrations
  scripts/       Bootstrap admin + UBIT institutional data seed scripts
  tests/         165 automated tests
frontend/
  src/
    api/         Fetch wrappers per resource
    components/  Reusable UI + design-system primitives
    context/     AuthContext (React Context, no external state library)
    pages/       Route-level pages (login, dashboard, admin, courses, ...)
docs/
  SDD.md               Software Design Document with 5 verified architecture/UML diagrams
  AdaptOBE_SDD.pdf     Print-ready version of the same
```

## Documentation

- **[CLAUDE.md](CLAUDE.md)** — the governing project specification: full API catalog, database schema, attainment formulas, AI/ML specs, and the complete modular roadmap.
- **[HANDOFF.md](HANDOFF.md)** — developer handoff for continuing work from Module 5 onward: setup details, schema reference, codebase conventions, and known gotchas.
- **[docs/SDD.md](docs/SDD.md)** — Software Design Document with system architecture, use case, ER, AI-sequence, and workflow-activity diagrams.
