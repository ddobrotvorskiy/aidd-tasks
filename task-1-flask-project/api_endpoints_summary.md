# API ENDPOINTS SUMMARY

## Authentication Endpoints

| Метод | Endpoint | Auth | Параметры | Описание |
|-------|----------|------|-----------|----------|
| POST | `/api/auth/register` | ❌ | JSON body | Регистрация нового пользователя |
| POST | `/api/auth/login` | ❌ | JSON body | Вход и получение JWT токена |

### Register Request Body
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "full_name": "John Doe",
  "job_title": "Engineer",
  "department": "Engineering",
  "phone": "+1234567890"
}
```

### Login Request Body
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

---

## Employee Endpoints

| Метод | Endpoint | Auth | Параметры | Описание |
|-------|----------|------|-----------|----------|
| GET | `/api/employees/` | ✅ JWT | query: page, per_page, search | Получить список сотрудников |
| GET | `/api/employees/{id}` | ✅ JWT | id (path param) | Получить одного сотрудника |

### List Query Parameters
- `page` (int, default=1) - номер страницы
- `per_page` (int, default=20) - количество на странице
- `search` (string, optional) - поиск по имени/телефону/email

### Response Example
```json
{
  "items": [
    {
      "id": 1,
      "email": "user@example.com",
      "full_name": "John Doe",
      "job_title": "Engineer",
      "department": "Engineering",
      "phone": "+1234567890",
      "photo_url": "/uploads/avatars/uuid.jpg",
      "created_at": "2026-04-17T10:00:00+00:00"
    }
  ],
  "total": 100,
  "page": 1,
  "per_page": 20,
  "pages": 5
}
```

---

## Profile Endpoints

| Метод | Endpoint | Auth | Параметры | Описание |
|-------|----------|------|-----------|----------|
| GET | `/api/profile/me` | ✅ JWT | - | Получить профиль текущего пользователя |
| PATCH | `/api/profile/me` | ✅ JWT | JSON body | Обновить профиль |
| POST | `/api/profile/me/photo` | ✅ JWT | multipart/form-data | Загрузить фото профиля |
| POST | `/api/profile/me/change-password` | ✅ JWT | JSON body | Изменить пароль |

### Profile Update Request Body
```json
{
  "full_name": "Jane Doe",
  "job_title": "Senior Engineer",
  "department": "Engineering",
  "phone": "+0987654321"
}
```

### Change Password Request Body
```json
{
  "current_password": "OldPass123!",
  "new_password": "NewPass456!"
}
```

### Photo Upload
- Multipart form data
- Field name: `photo`
- Allowed types: png, jpg, jpeg, gif, webp
- Max size: 5 MB

---

## File Upload Endpoints

| Метод | Endpoint | Auth | Параметры | Описание |
|-------|----------|------|-----------|----------|
| GET | `/uploads/{filename}` | ❌ | filename (path param) | Скачать загруженный файл |

---

## Error Responses

### Standard Error Response
```json
{
  "error": "Error message",
  "code": "ERROR_CODE",
  "details": []  // Optional, only for validation errors
}
```

### HTTP Status Codes
- 200 - OK
- 201 - Created
- 400 - Bad Request
- 401 - Unauthorized
- 403 - Forbidden
- 404 - Not Found
- 409 - Conflict
- 422 - Validation Error
- 500 - Internal Server Error

---

## Input Validation

### Email Validation
- Must be valid email format
- Used in: register, login

### Password Validation
- Min length: 8 characters
- Max length: 128 characters
- Currently: no complexity requirements (SECURITY ISSUE)

### Full Name
- Min length: 1 character
- Max length: 255 characters
- Cannot be blank/whitespace only

### Search Parameter
- Type: string
- Searches in: full_name, phone, email
- Case-insensitive ILIKE matching

### Pagination
- Page: minimum 1
- Per Page: default 20, max 100 (not enforced currently - SECURITY ISSUE)

---

## Frontend Forms

### Login Form
- Email input (email validation)
- Password input (password field)

### Register Form
- Full Name input (required)
- Email input (email validation)
- Password input (password field, min 8 chars)
- Job Title input (optional)
- Department input (optional)
- Phone input (optional)

### Profile Update Form
- Full Name input (optional)
- Job Title input (optional)
- Department input (optional)
- Phone input (optional)
- Photo upload (accept image/*, max 5MB)

### Change Password Form
- Current Password input
- New Password input (min 8 chars)

---

## Security-Related Query Parameters

### Search Parameter Security
- ✅ Uses ORM with parameterized queries (no SQL injection risk)
- ❌ No length validation (could be DoS vector)
- ❌ Logged in detail (could leak data)

### Pagination Security
- ❌ No minimum/maximum validation
- ❌ Negative values accepted
- ❌ No rate limiting

---

## Authentication Flow

1. User submits registration form
2. Backend validates with Pydantic schemas
3. Password hashed with bcrypt
4. User stored in database
5. Backend automatically logs in user
6. JWT token returned
7. Token stored in localStorage (SECURITY ISSUE)
8. Token sent in Authorization header for all API requests

---

## JWT Token Details

- Algorithm: HS256 (HMAC with SHA-256)
- Secret: `JWT_SECRET_KEY` from config
- TTL: 60 minutes (default)
- Claims: user_id as identity
- Header: `Authorization: Bearer {token}`

---

## Data Flow

```
Frontend Form
    ↓
Frontend Validation
    ↓
Axios API Client
    ↓
Backend Route Handler
    ↓
Pydantic Schema Validation
    ↓
Service Layer (Business Logic)
    ↓
SQLAlchemy ORM
    ↓
PostgreSQL Database
```

