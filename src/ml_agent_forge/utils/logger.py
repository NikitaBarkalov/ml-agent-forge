"""Structlog configuration: console (colored) + file (JSONL) with timestamps and log levels."""

import logging
import sys
from contextvars import ContextVar
from pathlib import Path
from queue import Empty, Queue

import structlog
from structlog.stdlib import ProcessorFormatter

# Context var for session-scoped log queue (WebSocket streaming)
_log_queue: ContextVar[Queue | None] = ContextVar("log_queue", default=None)


def set_log_queue(queue: Queue | None) -> None:
    """Set the current session's log queue for WebSocket streaming."""
    _log_queue.set(queue)


def get_log_queue() -> Queue | None:
    """Get the current session's log queue, if any."""
    try:
        return _log_queue.get()
    except LookupError:
        return None


class WebSocketLogHandler(logging.Handler):
    """Logging handler that pushes events to the current session's queue for WebSocket streaming."""

    _STANDARD_ATTRS = {
        "name", "msg", "args", "created", "filename", "funcName", "levelname",
        "levelno", "lineno", "module", "msecs", "pathname", "process", "processName",
        "relativeCreated", "stack_info", "exc_info", "exc_text", "thread", "threadName",
        "message", "taskName",
    }

    def emit(self, record: logging.LogRecord) -> None:
        queue = get_log_queue()
        if queue is None:
            return
        try:
            # Build message from record
            msg = record.getMessage()
            # Extract structlog/extra fields (agent, task, etc.)
            extra = {
                k: v for k, v in record.__dict__.items()
                if k not in self._STANDARD_ATTRS and not k.startswith("_")
            }
            payload = {
                "type": "log",
                "level": record.levelname.lower(),
                "message": msg,
                "agent": extra.get("agent"),
                "timestamp": getattr(record, "timestamp", None),
            }
            payload.update({k: v for k, v in extra.items() if k not in ("agent", "timestamp")})
            queue.put_nowait(payload)
        except Exception:
            self.handleError(record)


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

    # WebSocket streaming handler (pushes to queue when set via set_log_queue)
    ws_handler = WebSocketLogHandler()
    ws_handler.setLevel(logging.DEBUG)
    ws_handler.setFormatter(console_formatter)  # format not used for queue, but required

    # Root logger
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(ws_handler)
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
