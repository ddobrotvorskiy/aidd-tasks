from __future__ import annotations

from flask import Blueprint, jsonify, request, send_from_directory, current_app
from flask_jwt_extended import get_jwt_identity, jwt_required
from pydantic import ValidationError

from app.schemas.employee import ChangePasswordRequest, EmployeeResponse, ProfileUpdateRequest
from app.services.employee_service import EmployeeService
from app.utils.file_upload import save_upload

profile_bp = Blueprint("profile", __name__)


@profile_bp.get("/me")
@jwt_required()
def get_my_profile():
    """Get the current user's profile."""
    user_id = int(get_jwt_identity())
    user = EmployeeService.get_by_id(user_id)
    return jsonify(EmployeeResponse.model_validate(user).model_dump()), 200


@profile_bp.patch("/me")
@jwt_required()
def update_my_profile():
    """Update the current user's profile fields."""
    user_id = int(get_jwt_identity())
    try:
        data = ProfileUpdateRequest.model_validate(request.get_json(force=True) or {})
    except ValidationError as e:
        return jsonify({"error": "Validation failed", "code": "VALIDATION_ERROR", "details": e.errors()}), 422

    user = EmployeeService.update_profile(user_id, data)
    return jsonify(EmployeeResponse.model_validate(user).model_dump()), 200


@profile_bp.post("/me/photo")
@jwt_required()
def upload_photo():
    """Upload a profile photo."""
    user_id = int(get_jwt_identity())

    if "photo" not in request.files:
        return jsonify({"error": "No file provided", "code": "BAD_REQUEST"}), 400

    file = request.files["photo"]
    try:
        photo_url = save_upload(file, subfolder="avatars")
    except ValueError as e:
        return jsonify({"error": str(e), "code": "BAD_REQUEST"}), 400

    user = EmployeeService.update_photo(user_id, photo_url)
    return jsonify({"photo_url": user.photo_url}), 200


@profile_bp.post("/me/change-password")
@jwt_required()
def change_password():
    """Change the current user's password."""
    user_id = int(get_jwt_identity())
    try:
        data = ChangePasswordRequest.model_validate(request.get_json(force=True) or {})
    except ValidationError as e:
        return jsonify({"error": "Validation failed", "code": "VALIDATION_ERROR", "details": e.errors()}), 422

    EmployeeService.change_password(user_id, data.current_password, data.new_password)
    return jsonify({"message": "Password changed successfully"}), 200
