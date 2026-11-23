"""Великий набір даних для вимірювання продуктивності (ЛР №7).

    python -m scripts.seed_demo     # спершу демо-користувачі (їх використовує locustfile)
    python -m scripts.seed_bulk     # потім масовка: ~1000 учнів, 40 вчителів, ~300 тис. оцінок

На 4 демо-уроках і 1 оцінці індекси та кеш нічого не змінюють, тому для чесного порівняння
«ДО/ПІСЛЯ» БД наповнюється обсягом, близьким до реальної школи. Скрипт ідемпотентний.
Потрібен PostgreSQL (використовується generate_series).
"""

import datetime as dt
import random

from sqlalchemy import select, text
from src.core.database import SessionLocal
from src.core.security import hash_password
from src.core.seed import init_db
from src.models.schedule import Schedule
from src.models.school_class import SchoolClass
from src.models.user import Role, User

N_CLASSES = 40
STUDENTS_PER_CLASS = 25
N_TEACHERS = 40
GRADES_PER_STUDENT_SUBJECT = 60
SUBJECTS = ["Математика", "Українська мова", "Англійська мова", "Історія", "Фізика", "Біологія", "Хімія", "Географія"]
SLOTS = [dt.time(8, 30), dt.time(9, 25), dt.time(10, 20), dt.time(11, 25), dt.time(12, 20)]


def main():
    random.seed(7)
    init_db()
    with SessionLocal() as db:
        if db.scalar(select(User.id).where(User.email == "bulk.teacher0@school.ua")):
            print("Масовка вже створена - пропускаю.")
            return
        # один хеш на всіх: 1000 викликів bcrypt тривали б хвилини, а пароль тут не перевіряється
        pwd = hash_password("Passw0rd!")

        classes = [SchoolClass(name=f"{5 + i // 4}-{'АБВГ'[i % 4]}") for i in range(N_CLASSES)]
        classes = [c for c in classes if not db.scalar(select(SchoolClass.id).where(SchoolClass.name == c.name))]
        db.add_all(classes)
        db.flush()
        all_classes = list(db.scalars(select(SchoolClass)).all())

        teachers = [
            User(email=f"bulk.teacher{i}@school.ua", full_name=f"Вчитель Масовий {i}", hashed_password=pwd, role=Role.TEACHER)
            for i in range(N_TEACHERS)
        ]
        db.add_all(teachers)
        db.flush()

        students = []
        for ci, cls in enumerate(all_classes):
            for k in range(STUDENTS_PER_CLASS):
                students.append(
                    User(
                        email=f"bulk.student{ci}_{k}@school.ua",
                        full_name=f"Учень Масовий {ci}-{k}",
                        hashed_password=pwd,
                        role=Role.STUDENT,
                        class_id=cls.id,
                    )
                )
        db.add_all(students)
        db.flush()

        lessons = []
        for ci, cls in enumerate(all_classes):
            for wd in range(5):
                for si, tm in enumerate(SLOTS):
                    lessons.append(
                        Schedule(
                            class_id=cls.id,
                            teacher_id=teachers[(ci + wd * 5 + si) % N_TEACHERS].id,
                            subject=SUBJECTS[(wd + si + ci) % len(SUBJECTS)],
                            room=str(100 + (ci * 7 + si) % 90),
                            weekday=wd,
                            start_time=tm,
                        )
                    )
        db.add_all(lessons)
        db.commit()

        # оцінки: генеруємо на боці БД (generate_series), щоб це зайняло секунди, а не хвилини
        subjects_sql = ", ".join(f"'{s}'" for s in SUBJECTS[:5])
        db.execute(
            text(
                f"""
                WITH t AS (SELECT array_agg(id ORDER BY id) AS ids FROM users WHERE email LIKE 'bulk.teacher%')
                INSERT INTO journal_records (student_id, teacher_id, subject, grade, graded_on)
                SELECT u.id,
                       t.ids[1 + (u.id * 31 + g) % :nt],
                       (ARRAY[{subjects_sql}])[1 + (g % 5)],
                       1 + (random() * 11)::int,
                       DATE '2025-09-01' + (g % 240)
                FROM users u
                CROSS JOIN t
                CROSS JOIN generate_series(1, :n) AS g
                WHERE u.email LIKE 'bulk.student%'
                """
            ),
            {"n": GRADES_PER_STUDENT_SUBJECT * 5, "nt": N_TEACHERS},
        )
        # демо-вчителі й демо-учень (їх використовує locust) теж мають «історію»
        db.execute(
            text(
                """
                INSERT INTO journal_records (student_id, teacher_id, subject, grade, graded_on)
                SELECT s.id, t.id, t.subj, 1 + (random() * 11)::int, DATE '2025-09-01' + (g % 240)
                FROM generate_series(1, 400) g
                JOIN users s ON s.email = 'student@school.ua'
                JOIN (SELECT id, CASE email WHEN 'ivanenko@school.ua' THEN 'Математика' ELSE 'Українська мова' END AS subj
                      FROM users WHERE email IN ('ivanenko@school.ua', 'koval@school.ua')) t ON (g % 2) = (t.id % 2)
                """
            )
        )
        db.commit()
        n = db.scalar(text("SELECT count(*) FROM journal_records"))
        print(f"Готово: {len(students)} учнів, {N_TEACHERS} вчителів, {len(lessons)} уроків, {n} оцінок.")


if __name__ == "__main__":
    main()
