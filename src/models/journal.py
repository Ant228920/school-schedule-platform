import datetime as dt

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base


class JournalRecord(Base):
    __tablename__ = "journal_records"
    __table_args__ = (
        Index("ix_journal_student_date_id", "student_id", "graded_on", "id"),
        Index("ix_journal_teacher_id_id", "teacher_id", "id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    subject: Mapped[str] = mapped_column(String(100))
    grade: Mapped[int]
    graded_on: Mapped[dt.date] = mapped_column(default=dt.date.today)

    student = relationship("User", foreign_keys=[student_id])
    teacher = relationship("User", foreign_keys=[teacher_id])
