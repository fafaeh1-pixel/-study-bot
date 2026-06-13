@"
with open(r'C:\Users\1001\StudyBotPro\dashboard\auth.py', 'w', encoding='utf-8') as f:
    f.write("""import jwt
import bcrypt
from datetime import datetime, timedelta
from fastapi import Request

SECRET_KEY = 'studybot-secret-key'
ALGORITHM = 'HS256'

def hash_password(plain):
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()

def verify_password(plain, hashed):
    return bcrypt.checkpw(plain.encode(), hashed.encode())

def create_token(data, expire_hours=8):
    payload = data.copy()
    payload['exp'] = datetime.utcnow() + timedelta(hours=expire_hours)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except Exception:
        return None

def get_current_user(request):
    token = request.cookies.get('access_token')
    if not token:
        return None
    return decode_token(token)
""")
print('OK')
"@ | Set-Content fix_auth.py -Encoding UTF8
python fix_auth.py