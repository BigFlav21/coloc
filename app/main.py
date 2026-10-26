from urllib.parse import urlparse

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, select
from starlette.middleware.sessions import SessionMiddleware

from .auth import AuthRedirect, LoginLimiter
from .config import DEFAULT_SECRET, Settings
from .db import init_db, make_engine
from .routers import auth, courses, home, ideas, menus
from .templating import BASE_DIR

UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def create_app(settings: Settings | None = None, engine=None) -> FastAPI:
    settings = settings or Settings()
    if settings.cookie_secure and settings.secret_key == DEFAULT_SECRET:
        raise RuntimeError("COLOC_SECRET_KEY doit être défini quand COLOC_COOKIE_SECURE=true")

    engine = engine or make_engine(settings.database_url)
    init_db(engine)

    app = FastAPI(title="Coloc", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.settings = settings
    app.state.engine = engine
    app.state.limiter = LoginLimiter()

    @app.middleware("http")
    async def protect(request: Request, call_next):
        if request.method in UNSAFE_METHODS:
            origin = request.headers.get("origin")
            if origin:
                allowed = {request.headers.get("host", ""), request.headers.get("x-forwarded-host", "")}
                if urlparse(origin).netloc not in allowed:
                    return PlainTextResponse("Origine refusée", status_code=403)
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        return response

    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.secret_key,
        max_age=settings.session_days * 86400,
        https_only=settings.cookie_secure,
        same_site="lax",
    )

    @app.exception_handler(AuthRedirect)
    async def auth_redirect(request: Request, exc: AuthRedirect):
        if request.headers.get("hx-request"):
            return Response(status_code=200, headers={"HX-Redirect": exc.url})
        return RedirectResponse(exc.url, status_code=303)

    @app.get("/healthz", include_in_schema=False)
    def healthz():
        with Session(app.state.engine) as db:
            db.exec(select(1)).one()
        return {"status": "ok"}

    app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
    for module in (auth, home, menus, courses, ideas):
        app.include_router(module.router)
    return app


def get_app() -> FastAPI:
    return create_app()
