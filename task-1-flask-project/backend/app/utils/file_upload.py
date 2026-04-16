from __future__ import annotations

import os
import uuid

from flask import current_app
from werkzeug.datastructures import FileStorage


ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_upload(file: FileStorage, subfolder: str = "avatars") -> str:
    """Save an uploaded file and return its public URL path."""
    if not file or not file.filename:
        raise ValueError("No file provided")

    if not allowed_file(file.filename):
        raise ValueError(
            f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    ext = file.filename.rsplit(".", 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    upload_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], subfolder)
    os.makedirs(upload_dir, exist_ok=True)

    filepath = os.path.join(upload_dir, filename)
    file.save(filepath)

    return f"/uploads/{subfolder}/{filename}"
