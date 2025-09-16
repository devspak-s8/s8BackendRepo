# app/routes/generated_pages.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
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

class ComponentOut(ComponentSchema):
    pass

class PageOut(PageSchema):
    components: List[ComponentOut]

class GeneratedPageOut(BaseModel):
    id: str
    page_type: str
    website_type: str
    pages: List[PageOut]

# --------------------
# 📌 Routes
# --------------------
@router.post("/", response_model=GeneratedPageOut)
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

    return {
        "id": str(result.inserted_id),
        "page_type": payload["page_type"],
        "website_type": payload["website_type"],
        "pages": payload["pages"]
    }

@router.get("/", response_model=List[GeneratedPageOut])
async def list_generated_pages(current_user: dict = Depends(get_current_user)):
    """
    Returns all generated pages belonging to the authenticated user.
    """
    projects = await db.generated_pages.find(
        {"user_id": str(current_user["_id"])}
    ).to_list(100)

    clean_projects = []
    for project in projects:
        clean_projects.append({
            "id": str(project["_id"]),
            "page_type": project.get("page_type"),
            "website_type": project.get("website_type"),
            "pages": project.get("pages", [])
        })

    return clean_projects
