import json
import logging
from datetime import datetime, timezone
from time import perf_counter
from uuid import uuid4

from flask import g, has_request_context, request
from psycopg2 import OperationalError


def database_error_category(error):
    state = error.pgcode
    detail = str(error).lower()
    if (state and state.startswith("28")) or "authentication failed" in detail:
        return "authentication"
    if "tenant or user not found" in detail:
        return "pooler_user"
    if "could not translate host name" in detail:
        return "dns"
    if "ssl" in detail or "certificate" in detail:
        return "tls"
    if "timeout" in detail or "timed out" in detail:
        return "timeout"
    if "network is unreachable" in detail or "connection refused" in detail:
        return "network"
    return "other"


class JsonFormatter(logging.Formatter):
    def format(self, record):
        entry = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if has_request_context():
            entry["correlation_id"] = getattr(g, "correlation_id", None)
            entry["route"] = request.url_rule.rule if request.url_rule else None
            entry["method"] = request.method
        for field in ("status_code", "duration_ms"):
            if hasattr(record, field):
                entry[field] = getattr(record, field)
        if record.exc_info:
            entry["error_type"] = record.exc_info[0].__name__
            error = record.exc_info[1]
            if isinstance(error, OperationalError):
                entry["database_error"] = database_error_category(error)
        return json.dumps(entry, ensure_ascii=False)


def configure_logging(app) -> None:
    level = getattr(logging, app.config.get("LOG_LEVEL", "INFO").upper(), logging.INFO)
    formatter = JsonFormatter()
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    app.logger.handlers.clear()
    app.logger.addHandler(handler)
    app.logger.setLevel(level)
    app.logger.propagate = False

    log_file = app.config.get("LOG_FILE")
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        app.logger.addHandler(file_handler)

    @app.before_request
    def start_request():
        g.correlation_id = uuid4().hex
        g.started_at = perf_counter()

    @app.after_request
    def finish_request(response):
        response.headers["X-Request-ID"] = g.correlation_id
        app.logger.info("request_completed", extra={
            "status_code": response.status_code,
            "duration_ms": round((perf_counter() - g.started_at) * 1000, 2),
        })
        return response
