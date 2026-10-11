import datetime as dt

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base


class JournalRecord(Base):
    __tablename__ = "journal_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    subject: Mapped[str] = mapped_column(String(100))
    grade: Mapped[int]
    graded_on: Mapped[dt.date] = mapped_column(default=dt.date.today)

    student = relationship("User", foreign_keys=[student_id], lazy="joined")
    teacher = relationship("User", foreign_keys=[teacher_id], lazy="joined")
