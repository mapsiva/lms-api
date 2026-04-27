"""
Structured application exception and error response utilities.

Based on REST API error handling best practices:
- Machine-readable error code (English constant)
- Human-readable message in Portuguese
- HTTP status code
- Optional field-level validation details
- Request path and timestamp for diagnostics

Response body structure:
    {
        "status": 404,
        "error":   "NOT_FOUND",
        "code":    "ASSESSMENT_NOT_FOUND",
        "message": "Avaliação não encontrada.",
        "path":    "/assessments/abc-123",
        "timestamp": "2024-01-15T10:30:00Z",
        "details": []          # optional, used for validation errors
    }
"""

from datetime import datetime, timezone
from typing import Any, List, Optional

from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.error_codes import ErrorDefinition


# Mapping HTTP status → generic error category label
_HTTP_STATUS_LABELS = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    402: "PAYMENT_REQUIRED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    409: "CONFLICT",
    422: "UNPROCESSABLE_ENTITY",
    500: "INTERNAL_SERVER_ERROR",
}


def _error_label(http_status: int) -> str:
    return _HTTP_STATUS_LABELS.get(http_status, "ERROR")


def build_error_response(
    *,
    error_def: ErrorDefinition,
    request: Optional[Request] = None,
    details: Optional[List[Any]] = None,
    override_message: Optional[str] = None,
) -> JSONResponse:
    """
    Build a standardised JSONResponse for a known ErrorDefinition.

    Args:
        error_def:        The ErrorDefinition constant from ErrorCode.
        request:          Current FastAPI request (used to populate `path`).
        details:          Optional list of field-level error descriptors.
        override_message: Replaces the default Portuguese message when set.
    """
    body = {
        "status": error_def.http_status,
        "error": _error_label(error_def.http_status),
        "code": error_def.code,
        "message": override_message or error_def.message,
        "path": str(request.url.path) if request else None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if details:
        body["details"] = details
    
    # Log the error to the console before responding
    print(f"❌ [Error] {body.get('status')} {body.get('code')}: {body.get('message')}")
    if details:
        print(f"   Details: {details}")

    return JSONResponse(status_code=error_def.http_status, content=body)


class AppError(Exception):
    """
    Application-level exception that carries a structured ErrorDefinition.

    Raise this anywhere in service or router code; the global exception
    handler in main.py converts it into the standard JSON error body.

    Usage:
        from app.core.errors import AppError
        from app.core.error_codes import ErrorCode

        raise AppError(ErrorCode.USER_NOT_FOUND)
        raise AppError(ErrorCode.VALIDATION_ERROR, details=[{"field": "email", "msg": "inválido"}])
        raise AppError(ErrorCode.COMPANY_NOT_FOUND, message="Empresa 'ACME' não encontrada.")
    """

    def __init__(
        self,
        error_def: ErrorDefinition,
        *,
        message: Optional[str] = None,
        details: Optional[List[Any]] = None,
    ):
        self.error_def = error_def
        self.override_message = message
        self.details = details
        super().__init__(message or error_def.message)


def _format_pydantic_errors(raw_errors: List[dict]) -> List[dict]:
    """
    Convert Pydantic v2 validation errors into a cleaner, frontend-friendly list.
    """
    formatted = []
    for err in raw_errors:
        location = " → ".join(str(loc) for loc in err.get("loc", []))
        formatted.append({
            "field": location,
            "message": err.get("msg", "Valor inválido."),
            "type": err.get("type", "value_error"),
        })
    return formatted
