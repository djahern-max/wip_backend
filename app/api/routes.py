# ===== backend/app/api/routes.py =====
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.auth import (
    authenticate_user, 
    create_access_token, 
    get_password_hash,
    get_current_active_user
)
from app.models.user import User as UserModel
from app.schemas.user import User, UserCreate, UserUpdate
from app.schemas.auth import LoginRequest, Token
from app.core.config import settings

router = APIRouter()

@router.get("/health")
def health_check():
    return {"status": "healthy"}

# Authentication endpoints
@router.post("/auth/login", response_model=Token)
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    """Login endpoint - authenticate user and return JWT token."""
    user = authenticate_user(db, login_data.username, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/auth/me", response_model=User)
def read_current_user(current_user: UserModel = Depends(get_current_active_user)):
    """Get current user profile."""
    return current_user

# User management endpoints (protected and hidden registration)
@router.post("/users/", response_model=User)
def create_user(
    user: UserCreate, 
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)  # Requires authentication
):
    """Create a new user - requires authentication (hidden registration)."""
    # Check if user already exists
    db_user = db.query(UserModel).filter(UserModel.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    db_user = db.query(UserModel).filter(UserModel.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already taken")
    
    # Hash the password and create user
    hashed_password = get_password_hash(user.password)
    db_user = UserModel(
        email=user.email,
        username=user.username,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.get("/users/", response_model=List[User])
def read_users(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
):
    """Get all users - requires authentication."""
    users = db.query(UserModel).offset(skip).limit(limit).all()
    return users

@router.get("/users/{user_id}", response_model=User)
def read_user(
    user_id: int, 
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
):
    """Get a specific user - requires authentication."""
    db_user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

# Admin-only endpoint to create first user (for initial setup)
@router.post("/admin/create-first-user", response_model=User)
def create_first_user(user: UserCreate, db: Session = Depends(get_db)):
    """Create the first user when no users exist - admin setup only."""
    # Check if any users exist
    user_count = db.query(UserModel).count()
    if user_count > 0:
        raise HTTPException(
            status_code=400, 
            detail="Users already exist. Use the protected endpoint to create more users."
        )
    
    # Create the first user
    hashed_password = get_password_hash(user.password)
    db_user = UserModel(
        email=user.email,
        username=user.username,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user