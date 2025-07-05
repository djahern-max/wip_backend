from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_password_hash
from app.models.user import User
from app.schemas.user import UserCreate, UserInDB
from app.api.auth import get_current_active_user

router = APIRouter()


def create_user(db: Session, user: UserCreate):
    # Check if user already exists
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        hashed_password=hashed_password,
        is_active=user.is_active
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.post("/register", response_model=UserInDB)
async def register_user(user: UserCreate, db: Session = Depends(get_db)):
    return create_user(db=db, user=user)


@router.get("/profile", response_model=UserInDB)
async def get_user_profile(current_user: User = Depends(get_current_active_user)):
    return current_user
