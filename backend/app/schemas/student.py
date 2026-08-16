from pydantic import BaseModel

from app.models.question import QuestionType


# ---- Progress & score history ------------------------------------------------

class StudentCLOProgress(BaseModel):
    clo_id: int
    code: str
    title: str
    attainment_percentage: float
    is_weak: bool  # this student's own attainment is below the course threshold


class CourseProgress(BaseModel):
    course_id: int
    code: str
    name: str
    semester: int
    threshold: float
    overall_average: float
    weak_clo_count: int
    clo_progress: list[StudentCLOProgress]


class StudentProgressResponse(BaseModel):
    overall_average: float
    courses: list[CourseProgress]


class ScoreHistoryItem(BaseModel):
    assessment_id: int
    title: str
    type: str
    obtained: float
    total_marks: float
    percentage: float


class CourseScoreHistory(BaseModel):
    course_id: int
    items: list[ScoreHistoryItem]


# ---- Adaptive quiz -----------------------------------------------------------

class QuizOption(BaseModel):
    label: str
    text: str | None = None


class QuizQuestion(BaseModel):
    question_id: int
    clo_id: int
    clo_code: str
    question_type: QuestionType
    text: str
    options: list[QuizOption] | None = None  # populated for MCQ only


class AdaptiveQuiz(BaseModel):
    course_id: int
    questions: list[QuizQuestion]


class QuizAnswer(BaseModel):
    question_id: int
    # A JSON boolean (true/false) or a string (MCQ option label / fill-in text).
    answer: bool | str | None = None


class QuizSubmit(BaseModel):
    answers: list[QuizAnswer]


class QuizResultItem(BaseModel):
    question_id: int
    clo_id: int
    clo_code: str
    correct: bool


class QuizResult(BaseModel):
    course_id: int
    total: int
    correct: int
    score_percentage: float
    results: list[QuizResultItem]
    focus_clos: list[str]  # CLO codes the student still answered weakest on
