from src.models.user import Role

from tests.conftest import make_auth_cookie


def test_student_cannot_modify_other_user(client, test_users):
    """
    Звичайний учень намагається надіслати запит на зміну ролі або
    статусу іншого учня через ендпоінт модифікації.
    """
    student_cookies = make_auth_cookie(test_users["student"])
    victim = test_users["other_student"]

    response = client.post(
        f"/web/admin/users/{victim.id}",
        data={
            "role": Role.ADMIN.value,
            "class_id": "",
            "child_id": "",
            "is_active": "true",
        },
        cookies=student_cookies,
    )
    assert response.status_code == 403


def test_student_cannot_create_classes(client, test_users):
    """Учень не може створювати нові класи предметної області."""
    student_cookies = make_auth_cookie(test_users["student"])
    response = client.post(
        "/web/admin/classes",
        data={"name": "11-C"},
        cookies=student_cookies,
    )
    assert response.status_code == 403
