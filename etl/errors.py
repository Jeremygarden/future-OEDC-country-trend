"""Shared ETL error payload helpers.

Keep Python data-pipeline failures aligned with the TypeScript backend's
HTTP error envelope: {"error": {"code", "message", "status_code", "details"}}.
The snake_case status_code is intentional for Python callers; it maps directly
to the backend statusCode field documented in SECURITY/CONTRIBUTING.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class EtlError(Exception):
    code: str
    message: str
    status_code: int = 500
    details: Any | None = None

    def __str__(self) -> str:
        return self.message

    def to_payload(self) -> dict[str, dict[str, Any]]:
        payload: dict[str, Any] = {
            "code": self.code,
            "message": self.message,
            "status_code": self.status_code,
        }
        if self.details is not None:
            payload["details"] = self.details
        return {"error": payload}


def etl_error_payload(
    code: str,
    message: str,
    status_code: int = 500,
    details: Any | None = None,
) -> dict[str, dict[str, Any]]:
    return EtlError(code=code, message=message, status_code=status_code, details=details).to_payload()
