from tests.conftest import make_auth_cookie


def test_student_forbidden_from_admin_cabinet(client, test_users):
    """Учень отримує 403 при переході в кабінет адміністратора."""
    cookies = make_auth_cookie(test_users["student"])
    response = client.get("/admin/home", cookies=cookies)
    assert response.status_code == 403


def test_student_forbidden_from_teacher_cabinet(client, test_users):
    """Учень отримує 403 при переході в кабінет вчителя."""
    cookies = make_auth_cookie(test_users["student"])
    response = client.get("/teacher/home", cookies=cookies)
    assert response.status_code == 403


def test_teacher_forbidden_from_admin_cabinet(client, test_users):
    """Вчитель отримує 403 при спробі відкрити кабінет адміністратора."""
    cookies = make_auth_cookie(test_users["teacher"])
    response = client.get("/admin/home", cookies=cookies)
    assert response.status_code == 403


def test_admin_can_access_admin_cabinet(client, test_users):
    """Адміністратор успішно заходить у свій кабінет (200 OK)."""
    cookies = make_auth_cookie(test_users["admin"])
    response = client.get("/admin/home", cookies=cookies)
    assert response.status_code == 200
