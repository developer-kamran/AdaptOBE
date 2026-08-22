# Changelog

All notable changes to AdaptOBE are recorded here, most recent first. Each
entry is a short summary of what changed, not a full diff — see git history
for that.

## 2026-08-19 — Attendance count, drag-and-drop reordering, seat-no data fix, Upload Assessment Paper

Four independent faculty-facing additions.

- **Attendance tab shows a live student count.** `AttendancePanel.jsx` now
  displays "Showing N students" next to the existing search/threshold
  filters, computed from the same `visibleEnrollments` array the table
  itself renders from, so it updates automatically as filters change. No
  backend change.
- **Frontend-only drag-and-drop reordering** for CLOs (`CLOsPanel.jsx`),
  Assessments (`AssessmentsPanel.jsx`), and Questions
  (`AssessmentDetailPage.jsx`'s Questions table), using `@dnd-kit/core` +
  `@dnd-kit/sortable` + `@dnd-kit/utilities` (new frontend deps) rather than
  native HTML5 drag-and-drop, which doesn't work on touch devices. A new
  shared `SortableRow`/`DragHandle` pair makes only a small grip icon
  draggable — not the whole row — so existing Edit/Delete/"Map to
  PLOs"/row-click actions keep working unchanged; `Table.jsx`'s `TR` is now
  `forwardRef` so dnd-kit can attach its node ref. A new `useLocalOrder`
  hook persists the reordered id list to `localStorage` (keyed per
  course/assessment) and reconciles it against the live API list on every
  load — new rows append at the end, deleted rows drop out silently. **No
  `display_order` column, no backend/API/migration change** — reordering is
  purely a client-side display concern, per explicit product direction.
  `useDndSensors` wires up `PointerSensor` (mouse + touch + pen through one
  path) and `KeyboardSensor` so reordering works by touch and by keyboard,
  down to 375px.
- **`data/add_students/*` reseated alphabetically.** The four sample
  roster files (`BSSE_students.xlsx/.pdf`, `enroll_bsse_students.xlsx/.pdf`)
  previously had seat numbers assigned in an arbitrary order unrelated to
  name. A one-off script (`backend/scripts/reorder_add_students_data.py`,
  not part of the running app) sorted all 80 rows by Full Name and
  reassigned only the Seat No column sequentially in that order (same
  `B22110106###` prefix, so "Adeel Hashmi" is now `...001` and "Zain Iqbal"
  is `...080`). Father's Name, Enrollment No, and Email/Eligible stay
  attached to whichever student they already belonged to.
- **Upload Assessment Paper.** The Questions card on an assessment's detail
  page gained a second way to add questions alongside the existing manual
  "+ Add Question" flow: upload the actual paper (PDF/Word) and have its
  questions extracted automatically.
  - **Extraction is a Groq generative-AI call**
    (`app/ml/question_extractor.py`), not a regex/layout parser — mirrors
    `clo_generator.py`'s existing pattern exactly (lazy `AsyncGroq` client,
    same `openai/gpt-oss-120b` model, strict-JSON prompt,
    `LLMGenerationError` on any failure) rather than introducing new
    architecture, since real exam papers vary too much in format (MCQ
    styles, fill-blank markers, numbering) for a brittle parser. Detects
    Question / MCQ / Fill in the Blank / True-False items, plus header
    metadata (course name, course code, assessment title, instructor) —
    correct answers are only ever populated if an answer key is actually
    present in the document (most student-facing papers have none, so
    faculty typically fill those in during review).
  - **Verification before import**: the extracted header metadata is fuzzy-
    matched (`app/services/assessment_paper_import_service.py`) against the
    real assessment/course/instructor — course code uses exact match
    (ignoring punctuation/case) rather than fuzzy similarity, since two
    different short codes ("CS-201" vs "CS-101") can look deceptively
    similar by character overlap. Any mismatch is shown as a clear ✗ per
    field with the detected vs. expected value, and the faculty must tick
    an explicit "I've checked this and it's correct" box before the confirm
    button is enabled — mismatches are never auto-imported.
  - **Workflow**: Upload → Extract → Verify → Preview (per-question
    include/exclude checkboxes, editable marks/text/options/answers via the
    existing `TypeFieldsEditor`, optional "Suggest with AI" CLO tagging) →
    Faculty confirmation → Add. The preview endpoint
    (`POST /assessments/{id}/paper-import/preview`) writes nothing at all;
    confirming reuses the *existing*
    `POST /assessments/{id}/questions/bulk` endpoint directly with whatever
    the faculty approved — no parallel write path, so the same
    numbering/marks-budget/CLO-ownership validation applies as the manual
    bulk-add flow.
  - Existing manual question creation (single and bulk) is unchanged.
  - New tests: `test_question_extractor.py` (pure/monkeypatched, mirrors
    `test_clo_generator.py`), `test_assessment_paper_import.py` (matching
    logic + API-level preview tests with the Groq call monkeypatched).
    **387 backend tests passing** (was 357). `npm run lint` / `npm run
    build` clean. `alembic check` clean (no schema change).

