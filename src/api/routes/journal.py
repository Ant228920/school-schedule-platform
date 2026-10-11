from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src import services
from src.api.deps import get_current_user, require_roles
from src.core.database import get_db
from src.models.journal import JournalRecord
from src.models.user import Role, User
from src.schemas.school import GradeCreate, GradeUpdate, JournalOut

router = APIRouter(prefix="/journal", tags=["journal"])


@router.post("", response_model=JournalOut, status_code=201)
def create_record(
    data: GradeCreate,
    teacher: User = Depends(require_roles(Role.TEACHER)),
    db: Session = Depends(get_db),
):
    return services.add_grade(db, teacher, **data.model_dump())


@router.get("/{record_id}", response_model=JournalOut)
def get_record(
    record_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = db.get(JournalRecord, record_id)
    if not record:
        raise HTTPException(404, "Record not found")
    if not services.can_view_record(user, record):  # IDOR-захист
        raise HTTPException(403, "Access denied")
    return record


@router.patch("/{record_id}", response_model=JournalOut)
def update_record(
    record_id: int,
    data: GradeUpdate,
    user: User = Depends(require_roles(Role.TEACHER, Role.ADMIN)),
    db: Session = Depends(get_db),
):
    return services.update_grade(db, user, record_id, data.grade)
