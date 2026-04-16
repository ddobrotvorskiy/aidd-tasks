from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from app.schemas.employee import EmployeeResponse
from app.services.employee_service import EmployeeService

employees_bp = Blueprint("employees", __name__)


@employees_bp.get("/")
@jwt_required()
def list_employees():
    """List employees with optional search and pagination."""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    search = request.args.get("search", None, type=str) or None

    result = EmployeeService.get_list(page=page, per_page=per_page, search=search)
    return jsonify(result.model_dump()), 200


@employees_bp.get("/<int:employee_id>")
@jwt_required()
def get_employee(employee_id: int):
    """Get a single employee card by ID."""
    user = EmployeeService.get_by_id(employee_id)
    return jsonify(EmployeeResponse.model_validate(user).model_dump()), 200
