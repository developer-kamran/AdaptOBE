from pydantic import BaseModel, ConfigDict


class CLOAttainmentSummary(BaseModel):
    clo_id: int
    code: str
    title: str
    class_average: float
    is_achieved: bool
    student_count: int


class PLOAttainmentSummary(BaseModel):
    plo_id: int
    code: str
    title: str
    class_average: float


class HeatmapCell(BaseModel):
    clo_id: int
    plo_id: int
    strength: int


class StudentCLOAttainment(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    student_id: int
    clo_id: int
    attainment_percentage: float
    is_achieved: bool


class CourseAttainmentReport(BaseModel):
    course_id: int
    threshold: float
    student_count: int
    clo_attainment: list[CLOAttainmentSummary]
    plo_attainment: list[PLOAttainmentSummary]
    heatmap: list[HeatmapCell]


class StudentProgressReport(BaseModel):
    student_id: int
    course_id: int
    clo_attainment: list[StudentCLOAttainment]
