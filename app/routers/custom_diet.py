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
    """Create or return a custom ingredient-driven diet plan for today.

    Input JSON: {"email": "user@example.com", "ingredients": ["tomato", "eggs"] }
    Response: {date, custom_diet_id, ingredients, diet_plan}
    """
    email = data.get("email")
    ingredients = data.get("ingredients")

    if not email or ingredients is None:
        raise HTTPException(status_code=400, detail="email and ingredients are required")

    # Find user profile
    profile = db.query(UserProfile).filter(UserProfile.email == email).first()
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")

    today = date.today()

    # Check if custom diet exists for today
    existing = db.query(UserCustomDiet).filter(
        UserCustomDiet.user_email == email,
        func.date(UserCustomDiet.created_at) == today
    ).first()

    if existing:
        return {
            "date": today,
            "custom_diet_id": existing.custom_diet_id,
            "ingredients": existing.ingredients,
            "diet_plan": existing.diet_plan,
        }

    # Fetch latest past diet plan (for context) if present
    latest_past_diet = db.query(UserDiet).filter(UserDiet.user_email == email).order_by(UserDiet.created_at.desc()).first()

    previous_date = "N/A"
    yesterday_plan = "None"
    if latest_past_diet:
        previous_date = str(latest_past_diet.created_at.date())
        yesterday_plan = json.dumps(latest_past_diet.diet_plan)

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

    assistant = CustomDietAssistant()
    plan = assistant.get_custom_plan(user_data, ingredients, current_date=today)

    # Ensure ingredients saved as list
    if isinstance(ingredients, (list, tuple)):
        ingredient_save = list(ingredients)
    elif isinstance(ingredients, str):
        # attempt to split by comma
        if "," in ingredients:
            ingredient_save = [i.strip() for i in ingredients.split(",") if i.strip()]
        else:
            ingredient_save = [ingredients]
    else:
        ingredient_save = [str(ingredients)]

    new = UserCustomDiet(user_email=email, ingredients=ingredient_save, diet_plan=plan)
    db.add(new)
    db.commit()
    db.refresh(new)

    return {
        "date": today,
        "custom_diet_id": new.custom_diet_id,
        "ingredients": ingredient_save,
        "diet_plan": plan,
    }
