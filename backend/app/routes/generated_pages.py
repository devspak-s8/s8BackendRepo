# app/routes/generated_pages.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from bson import ObjectId
from s8.db.database import db
from app.middleware.rbac import get_current_user

router = APIRouter(prefix="/api/generated-pages", tags=["Generated Pages"])

# --------------------
# 📌 Schemas
# --------------------
class ComponentSchema(BaseModel):
    component_name: str
    variant_name: str
    props: Dict[str, Any]

class PageSchema(BaseModel):
    page_name: str
    components: List[ComponentSchema]

class GeneratedPageSchema(BaseModel):
    page_type: str   # e.g. "single", "multi"
    website_type: str  # e.g. "portfolio", "e-commerce"
    pages: List[PageSchema]

# --------------------
# 📌 Routes
# --------------------
@router.post("/")
async def create_generated_page(
    data: GeneratedPageSchema,
    current_user: dict = Depends(get_current_user)
):
    """
    Creates a generated page project linked to the authenticated user.
    """
    payload = data.dict()
    payload["user_id"] = str(current_user["_id"])  # force ownership

    result = await db.generated_pages.insert_one(payload)
    return {"inserted_id": str(result.inserted_id)}

@router.get("/")
async def list_generated_pages(current_user: dict = Depends(get_current_user)):
    """
    Returns all generated pages belonging to the authenticated user.
    """
    projects = await db.generated_pages.find(
        {"user_id": str(current_user["_id"])}
    ).to_list(100)

    # Convert ObjectId to string for JSON response
    for project in projects:
        project["_id"] = str(project["_id"])

    return projects
