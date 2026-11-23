"""NovaEnterprise FastAPI application factory."""

from fastapi import FastAPI

from backend.app.api.system import router as system_router
from backend.app.core.config import Settings, get_settings
from backend.app.core.exceptions import install_exception_handlers
from backend.app.core.logging import configure_logging
from novaenterprise import __version__


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build an isolated application instance for runtime or tests."""

    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings.log_level)
    application = FastAPI(
        title=resolved_settings.app_name,
        version=__version__,
        debug=resolved_settings.debug,
        description="Phase 1 runtime shell for NovaEnterprise.",
    )
    application.state.settings = resolved_settings
    install_exception_handlers(application)
    application.include_router(system_router)
    return application


app = create_app()