### Same-day follow-ups

- **Attendance filtering is one control, not two.** The separate "below"/
  "above" number inputs were replaced with a single `filterMode` (`none` /
  `below` / `above`) dropdown plus one `%` input, so only one threshold
  comparison ever applies at once instead of the two being silently
  combinable.
- **"Upload Assessment Paper" moved next to "Export"** at the top of the
  assessment detail page, out of the Questions card header (which now only
  has "+ Add Question"); hidden for Lab/Project assessments, which can't
  hold the question types this flow extracts.
- **Questions imported via paper upload are now tagged.** `PaperImportModal`
  stamps `type_data.source = "paper_import"` on every question it creates
  (the existing flexible `type_data` JSONB column, no schema change), and
  the Questions table shows an "⇪ Extracted" badge plus a light row tint for
  any question carrying that tag — persists after refresh, survives edits
  through the normal Edit form (`type_data` round-trips unless a field it
  actually controls is changed).
- **Live data correction, not just the sample files**: the earlier seat-no
  reorder only touched `data/add_students/*`. The real `B22110106` batch in
  the running dev DB had 81 students (80 from that file plus one added
  later, "Abdul Aziz", who'd landed at the end of the sequence rather than
  alphabetically first) with the *old*, non-alphabetical seat assignment
  still live. A one-off script re-sorted all 81 real rows by name and
  reassigned `seat_no` sequentially (two-phase update, since `seat_no` is
  globally `UNIQUE` and the target values overlap with current ones — every
  row first moves to a `TMP-<id>` placeholder, then to its final value), and
  `data/add_students/*` was regenerated from that same authoritative
  81-student list so the files and the running system now agree exactly.
- **Two real assessments added for manual testing**: `Quiz #3` (10 marks,
  10%) and `Assignment #3` (5 marks, 5%) under Ms. Madiha Khurram's
  `SE-301` Operating Systems course, matching the existing `Quiz #1/#2` /
  `Assignment #1/#2` pattern (course weightage now 65%, still under the
  100% cap) — created via `assessment_service.create_assessment` directly,
  not a migration. Sample paper documents for both (covering CLO-7 Virtual
  Memory and CLO-8 File Systems, no answer key) were generated for the
  faculty to upload and verify end-to-end, and live under
  `data/assessment_paper/` (a new sibling to `data/add_students/` — sample
  files to manually upload via "Upload Assessment Paper", not something the
  app reads itself).
- **Enrollments tab is alphabetical by student name**, not enrollment-id
  order. `EnrollmentsPanel.jsx`'s main enrolled-students table, the
  "+ Enroll Students" candidate picker, and `BacklogEnrollModal`'s search
  results are all now sorted by `full_name` (locale-aware, case-insensitive)
  before rendering. Purely a frontend display-order change — no API change.
  A just-added backlog student stays pinned at the bottom of the table
  (highlighted amber) instead of jumping into alphabetical position, until
  the page is next reloaded — restores the original backlog-enrollment
  behavior the alphabetical sort would otherwise have broken.
