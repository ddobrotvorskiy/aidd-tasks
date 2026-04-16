from __future__ import annotations

from flask_jwt_extended import create_access_token

from app import bcrypt, db
from app.models.user import User
from app.schemas.auth import RegisterRequest
from app.services.exceptions import AuthError, ConflictError


class AuthService:
    @staticmethod
    def register(data: RegisterRequest) -> User:
        existing = db.session.execute(
            db.select(User).where(User.email == data.email)
        ).scalar_one_or_none()

        if existing:
            raise ConflictError(f"Email {data.email} is already registered")

        password_hash = bcrypt.generate_password_hash(data.password).decode("utf-8")

        user = User(
            email=data.email,
            password_hash=password_hash,
            full_name=data.full_name,
            job_title=data.job_title,
            department=data.department,
            phone=data.phone,
        )
        db.session.add(user)
        db.session.commit()
        return user

    @staticmethod
    def login(email: str, password: str) -> str:
        user = db.session.execute(
            db.select(User).where(User.email == email)
        ).scalar_one_or_none()

        if not user or not bcrypt.check_password_hash(user.password_hash, password):
            raise AuthError("Invalid email or password")

        token = create_access_token(identity=str(user.id))
        return token
