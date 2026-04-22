"""Auth routes — async throughout."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field, field_validator
from app.database import get_db, User
from app.auth import verify_password, create_token, hash_password, get_current_user
from app.schemas import TokenResponse, UserMe

router = APIRouter(prefix="/auth", tags=["auth"])

_COMMON_PASSWORDS = {"password", "12345678", "password1", "qwerty123", "demo1234"}


class RegisterRequest(BaseModel):
    username:  str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")
    password:  str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(default="", max_length=200)

    @field_validator("password")
    @classmethod
    def password_not_common(cls, v: str) -> str:
        if v.lower() in _COMMON_PASSWORDS:
            raise ValueError("Password is too common — choose a stronger password")
        return v


@router.post("/login", response_model=TokenResponse)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).filter(User.username == form.username))
    user   = result.scalar_one_or_none()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token({"sub": user.username, "role": user.role})
    return TokenResponse(access_token=token, token_type="bearer",
                         role=user.role, full_name=user.full_name)


@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).filter(User.username == req.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already exists")
    user = User(username=req.username, hashed_password=hash_password(req.password),
                full_name=req.full_name, role="applicant")
    db.add(user)
    await db.commit()
    await db.refresh(user)
    token = create_token({"sub": user.username, "role": user.role})
    return TokenResponse(access_token=token, token_type="bearer",
                         role=user.role, full_name=user.full_name)


@router.get("/me", response_model=UserMe)
async def me(current_user: User = Depends(get_current_user)):
    return UserMe(username=current_user.username, role=current_user.role,
                  full_name=current_user.full_name)
