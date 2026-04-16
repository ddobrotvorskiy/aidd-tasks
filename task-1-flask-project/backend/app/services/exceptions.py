from __future__ import annotations


class AppError(Exception):
    """Base application error."""

    http_status: int = 400
    code: str = "APP_ERROR"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(AppError):
    http_status = 404
    code = "NOT_FOUND"


class ConflictError(AppError):
    http_status = 409
    code = "CONFLICT"


class AuthError(AppError):
    http_status = 401
    code = "UNAUTHORIZED"


class ForbiddenError(AppError):
    http_status = 403
    code = "FORBIDDEN"


class ValidationError(AppError):
    http_status = 422
    code = "VALIDATION_ERROR"
