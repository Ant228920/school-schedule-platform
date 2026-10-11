import datetime as dt

from pydantic import BaseModel, Field


class ClassCreate(BaseModel):
    name: str = Field(min_length=1, max_length=20)


class ClassOut(BaseModel):
    id: int
    name: str
    model_config = {"from_attributes": True}


class LessonCreate(BaseModel):
    class_id: int
    teacher_id: int
    subject: str = Field(min_length=2, max_length=100)
    room: str = Field(min_length=1, max_length=20)
    weekday: int = Field(ge=0, le=4)
    start_time: dt.time


class LessonOut(LessonCreate):
    id: int
    model_config = {"from_attributes": True}


class GradeCreate(BaseModel):
    student_id: int
    subject: str = Field(min_length=2, max_length=100)
    grade: int = Field(ge=1, le=12)
    graded_on: dt.date | None = None


class GradeUpdate(BaseModel):
    grade: int = Field(ge=1, le=12)


class JournalOut(BaseModel):
    id: int
    student_id: int
    teacher_id: int
    subject: str
    grade: int
    graded_on: dt.date
    model_config = {"from_attributes": True}
