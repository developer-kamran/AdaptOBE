# CLAUDE.md - AdaptOBE Development Guidelines & Architecture

## 1. Project Overview
AdaptOBE is an Intelligent Outcome-Based Education (OBE) Attainment & Adaptive Learning Platform for academic institutions. It automates Course Learning Outcome (CLO) to Program Learning Outcome (PLO) mapping using NLP sentence embeddings, calculates direct attainment from assessment scores, and applies machine learning (XGBoost + SHAP) for student risk prediction.

---

## 2. Technology Stack & Environment
* **Frontend:** React.js (JavaScript / `.jsx` / ECMAScript) + TailwindCSS (No TypeScript)
* **Backend:** Python 3.11+ with FastAPI (Async architecture)
* **Database:** Local PostgreSQL 18 instance with `pgvector` extension enabled
* **ORM / Migrations:** SQLAlchemy 2.0 (AsyncSession) + Alembic
* **Validation:** Pydantic v2 (do not use v1-style validators or `Config` classes)
* **Authentication:** JWT (`python-jose`) + bcrypt password hashing
* **AI / ML Runtime:** PyTorch, `sentence-transformers` (`all-MiniLM-L6-v2`), scikit-learn, XGBoost, SHAP
* **Realtime:** Native FastAPI WebSockets
* **Containerization:** Deferred to final phase (No Docker during local module development)

---

## 3. Project Structure

```
/backend
  /app
    /models        (SQLAlchemy ORM models)
    /schemas       (Pydantic v2 request/response schemas)
    /routers       (FastAPI route handlers, one file per resource)
    /services      (business logic — attainment calc, mapping, etc.)
    /ml            (embedding generation, XGBoost training/inference, SHAP)
    /core          (config, security/JWT, dependencies)
    main.py
  /alembic
    /versions
  /tests
  .env             (gitignored — never committed)
  .env.example     (committed — documents required vars, no real values)
/frontend
  /src
    /components
    /pages
    /hooks
    /api           (fetch/axios wrappers per resource)
    /context or /store  (state management — decide and document here once chosen)
```

Keep business logic (attainment math, ML calls) out of routers — routers should call into `/services` or `/ml`, not contain calculation logic inline. This keeps the math testable in isolation.

---

## 4. Secrets & Environment Configuration
* All secrets (DB connection string, JWT secret key, any API keys) live in `.env` and are loaded via `python-dotenv` / `pydantic-settings`. **Never hardcode these in source files.**
* `.env` must be in `.gitignore` from the first commit. Commit a `.env.example` with placeholder values instead.
* Local Postgres connection: `postgresql+asyncpg://user:password@localhost:5432/adaptobe` — this value belongs in `.env`, not inline in `database.py`.
* CORS: FastAPI must explicitly allow the local Vite/React dev origin (e.g. `http://localhost:5173`) during development.

---

## 5. Local Development Rules & Commands

### Backend Commands (FastAPI / Python)
* **Run Virtual Environment:** `source venv/bin/activate` (Linux/Mac) or `venv\Scripts\activate` (Windows)
* **Start API Server:** `uvicorn app.main:app --reload --port 8000`
* **Run Migrations:** `alembic upgrade head`
* **Create Migration:** `alembic revision --autogenerate -m "description"`
* **Run Backend Tests:** `pytest -v`

### Frontend Commands (React / JavaScript)
* **Start Dev Server:** `npm run dev`
* **Run Linter:** `npm run lint`
* **Build Production:** `npm run build`

### Coding & Architectural Conventions
1. **JavaScript Only for Frontend:** Use standard `.jsx` and `.js` files. Avoid TypeScript syntax or `.ts/.tsx` extensions.
2. **Local PostgreSQL 18 First:** Connect directly to the local PostgreSQL 18 service. Do not generate Docker or `docker-compose.yml` files until Phase 7.
3. **Async SQLAlchemy:** Use `AsyncSession` for all database interactions. Prevent blocking I/O calls in FastAPI endpoints.
4. **Role-Based Access Control (RBAC):** Every protected endpoint must explicitly verify user role (`admin`, `faculty`, or `student`) via JWT middleware.
5. **Explainable AI:** All risk predictions must return both a classification/score and a SHAP explainability payload.
6. **Business logic stays out of routers:** routers call `/services` or `/ml` functions; they don't contain calculation logic inline.

### Git Conventions
* Commit after each completed module (not mid-module), with a descriptive message referencing the module (e.g. `Module 2: CLO-PLO embedding mapping engine`).
* Do not commit `.env`, `venv/`, `node_modules/`, or `__pycache__/`.

---

## 6. Database Schema & Vector Storage Specification (PostgreSQL 18)

Ensure the `pgvector` extension is enabled (`CREATE EXTENSION IF NOT EXISTS vector;`) before running migrations.

