from sqlalchemy import select

from src.core.config import settings
from src.core.database import Base, SessionLocal, engine
from src.core.security import hash_password


def init_db() -> None:
    import src.models  # noqa: F401
    from src.models.user import Role, User

    Base.metadata.create_all(engine)
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
