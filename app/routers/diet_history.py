from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date
from app.database import SessionLocal
from app.models import UserProfile, UserDiet

router = APIRouter(prefix="/profile/diet-history", tags=["Diet History"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("", response_model=list)
def get_diet_history(data: dict, db: Session = Depends(get_db)):
    """
    Get all past diet history for a user, excluding today's plan.
    Input: name, email
    """
    name = data.get("name")
    email = data.get("email")
    
    if not name or not email:
        raise HTTPException(status_code=400, detail="Name and email are required")

    # Verify user exists
    profile = db.query(UserProfile).filter(
        UserProfile.name == name,
        UserProfile.email == email
    ).first()

    if not profile:
        raise HTTPException(status_code=404, detail="User not found")

    today = date.today()
    
    # Query past diets (excluding today)
    history = db.query(UserDiet).filter(
        UserDiet.user_email == email,
        func.date(UserDiet.created_at) != today
    ).order_by(UserDiet.created_at.desc()).all()

    return [
        {
            "diet_plan_id": item.diet_planid,
            "date": str(item.created_at.date()),
            "diet_plan": item.diet_plan
        }
        for item in history
    ]
