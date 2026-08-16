# AdaptOBE — Remaining Modules (Updated Plan)

**Status as of 2026-08-15.** Modules 0–4 are built and were then heavily
enhanced by the merged **FYP-1 Updates** PR (see [`CHANGELOG.md`](../CHANGELOG.md),
entries 2026-08-08 → 2026-08-13). Those enhancements did **not** start a new
numbered module — they refined the admin/faculty surface of Modules 1–4.

**Modules 5 and 6 are now built** (2026-08-15 — see [`CHANGELOG.md`](../CHANGELOG.md)).
**One module remains: Module 7 (Containerization & Deployment).**

This document restates each remaining module from `CLAUDE.md` §10, **revised to
account for what the FYP-1 PR actually changed** so the original roadmap doesn't
send you building against assumptions that are no longer true. Where a task
differs from the original `CLAUDE.md`/`HANDOFF.md` wording, it's marked
**[CHANGED]** or **[NEW]**.

---

## What changed under your feet (read this first)

The FYP-1 PR changed six things that ripple into every remaining module:

1. **Role model.** The flat `admin` role is gone. RBAC is now
   `super_admin` / `sub_admin` / `faculty` / `student`, enforced via
   `Depends(require_roles(UserRole.faculty, ...))` in `app/core/dependencies.py`.
   Teaching-workflow endpoints are **faculty-only** now (not faculty+admin).
2. **Question-type system.** `questions` gained a `question_type` enum
   (`question` / `mcq` / `fill_blank` / `true_false`) + a `type_data` JSONB
   column carrying options / correct answer / etc. This is the foundation the
   Module 6 adaptive quiz generator should build on — it no longer starts from
   nothing.
3. **Lab & Project are assessment types, not question types.**
   `AssessmentType` = `quiz` / `assignment` / `lab` / `project` / `midterm` /
   `final`. `question_service.py` enforces that a lab/project assessment's items
   carry the matching `question_type`. Auto-gradable question types
   (mcq/true_false/fill_blank) are the ones with usable `type_data`.
4. **New user fields + reversible passwords.** `users` has `employee_id`,
   `father_name`, and `password_encrypted` (Fernet, key `PASSWORD_ENCRYPTION_KEY`).
   Any new account path must set both password columns via
   `auth_service.register_user`. Login still checks bcrypt `password_hash` only.
5. **Batch-year seat eligibility.** `app/core/institution.py` exposes
   `expected_seat_no_year/prefix(...)` and `is_backlog_batch_year(...)`, computed
   against the real calendar year. Any new student-facing filtering should reuse
   these, not reinvent a fixed year.
6. **Mobile-responsive is now the baseline.** Every existing page scales to
   375px. All new UI in Modules 5/6 must follow the responsive patterns in
   `HANDOFF.md` §7.11 (header rows stack below `sm`, modal grids
   `grid-cols-1 sm:grid-cols-N`, `w-full sm:w-64`, etc.).

---

## Module 5 — ML Risk Prediction & Learning Gap Detection

**Goal (unchanged):** XGBoost classifier predicting per-course student risk
(`low`/`medium`/`high`) with a mandatory SHAP explainability payload, plus
automated below-threshold CLO detection.

### 5.0 Dependencies **[CHANGED]**
Only `sentence-transformers` (which pulls `torch`/`numpy`) is installed today.
**Add to `requirements.txt` and `pip install`:** `xgboost`, `shap`,
`scikit-learn`, `pandas`. Pin versions. This is a real setup step the original
roadmap glossed over.

### 5.1 New table: `student_predictions` **[NEW MIGRATION]**
Per `CLAUDE.md` §6, add via a reviewed Alembic migration:
```
student_predictions: id (PK), student_id (FK), course_id (FK),
  risk_level (ENUM risk_level: low/medium/high),
  confidence_score (Float), predicted_score (Float),
  shap_explanation (JSONB)
```
Because this is a **new** `create_table`, the enum is created automatically — no
need for the manual `sa.Enum(...).create(checkfirst=True)` dance that adding an
enum column to an *existing* table required (HANDOFF §9). Still add an explicit
`sa.Enum(name="risk_level").drop(...)` in `downgrade()`.
Treat this table as **derived data**: delete-then-reinsert per
(student, course) on each prediction run, matching the attainment engine — never
patch in place.

### 5.2 Feature engineering **[CHANGED — now mostly sourceable]**
Fixed 5-feature schema (`CLAUDE.md` §9), each 0.0–100.0, ≥5 assessment records
required per student. Where each comes from *now*:

