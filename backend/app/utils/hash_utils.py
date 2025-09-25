# app/utils/hash_utils.py
from passlib.hash import argon2

def hash_password(password: str) -> str:
    """Hash plain password with Argon2."""
    return argon2.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against Argon2 hash."""
    return argon2.verify(plain_password, hashed_password)
