def test_login_successful(client, test_users):
    response = client.post(
        "/login",
        data={"email": "student@test.com", "password": "password123"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/student/home"
    assert "access_token" in response.cookies


def test_login_invalid_password(client, test_users):
    response = client.post(
        "/login",
        data={"email": "student@test.com", "password": "incorrect_password"},
        follow_redirects=False,
    )
    assert response.status_code == 401
    assert "access_token" not in response.cookies


def test_login_nonexistent_user(client, test_users):
    response = client.post(
        "/login",
        data={"email": "ghost@test.com", "password": "password123"},
        follow_redirects=False,
    )
    assert response.status_code == 401


def test_register_new_student(client):
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
