from app.models.clo import CLO
from app.models.course import Course
from app.models.department import Department
from app.models.mapping import CloPloMapping
from app.models.plo import PLO
from app.models.program import Program
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
]
