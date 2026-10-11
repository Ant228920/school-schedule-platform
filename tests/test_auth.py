def test_login_successful(client, test_users):
    """Вхід з коректними даними повертає 303 Redirect та виставляє access_token."""
    response = client.post(
        "/login",
        data={"email": "student@test.com", "password": "password123"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/student/home"
    assert "access_token" in response.cookies


def test_login_invalid_password(client, test_users):
    """Вхід із неправильним паролем повертає помилку 401 Unauthorized."""
    response = client.post(
        "/login",
        data={"email": "student@test.com", "password": "incorrect_password"},
        follow_redirects=False,
    )
    assert response.status_code == 401
    assert "access_token" not in response.cookies


def test_login_nonexistent_user(client, test_users):
    """Спроба входу під неіснуючим email."""
    response = client.post(
        "/login",
        data={"email": "ghost@test.com", "password": "password123"},
        follow_redirects=False,
    )
    assert response.status_code == 401


def test_register_new_student(client):
    """Реєстрація створює запис у PostgreSQL і одразу видає cookie."""
    response = client.post(
        "/register",
        data={
            "full_name": "Іван Коваленко",
            "email": "ivan.koval@test.com",
            "password": "strongPassword123",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/student/home"
    assert "access_token" in response.cookies
