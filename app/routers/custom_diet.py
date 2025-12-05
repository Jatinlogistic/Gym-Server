from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date
import json

from app.database import SessionLocal
from app.models import UserProfile, UserCustomDiet, UserDiet
from app.ai.custom_diet import CustomDietAssistant

router = APIRouter(prefix="/profile", tags=["Custom Diet"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/custom-diet", response_model=dict)
def custom_diet_plan(data: dict, db: Session = Depends(get_db)):
    email = data.get("email")
    ingredients = data.get("ingredients")

    if not email or ingredients is None:
        raise HTTPException(status_code=400, detail="email and ingredients are required")

    profile = db.query(UserProfile).filter(UserProfile.email == email).first()
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")

    today = date.today()

    # Check if today's plan exists
    existing = (
        db.query(UserCustomDiet)
        .filter(
            UserCustomDiet.user_email == email,
            func.date(UserCustomDiet.created_at) == today
        )
        .first()
    )

    if existing:
        return {
            "date": today,
            "custom_diet_id": existing.custom_diet_id,
            "ingredients": existing.ingredients,
            "diet_plan": existing.diet_plan,
        }

    # Fetch YESTERDAY'S custom plan
    yesterday_custom = (
        db.query(UserCustomDiet)
        .filter(
            UserCustomDiet.user_email == email,
            func.date(UserCustomDiet.created_at) < today
        )
        .order_by(UserCustomDiet.created_at.desc())
        .first()
    )

    previous_date = "N/A"
    yesterday_plan = "None"

    if yesterday_custom:
        previous_date = str(yesterday_custom.created_at.date())
        yesterday_plan = json.dumps(yesterday_custom.diet_plan)

    # Prepare user data including yesterday plan for LLM
    user_data = {
        "name": profile.name,
        "email": profile.email,
        "age": profile.age,
        "gender": profile.gender,
        "height": profile.height,
        "weight": profile.weight,
        "goal": profile.goal,
        "activity_level": profile.activity_level,
        "diet_type": profile.diet_type,
        "food_allergies": profile.food_allergies,
        "food_dislikes": profile.food_dislikes,
        "previous_date": previous_date,
        "yesterday_plan": yesterday_plan,
    }

    # Generate new custom plan
    assistant = CustomDietAssistant()
    plan = assistant.get_custom_plan(user_data, ingredients, current_date=today)

    # Normalize ingredients
    if isinstance(ingredients, str):
        ingredients = [i.strip() for i in ingredients.split(",")]

    new = UserCustomDiet(
        user_email=email,
        ingredients=ingredients,
        diet_plan=plan
    )
    db.add(new)
    db.commit()
    db.refresh(new)

    return {
        "date": today,
        "custom_diet_id": new.custom_diet_id,
        "ingredients": new.ingredients,
        "diet_plan": new.diet_plan,
    }
