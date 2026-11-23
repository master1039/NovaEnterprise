"""NovaEnterprise FastAPI application factory."""

from fastapi import FastAPI

from backend.app.api.auth import router as auth_router
from backend.app.api.system import router as system_router
from backend.app.core.config import Settings, get_settings
from backend.app.core.exceptions import install_exception_handlers
from backend.app.core.logging import configure_logging
from backend.app.middleware.audit import AuditMiddleware, AuditTrail
from backend.app.middleware.rate_limit import InMemoryRateLimiter, RateLimitMiddleware
from backend.app.middleware.request_context import RequestContextMiddleware
from novaenterprise import __version__


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build an isolated application instance for runtime or tests."""

    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings.log_level)
    application = FastAPI(
        title=resolved_settings.app_name,
        version=__version__,
        debug=resolved_settings.debug,
        description="NovaEnterprise runtime, persistence, and security foundation.",
    )
    application.state.settings = resolved_settings
    audit_trail = AuditTrail(max_records=resolved_settings.audit_trail_max_records)
    application.state.audit_trail = audit_trail
    install_exception_handlers(application)
    # Starlette executes the last-added middleware first. Request context must
    # be outermost so rate-limit responses are correlated, then audit records
    # every outcome, including requests rejected by the limiter.
    application.add_middleware(
        RateLimitMiddleware,
        limiter=InMemoryRateLimiter(resolved_settings.rate_limit_per_minute),
    )
    application.add_middleware(AuditMiddleware, trail=audit_trail)
    application.add_middleware(RequestContextMiddleware)
    application.include_router(system_router)
    application.include_router(auth_router, prefix=resolved_settings.api_prefix)
    return application


app = create_app()
