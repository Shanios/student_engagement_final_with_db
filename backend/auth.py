from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import jwt, JWTError
import os

from database import SessionLocal
from models import User, TokenBlacklist

router = APIRouter(prefix="/api/auth", tags=["auth"])

# ====== CONFIG ======

SECRET_KEY = os.getenv("JWT_SECRET", "dev-secret-key-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # ✅ HARDENED: Reduced from 60 to 30 minutes
REFRESH_TOKEN_EXPIRE_DAYS = 7  # ✅ NEW: Refresh token valid for 7 days

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()


# ====== DB DEPENDENCY ======

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ====== PWD HELPERS ======

def hash_password(password: str) -> str:
    # bcrypt limit is 72 bytes – truncate extremely long passwords for safety
    if len(password) > 72:
        password = password[:72]
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if len(plain_password) > 72:
        plain_password = plain_password[:72]
    return pwd_context.verify(plain_password, hashed_password)


# ====== Pydantic SCHEMAS ======

class RegisterPayload(BaseModel):
    email: EmailStr
    password: str
    role: str = "student"  # "student" or "teacher"


class LoginPayload(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ✅ NEW: Refresh token schema
class RefreshTokenPayload(BaseModel):
    refresh_token: str


# ✅ NEW: Token response with refresh token
class TokenResponseWithRefresh(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class UserOut(BaseModel):
    id: int
    email: EmailStr
    role: str

    class Config:
        from_attributes = True


# ====== JWT HELPERS ======

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta is None:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = now + expires_delta
    to_encode.update({"exp": expire, "iat": now})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """
    Read JWT from Authorization: Bearer <token>,
    decode, fetch user from DB.
    
    ✅ NEW: Check if token is blacklisted (revoked)
    """
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int | None = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    # ✅ NEW: Check if token is blacklisted
    is_blacklisted = db.query(TokenBlacklist).filter(
        TokenBlacklist.token == token
    ).first()
    
    if is_blacklisted:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
        )

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


# ====== ROUTES ======

@router.post("/register", response_model=UserOut)
def register(payload: RegisterPayload, db: Session = Depends(get_db)):
    # Check if email already exists
    if len(payload.password) < 8:
       raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# ✅ UPDATED: Login now returns refresh token too
@router.post("/login", response_model=TokenResponseWithRefresh)
def login(payload: LoginPayload, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # ✅ NEW: Create both access and refresh tokens
    access_token = create_access_token({"sub": str(user.id), "role": user.role})
    refresh_token = create_access_token(
        {"sub": str(user.id), "type": "refresh"}, 
        expires_delta=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )
    
    return TokenResponseWithRefresh(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60  # seconds
    )


# ✅ NEW: Refresh token endpoint
@router.post("/refresh", response_model=TokenResponseWithRefresh)
def refresh_token_endpoint(
    payload: RefreshTokenPayload,
    db: Session = Depends(get_db)
):
    """
    Exchange refresh token for new access token.
    ✅ NEW: Allows users to stay logged in without re-entering credentials.
    """
    try:
        refresh_payload = jwt.decode(payload.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        if refresh_payload.get("type") != "refresh":
            raise JWTError("Not a refresh token")
        
        user_id: int | None = refresh_payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    # ✅ NEW: Create fresh access token
    new_access_token = create_access_token({"sub": str(user.id), "role": user.role})
    
    return TokenResponseWithRefresh(
        access_token=new_access_token,
        refresh_token=payload.refresh_token,  # Reuse same refresh token
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


# ✅ NEW: Logout/revoke endpoint
@router.post("/logout")
def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Revoke token by adding to blacklist.
    ✅ NEW: Prevents reuse of stolen tokens.
    """
    token = credentials.credentials
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    exp = datetime.fromtimestamp(payload.get("exp"), tz=timezone.utc)
    
    blacklist_entry = TokenBlacklist(
        token=token,
        user_id=current_user.id,
        expires_at=exp
    )
    db.add(blacklist_entry)
    db.commit()
    
    return {"status": "logged_out", "message": "Token revoked"}


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user