- **`data/assessment_paper/` sample papers are PDF, not `.docx`.** Quiz #3
  and Assignment #3 regenerated as PDF (reportlab, same boxed meta-grid
  layout `assessment_export_service.build_exam_pdf` uses) and the `.docx`
  versions removed — same content, same CLO-7/CLO-8 coverage, no answer key.
- **Attendance and Enrollments tabs both sort backlog students to the
  bottom, highlighted.** The Attendance tab has no add-backlog action of its
  own to hook into, so "backlog" is a *computed* fact instead: a new
  `frontend/src/utils/seatNo.js` mirrors `app/core/institution.py`'s
  `expected_seat_no_year` / `is_backlog_batch_year` exactly (a student is
  "backlog" if their seat number's encoded enrollment year is earlier than
  this course's semester currently expects), so it works the same on every
  page load rather than only right after an action. Both
  `AttendancePanel.jsx` and `EnrollmentsPanel.jsx` pull those students out
  of their normal sort, append them at the bottom, and render them with an
  amber row highlight plus a "Backlog" badge next to their name.
  Enrollments' previous "just added this session" `highlightedIds` state
  (pinned only until the next reload) is gone, replaced by this same
  always-on computed check.
- **Filled 5 missing rows in `data/attendance/Attendance_Template.*` and
  `data/scores/ScoreEntry_MidtermExam_Template.*`.** Both files had 76 rows
  against the 81-student `enroll_bsse_students.xlsx` roster; comparing by
  Full Name found the same 5 missing from both: Junaid Malik, Nimra Sheikh,
  Rayyan Chaudhry, Shahzad Baig, Zain Abbasi (Father's Name/Seat No pulled
  from the roster — "Zain Abbasi" is ambiguous by name alone, there's a
  second student with that name in a different batch; the roster file
  already disambiguates to the right one). Filled with plausible values in
  the same range as the surrounding data and re-sorted alphabetically; both
  files now have exactly 81 rows matching the roster 1:1, xlsx and PDF.
  **Follow-up**: the remaining 76 rows' Seat No values (stale since the
  live-system reseat) were then updated too, matched by Full Name against
  `enroll_bsse_students.xlsx` (no duplicate names within this 81-student
  roster) — every row in both files now carries the current seat number,
  xlsx and PDF.
- **Enrollments tab shows an enrolled-student count** ("N students
  enrolled") next to the search box, mirroring the Attendance tab's count —
  total enrolled, not the filtered/visible count.
- **Score Entry gained search by Name or Seat No.** `ScoreEntryCard` (on the
  assessment detail page) now filters its student rows the same way
  Attendance/Enrollments do; manual score entry and the existing "Upload
  Scores" import are otherwise unchanged.
- **5 students marked ineligible, removed from Attendance/Scores.**
  `enroll_bsse_students.xlsx/.pdf`'s `Eligible` column flipped to `No` for
  Seat No `...038/050/055/061/078` (Junaid Malik, Nimra Sheikh, Rayyan
  Chaudhry, Shahzad Baig, Zain Abbasi — the same 5 added two changes ago).
  They stay in the roster file (ineligible is a real, visible status there,
  not a deletion), but were removed entirely from
  `Attendance_Template.*` and `ScoreEntry_MidtermExam_Template.*` (81 → 76
  rows in both), since an ineligible student shouldn't be tracked for
  attendance or scoring.
- **Fixed a real bug in `Attendance_Template.*` / `ScoreEntry_MidtermExam_
  Template.*`: a decorative title row was breaking the actual upload
  parser.** `app/services/file_parsers.py`'s `parse_excel`/`parse_pdf` (used
  by every upload endpoint in this app: Upload Attendance, Upload Scores,
  Add Students via File, admin bulk import) always treats the sheet's first
  row as the header. These two files had `Title / blank / real header /
  data`, so the parser read the *title* as the header and the *real header
  row* as the first data row — a phantom "student" literally named "Full
  Name" with seat no "Seat No" (explaining the "Full Name equals Full Name"
  row reported), and every real row's number was off by two from where a
  faculty member would expect. Fixed by stripping the title/blank rows so
  the real header is row 1, matching the structure
  `data/add_students/{BSSE_students,enroll_bsse_students}.xlsx` already
  had (and were never affected). Verified end-to-end against the real DB
  via `attendance_import_service.build_preview` /
  `score_import_service.build_preview` directly: 76/76 attendance rows
  `ready`, row 2 correctly resolves to the actual first student
  (alphabetically, Abdul Aziz) with the right `matched_student_id`, no
  phantom rows.
