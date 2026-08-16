from app.models.assessment import Assessment, AssessmentType
from app.models.attainment import AttainmentRecord
from app.models.attendance import AttendanceRecord
from app.models.clo import CLO
from app.models.course import Course
from app.models.department import Department
from app.models.enrollment import CourseEnrollment
from app.models.mapping import CloPloMapping
from app.models.plo import PLO
from app.models.prediction import RiskLevel, StudentPrediction
from app.models.program import Program
from app.models.question import Question
from app.models.student_score import StudentScore
from app.models.user import User, UserRole

__all__ = [
    "User",
    "UserRole",
    "Department",
    "Program",
    "PLO",
    "Course",
    "CLO",
    "CloPloMapping",
    "Assessment",
    "AssessmentType",
    "Question",
    "StudentScore",
    "CourseEnrollment",
    "AttainmentRecord",
    "AttendanceRecord",
    "StudentPrediction",
    "RiskLevel",
]