### Core Relational & Vector Tables
* `users`: `id (PK)`, `email (UNIQUE)`, `password_hash`, `full_name`, `role (ENUM: admin, faculty, student)`, `enrollment_no (UNIQUE, nullable)`, `seat_no (UNIQUE, nullable)`, `is_active`
* `departments`: `id (PK)`, `name`, `code (UNIQUE)`
* `programs`: `id (PK)`, `dept_id (FK)`, `name`, `total_semesters`
* `plos`: `id (PK)`, `program_id (FK)`, `code (e.g., PLO-1)`, `title`, `description`, `domain`, `embedding vector(384)`
* `courses`: `id (PK)`, `program_id (FK)`, `owner_faculty_id (FK)`, `code (UNIQUE)`, `name`, `credit_hours`, `semester`
* `clos`: `id (PK)`, `course_id (FK)`, `code (e.g., CLO-1)`, `title`, `description`, `bloom_level`, `embedding vector(384)`
* `clo_plo_mappings`: `id (PK)`, `clo_id (FK)`, `plo_id (FK)`, `strength (1=weak, 2=mod, 3=strong)`, `is_ai_generated (BOOL)`, `similarity_score (FLOAT)`, `UNIQUE(clo_id, plo_id)`
* `course_enrollments`: `id (PK)`, `course_id (FK)`, `student_id (FK)`, `UNIQUE(course_id, student_id)`
* `assessments`: `id (PK)`, `course_id (FK)`, `title`, `type (ENUM: quiz, assignment, lab, midterm, final)`, `total_marks`, `weightage_percent`, `date`
* `questions`: `id (PK)`, `assessment_id (FK)`, `question_number`, `marks`, `clo_id (FK)`
* `student_scores`: `id (PK)`, `question_id (FK)`, `student_id (FK)`, `marks_obtained`
* `attainment_records`: `id (PK)`, `student_id (FK)`, `course_id (FK)`, `clo_id (FK)`, `attainment_percentage`, `is_achieved (BOOL)`
* `student_predictions`: `id (PK)`, `student_id (FK)`, `course_id (FK)`, `risk_level (ENUM: low, medium, high)`, `confidence_score`, `predicted_score`, `shap_explanation (JSONB)`

---

## 7. API Endpoint Catalog