| Feature | Source in the current schema |
|---|---|
| `quiz_average_percentage` | avg of `assessments.type == quiz` scores |
| `assignment_average_percentage` | avg of `assessments.type == assignment` scores |
| `midterm_score_percentage` | `assessments.type == midterm` score |
| `current_avg_clo_attainment` | avg of that student's `attainment_records.attainment_percentage` for the course (already computed by the attainment engine — **reuse, don't recompute**) |
| `attendance_percentage` | **STILL A GAP — no attendance table exists.** See 5.3. |

Note the assessment-type split is cleaner than before: `lab`/`project` are now
their own assessment types, so quiz/assignment/midterm averages are unambiguous.

### 5.3 The attendance gap — decision required **[CHANGED]**
There is no attendance table or endpoint anywhere. Two options:
- **(a) Add a minimal `attendance` table + faculty CRUD** — most correct;
  `attendance_percentage` becomes real data. One migration, one small service,
  one faculty-only router, a simple entry grid on the course page.
- **(b) Treat attendance as a manually-entered/estimated input** on the
  predict-risk call for now, and document it as a known limitation.

**Recommendation: (a)** if time allows — it's the only feature with no source and
the model is only as honest as its inputs. Ship it as a small sub-step before the
classifier so the feature vector is complete. Whichever you pick, **write it down**
in CHANGELOG.md.

### 5.4 Model + math **[CHANGED — conventions]**
- XGBoost train/inference lives in `app/ml/` (e.g. `risk_model.py`), called from
  a **new** `app/services/risk_service.py`, called from a **new** thin
  `app/routers/ml.py`. Business logic never in the router.
- XGBoost is CPU-bound/synchronous — wrap training and inference in
  `asyncio.to_thread(...)`, exactly like `app/ml/embeddings.py`.
- Keep feature normalization / threshold logic as **pure functions** (framework-
  free, unit-testable like `attainment_math.py`).
- SHAP payload must match the **exact** JSON schema in `CLAUDE.md` §9
  (`base_value`, `predicted_risk`, `confidence`, `feature_contributions[]` with
  `feature`/`value`/`shap_value`/`impact`). Other code will depend on this shape.

### 5.5 Endpoint **[CHANGED — RBAC]**
`POST /api/v1/ml/predict-risk/{course_id}` → `require_roles(UserRole.faculty)`
**only**. Under the new role split this is a teaching endpoint; `super_admin` and
`sub_admin` should get 403 (they no longer touch course-level teaching data).
Verify course ownership (`owner_faculty_id`) like other faculty endpoints.

### 5.6 Learning-gap detection **[CHANGED — reuse existing]**
Reuse `courses.attainment_threshold` (default 50%) and
`attainment_records.is_achieved` — both already exist and are populated by the
attainment engine. Do not add a second threshold concept. Detection = list CLOs
where class-average attainment < threshold.

### 5.7 Frontend **[NEW]**
- Add a risk panel to the existing **faculty** dashboard (`/dashboard`), not a
  new top-level role area.
- Reuse the qualitative-label idiom the FYP-1 PR introduced: show `low/med/high`
  as colored badges and put the SHAP feature contributions behind an
  `InfoTooltip` (the same `components/ui/InfoTooltip.jsx` used for the
  Strong/Moderate/Weak mapping explanation), rather than dumping raw SHAP floats.
- Mobile-responsive per HANDOFF §7.11.

### 5.8 Tests (write alongside, per `CLAUDE.md` §8) **[CHANGED — new edge cases]**
- Student with `< 5` assessment records → predictable, non-crashing result.
- Course with no CLOs yet / no attainment_records.
- Missing attendance data (whichever 5.3 path you took).
- SHAP payload shape assertion (exact keys).
- RBAC: faculty 200, sub_admin/super_admin/student 403.
- Reuse the `NullPool` `db_session`/`client` fixtures — don't roll your own DB
  connection (HANDOFF §8 isolation gotcha).

---

## Module 6 — Student Web Portal & Adaptive Learning

**Goal (unchanged):** student dashboard (personal CLO attainment + score
history), learning-gap alerts, adaptive quiz generator scaling difficulty to
per-student CLO performance.

### 6.1 Backend endpoint **[CHANGED — RBAC + not built]**
`GET /api/v1/student/progress` → `require_roles(UserRole.student)`. Not
implemented yet — build the endpoint (new `app/routers/student.py` +
`student_service.py`) and the page. A student only ever sees **their own** data;
scope every query by the authenticated `user.id`, never a path/body id.

### 6.2 Data sources **[CHANGED — mostly exists]**
- CLO attainment breakdown + score history → `attainment_records` +
  `student_scores` (both populated). No new computation.
- Weak-CLO alerts → same `attainment_threshold` / `is_achieved` reuse as 5.6.
- Student profile now has `father_name`, `enrollment_no`, `seat_no` (required
  fields from FYP-1) — surface them on the profile header.

