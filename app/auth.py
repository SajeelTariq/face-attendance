from datetime import datetime, timedelta
from jose import JWTError, jwt
import bcrypt
from fastapi import Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from . import models

SECRET_KEY = "face-attendance-secret-key-ipcv-2024"
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 8


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(user_id: int, role: str) -> str:
    expire = datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_HOURS)
    payload = {"sub": str(user_id), "role": role, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


def get_current_user(request: Request, db: Session) -> models.User | None:
    token = request.cookies.get("access_token")
    if not token:
        return None
    payload = decode_token(token)
    if not payload:
        return None
    user = db.query(models.User).filter(models.User.id == int(payload["sub"])).first()
    return user


def require_role(request: Request, db: Session, role: str) -> models.User | None:
    user = get_current_user(request, db)
    if not user or user.role != role:
        return None
    return user
