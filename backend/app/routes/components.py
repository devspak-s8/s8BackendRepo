from fastapi import APIRouter
from s8.db.database import db

router = APIRouter(prefix="/api/components", tags=["Components"])

@router.get("/")
async def get_components():
    return await db.components.find().to_list(100)

@router.get("/{component_name}")
async def get_component(component_name: str):
    return await db.components.find_one({"name": component_name})