- **Upload Assessment Paper now suggests a CLO tag per question, straight
  from the document.** `question_extractor.py`'s prompt gained a
  `clo_hint` field per question (e.g. "[CLO-7]" marked next to it in the
  paper) alongside the existing answer-key fields; a new
  `assessment_paper_import_service.match_clo()` resolves that hint against
  the course's real CLOs (exact code match first, ignoring
  punctuation/case, then a fuzzy title-match fallback for a hint that names
  the CLO instead of coding it — e.g. "Virtual Memory"), never guessing
  when nothing lines up. `ExtractedQuestionRow` gained `clo_id`, and the
  router now loads the course's CLOs to pass through.
  **The manual CLO Select and "Suggest with AI" button in the confirmation
  preview are unchanged and still fully usable** — a resolved `clo_id` is
  only ever a pre-filled starting point (labeled "Detected from document"
  in `PaperImportModal`), never a replacement for faculty review; picking a
  different CLO or re-running "Suggest with AI" clears that label. Verified
  live against the real Groq API and the real Operating Systems course/CLOs
  (not just monkeypatched): both `data/assessment_paper/` PDFs — now
  annotated with `[CLO-7]`/`[CLO-8]` tags and a full answer key (correct
  MCQ option, fill-blank answer, true/false answer) — resolve every
  question to the right `clo_id` and the right answer, `all_matched: True`,
  zero warnings. New tests: `match_clo` unit tests, a `clo_hint` parsing
  test in `question_extractor`, and an API-level test asserting a matched
  vs. unmatched hint resolves/doesn't resolve through the router.
- **`data/scores/` split into one file per assessment.** The single
  Midterm-targeted `ScoreEntry_MidtermExam_Template.*` is gone, replaced by
  `ScoreEntry_Quiz3_Template.*` and `ScoreEntry_Assignment3_Template.*` --
  each matching that specific assessment's real, now-persisted questions
  (Quiz #3: 5 questions, caps 3/2/2/2/1 = 10; Assignment #3: 2 questions,
  caps 3/2 = 5; Assignment #3's questions didn't exist yet, created via
  `question_service.bulk_create_questions` with the same text/marks/CLO
  tags as the paper). Both use the 76 eligible students from
  `enroll_bsse_students.xlsx`, header-row-first (no title row, per the
  parser bug fixed last turn). Verified against the real
  `score_import_service.build_preview`: 76/76 ready in both files, every
  `Qn` column alias-matched, zero warnings.
