from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings, get_settings
from app.database import build_session_factory, initialize_database
from app.routers import auth, posts, users
from app.services.storage import SupabaseStorageService


def create_app(
    *,
    settings: Settings | None = None,
    storage_service: SupabaseStorageService | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    if settings.is_production and settings.database_url.strip().lower().startswith("sqlite"):
        raise RuntimeError("Production cannot use SQLite. Set SHOWFZU_DATABASE_URL to Supabase Postgres.")
    if settings.database_url.startswith("sqlite"):
        import app.models  # noqa: F401

        initialize_database(settings.database_url)

    app = FastAPI(title=settings.app_name)

    app.state.settings = settings
    app.state.session_factory = build_session_factory(settings.database_url)
    app.state.storage_service = storage_service or SupabaseStorageService(settings)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(auth.router, prefix="/api")
    app.include_router(users.router, prefix="/api")
    app.include_router(posts.router, prefix="/api")

    return app


app = create_app()
