"""Сценарій навантажувального тестування School Schedule Platform (Locust).

Три типи віртуальних користувачів (співвідношення 6 : 3 : 1):
  * StudentUser (60%) - логін, потім перегляд кабінету, розкладу й оцінок;
  * TeacherUser (30%) - логін, потім кабінет, розклад і виставлення оцінок (запис у БД);
  * VisitorUser (10%) - неавторизований відвідувач (GET /, GET /login).

Запуск (сервер має працювати на --host):
    locust -f loadtest/locustfile.py --headless --host http://127.0.0.1:8000 -u 50 -r 2 -t 3m

Демо-користувачі створюються командою: python -m scripts.seed_demo
"""

import os
import random

import requests
from locust import HttpUser, between, events, task

PASSWORD = os.getenv("LT_PASSWORD", "Passw0rd!")
STUDENT_EMAIL = "student@school.ua"
# (email вчителя, предмет, який він веде у 7-А) - відповідає scripts/seed_demo.py
TEACHERS = [
    ("ivanenko@school.ua", "Математика"),
    ("koval@school.ua", "Українська мова"),
]

STUDENT_ID: int | None = None


@events.test_start.add_listener
def discover_student_id(environment, **_):
    """Один раз дізнаємось id учня, щоб вчителі могли виставляти йому оцінки."""
    global STUDENT_ID
    host = environment.host
    if not host:
        raise RuntimeError("Вкажіть --host, наприклад http://127.0.0.1:8000")
    login = requests.post(
        f"{host}/auth/login",
        data={"username": STUDENT_EMAIL, "password": PASSWORD},
        timeout=15,
    )
    login.raise_for_status()
    token = login.json()["access_token"]
    me = requests.get(f"{host}/users/me", headers={"Authorization": f"Bearer {token}"}, timeout=15)
    me.raise_for_status()
    STUDENT_ID = me.json()["id"]


class AuthenticatedUser(HttpUser):
    """Базовий клас: логін через HTML-форму, JWT зберігається в cookie access_token."""

    abstract = True
    wait_time = between(1, 3)  # "час на роздуми" користувача

    def credentials(self) -> tuple[str, str]:
        raise NotImplementedError

    def on_start(self):
        email, password = self.credentials()
        with self.client.post(
            "/login",
            data={"email": email, "password": password},
            allow_redirects=False,  # 303 -> кабінет; кабінет міряємо окремим запитом
            name="POST /login",
            catch_response=True,
        ) as resp:
            if resp.status_code == 303 and self.client.cookies.get("access_token"):
                resp.success()
            else:
                resp.failure(f"login failed: HTTP {resp.status_code}")


class StudentUser(AuthenticatedUser):
    weight = 6

    def credentials(self):
        return STUDENT_EMAIL, PASSWORD

    @task(3)
    def home(self):
        self.client.get("/student/home", name="GET /student/home")

    @task(2)
    def schedule(self):
        self.client.get("/student/schedule", name="GET /student/schedule")

    @task(2)
    def grades(self):
        self.client.get("/student/grades", name="GET /student/grades")

    @task(1)
    def profile(self):
        self.client.get("/users/me", name="GET /users/me")


class TeacherUser(AuthenticatedUser):
    weight = 3

    def on_start(self):
        self.email, self.subject = random.choice(TEACHERS)
        super().on_start()

    def credentials(self):
        return self.email, PASSWORD

    @task(3)
    def home(self):
        self.client.get("/teacher/home", name="GET /teacher/home")

    @task(2)
    def schedule(self):
        self.client.get("/teacher/schedule", name="GET /teacher/schedule")

    @task(1)
    def add_grade(self):
        payload = {"student_id": STUDENT_ID, "subject": self.subject, "grade": random.randint(7, 12)}
        with self.client.post("/journal", json=payload, name="POST /journal", catch_response=True) as resp:
            if resp.status_code == 201:
                resp.success()
            else:
                resp.failure(f"HTTP {resp.status_code}")


class VisitorUser(HttpUser):
    weight = 1
    wait_time = between(1, 3)

    @task
    def landing(self):
        with self.client.get("/", allow_redirects=False, name="GET /", catch_response=True) as resp:
            if resp.status_code in (302, 307):
                resp.success()
            else:
                resp.failure(f"HTTP {resp.status_code}")
        self.client.get("/login", name="GET /login")
