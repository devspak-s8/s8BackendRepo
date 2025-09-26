# app/main.py

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
from fastapi.security import OAuth2PasswordBearer
from fastapi.openapi.utils import get_openapi
import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

# Routers
from app.routes.auth import auth_router
from app.routes.templates import template_router
from app.routes.bookings import booking_router
from app.routes.dashboard import dashboard_router
from app.routes.ws import ws_router
from app.routes.generated_pages import router as generated_pages_router
from app.routes.generate_app import router as generate_app_router
from app.routes.profile import profile_router 
from app.routes.download import router as download_router
from app.routes.test import test_router

# Error Handlers
from s8.core.error_handlers import (
    http_exception_handler,
    validation_exception_handler,
    generic_exception_handler
)

# ------------------------
# MongoDB setup
# ------------------------

MONGO_URL = os.environ.get("MONGO_URL")  # Railway-provided string
client = AsyncIOMotorClient(MONGO_URL)
db = client["s8builder"]  # your database name
user_collection = db["users"]

# ------------------------
# App init
# ------------------------
app = FastAPI(title="S8Builder API")

# ------------------------
# OAuth2 / Swagger Authorize
# ------------------------
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="S8Builder API",
        version="1.0.0",
        description="API for S8Builder",
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "OAuth2Password": {
            "type": "oauth2",
            "flows": {"password": {"tokenUrl": "/api/auth/login", "scopes": {}}}
        }
    }
    for path in openapi_schema["paths"].values():
        for method in path.values():
            method["security"] = [{"OAuth2Password": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# ------------------------
# CORS
# ------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://10.156.117.138:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------
# Routes
# ------------------------
app.include_router(auth_router, prefix="/api/auth")
app.include_router(booking_router, prefix="/api/bookings")
app.include_router(ws_router, prefix="/api/ws")
app.include_router(template_router, prefix="/api/templates")
app.include_router(dashboard_router, prefix="/api/dashboard")
app.include_router(generated_pages_router, prefix="/api/pages")
app.include_router(generate_app_router, prefix="/api/pagesgenerated")
app.include_router(download_router)
app.include_router(test_router, prefix="/api/test", tags=["test"])
app.include_router(profile_router, prefix="/api")

# ------------------------
# Exception handlers
# ------------------------
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# ------------------------
# Health & root
# ------------------------
@app.get("/")
async def root():
    return {"message": "🚀 Welcome to S8Builder API"}

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

# ------------------------
# DB connectivity check
# ------------------------
@app.on_event("startup")
async def startup_db_check():
    try:
        # 5-second timeout to avoid blocking Railway
        await asyncio.wait_for(user_collection.find_one({}), timeout=5)
        logging.info("✅ MongoDB connected successfully.")
    except Exception as e:
        logging.error("❌ MongoDB connection failed: %s", e)
