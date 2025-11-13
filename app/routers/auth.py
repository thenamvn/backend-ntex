from datetime import timedelta
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session

from ..dependencies import get_db_session
from ..config import settings
from ..schemas.user import UserCreate, UserRead, Token, UserLogin
from ..services import (
    create_user,
    authenticate_user,
    create_access_token,
    get_current_user,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db_session)
):
    """
    Register a new user.
    
    - **email**: Valid email address (must be unique)
    - **password**: User password (will be hashed)
    - **name**: Optional user name
    """
    try:
        user = create_user(db, user_data)
        return user
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating user: {str(e)}"
        )


@router.post("/token", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db_session)
):
    """
    Authenticate user and return JWT token.
    
    Uses OAuth2 password flow (form data):
    - **username**: User's email address
    - **password**: User's password
    
    Returns:
    - **access_token**: JWT token for authentication
    - **token_type**: "bearer"
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.email, "user_id": user.id},
        expires_delta=access_token_expires
    )
    
    return Token(access_token=access_token, token_type="bearer")


@router.post("/login", response_model=Token)
async def login_json(
    user_data: UserLogin,
    db: Session = Depends(get_db_session)
):
    """
    Alternative login endpoint that accepts JSON instead of form data.
    
    - **email**: User's email address
    - **password**: User's password
    
    Returns:
    - **access_token**: JWT token for authentication
    - **token_type**: "bearer"
    """
    user = authenticate_user(db, user_data.email, user_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.email, "user_id": user.id},
        expires_delta=access_token_expires
    )
    
    return Token(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=UserRead)
async def get_me(current_user: UserRead = Depends(get_current_user)):
    """
    Get current user information.
    
    Requires authentication (JWT token in Authorization header).
    """
    return current_user


@router.get("/test")
async def test_auth():
    """Test endpoint to verify auth router is working."""
    return {"message": "Auth router is working!"}
