import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from src.core.database import Base, get_db
from src.core.security import create_access_token, hash_password
from src.main import app
from src.models.user import Role, User

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_database_schema():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_users(db_session):
    """Створює набір користувачів із різними ролями."""
    student = User(
        email="student@test.com",
        full_name="Тестовий Учень",
        hashed_password=hash_password("password123"),
        role=Role.STUDENT,
        is_active=True,
    )
    teacher = User(
        email="teacher@test.com",
        full_name="Тестовий Вчитель",
        hashed_password=hash_password("password123"),
        role=Role.TEACHER,
        is_active=True,
    )
    admin = User(
        email="admin@test.com",
        full_name="Тестовий Адмін",
        hashed_password=hash_password("password123"),
        role=Role.ADMIN,
        is_active=True,
    )
    other_student = User(
        email="victim@test.com",
        full_name="Інший Учень",
        hashed_password=hash_password("password123"),
        role=Role.STUDENT,
        is_active=True,
    )

    db_session.add_all([student, teacher, admin, other_student])
    db_session.commit()

    for u in (student, teacher, admin, other_student):
        db_session.refresh(u)

    return {
        "student": student,
        "teacher": teacher,
        "admin": admin,
        "other_student": other_student,
    }


def make_auth_cookie(user: User) -> dict:
    """Генерація валідного cookie для клієнта."""
    token = create_access_token(user.id, user.role.value)
    return {"access_token": token}
