from datetime import date, datetime, timedelta
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    field_validator,
    model_validator,
)

from .jalali import format_jalali, format_jalali_datetime
from .palette import DEFAULT_PROJECT_COLOR, is_valid_project_color
from .phones import normalize_phone


def resolve_due_date(
    due_date: date | None,
    due_in_days: int | None,
) -> date | None:
    if due_date is not None:
        return due_date
    if due_in_days is not None:
        return date.today() + timedelta(days=due_in_days)
    return None


class UserRegister(BaseModel):
    full_name: str = Field(min_length=1, max_length=100)
    phone: str
    password: str = Field(min_length=8, max_length=128)

    @field_validator("full_name")
    @classmethod
    def clean_full_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("full name must not be blank")
        return value

    @field_validator("phone")
    @classmethod
    def clean_phone(cls, value: str) -> str:
        return normalize_phone(value)

    @field_validator("password")
    @classmethod
    def password_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("password must not be blank")
        return value


class LoginRequest(BaseModel):
    phone: str
    password: str = Field(min_length=1, max_length=128)

    @field_validator("phone")
    @classmethod
    def clean_phone(cls, value: str) -> str:
        return normalize_phone(value)


class UserBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    phone: str


class UserRead(UserBrief):
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    color: str = DEFAULT_PROJECT_COLOR

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("project name must not be blank")
        return value

    @field_validator("color")
    @classmethod
    def clean_color(cls, value: str) -> str:
        if not is_valid_project_color(value):
            raise ValueError("unknown project color")
        return value


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    color: str | None = None

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("project name must not be blank")
        return value

    @field_validator("color")
    @classmethod
    def clean_color(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if not is_valid_project_color(value):
            raise ValueError("unknown project color")
        return value

    @model_validator(mode="after")
    def name_cannot_be_null(self) -> "ProjectUpdate":
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("name cannot be null")
        if "color" in self.model_fields_set and self.color is None:
            raise ValueError("color cannot be null")
        return self


class ProjectSummary(BaseModel):
    id: int
    name: str
    description: str | None
    color: str
    owner_id: int
    role: str
    member_count: int
    card_count: int
    done_count: int
    progress_percent: int
    assigned_to_me_count: int = 0
    created_at: datetime


class MemberRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user: UserBrief
    role: str
    created_at: datetime


class InvitationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    phone: str
    created_at: datetime


class MemberInviteResult(BaseModel):
    status: Literal["member", "invited"]
    member: MemberRead | None = None
    invitation: InvitationRead | None = None


class MemberInviteRequest(BaseModel):
    phone: str

    @field_validator("phone")
    @classmethod
    def clean_phone(cls, value: str) -> str:
        return normalize_phone(value)


class ColumnCreate(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    is_done: bool = False

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("column name must not be blank")
        return value


class ColumnUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=60)
    is_done: bool | None = None

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("column name must not be blank")
        return value

    @model_validator(mode="after")
    def columns_cannot_be_null(self) -> "ColumnUpdate":
        for field_name in ("name", "is_done"):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class CardCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    column_id: int | None = None
    assignee_ids: list[int] = Field(default_factory=list)
    priority: Literal["low", "normal", "high", "urgent"] = "normal"
    due_date: date | None = None
    due_in_days: int | None = Field(default=None, ge=0, le=3650)

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("title must not be blank")
        return value

    @model_validator(mode="after")
    def due_fields_are_exclusive(self) -> "CardCreate":
        if self.due_date is not None and self.due_in_days is not None:
            raise ValueError("set either due_date or due_in_days, not both")
        return self


class CardUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    assignee_ids: list[int] | None = None
    priority: Literal["low", "normal", "high", "urgent"] | None = None
    due_date: date | None = None
    due_in_days: int | None = Field(default=None, ge=0, le=3650)

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("title must not be blank")
        return value

    @model_validator(mode="after")
    def validate_fields(self) -> "CardUpdate":
        if "title" in self.model_fields_set and self.title is None:
            raise ValueError("title cannot be null")
        if "priority" in self.model_fields_set and self.priority is None:
            raise ValueError("priority cannot be null")
        if self.due_date is not None and self.due_in_days is not None:
            raise ValueError("set either due_date or due_in_days, not both")
        return self


class CardMove(BaseModel):
    column_id: int
    position: int = Field(default=0, ge=0)


class AssigneesUpdate(BaseModel):
    user_ids: list[int] = Field(default_factory=list)


class CardRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    column_id: int
    title: str
    description: str | None
    priority: str
    due_date: date | None
    position: int
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None
    created_by: UserBrief | None = None
    assignees: list[UserBrief]

    @computed_field
    @property
    def days_remaining(self) -> int | None:
        if self.due_date is None or self.completed_at is not None:
            return None
        return (self.due_date - date.today()).days

    @computed_field
    @property
    def due_date_jalali(self) -> str | None:
        if self.due_date is None:
            return None
        return format_jalali(self.due_date)

    @computed_field
    @property
    def completed_at_jalali(self) -> str | None:
        if self.completed_at is None:
            return None
        return format_jalali_datetime(self.completed_at)


class ColumnRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    position: int
    is_done: bool
    cards: list[CardRead]


class BoardRead(BaseModel):
    id: int
    name: str
    description: str | None
    color: str
    owner_id: int
    role: str
    members: list[MemberRead]
    invitations: list[InvitationRead]
    columns: list[ColumnRead]


class MyTaskRead(BaseModel):
    id: int
    title: str
    priority: str
    due_date: date | None
    due_date_jalali: str | None
    days_remaining: int | None
    is_done: bool
    completed_at: datetime | None
    completed_at_jalali: str | None
    project_id: int
    project_name: str
    project_color: str
