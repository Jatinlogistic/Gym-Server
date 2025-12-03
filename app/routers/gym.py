# ...existing code...
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import SessionLocal
from app.models import UserProfile, GymSuggestion
from app.ai.gym_suggestion import GymAssistant
from datetime import date

router = APIRouter(prefix="/profile", tags=["Gym"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/gym-suggestion", response_model=dict)
def create_gym_suggestion(data: dict, db: Session = Depends(get_db)):
    email = data.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="email is required")

    profile = db.query(UserProfile).filter(UserProfile.email == email).first()
    if not profile:
        raise HTTPException(status_code=404, detail="User profile not found")

    today = date.today()

    # Check if suggestion exists for today's date
    existing_suggestion = (
        db.query(GymSuggestion)
        .filter(GymSuggestion.user_email == email)
        .filter(func.date(GymSuggestion.created_at) == today)
        .first()
    )

    if existing_suggestion:
        return {
            "id": existing_suggestion.id,
            "date": existing_suggestion.created_at,
            "suggestion": existing_suggestion.suggestion
        }

    # Generate new suggestion if not found
    user_data = {
        "location": profile.city or "Rajkot",
        "pincode": profile.pincode or "",
        "budget": profile.budget or "medium",
        "age": profile.age or "unknown",
        "goal": profile.goal or "general fitness",
    }

    assistant = GymAssistant()
    suggestion = assistant.get_gym_suggestion(user_data)

    gym_rec = GymSuggestion(
        user_email=email,
        suggestion=suggestion.get("suggestion"),
        raw_output=suggestion.get("raw_output")
    )
    db.add(gym_rec)
    db.commit()
    db.refresh(gym_rec)

    return {
        "id": gym_rec.id,
        "date": gym_rec.created_at,
        "suggestion": suggestion.get("suggestion")
    }
