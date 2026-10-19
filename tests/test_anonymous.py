def test_anonymous_access_student_home(client):
    response = client.get("/student/home", follow_redirects=False)
    assert response.status_code in (401, 302, 303)


def test_anonymous_access_teacher_home(client):
    response = client.get("/teacher/home", follow_redirects=False)
    assert response.status_code in (401, 302, 303)


def test_anonymous_access_admin_home(client):
    response = client.get("/admin/home", follow_redirects=False)
    assert response.status_code in (401, 302, 303)
