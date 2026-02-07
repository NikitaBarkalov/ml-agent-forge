"""Structlog configuration: console (colored) + file (JSONL) with timestamps and log levels."""

import logging
import sys
from pathlib import Path

import structlog
from structlog.stdlib import ProcessorFormatter


def configure_logging(log_file: str | Path = "pipeline.log") -> None:
    """Configure structlog for console (colored) and file (JSONL) output.

    - Console: Human-readable, colored via ConsoleRenderer.
    - File: JSONL format (one JSON object per line) for parsing.

    Timestamps and log levels are included in both outputs.
    Call this at the start of main() to capture all execution.
    """
    log_path = Path(log_file)

    # Shared processors for timestamps and log levels
    shared_processors = [
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    structlog.configure(
        processors=shared_processors + [ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Console: colored, human-readable
    console_formatter = ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            ProcessorFormatter.remove_processors_meta,
            structlog.dev.ConsoleRenderer(colors=True),
        ],
    )

    # File: JSONL (one JSON object per line)
    file_formatter = ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            ProcessorFormatter.remove_processors_meta,
            structlog.processors.JSONRenderer(),
        ],
    )

    # Handlers
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(file_formatter)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    root_logger.setLevel(logging.DEBUG)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a structlog logger for the given name."""
    return structlog.get_logger(name)


def truncate_for_log(value: str | object, max_len: int = 500) -> str:
    """Truncate long strings for safe log output (e.g., prompts, responses)."""
    if not isinstance(value, str):
        return str(value)
    if len(value) <= max_len:
        return value
    return value[:max_len] + f"...[truncated, total {len(value)} chars]"
