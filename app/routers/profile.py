# app/routers/profile.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
from datetime import date
from app.ai.diet_suggestion import DietAssistant
from app.database import SessionLocal
from app.models import UserProfile, UserDiet, UserWorkout, UserAuth
from app.schemas.profile_schema import ProfileCreate, ProfileResponse, ProfileUpdate
from sqlalchemy import text
from app.routers.auth import get_current_user

router = APIRouter(prefix="/profile", tags=["Profile"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# profile creation endpoint
@router.post("/", response_model=ProfileResponse)
def create_or_update_profile(data: ProfileCreate, db: Session = Depends(get_db)):
    # Check if profile already exists
    profile = db.query(UserProfile).filter(UserProfile.email == data.email).first()
    
    if profile:
        # Update existing profile instead of creating new
        for key, value in data.dict(exclude_unset=True).items():
            setattr(profile, key, value)
    else:
        # Create new profile
        profile = UserProfile(**data.dict())
        db.add(profile)

    try:
        db.commit()
        db.refresh(profile)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Profile creation failed: {str(e)}")
    return profile

# diet-plan endpoint 
@router.post("/diet-plan", response_model=dict)
def get_diet(data: dict, db: Session = Depends(get_db)):

    current_user: UserAuth = Depends(get_current_user)
    name = data.get("name")
    email = data.get("email")
    if not name or not email:
        raise HTTPException(status_code=400, detail="Name and email are required")

    profile = db.query(UserProfile).filter(
        UserProfile.name == name,
        UserProfile.email == email
    ).first()

    if not profile:
        raise HTTPException(status_code=404, detail="User not found")

    today = date.today()
    existing_diet = db.query(UserDiet).filter(
        UserDiet.user_email == current_user.email,
        func.date(UserDiet.created_at) == today
    ).first()

    if existing_diet:
        return {
            "date": today,
            "diet_plan_id": existing_diet.diet_planid,
            "diet_plan": existing_diet.diet_plan
        }

    # Fetch previous diet plan for context
    latest_past_diet = db.query(UserDiet).filter(
        UserDiet.user_email == current_user.email
    ).order_by(UserDiet.created_at.desc()).first()

    previous_date = "N/A"
    yesterday_plan = "None"

    if latest_past_diet:
        previous_date = str(latest_past_diet.created_at.date())
        # Ensure plan is stringified for prompt
        import json
        yesterday_plan = json.dumps(latest_past_diet.diet_plan)

    # 🔥 Send ALL profile data
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
        "yesterday_plan": yesterday_plan
    }

    assistant = DietAssistant()
    diet_plan = assistant.get_diet_suggestion(user_data, current_date=today)

    user_diet = UserDiet(user_email=email, diet_plan=diet_plan)
    db.add(user_diet)
    db.commit()
    db.refresh(user_diet)

    return {
        "date": today,
        "diet_plan_id": user_diet.diet_planid,
        "diet_plan": diet_plan
    }


@router.patch("/update", response_model=ProfileResponse)
def update_profile(
    data: ProfileUpdate,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    profile = db.query(UserProfile).filter(UserProfile.email == current_user.email).first()
    if not profile:
        raise HTTPException(status_code=404, detail="User profile not found")

    for key, value in data.dict(exclude_unset=True).items():
        setattr(profile, key, value)

    db.commit()
    db.refresh(profile)
    return profile

# Profile Summary Endpoint
@router.post("/summary", response_model=dict)
def get_profile_summary(
    current_user: UserAuth = Depends(get_current_user),  # JWT auth dependency
    db: Session = Depends(get_db)
):
    """
    Get full profile summary for the authenticated user.
    No need to send name/email in body.
    """
    email = current_user.email

    profile = db.query(UserProfile).filter(UserProfile.email == email).first()
    if not profile:
        raise HTTPException(status_code=404, detail="User profile not found")

    # Fetch latest diet plan date
    latest_diet = db.query(UserDiet).filter(
        UserDiet.user_email == email
    ).order_by(UserDiet.created_at.desc()).first()

    # Fetch latest workout plan status
    latest_workout = db.query(UserWorkout).filter(
        UserWorkout.user_email == email
    ).order_by(UserWorkout.created_at.desc()).first()

    return {
        "personal_info": {
            "name": profile.name,
            "email": profile.email,
            "age": profile.age,
            "gender": profile.gender,
            "height": profile.height,
            "weight": profile.weight,
            "location": {
                "city": profile.city,
                "pincode": profile.pincode
            }
        },
        "fitness_profile": {
            "goal": profile.goal,
            "activity_level": profile.activity_level,
            "medical_conditions": profile.medical_conditions,
            "injuries": profile.injuries,
            "workout_time_available": profile.workout_time
        },
        "diet_preferences": {
            "type": profile.diet_type,
            "allergies": profile.food_allergies,
            "dislikes": profile.food_dislikes,
            "budget": profile.budget,
            "meal_times": {
                "breakfast": profile.breakfast_time,
                "lunch": profile.lunch_time,
                "dinner": profile.dinner_time
            }
        },
        "sleep_schedule": {
            "wake_up": profile.wake_up_time,
            "sleep": profile.sleep_time
        },
        "current_status": {
            "latest_diet_date": latest_diet.created_at.date() if latest_diet else None,
            "current_workout_week": latest_workout.week_number if latest_workout else 0,
            "current_workout_start": latest_workout.week_start if latest_workout else None
        }
    }

