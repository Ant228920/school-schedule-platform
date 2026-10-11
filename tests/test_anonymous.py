def test_anonymous_access_student_home(client):
    """Анонімний запит до кабінету учня має блокуватися."""
    response = client.get("/student/home", follow_redirects=False)
    assert response.status_code in (401, 302, 303)


def test_anonymous_access_teacher_home(client):
    """Анонімний запит до кабінету вчителя має блокуватися."""
    response = client.get("/teacher/home", follow_redirects=False)
    assert response.status_code in (401, 302, 303)


def test_anonymous_access_admin_home(client):
    """Анонімний запит до кабінету адміна має блокуватися."""
    response = client.get("/admin/home", follow_redirects=False)
    assert response.status_code in (401, 302, 303)
