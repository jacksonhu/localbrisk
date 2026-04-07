"""Async-safe logging context helpers for runtime observability."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Any, Dict, Iterator, Mapping, Optional

_RUNTIME_LOG_CONTEXT: ContextVar[Dict[str, Any]] = ContextVar(
    "agent_engine_runtime_log_context",
    default={},
)


def _clean_context(values: Mapping[str, Any]) -> Dict[str, Any]:
    """Drop empty values so log payloads stay compact and stable."""
    return {
        key: value
        for key, value in values.items()
        if value is not None and value != ""
    }



def get_logging_context() -> Dict[str, Any]:
    """Return the current logging context as a detached copy."""
    return dict(_RUNTIME_LOG_CONTEXT.get())



def bind_logging_context(**kwargs: Any) -> Token:
    """Merge fields into the current logging context and return a reset token."""
    merged = get_logging_context()
    merged.update(_clean_context(kwargs))
    return _RUNTIME_LOG_CONTEXT.set(merged)



def reset_logging_context(token: Token) -> None:
    """Restore the previous logging context state."""
    _RUNTIME_LOG_CONTEXT.reset(token)


@contextmanager
def scoped_logging_context(**kwargs: Any) -> Iterator[Dict[str, Any]]:
    """Bind logging fields for the lifetime of a scoped operation."""
    token = bind_logging_context(**kwargs)
    try:
        yield get_logging_context()
    finally:
        reset_logging_context(token)



def merge_logging_context(extra: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    """Return current context merged with optional extra fields."""
    payload = get_logging_context()
    if extra:
        payload.update(_clean_context(extra))
    return payload



def format_logging_context(extra: Optional[Mapping[str, Any]] = None) -> str:
    """Render context into a stable key=value string for plain log lines."""
    payload = merge_logging_context(extra)
    if not payload:
        return ""
    ordered = [f"{key}={payload[key]}" for key in sorted(payload.keys())]
    return " | ".join(ordered)
