from pydantic import BaseModel, EmailStr


class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    phone: str | None = None
    password: str
    confirm_password: str


class SignupResponse(BaseModel):
    auth_id: int
    name: str
    email: EmailStr
    phone: str | None = None


class LoginRequest(BaseModel):
    username: str  # email or phone
    password: str


class LoginResponse(BaseModel):
    auth_id: int
    name: str
    email: EmailStr
    access_token: str | None = None
    token_type: str | None = "bearer"
