# app/utils/hash_utils.py
from passlib.hash import argon2

def hash_password(password: str) -> str:
    """Hash plain password with Argon2."""
    return argon2.hash(password)

async def verify_and_upgrade_password(email: str, plain_password: str, hashed_password: str, collection):
    from passlib.hash import argon2, bcrypt

    if hashed_password.startswith("$argon2"):
        return argon2.verify(plain_password, hashed_password)

    elif hashed_password.startswith("$2b$") or hashed_password.startswith("$2a$"):
        # Verify old bcrypt
        if bcrypt.verify(plain_password, hashed_password):
            # Auto-upgrade → store argon2
            new_hash = argon2.hash(plain_password)
            await collection.update_one(
                {"email": email},
                {"$set": {"password": new_hash}}
            )
            return True
    return False
