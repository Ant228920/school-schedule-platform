import enum

from sqlalchemy import Boolean, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base


class Role(str, enum.Enum):
    ADMIN = "admin"
    TEACHER = "teacher"
    STUDENT = "student"
    PARENT = "parent"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(Enum(Role), default=Role.STUDENT)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # для учня: клас, у якому він навчається
    class_id: Mapped[int | None] = mapped_column(ForeignKey("school_classes.id"), index=True)
    # для батьків: учень, чиї дані вони бачать
    child_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    school_class = relationship("SchoolClass", lazy="selectin")
