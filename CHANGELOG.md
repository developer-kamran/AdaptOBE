# Changelog

All notable changes to AdaptOBE are recorded here, most recent first. Each
entry is a short summary of what changed, not a full diff — see git history
for that.

## 2026-08-15 — Module 6: Student portal & adaptive learning

The first student-facing surface. Student accounts existed since Module 1 but
had no UI — they now have a portal.

- **Backend** (`app/routers/student.py`, student-only): `GET /student/progress`
  (per-course CLO attainment with personal weak-CLO flags — a CLO is "weak"
  when *this student's own* attainment is below the course threshold, not the
  class-level flag); `GET /student/courses/{id}/scores` (assessment score
  history); `GET /student/courses/{id}/adaptive-quiz` and `POST .../submit`.
  Every query is scoped to the authenticated student — one student can never
  read another's data or a course they're not enrolled in (403).
- **Adaptive quiz** builds on the FYP-1 typed-question system: it draws only
  from **auto-gradable** questions (`mcq` / `true_false` / `fill_blank`, which
  carry a machine-checkable answer in `type_data`) and skips free-form
  `question` items and the `lab`/`project` assessment components. It weights
  question selection toward the student's weakest CLOs (`quiz_logic.allocate_quiz_slots`),
  strips correct answers before sending, and grades on submit
  (`quiz_logic.grade_answer`) — practice only, never written to `student_scores`.
  Results include the CLOs to keep practicing. No new tables or migration.
- **Frontend**: a `/student` route (gated `roles={['student']}`), a **My
  Progress** dashboard (overall attainment, per-course CLO bars with weak
  badges, expandable score history) and a **Practice Quiz** modal (MCQ /
  True-False / Fill-blank inputs, instant scoring, focus-CLO feedback). Added
  the student section to `Navbar` (desktop + mobile) — students previously hit
  "no access" everywhere. **Fixed** `LoginPage` routing students to `/courses`
  (faculty-only) on sign-in; they now land on `/student`.
- **Tests**: `test_quiz_logic.py` (pure allocation + grading) and
  `test_student_portal.py` (own-data isolation, auto-gradable-only quiz with
  answers stripped, grading + focus CLOs, student-only RBAC). **313 backend
  tests passing** (was 299). `npm run lint` / `npm run build` clean. Both
  modules verified end-to-end in the running app.

## 2026-08-15 — Module 5: ML risk prediction, SHAP, learning-gap detection

The first module built after the FYP-1 merge. Adds per-course student risk
classification with explainability, plus automated weak-CLO detection.

