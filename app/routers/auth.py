from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import UserAuth, UserProfile
from app.schemas.auth_schema import SignupRequest, SignupResponse, LoginRequest, LoginResponse
from passlib.context import CryptContext

router = APIRouter(prefix="/auth", tags=["Auth"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


@router.post("/signup", response_model=SignupResponse)
def signup(data: SignupRequest, db: Session = Depends(get_db)):
    # Validate passwords match
    if data.password != data.confirm_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Passwords do not match")

    # Ensure email is unique across auth and profile tables
    existing = db.query(UserAuth).filter(UserAuth.email == data.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists with this email")

    # Also check user_profiles table to be safe
    existing_profile = db.query(UserProfile).filter(UserProfile.email == data.email).first()
    if existing_profile:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists with this email")

    # Hash password and store
    pwd_hash = hash_password(data.password)

    auth = UserAuth(name=data.name, email=data.email, phone=data.phone, password_hash=pwd_hash)
    db.add(auth)

    # Create a minimal UserProfile record so other endpoints using profiles work
    if not existing_profile:
        profile = UserProfile(name=data.name, email=data.email)
        db.add(profile)

    db.commit() 
    db.refresh(auth)

    return SignupResponse(auth_id=auth.auth_id, name=auth.name, email=auth.email, phone=auth.phone)


@router.post("/login", response_model=LoginResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    username = data.username

    # Try email first, then phone
    user = db.query(UserAuth).filter(UserAuth.email == username).first()
    if not user:
        user = db.query(UserAuth).filter(UserAuth.phone == username).first()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    return LoginResponse(auth_id=user.auth_id, name=user.name, email=user.email)
