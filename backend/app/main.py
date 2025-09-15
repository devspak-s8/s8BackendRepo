# app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging

from app.routes.auth import auth_router
from app.routes.templates import template_router
from app.routes.bookings import booking_router
from app.routes.dashboard import dashboard_router
from app.routes.ws import ws_router
from s8.db.database import user_collection

from s8.core.error_handlers import (
    http_exception_handler,
    validation_exception_handler,
    generic_exception_handler
)

app = FastAPI(title="S8Builder Auth API")

# Enable CORS for testing (adjust origins in production)
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

# ✅ Register routes
app.include_router(auth_router, prefix="/api/auth")
app.include_router(booking_router, prefix="/api/bookings")
app.include_router(ws_router, prefix="/api/ws")
app.include_router(template_router, prefix="/api/templates")
app.include_router(dashboard_router, prefix="/api/dashboard")
# ✅ Register global exception handlers
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

@app.get("/")
async def root():
    return {"message": "Welcome to S8Builder Auth API"}

# ✅ DB connectivity check
@app.on_event("startup")
async def startup_db_check():
    try:
        await user_collection.find_one({})
        logging.info("✅ MongoDB connected successfully.")
    except Exception as e:
        logging.error("❌ MongoDB connection failed: %s", e)
