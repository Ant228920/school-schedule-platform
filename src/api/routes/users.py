from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.deps import get_current_user
from src.core.database import get_db
from src.models.user import Role, User
from src.schemas.user import UserOut, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    data: UserUpdate,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # горизонтальний захист (IDOR): редагувати можна лише себе (адмін — будь-кого)
    if current.id != user_id and current.role != Role.ADMIN:
        raise HTTPException(403, "You can only edit your own profile")
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(404, "User not found")
    if data.full_name:
        target.full_name = data.full_name
    db.commit()
    db.refresh(target)
    return target
