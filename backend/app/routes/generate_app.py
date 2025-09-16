# app/routes/generate_app.py
from fastapi import APIRouter, HTTPException, Depends, Body
from fastapi.responses import JSONResponse
from s8.db.database import db
from app.middleware.rbac import get_current_user
from bson import ObjectId
import os, shutil, tempfile, zipfile, uuid, json

router = APIRouter(prefix="", tags=["App Generator"])

@router.post("/")
async def generate_app(
    data: dict = Body(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Generate a React app from a given project.
    Body: { "project_id": "<id>" }
    """
    project_id = data.get("project_id")
    if not project_id:
        raise HTTPException(status_code=400, detail="project_id is required")

    # ✅ Convert project_id to ObjectId
    try:
        obj_id = ObjectId(project_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid project_id")

    # Verify ownership
    project = await db.generated_pages.find_one(
        {"_id": obj_id, "user_id": str(current_user["_id"])}
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found or not yours")

    temp_dir = tempfile.mkdtemp()
    src_dir = os.path.join(temp_dir, "src")
    os.makedirs(src_dir, exist_ok=True)

    try:
        # 1. package.json
        package_json = {
            "name": f"s8-project-{uuid.uuid4().hex[:6]}",
            "version": "1.0.0",
            "private": True,
            "dependencies": {
                "react": "^18.2.0",
                "react-dom": "^18.2.0",
                "sf-builder-components": "latest",
                "devspak-s8": "latest"
            }
        }
        with open(os.path.join(temp_dir, "package.json"), "w") as f:
            json.dump(package_json, f, indent=2)

        # 2. Generate pages
        pages = project.get("pages", [])
        app_imports, app_children = [], []

        for page in pages:
            page_name = page.get("page_name", "Page").replace(" ", "")
            page_file = os.path.join(src_dir, f"{page_name}.jsx")
            page_imports, page_body = [], []

            for comp in page.get("components", []):
                variant = comp.get("variant_name") or comp.get("component_name")
                props_map = comp.get("props", {})
                props = " ".join([f'{k}="{v}"' for k, v in props_map.items()])
                page_imports.append(f'import {{ {variant} }} from "sf-builder-components";')
                page_body.append(f"      <{variant} {props} />")

            code = f"""import React from "react";
{os.linesep.join(page_imports)}

export default function {page_name}() {{
  return (
    <div>
{os.linesep.join(page_body)}
    </div>
  );
}}"""
            with open(page_file, "w") as f:
                f.write(code)

            app_imports.append(f'import {page_name} from "./{page_name}";')
            app_children.append(f"<{page_name} />")

        # 3. App.jsx
        app_code = f"""import React from "react";
{os.linesep.join(app_imports)}

export default function App() {{
  return (
    <div>
{os.linesep.join(app_children)}
    </div>
  );
}}"""
        with open(os.path.join(src_dir, "App.jsx"), "w") as f:
            f.write(app_code)

        # 4. index.html
        index_html = """<!doctype html>
<html>
  <head><meta charset="utf-8"><title>Generated App</title></head>
  <body><div id="root"></div><script src="index.js"></script></body>
</html>"""
        with open(os.path.join(temp_dir, "index.html"), "w") as f:
            f.write(index_html)

        # 5. index.js
        index_js = """import React from "react";
import { createRoot } from "react-dom/client";
import App from "./src/App";

const root = createRoot(document.getElementById("root"));
root.render(<App />);"""
        with open(os.path.join(temp_dir, "index.js"), "w") as f:
            f.write(index_js)

        # 6. Zip everything
        zip_name = f"{uuid.uuid4().hex}.zip"
        zip_path = os.path.join(tempfile.gettempdir(), zip_name)
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(temp_dir):
                for file in files:
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, temp_dir)
                    zipf.write(full_path, rel_path)

        return JSONResponse({
            "status": "success",
            "message": "App generated successfully",
            "download_url": f"/downloads/{zip_name}"
        })

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
