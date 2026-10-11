from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from src import services
from src.api.deps import require_roles
from src.core.database import get_db
from src.models.schedule import Schedule
from src.models.user import Role, User
from src.schemas.school import JournalOut, LessonOut

router = APIRouter(tags=["schedule"])


@router.get("/student/schedule", response_model=list[LessonOut])
def student_schedule(
    user: User = Depends(require_roles(Role.STUDENT, Role.PARENT)),
    db: Session = Depends(get_db),
):
    student = services.resolve_student(db, user)
    return services.class_lessons(db, student.class_id) if student else []


@router.get("/student/grades", response_model=list[JournalOut])
def student_grades(
    user: User = Depends(require_roles(Role.STUDENT, Role.PARENT)),
    db: Session = Depends(get_db),
):
    student = services.resolve_student(db, user)
    return services.student_grades(db, student.id) if student else []


@router.get("/teacher/schedule", response_model=list[LessonOut])
def teacher_schedule(user: User = Depends(require_roles(Role.TEACHER)), db: Session = Depends(get_db)):
    return db.scalars(select(Schedule).where(Schedule.teacher_id == user.id).order_by(Schedule.weekday, Schedule.start_time)).all()
