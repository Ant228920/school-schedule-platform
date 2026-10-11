from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class SchoolClass(Base):
    __tablename__ = "school_classes"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(20), unique=True)
