# app/middleware/rbac.py
from fastapi import HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from app.utils.auth_utils import decode_token
from s8.db.database import user_collection

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = decode_token(token)
        email = payload.get("email")
        if not email:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user = await user_collection.find_one({"email": email})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return user
    except Exception as e:
        print(f"Token decode error or DB fetch failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")
    
async def get_current_client(user: dict = Depends(get_current_user)):
    if user["role"] != "Client":
        raise HTTPException(status_code=403, detail="Client access only")
    return user

async def get_current_dev(user: dict = Depends(get_current_user)):
    if user["role"] != "Dev":
        raise HTTPException(status_code=403, detail="Developer access only")
    return user

def is_admin(user: dict = Depends(get_current_user)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")
    return user
