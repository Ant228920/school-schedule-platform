from pydantic import BaseModel, EmailStr, Field

from src.models.user import Role


class UserRegister(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=255)
    password: str = Field(min_length=8, max_length=72)
    # role навмисно відсутня: самореєстрація завжди створює учня


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=255)


class AdminUserUpdate(BaseModel):
    role: Role | None = None
    class_id: int | None = None
    child_id: int | None = None
    is_active: bool | None = None


class AdminUserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=255)
    password: str = Field(min_length=8, max_length=72)
    role: Role = Role.STUDENT
    class_id: int | None = None
    child_id: int | None = None


class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: Role
    is_active: bool
    class_id: int | None = None
    child_id: int | None = None
    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
