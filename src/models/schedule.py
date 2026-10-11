import datetime as dt

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base


class Schedule(Base):
    __tablename__ = "schedules"

    id: Mapped[int] = mapped_column(primary_key=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("school_classes.id"), index=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    subject: Mapped[str] = mapped_column(String(100))
    room: Mapped[str] = mapped_column(String(20))
    weekday: Mapped[int]  # 0 = понеділок ... 4 = п'ятниця
    start_time: Mapped[dt.time]

    school_class = relationship("SchoolClass", lazy="joined")
    teacher = relationship("User", lazy="joined")
