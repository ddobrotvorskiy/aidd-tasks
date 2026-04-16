from __future__ import annotations

from app import bcrypt, db
from app.models.user import User
from app.schemas.employee import EmployeeListResponse, EmployeeResponse, ProfileUpdateRequest
from app.services.exceptions import AuthError, NotFoundError

MAX_PAGE_SIZE = 100
DEFAULT_PAGE_SIZE = 20


class EmployeeService:
    @staticmethod
    def get_list(
        page: int = 1,
        per_page: int = DEFAULT_PAGE_SIZE,
        search: str | None = None,
    ) -> EmployeeListResponse:
        per_page = min(per_page, MAX_PAGE_SIZE)
        query = db.select(User)

        if search:
            pattern = f"%{search}%"
            query = query.where(
                db.or_(
                    User.full_name.ilike(pattern),
                    User.phone.ilike(pattern),
                    User.email.ilike(pattern),
                )
            )

        query = query.order_by(User.full_name)
        paginated = db.paginate(query, page=page, per_page=per_page, error_out=False)

        items = [EmployeeResponse.model_validate(u) for u in paginated.items]
        return EmployeeListResponse(
            items=items,
            total=paginated.total,
            page=paginated.page,
            per_page=paginated.per_page,
            pages=paginated.pages,
        )

    @staticmethod
    def get_by_id(employee_id: int) -> User:
        user = db.session.get(User, employee_id)
        if not user:
            raise NotFoundError(f"Employee {employee_id} not found")
        return user

    @staticmethod
    def update_profile(user_id: int, data: ProfileUpdateRequest) -> User:
        user = db.session.get(User, user_id)
        if not user:
            raise NotFoundError(f"User {user_id} not found")

        update_data = data.model_dump(exclude_none=True)
        for field, value in update_data.items():
            setattr(user, field, value)

        db.session.commit()
        return user

    @staticmethod
    def update_photo(user_id: int, photo_url: str) -> User:
        user = db.session.get(User, user_id)
        if not user:
            raise NotFoundError(f"User {user_id} not found")
        user.photo_url = photo_url
        db.session.commit()
        return user

    @staticmethod
    def change_password(user_id: int, current_password: str, new_password: str) -> None:
        user = db.session.get(User, user_id)
        if not user:
            raise NotFoundError(f"User {user_id} not found")

        if not bcrypt.check_password_hash(user.password_hash, current_password):
            raise AuthError("Current password is incorrect")

        user.password_hash = bcrypt.generate_password_hash(new_password).decode("utf-8")
        db.session.commit()
