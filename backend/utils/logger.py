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


def websocket_log_processor(logger, method_name, event_dict):
    """Structlog processor that pushes events to the current session's log queue."""
    queue = get_log_queue()
    if queue is not None:
        try:
            # Prepare payload for WebSocket - only keep JSON serializable primitive types
            payload = {}
            for k, v in event_dict.items():
                # Skip internal records and non-serializable types
                if k.startswith("_") or k in ("metadata", "positional_args"):
                    continue
                if isinstance(v, (str, int, float, bool, list, dict)) or v is None:
                    payload[k] = v
                else:
                    payload[k] = str(v)

            payload["type"] = "log"
            # Ensure we have a message field
            if "event" in payload:
                payload["message"] = payload.pop("event")
            
            # Use level from structlog
            if "level" not in payload:
                payload["level"] = method_name
            
            queue.put_nowait(payload)
        except Exception as e:
            # Fallback for debugging
            import sys
            sys.stderr.write(f"Log queue error: {e}\n")
    return event_dict


def configure_logging(log_file: str | Path = "pipeline.log") -> None:
    """Configure structlog for console (colored) and file (JSONL) output."""
    log_path = Path(log_file)

    # Shared processors for timestamps and log levels
    shared_processors = [
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
        websocket_log_processor, # Push to WebSocket queue natively
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
