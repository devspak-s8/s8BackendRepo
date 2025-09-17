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
    Generate a Vite + React + Tailwind app for a given project.
    Body: { "project_id": "<id>" }
    """
    project_id = data.get("project_id")
    if not project_id:
        raise HTTPException(status_code=400, detail="project_id is required")

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
    components_dir = os.path.join(src_dir, "components")
    pages_dir = os.path.join(src_dir, "pages")
    public_dir = os.path.join(temp_dir, "public")

    os.makedirs(components_dir, exist_ok=True)
    os.makedirs(pages_dir, exist_ok=True)
    os.makedirs(public_dir, exist_ok=True)

    try:
        # 1. package.json
        package_json = {
            "name": f"s8-project-{uuid.uuid4().hex[:6]}",
            "version": "1.0.0",
            "private": True,
            "scripts": {
                "dev": "vite",
                "build": "vite build",
                "preview": "vite preview"
            },
            "dependencies": {
                "react": "^18.2.0",
                "react-dom": "^18.2.0",
                "sf-builder-components": "latest",
                "devspak-s8": "latest"
            },
            "devDependencies": {
                "vite": "^5.0.0",
                "tailwindcss": "^3.3.0",
                "postcss": "^8.4.0",
                "autoprefixer": "^10.4.0",
                "@vitejs/plugin-react": "^4.2.0"
            }
        }
        with open(os.path.join(temp_dir, "package.json"), "w") as f:
            json.dump(package_json, f, indent=2)

        # 2. Vite config
        vite_config = """import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
});
"""
        with open(os.path.join(temp_dir, "vite.config.js"), "w") as f:
            f.write(vite_config)

        # 3. Tailwind + PostCSS configs
        tailwind_config = """export default {
  content: ["./index.html", "./src/**/*.{js,jsx,ts,tsx}"],
  theme: { extend: {} },
  plugins: [],
};
"""
        postcss_config = """export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
"""
        with open(os.path.join(temp_dir, "tailwind.config.js"), "w") as f:
            f.write(tailwind_config)
        with open(os.path.join(temp_dir, "postcss.config.js"), "w") as f:
            f.write(postcss_config)

        # 4. index.html
        index_html = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>S8 Generated App</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
"""
        with open(os.path.join(temp_dir, "index.html"), "w") as f:
            f.write(index_html)

        # 5. index.css
        index_css = """@tailwind base;
@tailwind components;
@tailwind utilities;
"""
        with open(os.path.join(src_dir, "index.css"), "w") as f:
            f.write(index_css)

        # 6. main.jsx
        main_jsx = """import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
"""
        with open(os.path.join(src_dir, "main.jsx"), "w") as f:
            f.write(main_jsx)

        # 7. Generate Pages + Components
        pages = project.get("pages", [])
        app_imports, app_routes = [], []

        for page in pages:
            page_name = page.get("page_name", "Page").replace(" ", "")
            page_file = os.path.join(pages_dir, f"{page_name}.jsx")
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
    <div className="p-6">
{os.linesep.join(page_body)}
    </div>
  );
}}"""
            with open(page_file, "w") as f:
                f.write(code)

            app_imports.append(f'import {page_name} from "./pages/{page_name}";')
            app_routes.append(f"<{page_name} />")

        # 8. App.jsx
        app_code = f"""import React from "react";
{os.linesep.join(app_imports)}

export default function App() {{
  return (
    <div className="min-h-screen bg-gray-50">
{os.linesep.join(app_routes)}
    </div>
  );
}}"""
        with open(os.path.join(src_dir, "App.jsx"), "w") as f:
            f.write(app_code)

        # 9. Public placeholder
        with open(os.path.join(public_dir, "favicon.ico"), "wb") as f:
            f.write(b"")  # empty placeholder

        # 10. Zip everything
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
            "message": "Vite + Tailwind app generated successfully",
            "download_url": f"/downloads/{zip_name}"
        })

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
