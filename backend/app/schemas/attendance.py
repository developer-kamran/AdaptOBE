from pydantic import BaseModel, ConfigDict, Field


class AttendanceEntry(BaseModel):
    student_id: int
    attendance_percentage: float = Field(ge=0, le=100)


class BulkAttendanceRequest(BaseModel):
    entries: list[AttendanceEntry] = Field(min_length=1)


class AttendanceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    course_id: int
    student_id: int
    attendance_percentage: float


class BulkAttendanceResponse(BaseModel):
    saved: int