| Method | Endpoint | Allowed Roles | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/auth/register` | Admin | Register new users with role enforcement |
| `POST` | `/api/v1/auth/login` | Public | Authenticate user & return JWT access/refresh tokens |
| `POST` | `/api/v1/admin/departments` | Admin | Create department & assign faculty |
| `POST` | `/api/v1/admin/programs` | Admin | Create academic programs |
| `POST` | `/api/v1/admin/plos` | Admin | Create PLO and generate vector embedding |
| `POST` | `/api/v1/courses` | Faculty | Create course (assigns creator as owner) |
| `POST` | `/api/v1/courses/{id}/clos` | Faculty | Create CLO and generate `vector(384)` embedding |
| `POST` | `/api/v1/mappings/suggest` | Faculty | Top-3 PLO suggestions via cosine similarity |
| `POST` | `/api/v1/mappings/confirm` | Faculty | Save CLO-PLO mapping with strength (1-3) |
| `POST` | `/api/v1/assessments` | Faculty | Create assessment (validates sum of weightage <= 100%) |
| `POST` | `/api/v1/assessments/{id}/scores` | Faculty | Bulk score entry & background attainment calculation |
| `GET` | `/api/v1/attainment/course/{id}` | Faculty/Admin | Get course-level CLO/PLO attainment & heatmap |
| `POST` | `/api/v1/ml/predict-risk/{course_id}` | Faculty | Run XGBoost risk prediction & generate SHAP JSON |
| `GET` | `/api/v1/student/progress` | Student | View personalized CLO attainment & weak gaps |

---

## 8. Mathematical Formulas & Edge Case Specifications

### CLO Attainment Calculation (Student Level)
For a specific CLO tagged across multiple questions:
```
CLO Attainment (%) = (Sum of Marks Obtained in CLO-Tagged Questions / Sum of Total Possible Marks for Those Questions) * 100
```

### PLO Attainment Calculation (Student Level)
Weighted average of mapped CLO attainments based on mapping strength:
```
PLO Attainment (%) = Sum(CLO Attainment * Strength) / Sum(Strength)
```

### Required Edge Case Handlings
* **Division by Zero:** If total possible marks for a CLO `= 0`, or `Sum(Strength) = 0`, return `0.00%` and log a warning; never throw an unhandled zero-division exception.
* **Absent Students:** If a student has no submitted score record for an assessment, default `marks_obtained` to `0.0`. Do not exclude enrolled students from class average denominators.
* **Assessment Recalculation:** Editing questions, CLO tags, or student scores must trigger an asynchronous recalculation transaction that updates `attainment_records` and broadcasts a WebSocket notification.
* **Threshold Flagging:** Compare class-average CLO attainment against the course threshold (default `50.0%`). Set `is_achieved = False` if below threshold.

Write pytest cases for every edge case above alongside the attainment engine implementation (Module 3) — not after.

---

## 9. AI/ML Specifications, Feature Vectors & SHAP JSON Schema

### AI Model 1: NLP Embedding & Similarity (`all-MiniLM-L6-v2`)
* **Library:** `sentence-transformers` via PyTorch.
* **Usage:** Generates 384-dimensional vector embeddings stored in PostgreSQL (`pgvector`).
* **Functions:**
  1. Automated CLO-to-PLO mapping recommendations using cosine similarity distance.
  2. AI-suggested question tagging: matches quiz/exam question text to the most relevant course CLO.

### AI Model 2: Student Risk Classifier (`XGBoost`)
* **Library:** `scikit-learn` + `xgboost`.
* **Usage:** Predicts student risk level (`low`, `medium`, `high`) per course.
* **Input Feature Schema:** Requires >= 5 assessment records per student with the following numeric features:
  * `attendance_percentage` (Float: 0.0 to 100.0)
  * `quiz_average_percentage` (Float: 0.0 to 100.0)
  * `assignment_average_percentage` (Float: 0.0 to 100.0)
  * `midterm_score_percentage` (Float: 0.0 to 100.0)
  * `current_avg_clo_attainment` (Float: 0.0 to 100.0)

### Explainable AI Output (`SHAP` JSON Schema)
Store and return explainability payloads in `student_predictions.shap_explanation` using this exact JSON format:
```json
{
  "base_value": 0.45,
  "predicted_risk": "high",
  "confidence": 0.89,
  "feature_contributions": [
    {
      "feature": "quiz_average_percentage",
      "value": 42.5,
      "shap_value": 0.24,
      "impact": "increased_risk"
    },
    {
      "feature": "attendance_percentage",
      "value": 68.0,
      "shap_value": 0.15,
      "impact": "increased_risk"
    }
  ]
}
```

---

## 10. Modular Development Roadmap (Execute Sequentially)

**Definition of done for every module:** implement the module, then run the relevant `pytest` (and `npm run lint` / build where frontend is involved) and confirm they pass before moving to the next module. Do not proceed to the next module with failing tests. Commit with a module-referencing message once done.

### Module 0: Local PostgreSQL 18 & Base Setup (No Docker)
* Install and run PostgreSQL 18 locally.
* Enable pgvector (`CREATE EXTENSION IF NOT EXISTS vector;`).
* Initialize FastAPI project structure, SQLAlchemy 2.0 AsyncSession, and Alembic migration scripts.
* Set up `.env` / `.env.example` and confirm the app boots and connects to the DB.

### Module 1: Auth & User Management
* Implement JWT authentication, bcrypt hashing, and registration validation (unique email, seat_no, enrollment_no).
* Build RBAC middleware enforcing Admin, Faculty, and Student access scopes.
* Implement Admin CRUD for users, departments, and academic programs.

### Module 2: OBE Course Management & AI Mapping Engine
* Build CRUD APIs for Courses, PLOs, and CLOs.
* Integrate sentence-transformers (`all-MiniLM-L6-v2`) to generate `vector(384)` embeddings upon PLO/CLO creation.
* Implement the `/api/v1/mappings/suggest` endpoint using PostgreSQL `<->` (cosine distance) operator to return top-3 PLO recommendations.

### Module 3: Assessments, Scoring & Direct Attainment Engine
* Implement Assessment CRUD and Question-to-CLO tagging.
* Add AI-suggested question tagging mode using `all-MiniLM-L6-v2` cosine similarity against CLO embeddings.
* Create bulk score entry endpoints with input validation (`marks_obtained <= total_marks`).
* Write unit tests (pytest) verifying CLO and PLO attainment mathematical accuracy across all edge cases (Section 8).

### Module 4: Faculty Dashboard, Real-time WebSockets & Analytics
* Build React (.jsx) Faculty Dashboard with TailwindCSS.
* Create CLO vs. PLO Heatmap grid showing mapping strengths and class averages.
* Connect FastAPI native WebSockets to broadcast instant dashboard refreshes when scores are updated.
* Implement report export engines for PDF and Excel.

### Module 5: ML Risk Prediction & Learning Gap Detection
* Train/integrate XGBoost classifier to predict student risk levels (low, medium, high).
* Integrate SHAP library to output feature-level explanations for every prediction.
* Implement automated detection of CLOs performing below the configurable threshold (default 50%).

### Module 6: Student Web Portal & Adaptive Learning
* Build Student Dashboard (.jsx) displaying personal CLO attainment breakdown and score history.
* Implement automated learning gap detection alerting students to weak CLOs.
* Build adaptive quiz generator that scales question difficulty based on student CLO performance.

### Module 7: Production Containerization & Deployment (Final Phase)
* Create optimized Dockerfile for Python/FastAPI backend and React frontend.
* Write production `docker-compose.yml` bundling FastAPI, PostgreSQL (with pgvector), and frontend static serving.
