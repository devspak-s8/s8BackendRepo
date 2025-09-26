from datetime import timedelta
from fastapi import APIRouter, Body, Security, HTTPException
from app.middleware.rbac import get_current_user
from app.schemas.user import *
from app.utils.hash_utils import hash_password, verify_and_upgrade_password
from app.utils.auth_utils import create_access_token, decode_token, create_refresh_token
from s8.db.database import user_collection
from s8.core.config import settings
from s8.core.error_messages import ErrorResponses
from uuid import uuid4
from bson import ObjectId

auth_router = APIRouter(tags=["Auth"])

# Temporary in-memory token storage
reset_tokens = {}

# ------------------------
# Register
# ------------------------
@auth_router.post("/register")
async def register(data: RegisterSchema):
    # Check if user already exists
    user = await user_collection.find_one({"email": data.email})
    if user:
        raise ErrorResponses.USER_EXISTS

    hashed_pw = hash_password(data.password)

    # Assign role
    if data.email == settings.ADMIN_EMAIL and data.password == settings.ADMIN_PASSWORD:
        role = "admin"
    else:
        if data.role not in ["Client", "Dev"]:
            raise HTTPException(
                status_code=400, 
                detail="Invalid role. Role must be either 'Client' or 'Dev'."
            )
        role = data.role

    # Insert user and mark as verified immediately
    await user_collection.insert_one({
        **data.dict(exclude={"password"}),
        "password": hashed_pw,
        "is_verified": True,
        "role": role
    })

    return {"msg": "✅ Registered successfully. You can now log in."}


# ------------------------
# Login
# ------------------------
@auth_router.post("/login", response_model=TokenResponse)
async def login(data: LoginSchema):
    user = await user_collection.find_one({"email": data.email})
    if not user:
        raise ErrorResponses.INVALID_CREDENTIALS

    valid = await verify_and_upgrade_password(
        user["email"],
        data.password,
        user["password"],
        user_collection
    )
    if not valid:
        raise ErrorResponses.INVALID_CREDENTIALS

    # Skip verification check
    return {
        "access_token": create_access_token({"email": user["email"], "role": user["role"]}),
        "refresh_token": create_refresh_token({"email": user["email"], "role": user["role"]}, timedelta(days=7)),
        "is_verified": True,
        "is_admin": user.get("role") == "admin"
    }


# ------------------------
# Refresh token
# ------------------------
@auth_router.post("/refresh", response_model=TokenResponse)
async def refresh_token(refresh_token: str = Body(...)):
    try:
        payload = decode_token(refresh_token, expected_type="refresh")
        email = payload.get("email")
        role = payload.get("role")

        if not email:
            raise ErrorResponses.INVALID_TOKEN

        user = await user_collection.find_one({"email": email})
        if not user:
            raise ErrorResponses.USER_NOT_FOUND

        token_data = {"email": email, "role": role}
        access_token = create_access_token(token_data)
        refresh_token_new = create_refresh_token(token_data, expires_delta=timedelta(days=7))

        return {"access_token": access_token, "refresh_token": refresh_token_new}

    except Exception:
        raise ErrorResponses.INVALID_TOKEN


# ------------------------
# Forgot/Reset Password
# ------------------------
@auth_router.post("/forgot-password")
async def forgot_password(email: str):
    user = await user_collection.find_one({"email": email})
    if not user:
        raise ErrorResponses.USER_NOT_FOUND

    token = str(uuid4())
    reset_tokens[token] = email
    reset_link = f"http://localhost:5173/reset-password?token={token}"

    subject = "🔑 Password Reset Request"
    body = f"You requested to reset your password. Click here: {reset_link}"

    try:
        send_email(email, subject, body)
    except Exception:
        raise ErrorResponses.INTERNAL_SERVER_ERROR

    return {"msg": "✅ Password reset email sent successfully"}


@auth_router.post("/reset-password")
async def reset_password(data: ResetPasswordSchema):
    email = reset_tokens.get(data.token)
    if not email:
        raise ErrorResponses.INVALID_TOKEN

    hashed_pw = hash_password(data.new_password)
    await user_collection.update_one({"email": email}, {"$set": {"password": hashed_pw}})
    del reset_tokens[data.token]
    return {"msg": "Password has been reset successfully"}


# ------------------------
# Get current user info
# ------------------------
@auth_router.get("/me", response_model=UserOut)
async def get_current_user_info(current_user: dict = Security(get_current_user)):
    user = await user_collection.find_one({"email": current_user["email"]})
    if not user:
        raise ErrorResponses.USER_NOT_FOUND

    user["_id"] = str(user["_id"])
    return user
