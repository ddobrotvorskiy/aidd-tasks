from __future__ import annotations

import os

from flask import Blueprint, send_from_directory, current_app

uploads_bp = Blueprint("uploads", __name__)


@uploads_bp.get("/uploads/<path:filename>")
def serve_upload(filename: str):
    """Serve uploaded files (avatars, etc.)."""
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)
