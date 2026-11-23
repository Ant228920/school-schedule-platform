"""Бізнес-логіка MVP. Використовується і JSON-ендпоінтами, і HTML-формами."""

import datetime as dt

from fastapi import HTTPException
from pydantic import EmailStr, TypeAdapter
from pydantic_core import ValidationError
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from src.core.cache import cache
from src.core.config import settings
from src.core.security import hash_password
from src.models.journal import JournalRecord
from src.models.schedule import Schedule
from src.models.school_class import SchoolClass
from src.models.user import Role, User


def get_user(db: Session, user_id: int) -> User | None:
    """Знімок користувача для перевірки доступу (кешується в Redis на CACHE_TTL_USER секунд).

    Повертає об'єкт User без прив'язки до сесії: читати можна id, email, full_name, role,
    is_active, class_id, child_id. Зв'язки (school_class) і hashed_password недоступні.
    """
    key = f"user:{user_id}"
    data = cache.get(key)
    if data is None:
        row = db.execute(
            select(User.id, User.email, User.full_name, User.is_active, User.class_id, User.child_id, User.role).where(User.id == user_id)
        ).one_or_none()
        if row is None:
            return None
        data = {
            "id": row.id,
            "email": row.email,
            "full_name": row.full_name,
            "is_active": row.is_active,
            "class_id": row.class_id,
            "child_id": row.child_id,
            "role": row.role.value,
        }
        cache.set(key, data, settings.CACHE_TTL_USER)
    return User(**{**data, "role": Role(data["role"])})


def create_class(db: Session, name: str) -> SchoolClass:
    name = name.strip()
    if db.scalar(select(SchoolClass).where(SchoolClass.name == name)):
        raise HTTPException(409, "Клас з такою назвою вже існує")
    school_class = SchoolClass(name=name)
    db.add(school_class)
    db.commit()
    db.refresh(school_class)
    return school_class


def create_lesson(
    db: Session,
    class_id: int,
    teacher_id: int,
    subject: str,
    room: str,
    weekday: int,
    start_time: dt.time,
) -> Schedule:
    if not db.get(SchoolClass, class_id):
        raise HTTPException(404, "Клас не знайдено")
    teacher = db.get(User, teacher_id)
    if not teacher or teacher.role != Role.TEACHER:
        raise HTTPException(400, "Вказаний користувач не є вчителем")
    clash = db.scalar(
        select(Schedule.id)
        .where(
            Schedule.weekday == weekday,
            Schedule.start_time == start_time,
            or_(Schedule.class_id == class_id, Schedule.teacher_id == teacher_id),
        )
        .limit(1)
    )
    if clash:
        raise HTTPException(409, "Конфлікт розкладу: клас або вчитель уже зайняті в цей час")
    lesson = Schedule(
        class_id=class_id,
        teacher_id=teacher_id,
        subject=subject.strip(),
        room=room.strip(),
        weekday=weekday,
        start_time=start_time,
    )
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return lesson


_email_adapter = TypeAdapter(EmailStr)


def _validate_links(db: Session, class_id: int | None, child_id: int | None) -> None:
    """Клас має існувати, а child_id — вказувати на учня."""
    if class_id is not None and not db.get(SchoolClass, class_id):
        raise HTTPException(404, "Клас не знайдено")
    if child_id is not None:
        child = db.get(User, child_id)
        if not child or child.role != Role.STUDENT:
            raise HTTPException(400, "child_id має вказувати на учня")


