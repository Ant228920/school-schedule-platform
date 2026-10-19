"""HTML-кабінети ролей та обробники форм (MVP)."""

import datetime as dt

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src import services
from src.api.deps import require_roles
from src.core.database import get_db
from src.core.templating import templates
from src.models.journal import JournalRecord
from src.models.schedule import Schedule
from src.models.school_class import SchoolClass
from src.models.user import Role, User

router = APIRouter(include_in_schema=False)


def _int_or_none(value: str) -> int | None:
    value = value.strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        raise HTTPException(400, "Очікувалося число")


@router.get("/student/home")
def student_home(
    request: Request,
    user: User = Depends(require_roles(Role.STUDENT, Role.PARENT)),
    db: Session = Depends(get_db),
):
    student = services.resolve_student(db, user)
    lessons = services.class_lessons(db, student.class_id) if student else []
    grades = services.student_grades(db, student.id, limit=20) if student else []
    avg = round(sum(g.grade for g in grades) / len(grades), 1) if grades else None
    return templates.TemplateResponse(
        request,
        "student_home.html",
        {
            "user": user,
            "student": student,
            "lessons": lessons,
            "grades": grades,
            "avg": avg,
            "today": dt.date.today().weekday(),
        },
    )


# ---------- вчитель ----------
@router.get("/teacher/home")
def teacher_home(
    request: Request,
    user: User = Depends(require_roles(Role.TEACHER)),
    db: Session = Depends(get_db),
):
    lessons = list(db.scalars(select(Schedule).where(Schedule.teacher_id == user.id).order_by(Schedule.weekday, Schedule.start_time)).all())
    class_ids = {lesson.class_id for lesson in lessons}
    students = (
        list(db.scalars(select(User).where(User.role == Role.STUDENT, User.class_id.in_(class_ids)).order_by(User.full_name)).all())
        if class_ids
        else []
    )
    recent = db.scalars(select(JournalRecord).where(JournalRecord.teacher_id == user.id).order_by(JournalRecord.id.desc()).limit(15)).all()
    return templates.TemplateResponse(
        request,
        "teacher_home.html",
        {
            "user": user,
            "lessons": lessons,
            "students": students,
            "recent": recent,
            "subjects": sorted({lesson.subject for lesson in lessons}),
            "today": dt.date.today().weekday(),
            "today_date": dt.date.today().isoformat(),
        },
    )


@router.post("/web/teacher/grades")
def web_add_grade(
    student_id: int = Form(...),
    subject: str = Form(...),
    grade: int = Form(..., ge=1, le=12),
    graded_on: dt.date = Form(...),
    teacher: User = Depends(require_roles(Role.TEACHER)),
    db: Session = Depends(get_db),
):
    services.add_grade(db, teacher, student_id, subject, grade, graded_on)
    return RedirectResponse("/teacher/home", status_code=303)


@router.post("/web/teacher/grades/{record_id}")
def web_update_grade(
    record_id: int,
    grade: int = Form(..., ge=1, le=12),
    teacher: User = Depends(require_roles(Role.TEACHER)),
    db: Session = Depends(get_db),
):
    services.update_grade(db, teacher, record_id, grade)
    return RedirectResponse("/teacher/home", status_code=303)


# ---------- адміністратор ----------
@router.get("/admin/home")
def admin_home(
    request: Request,
    user: User = Depends(require_roles(Role.ADMIN)),
    db: Session = Depends(get_db),
):
    counts = dict(db.execute(select(User.role, func.count()).group_by(User.role)).all())
    users = list(db.scalars(select(User).order_by(User.id)).all())
    classes = list(db.scalars(select(SchoolClass).order_by(SchoolClass.name)).all())
    lessons = list(db.scalars(select(Schedule).order_by(Schedule.class_id, Schedule.weekday, Schedule.start_time)).all())
    return templates.TemplateResponse(
        request,
        "admin_home.html",
        {
            "user": user,
            "users": users,
            "classes": classes,
            "lessons": lessons,
            "teachers": [u for u in users if u.role == Role.TEACHER],
            "counts": counts,
            "Role": Role,
        },
    )


@router.post("/web/admin/classes")
def web_create_class(
    name: str = Form(..., min_length=1, max_length=20),
    _: User = Depends(require_roles(Role.ADMIN)),
    db: Session = Depends(get_db),
):
    services.create_class(db, name)
    return RedirectResponse("/admin/home", status_code=303)


@router.post("/web/admin/lessons")
def web_create_lesson(
    class_id: int = Form(...),
    teacher_id: int = Form(...),
    subject: str = Form(..., min_length=2),
    room: str = Form(..., min_length=1),
    weekday: int = Form(..., ge=0, le=4),
    start_time: dt.time = Form(...),
    _: User = Depends(require_roles(Role.ADMIN)),
    db: Session = Depends(get_db),
):
    services.create_lesson(db, class_id, teacher_id, subject, room, weekday, start_time)
    return RedirectResponse("/admin/home", status_code=303)


@router.post("/web/admin/users/{user_id}")
def web_update_user(
    user_id: int,
    role: Role = Form(...),
    class_id: str = Form(""),
    child_id: str = Form(""),
    is_active: str = Form(""),
    admin: User = Depends(require_roles(Role.ADMIN)),
    db: Session = Depends(get_db),
):
    services.update_user(
        db,
        admin,
        user_id,
        {
            "role": role,
            "class_id": _int_or_none(class_id),
            "child_id": _int_or_none(child_id),
            "is_active": bool(is_active),
        },
    )
    return RedirectResponse("/admin/home", status_code=303)
