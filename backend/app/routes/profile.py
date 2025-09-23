# app/routers/profile.py
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Body, Form, Request
from app.middleware.rbac import get_current_user
from s8.db.database import user_collection
from app.schemas.profile import ClientProfileSchema, DevProfileSchema, ProjectSchema
from s8.core.config import settings
from app.utils.b2_utils import get_signed_url, upload_image_to_b2
from pathlib import Path
import uuid
from typing import List
import json
from bson import ObjectId
from pydantic import ValidationError
profile_router = APIRouter(prefix="/profile", tags=["Profile"])

UPLOAD_DIR = Path("uploads/temp")  # Temporary local storage
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@profile_router.post("/client")
async def create_client_profile(
    request: Request,
    profile: str | None = Form(None),  # for multipart
    file: UploadFile | None = File(default=None),
    profile_json: dict | None = Body(None),  # for raw JSON
    user: dict = Depends(get_current_user)
):
    if user["role"] != "Client":
        raise HTTPException(status_code=403, detail="Only clients can create this profile")

    # --- Handle raw JSON vs multipart
    if profile_json:  
        # came from JSON body
        profile_dict = profile_json
    elif profile:    
        # came as string inside multipart
        try:
            profile_dict = json.loads(profile)
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=422, detail=f"Invalid JSON in 'profile': {str(e)}")
    else:
        raise HTTPException(status_code=422, detail="Profile data is required")

    # --- Validate with Pydantic schema
    try:
        profile_obj = ClientProfileSchema(**profile_dict)
        profile_data = profile_obj.dict()
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())

    # --- Handle profile picture upload
    if file:
        file_ext = Path(file.filename).suffix
        filename = f"{uuid.uuid4()}{file_ext}"
        local_file_path = UPLOAD_DIR / filename

        with local_file_path.open("wb") as f:
            f.write(await file.read())

        b2_url = upload_image_to_b2(local_file_path)
        profile_data["profile_picture"] = b2_url
        local_file_path.unlink()

    # --- Save to DB
    result = await user_collection.update_one(
        {"_id": ObjectId(str(user["_id"]))},
        {"$set": {"profile": profile_data, "profile_completed": True}}
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=400, detail="Profile could not be updated")

    return {"msg": "✅ Client profile created successfully", "profile": profile_data}

@profile_router.get("/client/me")
async def get_client_profile(user: dict = Depends(get_current_user)):
    if user["role"] != "Client":
        raise HTTPException(status_code=403, detail="Only clients can view this profile")

    profile = user.get("profile")
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Generate signed URL for private bucket
    profile_picture = profile.get("profile_picture")
    if profile_picture and not settings.B2_BUCKET_PUBLIC:
        profile["profile_picture"] = get_signed_url(profile_picture)

    return {"profile": profile}


# ------------------------
# Developer Profile Endpoints
# ------------------------
@profile_router.post("/dev")
async def create_dev_profile(
    profile: DevProfileSchema,
    file: UploadFile | None = File(default=None),
    user: dict = Depends(get_current_user)
):
    if user["role"] != "Dev":
        raise HTTPException(status_code=403, detail="Only developers can create this profile")

    profile_data = profile.dict()

    # Handle profile picture
    if file:
        file_ext = Path(file.filename).suffix
        filename = f"{uuid.uuid4()}{file_ext}"
        local_file_path = UPLOAD_DIR / filename

        with local_file_path.open("wb") as f:
            f.write(await file.read())

        b2_url = upload_image_to_b2(local_file_path)
        profile_data["profile_picture"] = b2_url
        local_file_path.unlink()

    # Update MongoDB
    result = await user_collection.update_one(
        {"_id": user["_id"]},
        {"$set": {"dev_profile": profile_data, "profile_completed": True}}
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=400, detail="Developer profile could not be updated")

    return {"msg": "✅ Developer profile created successfully", "profile": profile_data}


@profile_router.get("/dev/me")
async def get_dev_profile(user: dict = Depends(get_current_user)):
    if user["role"] != "Dev":
        raise HTTPException(status_code=403, detail="Only developers can view this profile")

    profile = user.get("dev_profile")
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Generate signed URL for profile picture if bucket is private
    profile_picture = profile.get("profile_picture")
    if profile_picture and not settings.B2_BUCKET_PUBLIC:
        profile["profile_picture"] = get_signed_url(profile_picture)

    return {"profile": profile}

# ------------------------
# Developer Projects Endpoints
# ------------------------

@profile_router.post("/dev/projects")
async def add_dev_projects(
    projects: List[ProjectSchema] = Body(...),
    user: dict = Depends(get_current_user)
):
    if user["role"] != "Dev":
        raise HTTPException(status_code=403, detail="Only developers can add projects")

    dev_profile = user.get("dev_profile")
    if not dev_profile:
        raise HTTPException(status_code=404, detail="Developer profile not found. Create profile first.")

    # Assign unique IDs if missing
    new_projects = []
    for project in projects:
        if not project.id:
            project.id = str(uuid.uuid4())
        new_projects.append(project.dict())

    existing_projects = dev_profile.get("projects", [])
    dev_profile["projects"] = existing_projects + new_projects

    await user_collection.update_one(
        {"_id": user["_id"]},
        {"$set": {"dev_profile.projects": dev_profile["projects"]}}
    )

    return {"msg": "✅ Projects added successfully", "projects": dev_profile["projects"]}


@profile_router.get("/dev/projects")
async def get_dev_projects(user: dict = Depends(get_current_user)):
    if user["role"] != "Dev":
        raise HTTPException(status_code=403, detail="Only developers can view projects")

    dev_profile = user.get("dev_profile")
    if not dev_profile or "projects" not in dev_profile:
        raise HTTPException(status_code=404, detail="No projects found")

    return {"projects": dev_profile["projects"]}


@profile_router.put("/dev/projects/{project_id}")
async def update_dev_project(
    project_id: str,
    project: ProjectSchema,
    user: dict = Depends(get_current_user)
):
    if user["role"] != "Dev":
        raise HTTPException(status_code=403, detail="Only developers can update projects")

    dev_profile = user.get("dev_profile")
    if not dev_profile or "projects" not in dev_profile:
        raise HTTPException(status_code=404, detail="No projects found")

    updated = False
    for idx, existing in enumerate(dev_profile["projects"]):
        if existing["id"] == project_id:
            dev_profile["projects"][idx] = project.dict()
            dev_profile["projects"][idx]["id"] = project_id  # preserve ID
            updated = True
            break

    if not updated:
        raise HTTPException(status_code=404, detail="Project not found")

    await user_collection.update_one(
        {"_id": user["_id"]},
        {"$set": {"dev_profile.projects": dev_profile["projects"]}}
    )

    return {"msg": "✅ Project updated successfully", "project": project.dict()}


@profile_router.delete("/dev/projects/{project_id}")
async def delete_dev_project(
    project_id: str,
    user: dict = Depends(get_current_user)
):
    if user["role"] != "Dev":
        raise HTTPException(status_code=403, detail="Only developers can delete projects")

    dev_profile = user.get("dev_profile")
    if not dev_profile or "projects" not in dev_profile:
        raise HTTPException(status_code=404, detail="No projects found")

    new_projects = [p for p in dev_profile["projects"] if p["id"] != project_id]

    if len(new_projects) == len(dev_profile["projects"]):
        raise HTTPException(status_code=404, detail="Project not found")

    dev_profile["projects"] = new_projects

    await user_collection.update_one(
        {"_id": user["_id"]},
        {"$set": {"dev_profile.projects": new_projects}}
    )

    return {"msg": "✅ Project deleted successfully"}