"""FastAPI Application entry point for ArenaMate.

Sets up application factories, mounts static assets, registers routing paths,
enforces security policies, and configures rate-limiting check dependencies.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import Settings, get_settings
from app.logging_conf import get_logger
from app.models.schemas import (
    AccessibilityNeed,
    DestinationIntent,
    GuideResponse,
    HealthResponse,
    Language,
    UserContext,
)
from app.services.arena_data import Arena, get_arena
from app.services.context_engine import PathNotFoundException, run_guide
from app.services.llm import get_phraser_client
from app.services.security import RateLimiter

logger = get_logger("arenamate")

_STATIC_DIR = Path(__file__).resolve().parent / "static"

_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Content-Security-Policy": (
        "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; "
        "connect-src 'self'; base-uri 'none'; frame-ancestors 'none'"
    ),
}


def _arena_metadata(arena: Arena) -> dict:
    """Format sector and amenity information for the frontend client.

    Args:
        arena (Arena): Current in-memory Arena DB.

    Returns:
        dict: Formatted metadata dictionary containing arena settings and vocabulary.
    """
    return {
        "arena": {
            "name": arena.name,
            "fifa_name": arena.fifa_name,
            "city": arena.city,
            "capacity": arena.capacity,
        },
        "zones": [
            {"id": s.id, "name": s.names, "type": s.type, "level": s.level}
            for s in arena.sectors.values()
        ],
        "facilities": [
            {
                "id": a.id,
                "name": a.names,
                "type": a.type,
                "zone": a.sector,
                "accessible": a.accessible,
                "landmark": a.landmarks,
            }
            for a in arena.amenities
        ],
        "intents": [intent.value for intent in DestinationIntent],
        "languages": [lang.value for lang in Language],
        "accessibility_needs": [need.value for need in AccessibilityNeed],
    }


def _check_rate_limit(request: Request) -> None:
    """Check request source IP against rate limit buckets.

    Args:
        request (Request): The incoming Starlette/FastAPI request object.

    Raises:
        HTTPException: 429 status code if client exceeds request rate capacities.
    """
    limiter: RateLimiter = request.app.state.rate_limiter
    client_ip = request.client.host if request.client else "unknown"
    allowed, retry_after = limiter.check(client_ip)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please slow down.",
            headers={"Retry-After": str(int(retry_after) + 1)},
        )


def create_app(settings: Settings | None = None) -> FastAPI:
    """FastAPI Application Factory.

    Args:
        settings (Settings | None): Configuration overrides (typically in tests).

    Returns:
        FastAPI: The configured FastAPI application instance.
    """
    settings = settings or get_settings()

    app = FastAPI(
        title="ArenaMate",
        description="Multilingual, accessible wayfinding assistant for Los Angeles Stadium (SoFi Stadium).",
        version="1.0.0",
    )

    # Initialize app states
    app.state.settings = settings
    app.state.arena = get_arena()
    app.state.phraser = get_phraser_client(settings)
    app.state.rate_limiter = RateLimiter(
        settings.rate_limit_capacity, settings.rate_limit_refill_per_sec
    )

    # CORS settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @app.middleware("http")
    async def append_security_headers(request: Request, call_next):
        response = await call_next(request)
        for header, value in _SECURITY_HEADERS.items():
            response.headers.setdefault(header, value)
        return response

    @app.exception_handler(PathNotFoundException)
    async def path_not_found_handler(request: Request, exc: PathNotFoundException):
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.get("/health", response_model=HealthResponse, tags=["system"])
    async def health() -> HealthResponse:
        return HealthResponse(status="ok")

    @app.get("/api/arena", tags=["data"])
    @app.get("/api/stadium", tags=["data"])
    async def arena_metadata(request: Request) -> dict:
        return _arena_metadata(request.app.state.arena)

    @app.post(
        "/api/guide",
        response_model=GuideResponse,
        dependencies=[Depends(_check_rate_limit)],
        tags=["guide"],
    )
    @app.post(
        "/api/assist",
        response_model=GuideResponse,
        dependencies=[Depends(_check_rate_limit)],
        tags=["guide"],
    )
    async def guide(ctx: UserContext, request: Request) -> GuideResponse:
        arena: Arena = request.app.state.arena
        phraser = request.app.state.phraser
        response = await run_guide(ctx, arena, phraser)

        logger.info(
            "guide location=%s intent=%s needs=%s occupancy=%s used_llm=%s",
            ctx.current_location,
            ctx.destination_intent.value,
            "+".join(n.value for n in ctx.accessibility_needs),
            response.occupancy_level.value,
            response.used_llm,
        )
        return response

    @app.get("/", include_in_schema=False)
    async def serve_index() -> FileResponse:
        return FileResponse(_STATIC_DIR / "index.html")

    app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

    return app


app = create_app()
