from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.api.routes import admin, auth, home, journal, pages, schedule, users
from src.core.seed import init_db
from src.core.templating import BASE_DIR, templates


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()  # створює таблиці та першого адміна з .env
    yield


app = FastAPI(title="School Schedule Platform", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


@app.exception_handler(StarletteHTTPException)
async def html_aware_errors(request: Request, exc: StarletteHTTPException):
    if "text/html" in request.headers.get("accept", ""):
        if exc.status_code == 401:
            return RedirectResponse("/login", status_code=302)  # анонім у браузері -> логін
        return templates.TemplateResponse(
            request,
            "error.html",
            {"user": None, "code": exc.status_code, "message": exc.detail},
            status_code=exc.status_code,
        )
    return await http_exception_handler(request, exc)  # API/тести: JSON


for r in (
    pages.router,
    auth.router,
    users.router,
    admin.router,
    journal.router,
    schedule.router,
    home.router,
):
    app.include_router(r)
