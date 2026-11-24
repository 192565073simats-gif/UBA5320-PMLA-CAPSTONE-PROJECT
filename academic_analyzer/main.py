"""
main.py — FastAPI application entry-point for the Academic Analyzer.

Run with:
    uvicorn academic_analyzer.main:app --reload --host 0.0.0.0 --port 8000
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from academic_analyzer.database import create_tables, get_db
from academic_analyzer.auth import get_password_hash
from pathlib import Path as _Path
_BASE_DIR = _Path(__file__).parent

# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ---------------------------------------------------------------------------
# Lazy router imports (they depend on models/db which must be ready first)
# ---------------------------------------------------------------------------
def _import_routers():
    from academic_analyzer.routes.auth import router as auth_router
    from academic_analyzer.routes.students import router as students_router
    from academic_analyzer.routes.subjects import router as subjects_router
    from academic_analyzer.routes.marks import router as marks_router
    from academic_analyzer.routes.analysis import router as analysis_router
    from academic_analyzer.routes.reports import router as reports_router
    from academic_analyzer.routes.dashboard import router as dashboard_router
    from academic_analyzer.routes.pages import router as pages_router
    return (
        auth_router,
        students_router,
        subjects_router,
        marks_router,
        analysis_router,
        reports_router,
        dashboard_router,
        pages_router,
    )


# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialise DB tables and seed admin user."""
    logger.info("Starting up Academic Analyzer …")
    create_tables()
    _seed_admin()
    yield
    logger.info("Shutting down Academic Analyzer …")


def _seed_admin() -> None:
    """Create the configured admin account if one does not already exist."""
    from academic_analyzer.models import User  # noqa: PLC0415

    admin_username = os.getenv("ADMIN_USERNAME", "admin")
    admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
    db = next(get_db())
    try:
        existing = db.query(User).filter(User.is_admin == True).first()  # noqa: E712
        if existing is None:
            admin = User(
                username=admin_username,
                email="admin@academic-analyzer.local",
                hashed_password=get_password_hash(admin_password),
                is_active=True,
                is_admin=True,
            )
            db.add(admin)
            db.commit()
            logger.info("Admin user created (username=%s).", admin_username)
        else:
            logger.info("Existing admin user retained.")
    except Exception as exc:
        db.rollback()
        logger.error("Failed to seed admin user: %s", exc)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Academic Analyzer",
    description=(
        "Statistical Analysis of Student Academic Performance "
       
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS (allow all origins for development)
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Static files & templates
# ---------------------------------------------------------------------------
app.mount("/static", StaticFiles(directory=str(_BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(_BASE_DIR / "templates"))

# ---------------------------------------------------------------------------
# Register routers
# ---------------------------------------------------------------------------
(
    auth_router,
    students_router,
    subjects_router,
    marks_router,
    analysis_router,
    reports_router,
    dashboard_router,
    pages_router,
) = _import_routers()

app.include_router(auth_router,      prefix="/api/auth",      tags=["Authentication"])
app.include_router(students_router,  prefix="/api/students",  tags=["Students"])
app.include_router(subjects_router,  prefix="/api/subjects",  tags=["Subjects"])
app.include_router(marks_router,     prefix="/api/marks",     tags=["Marks / Assessments"])
app.include_router(analysis_router,  prefix="/api/analysis",  tags=["Statistical Analysis"])
app.include_router(reports_router,   prefix="/api/reports",   tags=["Reports"])
app.include_router(dashboard_router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(pages_router,     prefix="",               tags=["Pages"])

# ---------------------------------------------------------------------------
# Root redirect
# ---------------------------------------------------------------------------
@app.get("/", include_in_schema=False)
async def root_redirect():
    return RedirectResponse(url="/dashboard", status_code=302)


# ---------------------------------------------------------------------------
# Custom 404 handler
# ---------------------------------------------------------------------------
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(status_code=404, content={"detail": "Not Found"})


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "app": "Academic Analyzer", "version": "1.0.0"}
