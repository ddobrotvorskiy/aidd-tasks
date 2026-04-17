# SECURITY QUICK REFERENCE - Flask Employee Directory

## КРИТИЧЕСКИЕ УЯЗВИМОСТИ (НЕМЕДЛЕННО ИСПРАВИТЬ)

### 1️⃣ CORS: Wildcard Origin (*) - КРИТИЧЕСКАЯ
**Файл:** `backend/app/__init__.py:43`
```python
CORS(app, resources={r"/api/*": {"origins": "*"}})  # ❌ ОПАСНО!
```
**Исправление:** Указать конкретные домены в `origins`

### 2️⃣ JWT in localStorage - КРИТИЧЕСКАЯ (XSS)
**Файл:** `frontend/src/contexts/AuthContext.tsx:20`
```typescript
localStorage.setItem('access_token', access_token);  // ❌ Уязвимо для XSS!
```
**Исправление:** Использовать httpOnly cookies вместо localStorage

### 3️⃣ Path Traversal in File Upload
**Файл:** `backend/app/routes/uploads.py:11`
```python
return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)
```
**Исправление:** Проверить, что путь находится в пределах upload папки

---

## ВЫСОКИЕ УЯЗВИМОСТИ (ИСПРАВИТЬ ПЕРЕД PRODUCTION)

### 4️⃣ Missing Security Headers
**Файл:** `backend/app/__init__.py`
**Отсутствуют:** X-Frame-Options, X-Content-Type-Options, CSP, HSTS
**Добавить:** @app.after_request функцию с security headers

### 5️⃣ Default Hardcoded Secrets
**Файл:** `backend/app/config.py:13,15`
```python
SECRET_KEY: str = "change-me-in-production"  # ❌
JWT_SECRET_KEY: str = "jwt-change-me-in-production"  # ❌
```
**Исправление:** Требовать через .env или выбросить ошибку

### 6️⃣ No Rate Limiting
**Файлы:** `backend/app/routes/auth.py`
**Проблема:** Brute-force на login/register не ограничен
**Решение:** pip install flask-limiter + @limiter.limit()

---

## СРЕДНИЕ УЯЗВИМОСТИ

### 7️⃣ Weak File Upload Validation
**Файл:** `backend/app/utils/file_upload.py:13`
**Проблема:** Проверка только расширения, нет MIME/magic bytes
**Исправление:** Добавить MIME-type check и magic bytes validation

### 8️⃣ No Password Complexity Rules
**Файл:** `backend/app/schemas/auth.py:8`
**Проблема:** Пароль "12345678" проходит валидацию
**Исправление:** Требовать uppercase, lowercase, digits, special chars

### 9️⃣ Sensitive Data in Logs
**Файл:** `backend/app/routes/errors.py:17`
**Проблема:** Логирование всех ошибок валидации (может быть пароль)
**Исправление:** Фильтровать sensitive fields в production

### 🔟 No Audit Logging
**Файл:** Везде
**Проблема:** Не логируются попытки входа/изменения
**Исправление:** Создать SecurityAudit класс с logger

---

## ЗЕЛЕНЫЕ ФЛАГИ (Хорошо сделано)

✅ Использование ORM SQLAlchemy (no SQL injection)
✅ Pydantic для валидации входных данных
✅ bcrypt для хеширования паролей
✅ JWT вместо сессий
✅ @jwt_required() на защищенных endpoints
✅ Нет eval/exec/pickle
✅ UUID для имен файлов

---

## БЫСТРЫЙ ЧЕКЛИСТ

### Перед production development:
- [ ] Исправить CORS (явные домены)
- [ ] Перенести JWT в httpOnly cookies
- [ ] Добавить path traversal проверку
- [ ] Добавить security headers
- [ ] Потребовать конфиг секреты
- [ ] Добавить rate limiting
- [ ] Усилить валидацию файлов
- [ ] Добавить аудит логирование

### Для production deployment:
- [ ] Все выше
- [ ] HTTPS с HSTS
- [ ] WAF (Web Application Firewall)
- [ ] Penetration testing
- [ ] Security scanning (bandit, safety)
- [ ] Dependency updates
- [ ] Backup & disaster recovery

---

## БЫСТРЫЕ ИСПРАВЛЕНИЯ

### 1. Security Headers (copy-paste)
```python
@app.after_request
def security_headers(response):
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    if app.config.get('ENV') == 'production':
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response
```

### 2. Rate Limiting (copy-paste)
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
limiter.init_app(app)

@auth_bp.post("/login")
@limiter.limit("5 per minute")
def login():
    # ...
```

### 3. Path Traversal Fix (copy-paste)
```python
import os
full_path = os.path.abspath(os.path.join(upload_dir, filename))
if not full_path.startswith(os.path.abspath(upload_dir)):
    return jsonify({"error": "Invalid path"}), 403
```

---

## ТЕСТИРОВАНИЕ

### Проверить CORS
```bash
curl -H "Origin: https://evil.com" \
  -H "Access-Control-Request-Method: POST" \
  -X OPTIONS http://localhost:5000/api/auth/login -v
```

### Проверить security headers
```bash
curl -I http://localhost:5000/
```

### Проверить можно ли скомпрометить файлы
```bash
curl http://localhost:5000/uploads/../../config.py
```

---

## СТАТИСТИКА

- **API Endpoints:** 8
  - 2 без аутентификации (auth)
  - 6 с JWT аутентификацией
  
- **Точки ввода данных:** 10
  - JSON body: 6
  - Query params: 2
  - File upload: 1
  - Path params: 1

- **Forms:** 4
  - Login (2 fields)
  - Register (6 fields)
  - Profile Update (4 fields)
  - Change Password (2 fields)

---

## РЕСУРСЫ

- OWASP Top 10: https://owasp.org/Top10/
- CWE Top 25: https://cwe.mitre.org/top25/
- NIST Cybersecurity Framework: https://www.nist.gov/cyberframework

