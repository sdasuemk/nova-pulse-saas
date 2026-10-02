import logging
import sys
from app.core.config import settings


def setup_logging() -> None:
    """Configures application-wide logging with structured format."""
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO

    log_format = (
        "[%(asctime)s] [%(levelname)s] [%(name)s:%(lineno)d] - %(message)s"
    )

    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )

    # Silence overly verbose third-party loggers in dev
    logging.getLogger("aiosqlite").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)


logger = logging.getLogger("novapulse")
