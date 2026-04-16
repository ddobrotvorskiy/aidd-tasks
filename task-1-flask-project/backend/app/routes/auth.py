from __future__ import annotations

from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.services.auth_service import AuthService

auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/register")
def register():
    """Register a new user."""
    try:
        data = RegisterRequest.model_validate(request.get_json(force=True) or {})
    except ValidationError as e:
        return jsonify({"error": "Validation failed", "code": "VALIDATION_ERROR", "details": e.errors()}), 422

    user = AuthService.register(data)
    return jsonify(user.to_dict()), 201


@auth_bp.post("/login")
def login():
    """Login and receive a JWT access token."""
    try:
        data = LoginRequest.model_validate(request.get_json(force=True) or {})
    except ValidationError as e:
        return jsonify({"error": "Validation failed", "code": "VALIDATION_ERROR", "details": e.errors()}), 422

    token = AuthService.login(data.email, data.password)
    return jsonify(TokenResponse(access_token=token).model_dump()), 200
