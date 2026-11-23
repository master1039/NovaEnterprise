"""Structured logs remain valid JSON with useful machine-readable fields."""

import json
import logging

from backend.app.core.logging import JsonFormatter, configure_logging


def test_json_formatter_emits_standard_and_context_fields() -> None:
    record = logging.LogRecord(
        name="novaenterprise.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=17,
        msg="phase one event",
        args=(),
        exc_info=None,
    )
    record.request_id = "request-123"

    payload = json.loads(JsonFormatter().format(record))

    assert payload["level"] == "INFO"
    assert payload["logger"] == "novaenterprise.test"
    assert payload["message"] == "phase one event"
    assert payload["request_id"] == "request-123"
    assert payload["timestamp"].endswith("Z")


def test_configure_logging_is_idempotent() -> None:
    configure_logging("WARNING")
    first_handlers = tuple(logging.getLogger().handlers)

    configure_logging("WARNING")

    assert tuple(logging.getLogger().handlers) == first_handlers
