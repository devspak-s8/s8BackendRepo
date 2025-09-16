from fastapi import APIRouter
from s8.db.database import db

router = APIRouter(prefix="/api/website-types", tags=["Website Types"])

@router.get("/")
async def get_website_types():
    return await db.website_types.find().to_list(100)
