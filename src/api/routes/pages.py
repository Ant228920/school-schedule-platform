from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.config import settings
from src.core.database import get_db
from src.core.security import create_access_token, hash_password, verify_password
from src.core.templating import templates
from src.models.user import Role, User

router = APIRouter(include_in_schema=False)

HOME_BY_ROLE = {
    Role.ADMIN: "/admin/home",
    Role.TEACHER: "/teacher/home",
    Role.STUDENT: "/student/home",
    Role.PARENT: "/student/home",
}


def _login_redirect(user: User) -> RedirectResponse:
    resp = RedirectResponse(HOME_BY_ROLE[user.role], status_code=303)
    resp.set_cookie(
        "access_token",
        create_access_token(user.id, user.role.value),
        httponly=True,
        samesite="lax",
        secure=settings.COOKIE_SECURE,
        max_age=settings.TOKEN_EXPIRE_MINUTES * 60,
    )
    return resp


@router.get("/")
def index():
    return RedirectResponse("/login")


@router.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {"user": None, "error": None})


@router.post("/login")
def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.scalar(select(User).where(User.email == email))
    if not user or not user.is_active or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            request,
            "login.html",
            {"user": None, "error": "Невірний email або пароль"},
            status_code=401,
        )
    return _login_redirect(user)


@router.get("/register")
def register_page(request: Request):
    return templates.TemplateResponse(request, "register.html", {"user": None, "error": None})


@router.post("/register")
def register_submit(
    request: Request,
    full_name: str = Form(..., min_length=2),
    email: str = Form(...),
    password: str = Form(..., min_length=8, max_length=72),
    db: Session = Depends(get_db),
):
    if db.scalar(select(User).where(User.email == email)):
        return templates.TemplateResponse(
            request,
            "register.html",
            {"user": None, "error": "Цей email уже зареєстровано"},
            status_code=409,
        )
    user = User(
        email=email,
        full_name=full_name,
        hashed_password=hash_password(password),
        role=Role.STUDENT,
    )  # роль ніколи не береться з форми
    db.add(user)
    db.commit()
    db.refresh(user)
    return _login_redirect(user)


@router.get("/logout")
def logout():
    resp = RedirectResponse("/login", status_code=302)
    resp.delete_cookie("access_token")
    return resp