- **Fixed a second, more general parser bug: multi-page PDF uploads got a
  phantom "student" row at every page break.** Found via manual testing of
  the PDFs above (the row-1 title-row bug from last turn was fixed, but a
  *different* bug remained). `file_parsers.py::parse_pdf` reads every
  page's table via `pdfplumber.extract_tables()`, but every multi-page PDF
  this codebase generates uses reportlab's `repeatRows=1` to redraw the
  header row at the top of each page for readability when printed —
  pdfplumber faithfully extracts that redraw too, so page 2 onward each
  contributed one extra row that was *exactly* the column headers (a
  "student" literally named "Full Name" with seat no "Seat No", appearing
  at *every* page boundary, not just once). Fixed by skipping any row after
  the first that's an exact match for the header row. This is a real fix in
  the shared parser, not the data files — it fixes every multi-page PDF
  upload across the whole app (rosters, attendance, scores, admin bulk
  import), not just these five. New `tests/test_file_parsers.py` (this
  module had no dedicated test file before): a synthetic 80-row multi-page
  PDF confirms zero repeated-header rows survive, a single-page PDF is
  provably unaffected, and a row that merely *shares* one cell's text with
  the header (but isn't identical across every column) is confirmed to
  survive — only an exact full-row match is treated as a repeat. Re-verified
  every PDF in `data/` (scores, attendance, add_students) has zero phantom
  rows, and re-ran `score_import_service.build_preview` against the real
  Quiz #3 assessment: 76/76 ready, zero duplicates, zero not-found.
- **Score Entry gets the same backlog highlighting as Attendance/
  Enrollments.** `ScoreEntryCard` now fetches the course (for `semester`)
  alongside its existing enrollments/students/scores calls, sorts backlog
  students (via the same `isBacklogStudent` check) to the bottom of the
  roster, and renders them with the amber row highlight + "Backlog" badge —
  identical treatment across all three tables now.
- **Score Entry's save error moved to the top of the card.** The
  save-failure message (e.g. a rejected `marks_obtained` exceeding a
  question's cap) previously rendered below the whole student table,
  off-screen for a large roster; `ScoreEntryCard` now shows it (and the
  success message) right under the header, above the search box and table,
  matching the error-placement convention every other panel in this app
  already uses.

## 2026-08-19 — CLO, Assessments, Export, Score Entry & Attendance updates

A round of six faculty-facing additions layered onto the existing modules,
each reusing an established pattern rather than inventing a new one.

- **AI-Based CLO Creation** (`app/ml/clo_generator.py`, new dep `groq`):
  the first *generative* AI in this codebase — every prior "AI" feature
  (CLO↔PLO mapping, question↔CLO tagging) was `all-MiniLM-L6-v2` embedding
  *similarity search*, which cannot write new text. Faculty give a target
  PLO(s), a topic, and free-text requirements; a Groq-hosted call (model:
  `openai/gpt-oss-120b` — the originally-picked `llama-3.3-70b-versatile`
  turned out to be deprecated/404 on Groq's current catalog, swapped after
  confirming the replacement against this account's live `models.list()`)
  returns a suggested title/description/bloom level as strict JSON.
  Nothing is saved until the faculty reviews and edits the suggestion and
  explicitly clicks "Add CLO" (`POST /courses/{id}/clos/generate` returns
  the suggestion only; the existing `createClo` does the actual write).
  Kept fully separate from the CLO→PLO mapping modal. Needs `GROQ_API_KEY`
  in `.env` (optional — the rest of the app boots and tests run without it).
- **Assessment/question marks must be > 0.** `total_marks` and `marks` were
  `>= 0` everywhere (schema + DB `CheckConstraint`); tightened to `> 0` on
  both (migration `a41902e022ec` — hand-written, since autogenerate doesn't
  diff `CHECK` constraint *bodies*, only presence by name). Frontend inputs
  and submit-time validation updated in the three places marks are entered
  (`AssessmentsPanel`, `QuestionFormModal`, `BulkQuestionModal`). Deliberately
  untouched: `ScoreEntry.marks_obtained` and `AttendanceEntry.attendance_percentage`
  stay `>= 0` — a student scoring/attending 0 is valid data; this rule is
  about the ceiling, not the obtained value.
- **Per-item "Suggest with AI" in bulk question creation.** `BulkQuestionModal`
  (MCQ/Fill-in-the-Blank/True-False, created N-at-a-time) now has the same
  "Suggest with AI" CLO-tagging button `QuestionFormModal` already had for a
  single question, once per item. No backend change — reuses the existing
  `POST /assessments/{id}/questions/suggest-tag` endpoint.
- **Export assessment to PDF/Word, with a PDF preview.** New
  `assessment_export_service.py` (distinct from the existing course-level
  attainment PDF/Excel export) renders an actual exam paper: course title
  centered at top, assessment name centered below it, then a boxed two-column
  meta grid (Total Marks / Course Code / Instructor on the left, Allocated
  Time / Date on the right, each field in its own bordered cell), then
  numbered questions in printable format (A4, ReportLab; new dep
  `python-docx` for the `.docx` path) — never the correct answers. The
  question-row marks column is sized to the same content width as the meta
  grid so both blocks' right edges line up, and MCQ/answer lines are slightly
  indented under their question. New nullable `assessments.duration_minutes`
  column ("Allocated Time" didn't exist on the model; "Instructor" reuses
  `Course.owner_faculty_id`). Preview: the frontend fetches the PDF's bytes
  once and renders them in an iframe (the real generated file, not an HTML
  mirror); "Download PDF" reuses that same blob rather than re-fetching, so
  what's previewed is guaranteed to match what's downloaded. Word export is
  direct-download only, per spec.
- **Upload Scores** and **Upload Attendance**: both follow the exact
  upload → preview (writes nothing) → confirm two-step pattern already
  established by the admin bulk student import and the faculty enrollment
  roster import (`file_parsers.py` + `column_matcher.py` + a
  schema/service/router triplet + a modal copying `EnrollImportModal.jsx`'s
  state machine). Both `confirm` steps delegate to the *existing*
  `score_service.bulk_enter_scores` / `attendance_service.bulk_set_attendance`
  — no parallel write path, so the same validation applies at commit time
  too, as defense in depth even if a row were somehow marked "ready"
  incorrectly. Manual entry (`ScoreEntryCard`, `AttendancePanel`) is
  unchanged. Unmatched/invalid rows are always shown with a reason, never
  silently dropped.
  - Score-column matching (`app/ml/column_matcher.py::match_question_columns`)
    deliberately does **not** use the embedding-similarity fallback the other
    matchers rely on: "question 3" vs "question 4" differ only by a number
    token surrounded by identical words, so MiniLM cosine similarity between
    them is unreliable noise. Uses alias matching ("Q1", "Question 1", ...)
    then a positional fallback (left-to-right by question number) that only
    fires when the leftover-column and leftover-question counts match, and
    is flagged in the preview (`matched_by: "position"`) for faculty to
    visually confirm.
  - Fixed a latent cache bug found while building this:
    `column_matcher._encode_prompts` cached embeddings by `id(field_prompts)`,
    which only worked because the two existing field-prompt dicts were
    module-level constants that live forever. A short-lived dict (built fresh
    per score-import request) can have its `id()` reused by Python after
    garbage collection, which would silently serve a stale/wrong cached
    embedding. Now keyed by dict content instead.
- **Attendance tab UX**: `AttendancePanel.jsx` now sorts the roster by Seat
  No. (numeric-aware, so `...007` sorts before `...081`) instead of whatever
  order the enrollments API returned; a live search box filters by Name *or*
  Seat No (the existing Enrollments-tab search only covered Seat No); and a
  new "Attendance below X%" number filter narrows the table to students
  whose currently-shown attendance value is under a faculty-chosen threshold
  (students with no attendance recorded yet are excluded from that filter
  rather than treated as 0%). All client-side over already-loaded data, no
  backend change.
- **Tests**: `test_clo_generator.py`, `test_assessment_export.py`,
  `test_column_matcher.py`, `test_score_import.py` (all new), plus new cases
  in `test_plos_clos.py`, `test_assessments.py`, `test_attendance.py`. One
  pre-existing test (`test_questions_with_zero_marks_yield_zero`) was removed
  as a direct consequence of the marks-must-be->0 rule — its scenario (a
  0-mark question) is no longer constructible, and the zero-division guard it
  checked is still covered by `test_clo_with_no_tagged_questions_yields_zero_not_error`
  via the realistic path (a CLO with no tagged questions at all). **357
  backend tests passing** (was 313). `npm run lint` / `npm run build` clean.
  `alembic check` clean.

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
