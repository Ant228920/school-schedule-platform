from sqlalchemy import select, text

from src.core.config import settings
from src.core.database import Base, SessionLocal, engine
from src.core.security import hash_password


def apply_perf_indexes() -> None:
    for table in Base.metadata.tables.values():
        for index in table.indexes:
            index.create(bind=engine, checkfirst=True)
    with engine.begin() as conn:
        for name in ("ix_schedules_class_id", "ix_schedules_teacher_id", "ix_journal_records_student_id", "ix_journal_records_teacher_id"):
            conn.execute(text(f"DROP INDEX IF EXISTS {name}"))


def init_db() -> None:
    import src.models  # noqa: F401
    from src.models.user import Role, User

    Base.metadata.create_all(engine)
    apply_perf_indexes()
    with SessionLocal() as db:
        if not db.scalar(select(User).where(User.email == settings.ADMIN_EMAIL)):
            db.add(
                User(
                    email=settings.ADMIN_EMAIL,
                    full_name="Адміністратор",
                    hashed_password=hash_password(settings.ADMIN_PASSWORD),
                    role=Role.ADMIN,
                )
            )
            db.commit()
