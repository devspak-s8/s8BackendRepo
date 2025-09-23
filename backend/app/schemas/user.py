from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class RegisterSchema(BaseModel):
    email: EmailStr
    name: str
    password: str
    role: str  # "Client" or "Dev"

class LoginSchema(BaseModel):
    email: EmailStr
    password: str

class ForgotPasswordSchema(BaseModel):
    email: EmailStr

class ResetPasswordSchema(BaseModel):
    token: str
    new_password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str

class UserOut(BaseModel):
    id: str = Field(..., alias="_id")
    email: EmailStr
    name: str
    role: str  # "Client" or "Dev"
    is_verified: bool
    profile_picture: Optional[str] = None  # optional profile URL