- **New deps**: `xgboost`, `shap`, `scikit-learn`, `pandas` (added to
  `requirements.txt`). Two friend-era deps that had never been installed in
  the local venv — `python-multipart`, `pdfplumber` — were installed too, and
  the local `.env` gained the `PASSWORD_ENCRYPTION_KEY` it was missing since
  the reversible-password change (the app wouldn't boot without it).
- **Two new tables** (migration `2e8ce4e237b9`):
  - `attendance_records` — one faculty-entered attendance % per (course,
    student). This was the one XGBoost feature with no existing source; rather
    than model every class session, attendance is a single percentage faculty
    maintain from a new **Attendance** tab on the course page.
  - `student_predictions` — `risk_level` (low/medium/high) + `confidence_score`
    + `predicted_score` + `shap_explanation` (JSONB), per CLAUDE.md §6/§9.
    Treated as derived data: wiped and rebuilt per run, never patched (same
    discipline as `attainment_records`).
- **The model** (`app/ml/risk_model.py`): a real XGBoost classifier (risk) +
  regressor (predicted score), with SHAP `TreeExplainer` producing the exact
  section-9 payload. Because this deployment has no historical labelled
  outcomes yet, the model is **bootstrapped on a synthetic sample** drawn from
  a domain-sensible feature→performance relationship — a genuine trained model
  with genuine SHAP values, retrainable on real outcomes later by swapping one
  function, with no interface change. Training/inference is offloaded with
  `asyncio.to_thread`, mirroring `embeddings.py`.
- **Feature sourcing**: `quiz`/`assignment`/`midterm` averages from
  assessment scores, `current_avg_clo_attainment` reused from the attainment
  engine's persisted records, `attendance_percentage` from the new table. A
  student needs ≥5 scored assessments (CLAUDE.md §9) or they're reported as
  skipped, not predicted.
- **Learning-gap detection** reuses `courses.attainment_threshold` and the
  attainment engine's own course report — a gap is a CLO with data whose class
  average is below threshold, exactly as the dashboard already defines it.
- **Endpoints** (`app/routers/ml.py`, faculty-only per the role split):
  `POST /api/v1/ml/predict-risk/{course_id}` runs + persists; `GET` returns
  the last stored predictions without re-running. Attendance CRUD at
  `GET/POST /api/v1/courses/{id}/attendance` (faculty-only).
- **Frontend**: an **Attendance** tab on Course Detail (bulk % entry) and a
  **Student Risk Prediction** card on the Faculty Dashboard — risk badges,
  confidence/predicted-score, SHAP "why" behind an `InfoTooltip`, skipped-count
  note, and below-threshold CLO gaps. Mobile-responsive, `npm run lint` /
  `npm run build` clean.
- **Tests**: `test_risk_math.py` (pure), `test_attendance.py`,
  `test_risk_prediction.py` — feature assembly/clamping, the ≥5 gate, exact
  SHAP shape, directional strong/weak sanity, learning-gap flagging, and the
  faculty-only RBAC matrix. **299 backend tests passing** (was 280).

## 2026-08-13 — Full mobile/responsive frontend pass

Before this pass, responsive Tailwind breakpoints (`sm:`/`md:`/`lg:`) appeared
in a handful of files and none of the shared layout components used them at
all — the app was effectively desktop-only. Every page and shared component
now scales down to a 375px phone.

- **`Navbar`** rebuilt with a hamburger menu below `md` (768px): nav links,
  user name/email/role, and sign-out collapse into a slide-down panel
  instead of overflowing the single header row they used to share.
- **Shared components**: `Tabs` scrolls horizontally instead of squeezing
  tab labels (this matters more now — Admin Panel and Course Detail both
  drive their tab bars through it); `Card`'s `CardHeader` stacks title above
  actions on mobile with actions wrapping instead of overflowing; `Modal`
  padding tightens on small screens; `InfoTooltip`'s popover width now
  clamps to `min(16rem, 100vw - 2.5rem)` so it can't run off the edge of a
  narrow viewport.
- **Every page**: main containers drop to smaller padding on mobile
  (`px-4 py-4 sm:px-6 sm:py-6`); every "title + action button(s)" header row
  — Courses, Course Detail, all Admin Panel tabs (Departments, Programmes,
  PLOs, Sub-Admins, Students, Faculty), CLOs, Enrollments, Assessments, and
  the CLO→PLO Mapping modal's confirmed/suggested-mapping rows — stacks
  vertically below `sm` instead of squeezing onto one row; multi-button
  groups (Enrollments' three actions, Students' two) wrap instead of
  overflowing.
- **Forms**: every modal grid that assumed desktop width — course/CLO/
  question create-edit forms, student registration, the question-type
  picker, bulk-import summary tiles — collapses to one column below `sm`
  and expands from there.
- **Left as-is, deliberately**: data tables already scroll horizontally via
  the shared `Table` component (including the CLO×PLO heatmap, which
  already had a sticky first column) — the standard mobile pattern for
  wide, dense tabular data, not something worth collapsing into cards here.
- No automated frontend test suite exists in this project to extend;
  verified with `npm run lint` and `npm run build` (both clean). Manual
  browser verification at 375px/768px is the recommended follow-up — see
  HANDOFF.md.

## 2026-08-13 — Lab and Project move from question types to assessment types

Lab and Project are no longer choices in the "+ Add Question" type picker.
They're assessment types now (`lab` already was one; `project` is new),
each with its own management screen instead of being added as a single
question-like item alongside MCQs and fill-in-the-blanks.

- **`AssessmentType` gains `project`** (`lab` already existed since Module 3).
  Migration `48e8e934eaba` adds the enum value with `ALTER TYPE ... ADD
  VALUE` inside an `autocommit_block()` — Postgres won't allow that
  statement inside Alembic's normal per-migration transaction.
- **The "+ Add Question" type picker** (`QuestionTypeStep` /
  `assessment/questionTypes.js`) now only offers Question, MCQ, Fill in the
  Blanks, and True/False. Lab and Project were removed from `QUESTION_TYPES`
  (the picker list); `QUESTION_TYPE_LABEL` still knows their labels since
  the underlying `question_type` values are unchanged.
- **New `assessment/LabProjectPanel.jsx`** is what a Lab or Project
  assessment's detail page shows instead of the generic Questions card.
  "+ Add Lab Component" / "+ Add Project Component" opens the existing
  single-item `QuestionFormModal` directly, skipping the type picker
  entirely — reusing the project/lab fields `TypeFieldsEditor` already had
  (Title, Description, Deliverable/Tasks). The component list drops the
  redundant Type column since it's implied by the assessment itself.
- **Backend enforcement, not just a UI convention.** `question_service` now
  validates that a Lab assessment's items are all `question_type: lab`, a
  Project assessment's are all `question_type: project`, and every other
  assessment type is refused either value — checked on create, bulk-create,
  and update (`update_question` when `question_type` is actually being
  changed).
- **Score Entry is unchanged.** Lab/Project components are still `Question`
  rows under the hood (`question_type` + `type_data`), so the existing
  per-question score grid (`ScoreEntryCard`) works identically for regular,
  Lab, and Project assessments — nothing in `score_service.py` or the
  scores endpoints changed.
- New backend tests in `test_assessments.py`: `project` assessment
  creation, the lab/project ↔ question_type coupling on create/bulk-
  create/update in both directions (280 backend tests passing).

## 2026-08-13 — Seat-number eligibility is now batch-year aware, not just programme

Student-enrollment filtering (normal picker, file import, and the new
backlog flow) used to only check a seat number's programme segment against
a fixed year ("22", frozen at seed time). It's now computed dynamically from
each course's semester and the real current year:

- `app.core.institution.expected_seat_no_year(semester)` — two semesters per
  academic year, so semester N implies enrollment `N // 2` years before now.
  Semester 4 in 2026 → enrolled 2024; semester 8 in 2026 → enrolled 2022.
- `expected_seat_no_prefix(program_code, semester)` — the full current-batch
  prefix, e.g. `B241101` for BSSE/semester 4 in 2026.
- `is_backlog_batch_year(seat_no, semester)` — true if a seat number's
  encoded year is *strictly earlier* than the current batch (any programme
  — backlog isn't programme-restricted, per the "Add Backlog Student" flow).

Replaces the old fixed `SEAT_NO_PREFIXES` dict with `SEAT_NO_PROGRAM_CODES`
(just the programme segment) plus the functions above. All three consumers
now use it:
- `GET /students` dropped `program_id` in favor of `course_id` (looks up the
  course's own programme + semester) and a `backlog=true` flag for the
  opposite rule. `EnrollmentsPanel`'s normal picker and `BacklogEnrollModal`
  both moved to this.
- The enrollment file-import "wrong programme" check is now "wrong
  programme or batch year", with a message pointing faculty at the backlog
  flow when that's actually what they meant.
- New pure-function tests in `test_seat_no.py`, plus updated/added
  `course_id`/`backlog` coverage in `test_enrollment_import.py`.

## 2026-08-13 — Backlog student enrollment

Faculty → Enrollments gains an "Add Backlog Student" button, for a student
repeating this course from a different cohort/programme than the course's
own. Unlike the normal "Enroll Students" picker (scoped to the course's
programme via seat-number prefix) and the file-import flow (which rejects
`wrong_programme` rows on purpose), this searches the **whole department**
by Seat No or Enrollment No as you type, then enrolls whichever match is
picked via the same `enroll_students` path everything else uses. Newly
added students land at the bottom of the enrolled-students table (already
true — enrollments are id-ordered) and their row is highlighted (amber)
until the page is next reloaded.

- **Bug fix along the way**: `GET /students` only department-scoped
  `sub_admin` callers; `faculty` callers (who also have a `dept_id`) got no
  scoping at all and could see every active student university-wide. Now
  both roles are scoped to their own department. Doesn't change behavior
  for this single-department UBIT deployment, but was the actual gap that
  made backlog search need fixing to be correct.
- The enrolled-student lookup map (`EnrollmentsPanel`) is no longer
  restricted to the course's own programme, since a backlog student's info
  now needs to resolve regardless of which programme they belong to.

## 2026-08-13 — Auto-generated password for manual "Add Student"

The Sub-Admin's "Add Student" form no longer has a Password field. Submitting
it now:
1. Registers the account with `password` omitted.
2. The backend generates one automatically (`app.core.security.generate_password`
   — 8 characters, guaranteed letter + digit, no ambiguous `0/O/1/l/I` glyphs;
   the same generator bulk import already used).
3. The modal immediately fetches it via the existing password-reveal endpoint
   and shows a result screen with the student's Full Name, Father's Name,
   Email, Enrollment No, Seat No, and the generated password (also viewable
   later from Edit, same as bulk-imported students).

Backend change: `UserCreate.password` is now optional (`auth_service.register_user`
generates one when omitted) rather than a new endpoint — every existing
caller that already sends a password is unaffected.

## 2026-08-13 — Reactivate accounts, search boxes, in-file seat-number dedup

- **Reactivate.** Every account list that already had "Deactivate" (Super
  Admin's Sub-Admins tab, Sub-Admin's Faculty and Students tabs) now shows
  "Reactivate" for inactive accounts. No backend change — `PATCH
  /admin/users/{id}` already accepted `is_active`, only the button was
  missing.
- **Search.** Live, as-you-type client-side filtering added to the same three
  tabs plus Faculty → Enrollments:
  - Students: matches Seat No or Enrollment No.
  - Faculty: matches Faculty ID.
  - Sub-Admins: matches Employee ID.
  - Enrollments tab: matches Seat No, on both the enrolled-students table and
    the "Enroll Students" picker modal.
- **Bulk student import now flags duplicate Seat No within the same file.**
  The preview already caught a repeated email or enrollment number in one
  upload; it silently missed a repeated seat number, which would only surface
  later as one row getting skipped at confirm time with no warning beforehand.
  Both Enrollment No and Seat No are now checked the same way.

## 2026-08-12 — Faculty modules: courses, CLOs, mappings, enrollments, assessments, questions

A round of faculty-facing fixes and additions across every module touched by
Courses/CLOs/Mappings/Enrollments/Assessments/Questions.

- **Course duplicate prevention.** Uniqueness moved from a global `courses.code`
  constraint to `(program_id, code, semester)` — the same code can now be
  legitimately reused in a different programme or a different semester (e.g. a
  retake offering), but the exact combination is rejected with a 409 on both
  create and edit. Migration `c3af4f47a354`.
- **CLOs**: Bloom Level is now required at creation, restricted to the six
  standard levels (Remember/Understand/Apply/Analyze/Evaluate/Create) via a
  dropdown — enforced in `schemas/clo.py`, existing rows are left as-is.
  Edit/Delete UI added (the backend already had PATCH/DELETE). Deleting a CLO
  now triggers an attainment recalculation, since untagging its questions
  (`SET NULL`) changes CLO/PLO numbers.
- **AI mapping suggestions** (CLO→PLO and question→CLO) no longer show the raw
  cosine similarity score as the primary value — faculty see a qualitative
  **Strong / Moderate / Weak** label instead (thresholds: ≥0.5 strong, ≥0.3
  moderate, else weak — same cutoffs the strength auto-suggestion already
  used). A new "ⓘ" `InfoTooltip` explains the method in plain language and
  reveals the underlying score. Purely a frontend change — no API change.
- **Enrollments**:
  - **Programme-based student filtering.** `GET /students` accepts an optional
    `program_id`, filtering to that programme's students by seat-number prefix
    (`app.core.institution.SEAT_NO_PREFIXES` — BSSE `B221101`, BSCS `B221100`,
    BSAI `B221102`, BSDS `B221103`). Applied to the manual "Enroll Students"
    picker so a course only ever offers its own programme's students.
  - **Add Students via File.** A new upload → preview → confirm flow
    (`/courses/{id}/enrollments/import/*`) matches an uploaded roster (Full
    Name, Father's Name, Enrollment No, Seat No, Eligible) to **existing**
    student accounts by Enrollment No/Seat No and enrolls the ones that are
    matched, eligible, in the course's own programme, and not already
    enrolled — everything else (not found, wrong programme, already enrolled,
    ineligible, duplicate row) is reported separately and excluded. This is
    deliberately distinct from the admin bulk import: it never creates
    accounts. Reuses the existing embedding-based column matcher, generalized
    to accept a different field set (`ml/column_matcher.py`).
  - The enrolled-student table now shows Name / Father's Name / Seat No.
    instead of Name / Email.
- **Assessments**: Edit/Delete UI added (backend already supported it).
- **Questions**:
  - Question Text is now required at creation; CLO Tag is always sent
    explicitly (including `null` for "Untagged") rather than omitted.
  - Question numbers are now unique per assessment (`uq_question_assessment_number`),
    and total question marks can no longer exceed the assessment's total —
    both enforced server-side with clear 409/422 messages, plus a fast client
    pre-check.
  - Edit/Delete UI added (backend already supported it).
  - **New question types**: alongside the existing free-form "Question", a
    faculty can now add **MCQ**, **Fill in the Blanks**, **True/False**
    (created N-at-a-time via a new bulk-create dialog and endpoint,
    `POST /assessments/{id}/questions/bulk`, all-or-nothing), **Project**, and
    **Lab** (single-item forms). Modeled as a `question_type` enum plus a
    flexible `type_data` JSONB column on `questions` — same idiom as
    `student_predictions.shap_explanation` — so attainment math, CLO tagging,
    and the uniqueness/marks-cap rules above work unchanged across every type.
- New backend tests: `test_enrollment_import.py`, plus new cases in
  `test_courses.py`, `test_plos_clos.py`, and `test_assessments.py` covering
  every rule above (243 backend tests passing).

## 2026-08-09 — Bulk student upload (Excel/PDF)

The Students tab gains an "Add Students via File" path alongside the existing
one-at-a-time form.

- **Upload → preview → confirm.** `POST /api/v1/admin/students/import/preview`
  parses an uploaded `.xlsx`/`.xls`/`.pdf` roster and reports what it found —
  total detected, ready-to-add count, incomplete count, the extracted data for
  every row, and which of your file's columns was matched to each field. It
  **writes nothing to the database**. Accounts are only created once you
  confirm, via `POST .../import/confirm`.
- **Extraction uses the embedding model already in this project, not an
  external LLM.** No API key, no per-upload cost, works offline. Structural
  parsing (`openpyxl` for Excel, `pdfplumber` for PDF tables) pulls out the
  rows; column headers are then resolved in two stages — an exact alias lookup
  for obvious headings, falling back to `all-MiniLM-L6-v2` similarity for
  anything unfamiliar, so "Guardian Name" or "Roll No" are understood without
  maintaining a list of every possible spelling.
- **Incomplete records are reported but never stored.** A row missing any of
  Full Name / Father's Name / Enrollment No / Seat No / Email (or with a
  malformed or duplicated email) is flagged on the preview with exactly what's
  wrong, and is simply left out when you confirm. There is deliberately no
  "Incomplete Students" table and no fix-and-promote flow — correct the file
  and upload again.
- **Passwords are generated automatically** — 8 characters, unique per
  student, excluding ambiguous glyphs (`0/O`, `1/l/I`). They're shown once on
  the result screen and remain viewable afterwards from each student's Edit
  page.
- **Per-row failure isolation**: a student whose email or enrollment number is
  already taken is skipped and reported; the rest of the batch still imports.
- **Department scoping needed no new code** — creation goes through the
  existing `user_service.create_user_scoped`, which already forces the calling
  sub-admin's own `dept_id`. Both endpoints are sub-admin-only; faculty,
  students, and super-admins get a 403.
- Server-side re-validation on confirm: the browser having decided a row was
  complete is not taken on trust.
- New deps: `python-multipart`, `pdfplumber`. New tests:
  `backend/tests/test_student_import.py` (27).

## 2026-08-08 — Student & Faculty management updates

- **Separate tabs**: the Sub-Admin's combined "Faculty & Students" tab is now
  two dedicated tabs (Students, Faculty), each with its own Add/Edit UI —
  `StudentsPanel.jsx` and `FacultyPanel.jsx` replace the role-dropdown that
  used to live in `UsersPanel.jsx` (which now only handles Super Admin's
  Sub-Admin management).
- **New required fields**: `employee_id` (labeled "Faculty ID" in the
  Faculty tab, same underlying column as Sub-Admin's "Employee ID") is now
  required when creating a faculty account; `father_name` is a new column,
  required when creating a student account.
- **Password visibility on Edit — a deliberate security trade-off.**
  Per explicit direction, a user's password is now recoverable from the
  Edit page, not just at creation. This required adding a *second*,
  reversibly-encrypted column (`users.password_encrypted`, Fernet, key in
  `PASSWORD_ENCRYPTION_KEY`) alongside the existing one-way bcrypt
  `password_hash`. **This is a real reduction in security posture** from
  the previous one-way-hash-only design: anyone with database access or the
  encryption key can now recover every plaintext password, whereas before
  this was mathematically impossible. Login/authentication is completely
  unchanged — `password_hash` remains the only thing checked at sign-in.
  The decrypted password is exposed through one dedicated, scope-checked
  endpoint (`GET /admin/users/{id}/password`) and is never included in any
  list/table response. Accounts whose password was set outside app code
  (e.g. the bootstrap `seed_admin.py` script, or a direct database update)
  have no encrypted copy on file and show "Not available" instead.
- Department-scoping for all of the above reuses the existing
  `ensure_can_manage_user`/`create_user_scoped` logic unchanged — no new
  authorization code was needed.
- **Not implemented in this pass**: bulk PDF/Excel student upload with
  AI-based data extraction and an "incomplete students" holding area
  (requested items 5-8) — scoped but intentionally deferred.

## 2026-08-08 — Admin hierarchy: Super Admin / Sub-Admin split

Replaced the single flat `admin` role with a two-tier, department-scoped
hierarchy, plus a handful of related data-quality fixes.

- **Roles**: `admin` role split into `super_admin` (manages Departments and
  Sub-Admins only) and `sub_admin` (department-scoped admin, manages that
  department's Programmes, PLOs, Faculty, Students, and Courses). The
  existing bootstrap admin account was promoted in place to `super_admin`.
- **Users**: added `dept_id` and `employee_id` columns to `users`.
  `dept_id` scopes sub-admins, faculty, and students to one department;
  `employee_id` is required for sub-admins.
- **Cross-department enforcement**: every admin-tier endpoint (users,
  programmes, PLOs, courses) now checks the caller's role and `dept_id`
  before returning or mutating a row — a sub-admin cannot read or write
  another department's data by editing a URL/body ID, verified with new
  tests. A super_admin is limited to departments and sub-admin accounts and
  can no longer touch programmes, PLOs, or courses directly.
- **Assessments, enrollments, CLO-PLO mappings, attainment reporting, and
  the live WebSocket dashboard** are now faculty-only (previously
  faculty+admin) — these are teaching-workflow endpoints, not
  administrative ones, under the new role split.
- **PLO Bloom Domain**: `domain` is now a validated enum
  (`Cognitive` / `Psychomotor` / `Affective`, matching the values already
  seeded for all 40 institutional PLOs) instead of a free-text field, with a
  matching dropdown in the admin UI.
- **Student registration**: `enrollment_no` and `seat_no` are now required
  (frontend + backend) when creating a student account, instead of optional.
- **Frontend**: Admin Panel tabs, navigation links, and route guards are now
  role-aware (Super Admin sees Departments/Sub-Admins; Sub-Admin sees
  Programmes/PLOs/Faculty & Students). Departments, Programmes, and PLOs
  gained Edit/Delete UI in the admin panel — previously create/list only,
  even though the backend already supported PATCH/DELETE.

## Modules 0–4 (prior to this changelog)

Foundational work, summarized retrospectively:

- **Module 0**: PostgreSQL 18 + pgvector, async FastAPI/SQLAlchemy skeleton, Alembic.
- **Module 1**: JWT auth, bcrypt hashing, RBAC middleware, Admin CRUD for users/departments/programmes.
- **Module 2**: Course/CLO/PLO management, AI semantic CLO→PLO mapping engine.
- **Module 3**: Assessments, questions, bulk scoring, the direct attainment engine.
- **Module 4**: Faculty dashboard (CLO×PLO heatmap), native WebSocket live updates, PDF/Excel export.
- Plus: UBIT institutional data seed script, full frontend UI for Modules 1–3.

See [HANDOFF.md](HANDOFF.md) for full architectural context.
