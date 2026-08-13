from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.models.user import UserRole


class UserCreate(BaseModel):
    email: EmailStr
    # Optional: when omitted, `auth_service.register_user` generates one
    # (same criteria as the bulk-import flow) -- lets a caller like the
    # manual "Add Student" form skip asking a human to pick a password.
    password: str | None = Field(default=None, min_length=8)
    full_name: str = Field(min_length=1, max_length=255)
    role: UserRole
    enrollment_no: str | None = None
    seat_no: str | None = None
    father_name: str | None = None
    # Required (from the caller) only for sub_admin, who a super_admin assigns
    # to a specific department. For faculty/student, whatever is sent here is
    # ignored -- the service forces it to the creating sub_admin's own
    # department. See user_service.create_user_scoped.
    dept_id: int | None = None
    # Required for sub_admin ("Employee ID" in the UI) and faculty ("Faculty
    # ID" in the UI) -- same column, different label per role.
    employee_id: str | None = None

    @model_validator(mode="after")
    def _check_role_specific_fields(self) -> "UserCreate":
        # Whether a *caller* may create a super_admin at all is an
        # authorization question, not a data-shape one -- enforced in
        # user_service.create_user_scoped, not here. This validator only
        # checks internal consistency, so scripts/seed_admin.py (the one
        # sanctioned way to create a super_admin) can still use this schema
        # directly without going through that authorization path.
        if self.role == UserRole.super_admin:
            return self

        if self.role == UserRole.sub_admin:
            if self.dept_id is None:
                raise ValueError("dept_id is required when creating a sub_admin")
            if self.employee_id is None:
                raise ValueError("employee_id is required when creating a sub_admin")
            if self.enrollment_no is not None or self.seat_no is not None:
                raise ValueError("sub_admin accounts cannot have enrollment_no/seat_no")
            if self.father_name is not None:
                raise ValueError("father_name is only valid for student accounts")
            return self

        if self.role == UserRole.student:
            if self.employee_id is not None:
                raise ValueError("employee_id is only valid for sub_admin/faculty accounts")
            if not self.enrollment_no:
                raise ValueError("enrollment_no is required for student accounts")
            if not self.seat_no:
                raise ValueError("seat_no is required for student accounts")
            if not self.father_name:
                raise ValueError("father_name is required for student accounts")
        elif self.role == UserRole.faculty:
            if not self.employee_id:
                raise ValueError("employee_id is required for faculty accounts")
            if self.enrollment_no is not None or self.seat_no is not None:
                raise ValueError("faculty accounts cannot have enrollment_no/seat_no")
            if self.father_name is not None:
                raise ValueError("father_name is only valid for student accounts")

        return self


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    role: UserRole | None = None
    enrollment_no: str | None = None
    seat_no: str | None = None
    father_name: str | None = None
    is_active: bool | None = None
    dept_id: int | None = None
    employee_id: str | None = None


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    role: UserRole
    enrollment_no: str | None
    seat_no: str | None
    father_name: str | None
    is_active: bool
    dept_id: int | None
    employee_id: str | None


class UserPasswordRead(BaseModel):
    """Response for the dedicated password-reveal endpoint. Deliberately
    separate from UserRead so a password never appears in a list/table
    response -- only this one narrow, scoped endpoint returns it."""

    password: str | None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str
