from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from src import services
from src.api.deps import require_roles
from src.core.database import get_db
from src.models.school_class import SchoolClass
from src.models.user import Role, User
from src.schemas.school import ClassCreate, ClassOut, LessonCreate, LessonOut
from src.schemas.user import AdminUserUpdate, UserOut

router = APIRouter(prefix="/admin", tags=["admin"])
AdminOnly = Depends(require_roles(Role.ADMIN))


@router.get("/users", response_model=list[UserOut])
def list_users(_: User = AdminOnly, db: Session = Depends(get_db)):
    return db.scalars(select(User).order_by(User.id)).all()


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    data: AdminUserUpdate,
    admin: User = AdminOnly,
    db: Session = Depends(get_db),
):
    return services.update_user(db, admin, user_id, data.model_dump(exclude_unset=True))


@router.get("/classes", response_model=list[ClassOut])
def list_classes(_: User = AdminOnly, db: Session = Depends(get_db)):
    return db.scalars(select(SchoolClass).order_by(SchoolClass.name)).all()


@router.post("/classes", response_model=ClassOut, status_code=201)
def create_class(data: ClassCreate, _: User = AdminOnly, db: Session = Depends(get_db)):
    return services.create_class(db, data.name)


@router.post("/schedule", response_model=LessonOut, status_code=201)
def create_lesson(data: LessonCreate, _: User = AdminOnly, db: Session = Depends(get_db)):
    return services.create_lesson(db, **data.model_dump())