def create_user(
    db: Session,
    email: str,
    full_name: str,
    password: str,
    role: Role,
    class_id: int | None = None,
    child_id: int | None = None,
) -> User:
    """Створення акаунта адміністратором (будь-яка роль)."""
    email = email.strip()
    try:
        email = _email_adapter.validate_python(email)
    except ValidationError:
        raise HTTPException(400, "Некоректний email")
    if len(full_name.strip()) < 2:
        raise HTTPException(400, "ПІБ занадто короткий")
    if not 8 <= len(password) <= 72:
        raise HTTPException(400, "Пароль має містити від 8 до 72 символів")
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "Користувач з таким email уже існує")
    _validate_links(db, class_id, child_id)
    user = User(
        email=email,
        full_name=full_name.strip(),
        hashed_password=hash_password(password),
        role=role,
        class_id=class_id,
        child_id=child_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user(db: Session, admin: User, user_id: int, changes: dict) -> User:
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(404, "Користувача не знайдено")
    if target.id == admin.id and (changes.get("role", target.role) != target.role or changes.get("is_active") is False):
        raise HTTPException(400, "Адміністратор не може змінити власну роль або заблокувати себе")
    if changes.get("class_id") is not None and not db.get(SchoolClass, changes["class_id"]):
        raise HTTPException(404, "Клас не знайдено")
    if changes.get("child_id") is not None:
        child = db.get(User, changes["child_id"])
        if not child or child.role != Role.STUDENT:
            raise HTTPException(400, "child_id має вказувати на учня")
    for field, value in changes.items():
        setattr(target, field, value)
    db.commit()
    db.refresh(target)
    # роль / активність / клас змінилися: знімок користувача в кеші вже недійсний
    cache.delete(f"user:{target.id}")
    return target


def add_grade(
    db: Session,
    teacher: User,
    student_id: int,
    subject: str,
    grade: int,
    graded_on: dt.date | None,
) -> JournalRecord:
    student = db.get(User, student_id)
    if not student or student.role != Role.STUDENT:
        raise HTTPException(404, "Учня не знайдено")
    teaches = student.class_id is not None and db.scalar(
        select(Schedule.id)
        .where(
            Schedule.teacher_id == teacher.id,
            Schedule.class_id == student.class_id,
            Schedule.subject == subject,
        )
        .limit(1)
    )
    if not teaches:
        raise HTTPException(403, "Ви не викладаєте цей предмет у класі цього учня")
    record = JournalRecord(
        student_id=student.id,
        teacher_id=teacher.id,
        subject=subject,
        grade=grade,
        graded_on=graded_on or dt.date.today(),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def update_grade(db: Session, user: User, record_id: int, grade: int) -> JournalRecord:
    record = db.get(JournalRecord, record_id)
    if not record:
        raise HTTPException(404, "Запис не знайдено")
    if user.role == Role.TEACHER and record.teacher_id != user.id:
        raise HTTPException(403, "Це не ваш запис")
    record.grade = grade
    db.commit()
    db.refresh(record)
    return record


def can_view_record(user: User, record: JournalRecord) -> bool:
    if user.role == Role.ADMIN or user.id in (record.student_id, record.teacher_id):
        return True
    return user.role == Role.PARENT and user.child_id == record.student_id


def resolve_student(db: Session, user: User) -> User | None:
    """Учень бачить себе, батьки — свою дитину."""
    if user.role == Role.STUDENT:
        return user
    if user.role == Role.PARENT and user.child_id:
        child = get_user(db, user.child_id)
        return child if child and child.role == Role.STUDENT else None
    return None


def class_name(db: Session, class_id: int | None) -> str | None:
    """Назва класу окремим легким запитом (у get_user зв'язок school_class недоступний)."""
    if class_id is None:
        return None
    return db.scalar(select(SchoolClass.name).where(SchoolClass.id == class_id))


def class_lessons(db: Session, class_id: int | None) -> list[Schedule]:
    if class_id is None:
        return []
    return list(
        db.scalars(
            select(Schedule)
            .options(joinedload(Schedule.teacher))  # шаблон читає l.teacher.full_name: один JOIN замість N запитів
            .where(Schedule.class_id == class_id)
            .order_by(Schedule.weekday, Schedule.start_time)
        ).all()
    )


def student_grades(db: Session, student_id: int, limit: int = 50) -> list[JournalRecord]:
    return list(
        db.scalars(
            select(JournalRecord)
            .where(JournalRecord.student_id == student_id)
            .order_by(JournalRecord.graded_on.desc(), JournalRecord.id.desc())
            .limit(limit)
        ).all()
    )
