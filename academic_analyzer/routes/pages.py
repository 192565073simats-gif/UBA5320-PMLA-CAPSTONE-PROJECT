"""
routes/pages.py — HTML page routes rendered via Jinja2 templates.
"""

from pathlib import Path as _Path
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import jinja2

router = APIRouter()
_TEMPLATES_DIR = _Path(__file__).parent.parent / "templates"

_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=jinja2.select_autoescape(["html"]),
    cache_size=0,
    auto_reload=True,
)
templates = Jinja2Templates(env=_env)


def _ctx(request: Request, extra: dict = None) -> dict:
    ctx = {"request": request}
    if extra:
        ctx.update(extra)
    return ctx


@router.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
async def dashboard_page(request: Request):
    return templates.TemplateResponse(request=request, name="dashboard.html", context=_ctx(request))


@router.get("/login", response_class=HTMLResponse, include_in_schema=False)
async def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html", context=_ctx(request))


@router.get("/students", response_class=HTMLResponse, include_in_schema=False)
async def students_page(request: Request):
    return templates.TemplateResponse(request=request, name="students/list.html", context=_ctx(request))


@router.get("/students/new", response_class=HTMLResponse, include_in_schema=False)
async def new_student_page(request: Request):
    return templates.TemplateResponse(request=request, name="students/form.html", context=_ctx(request))


@router.get("/students/{student_id}", response_class=HTMLResponse, include_in_schema=False)
async def student_detail_page(request: Request, student_id: int):
    return templates.TemplateResponse(
        request=request,
        name="students/detail.html",
        context=_ctx(request, {"student_db_id": student_id}),
    )


@router.get("/subjects", response_class=HTMLResponse, include_in_schema=False)
async def subjects_page(request: Request):
    return templates.TemplateResponse(request=request, name="subjects/list.html", context=_ctx(request))


@router.get("/subjects/new", response_class=HTMLResponse, include_in_schema=False)
async def new_subject_page(request: Request):
    return templates.TemplateResponse(request=request, name="subjects/form.html", context=_ctx(request))


@router.get("/marks", response_class=HTMLResponse, include_in_schema=False)
async def marks_page(request: Request):
    return templates.TemplateResponse(request=request, name="marks/list.html", context=_ctx(request))


@router.get("/marks/new", response_class=HTMLResponse, include_in_schema=False)
async def new_marks_page(request: Request):
    return templates.TemplateResponse(request=request, name="marks/form.html", context=_ctx(request))


@router.get("/marks/upload", response_class=HTMLResponse, include_in_schema=False)
async def upload_page(request: Request):
    return templates.TemplateResponse(request=request, name="marks/form.html", context=_ctx(request))


@router.get("/analysis", response_class=HTMLResponse, include_in_schema=False)
async def analysis_page(request: Request):
    return templates.TemplateResponse(request=request, name="analysis/index.html", context=_ctx(request))


@router.get("/analysis/distributions", response_class=HTMLResponse, include_in_schema=False)
async def distributions_page(request: Request):
    return templates.TemplateResponse(request=request, name="analysis/distributions.html", context=_ctx(request))


@router.get("/performance", response_class=HTMLResponse, include_in_schema=False)
async def performance_page(request: Request):
    return templates.TemplateResponse(request=request, name="performance/index.html", context=_ctx(request))


@router.get("/reports", response_class=HTMLResponse, include_in_schema=False)
async def reports_page(request: Request):
    return templates.TemplateResponse(request=request, name="reports/list.html", context=_ctx(request))


@router.get("/about", response_class=HTMLResponse, include_in_schema=False)
async def about_page(request: Request):
    return templates.TemplateResponse(request=request, name="about.html", context=_ctx(request))
