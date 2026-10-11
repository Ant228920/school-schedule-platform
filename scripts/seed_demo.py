"""Демо-дані: python -m scripts.seed_demo  (пароль для всіх: Passw0rd!)"""

import datetime as dt

from sqlalchemy import select
from src.core.database import SessionLocal
from src.core.security import hash_password
from src.core.seed import init_db
from src.models.journal import JournalRecord
from src.models.schedule import Schedule
from src.models.school_class import SchoolClass
from src.models.user import Role, User

PASSWORD = "Passw0rd!"


def user(db, email, name, role, **kw):
    u = db.scalar(select(User).where(User.email == email))
    if not u:
        u = User(
            email=email,
            full_name=name,
            hashed_password=hash_password(PASSWORD),
            role=role,
            **kw,
        )
        db.add(u)
        db.commit()
        db.refresh(u)
    return u


def main():
    init_db()
    with SessionLocal() as db:
        cls = db.scalar(select(SchoolClass).where(SchoolClass.name == "7-А"))
        if not cls:
            cls = SchoolClass(name="7-А")
            db.add(cls)
            db.commit()
            db.refresh(cls)
        t1 = user(db, "ivanenko@school.ua", "Іваненко Олена Петрівна", Role.TEACHER)
        t2 = user(db, "koval@school.ua", "Коваль Наталія Миколаївна", Role.TEACHER)
        st = user(db, "student@school.ua", "Петренко Андрій", Role.STUDENT, class_id=cls.id)
        user(db, "parent@school.ua", "Петренко Ірина", Role.PARENT, child_id=st.id)
        if not db.scalar(select(Schedule.id).limit(1)):
            for wd, tm, subj, room, t in [
                (0, dt.time(8, 30), "Математика", "214", t1),
                (0, dt.time(9, 25), "Українська мова", "108", t2),
                (1, dt.time(8, 30), "Українська мова", "108", t2),
                (2, dt.time(8, 30), "Математика", "214", t1),
            ]:
                db.add(
                    Schedule(
                        class_id=cls.id,
                        teacher_id=t.id,
                        subject=subj,
                        room=room,
                        weekday=wd,
                        start_time=tm,
                    )
                )
            db.add(JournalRecord(student_id=st.id, teacher_id=t1.id, subject="Математика", grade=11))
            db.commit()
    print(
        "Демо-дані створено. Логіни: admin@school.ua (з .env), ivanenko@school.ua, "
        "koval@school.ua, student@school.ua, parent@school.ua; пароль демо-користувачів: Passw0rd!"
    )


if __name__ == "__main__":
    main()
