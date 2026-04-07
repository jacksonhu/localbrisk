"""Structured event and audit helpers for runtime observability."""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, Optional

from .logging_context import merge_logging_context
from .metrics import runtime_metrics

runtime_event_logger = logging.getLogger("agent_engine.monitoring.events")
runtime_audit_logger = logging.getLogger("agent_engine.monitoring.audit")



def _sanitize_fields(fields: Dict[str, Any]) -> Dict[str, Any]:
    """Remove empty values so event payloads stay compact."""
    return {
        key: value
        for key, value in fields.items()
        if value is not None and value != ""
    }



def emit_runtime_event(
    event_name: str,
    *,
    level: int = logging.INFO,
    logger: Optional[logging.Logger] = None,
    **fields: Any,
) -> Dict[str, Any]:
    """Emit a structured runtime event and update in-memory metrics."""
    payload = merge_logging_context(
        {
            "event_name": event_name,
            "timestamp": round(time.time(), 3),
            **_sanitize_fields(fields),
        }
    )
    target_logger = logger or runtime_event_logger
    target_logger.log(
        level,
        "runtime_event %s",
        json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str),
    )
    runtime_metrics.increment(event_name)
    duration_ms = payload.get("duration_ms")
    if isinstance(duration_ms, (int, float)):
        runtime_metrics.observe_duration(event_name, float(duration_ms))
    return payload



def emit_audit_event(event_name: str, *, level: int = logging.INFO, **fields: Any) -> Dict[str, Any]:
    """Emit a structured audit event."""
    return emit_runtime_event(
        f"audit.{event_name}",
        level=level,
        logger=runtime_audit_logger,
        **fields,
    )
