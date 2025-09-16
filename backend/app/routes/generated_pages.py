from fastapi import APIRouter, Body, Depends, HTTPException
from s8.db.database import db
from bson import ObjectId
from typing import Optional
from app.middleware.rbac import get_current_user

router = APIRouter(prefix="/api/generated-pages", tags=["Generated Pages"])

# -------------------------
# Create generated page
# -------------------------
@router.post("/")
async def create_generated_page(data: dict = Body(...), current_user: Optional[dict] = Depends(get_current_user)):
    """
    Create a generated page project.
    If current_user is available, set ownership automatically.
    """
    if current_user:
        data["user_id"] = str(current_user["_id"])  # enforce ownership

    result = await db.generated_pages.insert_one(data)
    return {"inserted_id": str(result.inserted_id)}

# -------------------------
# List generated pages
# -------------------------
@router.get("/")
async def list_generated_pages(current_user: Optional[dict] = Depends(get_current_user)):
    """
    List generated pages.
    Authenticated → only user's projects.
    Unauthenticated → all projects.
    """
    query = {"user_id": str(current_user["_id"])} if current_user else {}
    projects = await db.generated_pages.find(query).to_list(100)
    for project in projects:
        project["_id"] = str(project["_id"])
    return projects

# -------------------------
# Fetch single project (for generate_app)
# -------------------------
@router.get("/{project_id}")
async def get_generated_page(project_id: str, current_user: Optional[dict] = Depends(get_current_user)):
    """
    Fetch a single project by ID.
    If user is authenticated, enforce ownership. Otherwise, fetch by ID only.
    """
    query = {"_id": ObjectId(project_id)}
    if current_user:
        query["user_id"] = str(current_user["_id"])

    project = await db.generated_pages.find_one(query)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found or not yours")
    
    project["_id"] = str(project["_id"])
    return project