### 6.3 Adaptive quiz generator **[CHANGED — big upgrade, build on question types]**
The original roadmap assumed you'd invent a question format. **You no longer
have to** — the FYP-1 PR added a real typed-question system:
- Draw candidate questions from existing `questions` with `question_type` in
  `mcq` / `true_false` / `fill_blank` — these carry `type_data` (options +
  correct answer), so they are **auto-gradable**. Exclude `question` (free-form,
  no machine answer) and `lab`/`project` (now assessment types, not quiz items).
- Scale difficulty by the student's per-CLO attainment from `attainment_records`:
  weak CLOs → pull more/easier questions tagged to that CLO; strong CLOs → fewer/
  harder. (If you need a difficulty signal beyond CLO strength, add a
  `difficulty` field to `type_data` rather than a new column.)
- Grading reuses the `type_data` correct-answer payload — no new scoring math.

### 6.4 Frontend **[NEW — routing + nav]**
- Add `/student/*` routes gated `roles={['student']}` in `ProtectedRoute`.
- Add a **student** section to `Navbar.jsx` — it currently renders nothing for
  the `student` role (faculty/sub_admin get Courses, faculty gets Dashboard,
  super_admin/sub_admin get Admin Panel). Students land on "no access" everywhere
  today.
- Mobile-responsive per HANDOFF §7.11 (students are the most likely to be on a
  phone — take this seriously here).

### 6.5 Tests **[NEW]**
- `GET /student/progress`: student sees only own data; faculty/sub_admin/
  super_admin get 403; a student cannot read another student's progress.
- Adaptive quiz: excludes free-form/lab/project questions; weights toward weak
  CLOs; grades mcq/true_false/fill_blank correctly from `type_data`.

---

## Module 7 — Production Containerization & Deployment (final)

**Goal (unchanged):** Dockerfiles for backend + frontend, production
`docker-compose.yml` bundling FastAPI + PostgreSQL(+pgvector) + frontend serving.
Still deliberately deferred until last — **don't add Docker files before this.**

### 7.1 Env/secrets the compose file must carry **[CHANGED — more secrets now]**
The FYP-1 PR added a secret the original roadmap didn't know about:
- `DATABASE_URL`, `JWT_SECRET_KEY` (original), **plus `PASSWORD_ENCRYPTION_KEY`**
  (Fernet key for reversible passwords) — the app fails to start without it now.
- `CORS_ORIGINS` must point at the deployed frontend origin (currently hardcoded
  to the Vite dev origin).

### 7.2 System deps in the backend image **[CHANGED]**
`requirements.txt` grew: `python-multipart`, `pdfplumber` (roster import), and —
after Module 5 — `xgboost`, `shap`, `scikit-learn`, `pandas`. The image also
needs the `all-MiniLM-L6-v2` model weights baked in or mounted (avoid
first-request download in a container). Same for any persisted XGBoost model
file.

### 7.3 pgvector in the DB image **[CHANGED]**
Use a Postgres image with pgvector available for **PG18** (e.g. a
`pgvector/pgvector:pg18` base or a build that installs it) — the local setup
compiled it from source, which won't translate to a stock `postgres:18` image.
`CREATE EXTENSION vector` must succeed at init.

### 7.4 WebSockets through the reverse proxy **[CHANGED]**
The live dashboard uses native WS with the JWT as a `?token=` query param
(browsers can't set WS headers). The reverse proxy (nginx) must pass
`Upgrade`/`Connection` headers for the WS route. Don't strip the query string.

### 7.5 Frontend serving
Static build (`npm run build`) served behind the same proxy; SPA fallback so the
new `/student/*` and existing deep routes resolve.

---

## Summary

| Module | Title | Status | Biggest FYP-1-driven change to the plan |
|---|---|---|---|
| **5** | ML Risk Prediction & Learning Gap Detection | **Built (2026-08-15)** | Shipped with attendance option (a) — a real `attendance_records` table; XGBoost+SHAP bootstrapped on synthetic data; faculty-only |
| **6** | Student Portal & Adaptive Learning | **Built (2026-08-15)** | Portal + adaptive quiz over the auto-gradable question types; `/student` route + nav added; post-login student redirect fixed |
| **7** | Containerization & Deployment | Not started | Extra secret `PASSWORD_ENCRYPTION_KEY`; more Python deps; pgvector-for-PG18 image; WS `?token=` proxy config |

**Cross-cutting rules for all three:** thin routers → services → models; typed
service exceptions; `AsyncSession` + `asyncio.to_thread` for CPU work; Pydantic
v2; pure functions for math; reviewed Alembic migrations; **mobile-responsive to
375px**; tests written alongside; commit per completed module.
