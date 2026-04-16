from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class EmployeeResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    job_title: str | None
    department: str | None
    phone: str | None
    photo_url: str | None
    created_at: datetime | None

    model_config = {"from_attributes": True}


class EmployeeListResponse(BaseModel):
    items: list[EmployeeResponse]
    total: int
    page: int
    per_page: int
    pages: int


class ProfileUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    job_title: str | None = Field(default=None, max_length=255)
    department: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=50)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)
