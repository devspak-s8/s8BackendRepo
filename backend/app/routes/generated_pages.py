# app/routes/generated_pages.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from s8.db.database import db
from bson import ObjectId
from app.middleware.rbac import get_current_user

router = APIRouter(prefix="", tags=["Generated Pages"])

# -----------------------------
# Schemas
# -----------------------------
class ComponentSchema(BaseModel):
    component_name: str
    variant_name: str
    props: Dict[str, Any]

class PageSchema(BaseModel):
    page_name: str
    components: List[ComponentSchema]

class GeneratedPageSchema(BaseModel):
    page_type: str   # e.g. "single", "multi"
    website_type: str
    pages: List[PageSchema]

# -----------------------------
# Routes
# -----------------------------
@router.post("/")
async def create_generated_page(
    data: GeneratedPageSchema,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new generated project linked to the user.
    """
    payload = data.dict()
    payload["user_id"] = str(current_user["_id"])  # enforce ownership

    result = await db.generated_pages.insert_one(payload)
    return {"inserted_id": str(result.inserted_id)}

@router.get("/")
async def list_generated_pages(current_user: dict = Depends(get_current_user)):
    """
    List all generated projects belonging to the current user.
    """
    projects = await db.generated_pages.find({"user_id": str(current_user["_id"])}).to_list(100)
    for project in projects:
        project["_id"] = str(project["_id"])  # convert ObjectId to string for JSON
    return projects

@router.get("/{project_id}")
async def get_generated_page(project_id: str, current_user: dict = Depends(get_current_user)):
    """
    Get a single project by ID if it belongs to the current user.
    """
    try:
        obj_id = ObjectId(project_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid project_id")

    project = await db.generated_pages.find_one({"_id": obj_id, "user_id": str(current_user["_id"])})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found or not yours")
    
    project["_id"] = str(project["_id"])
    return project
