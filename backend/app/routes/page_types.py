from fastapi import APIRouter
from s8.db.database import db

router = APIRouter(prefix="/api/page-types", tags=["Page Types"])

@router.get("/")
async def get_page_types():
    return await db.page_types.find().to_list(100)
