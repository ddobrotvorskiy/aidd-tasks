from __future__ import annotations

from flask import Flask, jsonify
from pydantic import ValidationError as PydanticValidationError

from app.services.exceptions import AppError


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(AppError)
    def handle_app_error(e: AppError):
        app.logger.warning("AppError: %s", e.message)
        return jsonify({"error": e.message, "code": e.code}), e.http_status

    @app.errorhandler(PydanticValidationError)
    def handle_pydantic_error(e: PydanticValidationError):
        errors = e.errors()
        app.logger.warning("ValidationError: %s", errors)
        return jsonify({"error": "Validation failed", "code": "VALIDATION_ERROR", "details": errors}), 422

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Resource not found", "code": "NOT_FOUND"}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({"error": "Method not allowed", "code": "METHOD_NOT_ALLOWED"}), 405

    @app.errorhandler(413)
    def request_entity_too_large(e):
        return jsonify({"error": "File too large", "code": "FILE_TOO_LARGE"}), 413

    @app.errorhandler(500)
    def internal_error(e):
        app.logger.error("Internal error: %s", e)
        return jsonify({"error": "Internal server error", "code": "INTERNAL_ERROR"}), 500
