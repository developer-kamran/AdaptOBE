# AdaptOBE — Developer Handoff

**You are picking up development starting at Module 5.** This document exists so you (and your Claude Code session) have full context without needing to reverse-engineer the codebase or ask the previous developer questions. Read this top to bottom before writing code — it's written in order, high-level first, details later, exactly so a fresh AI session can load it and be immediately productive.

If you're using Claude Code: **point it at this file first** (`Read HANDOFF.md`) before asking it to build anything. It contains the same architectural conventions the project's `CLAUDE.md` enforces, plus everything `CLAUDE.md` *doesn't* say because it only became true as the project was actually built.

---

## Table of Contents

1. [What This Project Is](#1-what-this-project-is)
2. [Architecture at a Glance](#2-architecture-at-a-glance)
3. [Local Development Setup](#3-local-development-setup)
4. [Database Schema Reference](#4-database-schema-reference)
5. [What's Already Built (Modules 0–4)](#5-whats-already-built-modules-04)
6. [What You're Building: Module 5 and Beyond](#6-what-youre-building-module-5-and-beyond)
7. [Codebase Conventions — Read Before You Write Code](#7-codebase-conventions--read-before-you-write-code)
8. [Testing](#8-testing)
9. [Known Gotchas & Non-Obvious Decisions](#9-known-gotchas--non-obvious-decisions)
10. [Current Repo State & Demo Data](#10-current-repo-state--demo-data)
11. [Command Cheat Sheet](#11-command-cheat-sheet)

---

## 1. What This Project Is

**AdaptOBE** is an Intelligent Outcome-Based Education (OBE) Attainment & Adaptive Learning Platform, built as a Final Year Project for the Department of Computer Science, UBIT (Umaer Basha Institute of Information Technology).

It automates three things academic departments normally do by hand:
1. **CLO → PLO mapping** — matching Course Learning Outcomes to Programme Learning Outcomes using NLP sentence embeddings (semantic similarity), not keyword matching or manual spreadsheets.
2. **Direct attainment calculation** — turning raw assessment scores into standardized CLO/PLO attainment percentages, with every edge case (absent students, zero-denominator CLOs, threshold flagging) handled explicitly and tested.
3. **Real-time reporting** — a live faculty dashboard (WebSocket-powered) plus one-click PDF/Excel export for accreditation.

**The governing spec is [`CLAUDE.md`](CLAUDE.md) in the repo root.** That file is the original project specification — tech stack, database schema, API catalog, math formulas, the full modular roadmap (Modules 0–7), and the fixed institutional data (UBIT department, 4 programmes, 10 PLOs). Read it once; this handoff assumes you have.

**For diagrams** (system architecture, use cases, ER diagram, AI mapping sequence, attainment/WebSocket activity flow), see [`docs/SDD.md`](docs/SDD.md) (renders live on GitHub) or [`docs/AdaptOBE_SDD.pdf`](docs/AdaptOBE_SDD.pdf) (print-ready). Both were generated from and verified against the actual codebase — they are not aspirational.

---

## 2. Architecture at a Glance

```
React 19 SPA (Vite + Tailwind v4)
        |  HTTPS REST (Bearer JWT)  +  WSS (?token= query param)
        v
FastAPI (fully async) — Routers → Services → SQLAlchemy models
        |
        +--> PostgreSQL 18 + pgvector (relational data + vector(384) columns, same DB)
        +--> sentence-transformers (all-MiniLM-L6-v2, PyTorch) — CLO/PLO embeddings
        +--> native FastAPI WebSockets — real-time dashboard push
        +--> ReportLab / openpyxl — PDF / Excel export
```

**The one architectural rule that matters most:** routers contain *no business logic*. They translate HTTP ↔ Pydantic schemas and convert typed service exceptions (`NotFoundError`, `ConflictError`, `PermissionDeniedError`, `ValidationError`) into HTTP status codes. All actual logic — math, AI matching, validation — lives in `app/services/*.py`, which is what makes it independently unit-testable with zero HTTP or DB mocking. **Follow this pattern for Module 5.** Your XGBoost training/inference code belongs in `app/ml/`, called from a new `app/services/risk_service.py`, called from a thin `app/routers/ml.py`.

Tech stack (full list in `CLAUDE.md` §2):
Python 3.11+, FastAPI, PostgreSQL 18 + pgvector, SQLAlchemy 2.0 (AsyncSession) + Alembic, Pydantic v2, JWT (`python-jose`) + bcrypt, PyTorch + `sentence-transformers`, React.js (JavaScript only, **no TypeScript**) + TailwindCSS v4, native WebSockets, ReportLab + openpyxl.

---

## 3. Local Development Setup

### Prerequisites already handled by the previous developer (do once, on a fresh machine)
- PostgreSQL 18 installed locally, running as a Windows service.
- **pgvector extension built from source and installed.** There is no official pgvector Windows binary — it had to be compiled with MSVC (Visual Studio Build Tools, C++ workload) against PG18's headers and manually copied into `Program Files\PostgreSQL\18\lib` and `...\share\extension` (both require admin rights to write to). If you're setting this up on a **new machine**, budget real time for this step — it's the single most annoying part of the whole setup. `CREATE EXTENSION vector;` will fail with "could not open extension control file" until this is done.

### Backend

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Copy `backend/.env.example` to `backend/.env` and fill in real values:
```
DATABASE_URL=postgresql+asyncpg://adaptobe_user:<password>@localhost:5432/adaptobe
JWT_SECRET_KEY=<generate one: python -c "import secrets; print(secrets.token_urlsafe(48))">
```
You'll need a Postgres role/database. If starting fresh:
```sql
CREATE ROLE adaptobe_user WITH LOGIN PASSWORD '<pick one>';
CREATE DATABASE adaptobe OWNER adaptobe_user;
```

Then:
```powershell
alembic upgrade head                 # builds the full schema, including CREATE EXTENSION vector
python scripts/seed_admin.py --email admin@yourdomain.edu --password YourPass123 --full-name "Admin"
python scripts/seed_ubit_data.py     # seeds department, 4 programmes, 40 PLOs with real embeddings
uvicorn app.main:app --reload --port 8000
```
API docs at `http://localhost:8000/docs`. Health check: `http://localhost:8000/api/v1/health/db` should return `{"pgvector_enabled": true}`.

### Frontend

```powershell
cd frontend
npm install
npm run dev
```
Runs at `http://localhost:5173`. Backend CORS is hardcoded to allow exactly this origin in dev (`backend/.env` → `CORS_ORIGINS`).

### Running both together
Two terminals, backend first (frontend's login page will just show network errors until the API is reachable). No Docker yet — that's Module 7.

---

## 4. Database Schema Reference

Full ER diagram: `docs/SDD.md` §5 / `docs/AdaptOBE_SDD.pdf` Diagram 3. Quick reference table:

| Table | Purpose | Key relationships |
|---|---|---|
| `users` | All accounts (admin/faculty/student) | — |
| `departments` | Single row today: UBIT | → `programs` |
| `programs` | 4 fixed rows: BSSE/BSCS/BSAI/BSDS | `dept_id` FK; → `plos`, `courses` |
| `plos` | **40 rows** — 10 standard outcomes × 4 programmes (per-programme, not shared) | `program_id` FK; `embedding vector(384)` |
| `courses` | Faculty-owned | `program_id`, `owner_faculty_id` FKs |
| `clos` | Course Learning Outcomes | `course_id` FK (CASCADE); `embedding vector(384)` |
| `clo_plo_mappings` | Confirmed CLO→PLO links | `UNIQUE(clo_id, plo_id)`; `strength` 1–3 CHECK |
| `assessments` | Quiz/assignment/lab/midterm/final | `course_id` FK (CASCADE) |
| `questions` | Tagged to a CLO (nullable) | `clo_id` FK **SET NULL** on delete — see §9 |
| `student_scores` | Raw marks | `UNIQUE(question_id, student_id)` |
| `course_enrollments` | Roster | `UNIQUE(course_id, student_id)` |
| `attainment_records` | **Derived data** — wiped and rebuilt on every recalculation, never patched | `UNIQUE(student_id, course_id, clo_id)` |

For Module 5 (ML risk prediction), `CLAUDE.md` §6 specifies a `student_predictions` table (not yet created — you'll add it via a new Alembic migration):
```
student_predictions: id (PK), student_id (FK), course_id (FK), risk_level (ENUM: low/medium/high),
                      confidence_score, predicted_score, shap_explanation (JSONB)
```
The exact SHAP JSON schema you must produce is in `CLAUDE.md` §9 — copy it exactly, it's load-bearing for anything that consumes this later (e.g. a future dashboard widget).

---

## 5. What's Already Built (Modules 0–4)

All of the below is implemented, tested (165 passing backend tests), and has a real frontend UI — not just API endpoints.

| Module | What's in it |
|---|---|
| **0** | Postgres 18 + pgvector, async FastAPI/SQLAlchemy skeleton, Alembic |
| **1** | JWT auth (access+refresh), bcrypt, RBAC middleware, Admin CRUD for users/departments/programmes |
| **2** | Course/CLO/PLO management, the AI semantic mapping engine (`mapping_service.py`) |
| **3** | Assessments, questions, bulk scoring, the direct attainment engine (`attainment_math.py` + `attainment_service.py`) |
| **4** | Faculty dashboard (CLO×PLO heatmap), native WebSocket live updates, PDF/Excel export |
| *(unnumbered)* | UBIT institutional data seed script (idempotent), full frontend UI for Modules 1–3 (Admin panel, course authoring, AI mapping modal, score-entry grid) |

**Frontend routes that exist today:** `/login`, `/dashboard`, `/admin` (admin-only), `/courses`, `/courses/:id`, `/courses/:id/assessments/:id`. There is **no student-facing route** — student accounts exist and can log in, but hit "no access" on every current page. That's Module 6, not built yet.

---

## 6. What You're Building: Module 5 and Beyond

Straight from `CLAUDE.md` §10, in order:

### Module 5 — ML Risk Prediction & Learning Gap Detection (your starting point)
- Train/integrate an **XGBoost** classifier predicting student risk level (`low`/`medium`/`high`) per course.
- **Feature schema is fixed** (`CLAUDE.md` §9) — five numeric features, each 0.0–100.0: `attendance_percentage`, `quiz_average_percentage`, `assignment_average_percentage`, `midterm_score_percentage`, `current_avg_clo_attainment`. Requires ≥5 assessment records per student.
- Integrate **SHAP** for feature-level explainability — every prediction must return both a classification and the SHAP payload, in the exact JSON schema in `CLAUDE.md` §9.
- Automated detection of CLOs performing below the configurable threshold (the `course.attainment_threshold` column already exists and is used by the attainment engine — reuse it, don't reinvent).
- New endpoint per the catalog: `POST /api/v1/ml/predict-risk/{course_id}` (Faculty).

**Where does `attendance_percentage` come from?** There is currently no attendance table or endpoint anywhere in the schema. You'll need to decide: add an `attendance` table + CRUD, or treat it as a manually-entered/estimated input for now. This is a real gap in the current implementation — flagging it explicitly so you don't spend an hour searching for code that doesn't exist.

### Module 6 — Student Web Portal & Adaptive Learning
- Student Dashboard (`.jsx`) showing personal CLO attainment breakdown and score history. The backend endpoint `GET /api/v1/student/progress` is in the catalog but **not implemented yet** — you'll build both the endpoint and the page.
- Automated learning-gap alerts for weak CLOs.
- Adaptive quiz generator scaling difficulty to per-student CLO performance.
- Frontend: add `/student/*` routes, gated `roles={['student']}` in `ProtectedRoute`, and a student-facing nav section in `Navbar.jsx` (currently only renders links for `faculty`/`admin`).

### Module 7 — Production Containerization & Deployment
- Dockerfiles for backend (Python/FastAPI) and frontend (React static build).
- Production `docker-compose.yml` bundling FastAPI + PostgreSQL(+pgvector) + frontend serving.
- **Nothing Docker-related exists yet on purpose** — `CLAUDE.md` explicitly deferred it to keep local module development simple. Don't add Docker files before this module.

---

## 7. Codebase Conventions — Read Before You Write Code

These aren't suggestions; the existing 165 tests and every reviewed decision in this project follow them. Breaking them will make your Module 5 code visibly inconsistent with everything around it.

1. **Async everywhere.** Every DB call uses SQLAlchemy `AsyncSession`. Never a blocking call inside an `async def` route or service function. XGBoost training/inference is itself CPU-bound and synchronous — offload it with `asyncio.to_thread(...)`, exactly like `app/ml/embeddings.py` already does for sentence-transformer encoding. Copy that pattern.
2. **Routers → Services → Models, strictly.** A router function is ~10 lines: call a service function, catch its typed exceptions, return. If you're writing an `if` statement that isn't RBAC or exception translation inside a router, it belongs in a service instead.
3. **RBAC on every protected endpoint**, via `Depends(require_roles(UserRole.faculty, UserRole.admin))` (see `app/core/dependencies.py`). Default to the narrowest role set the use case actually needs — two routers (`plos.py`, `programs.py`) were originally admin-only-by-accident on their GET endpoints and had to be fixed because faculty genuinely needed read access. Think about *who reads this* as well as *who writes it*, before shipping.
4. **Typed service exceptions, not raw ones.** Use `NotFoundError` / `ConflictError` / `PermissionDeniedError` / `ValidationError` from `app/services/exceptions.py`; routers translate these to HTTP codes. Don't raise `HTTPException` from inside a service.
5. **Pydantic v2 only** — no v1-style validators or `Config` classes.
6. **Pure functions for anything mathematical.** `attainment_math.py` takes numbers in, returns numbers out, no DB/HTTP awareness — that's why it has 24 unit tests that run in 0.06s. Your risk-scoring math (feature normalization, threshold logic) should follow the same pattern; wire it up in a service, keep the math itself framework-free.
7. **No TypeScript.** Frontend is `.jsx`/`.js` only, enforced by the project spec.
8. **State management is React Context, nothing else.** This was an explicit decision (documented in `CLAUDE.md` §3) after Module 4 — don't introduce Redux/Zustand/etc. unless cross-page state genuinely outgrows Context.
9. **Migrations are real, reviewed Alembic migrations**, not hand-edited SQL. Run `alembic revision --autogenerate`, **read the generated file** (autogenerate gets enum/cascade details wrong sometimes — see §9 below), then `alembic upgrade head`. Run `alembic check` before considering a schema change done.
10. **Commit per completed module**, with a message referencing the module, only after its tests pass. Don't commit mid-module.

---

## 8. Testing

165 backend tests, three tiers (see `docs/SDD.md` §9 for the full rationale):
1. **Pure unit tests** — math/logic with no DB, e.g. `tests/test_attainment_math.py`.
2. **Service/engine integration tests** — real (but transactionally rolled-back) Postgres, e.g. `tests/test_attainment_engine.py`.
3. **API/RBAC tests** — full HTTP surface per endpoint, asserting both success and that the wrong role gets a 403.

**Write edge-case tests alongside the implementation, not after** — this is an explicit project rule (`CLAUDE.md` §8) that was actually followed for the attainment engine and should be followed for your risk-prediction edge cases too (what happens with <5 assessment records? a student with zero attendance data? a course with no CLOs yet?).

Run everything: `cd backend && pytest -v` (from an activated venv). All 165 must pass before you commit a module.

**Test isolation gotcha you need to know about:** `tests/conftest.py` uses a dedicated `NullPool` engine (not the app's normal pooled engine) for the test fixtures. This isn't decorative — pytest-asyncio spins up a new event loop per test by default, and asyncpg connections are bound to the event loop they were created in. Reusing the app's normal connection pool across tests causes a cryptic `InterfaceError: cannot perform operation: another operation is in progress`. If you add new fixtures, reuse the existing `db_session`/`client` pattern rather than rolling your own DB connection — it's already solved this problem for you.

---

## 9. Known Gotchas & Non-Obvious Decisions

Things that cost real debugging time already — don't rediscover them:

- **pgvector has no official Windows binary.** See §3. If you're moving this to a new dev machine or CI, this is the step that will surprise you.
- **Alembic autogenerate doesn't add `ON DELETE` behavior by default**, and doesn't drop enum types on downgrade. Two real bugs shipped because of this: deleting a course with CLOs raised an unhandled 500 (no cascade on `clos.course_id`), fixed in migration `b3f1c72d9a41`. Always review autogenerated migrations for FK `ondelete` and, for new enums, add an explicit `sa.Enum(...).drop(...)` in `downgrade()`.
- **`questions.clo_id` uses `SET NULL` on delete, not `CASCADE`.** A question is exam-record data; deleting its CLO tag should untag it, not destroy the question. Don't "fix" this to CASCADE.
- **WebSocket auth can't use headers.** Browsers can't set custom headers on the WS handshake, so the JWT travels as `?token=` query param (`app/routers/ws.py`). It's validated against the same RBAC/ownership rules as REST. If Module 5/6 add more WebSocket endpoints, follow this same pattern (and be aware query-param tokens can end up in server access logs — acceptable for a local FYP demo, worth a short-lived ticket scheme if this ever goes to production).
- **The attainment engine deletes-then-reinserts, it never patches.** `attainment_records` for a course are wholesale rebuilt on every recalculation. If you add ML-driven fields to a similar "derived data" table, consider the same pattern — it's what makes correctness easy to reason about and test.
- **Embeddings are computed once, at creation time**, stored as `vector(384)` columns, never re-computed per request. If Module 5 needs any embeddings (e.g. for feature engineering from text), follow this pattern, not on-the-fly encoding per API call.
- **`GET /admin/plos` and `GET /admin/programs` are intentionally faculty+admin, not admin-only** — despite living under an `/admin/*` prefix. Only the mutating verbs (POST/PATCH/DELETE) are admin-only. This was a deliberate fix, not an oversight — don't "clean it up" back to admin-only.
- **No student portal exists**, but student *accounts* do (Module 1 built full user management for all three roles). Don't confuse "no UI" with "no backend support" when scoping Module 6.

---

## 10. Current Repo State & Demo Data

As of handoff, the local dev database has:
- 1 admin account (bootstrap, created via `seed_admin.py`)
- The full UBIT institutional seed: 1 department, 4 programmes, 40 PLOs with real embeddings
- No demo courses/students left seeded — prior demo data was cleaned up after each verification pass

If you need a quick working example to test against, either re-run through the UI (Admin Panel → register a faculty account → log in as faculty → create a course) or ask for the demo-data script used previously (it exists in conversation history but wasn't kept as a permanent script in the repo).

**Do not commit real `.env` values.** `backend/.env` and `frontend/.env` are gitignored; only `.env.example` files are tracked, with placeholder values.

---

## 11. Command Cheat Sheet

```powershell
# Backend
cd backend
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
pytest -v
alembic revision --autogenerate -m "description"
alembic upgrade head
alembic check                          # confirm no model/migration drift
python scripts/seed_admin.py --email <e> --password <p> --full-name "<n>"
python scripts/seed_ubit_data.py
python scripts/seed_ubit_data.py --force-embeddings

# Frontend
cd frontend
npm run dev
npm run lint
npm run build
```

Good luck with Module 5 — the SHAP JSON schema and feature list are the two things you cannot get wrong (other code will eventually depend on that exact shape), everything else is normal iteration.
