import jwt
import bcrypt
from datetime import datetime, timedelta
from fastapi import Request

SECRET_KEY = "studybot-secret-key"
ALGORITHM = "HS256"

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())

def create_token(data: dict, expire_hours: int = 8) -> str:
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(hours=expire_hours)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except Exception:
        return None

def get_current_user(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        return None
    return decode_token(token)
