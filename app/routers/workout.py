from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, timedelta
from app.database import SessionLocal
from app.models import UserProfile, UserWorkout
from app.ai.workout_suggestion import WorkoutAssistant
from fastapi.responses import StreamingResponse
from app.utils.pdf import workout_plan_to_pdf_bytes
import io
from datetime import datetime

router = APIRouter(prefix="/profile/workout-plan", tags=["Workout Plan"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("", response_model=dict)
def get_workout_plan(data: dict, db: Session = Depends(get_db)):
    """
    Get or generate a weekly workout plan (Mon-Sat).
    Returns existing plan if valid for current week, else generates new one.
    """
    name = data.get("name")
    email = data.get("email")
    
    if not name or not email:
        raise HTTPException(status_code=400, detail="Name and email are required")

    # 1. Verify User
    profile = db.query(UserProfile).filter(
        UserProfile.name == name,
        UserProfile.email == email
    ).first()

    if not profile:
        raise HTTPException(status_code=404, detail="User not found")

    # 2. Calculate Week Details (Calendar based for consistency)
    today = date.today()
    start_of_week = today - timedelta(days=today.weekday())  # Monday
    end_of_week = start_of_week + timedelta(days=6)          # Sunday

    # 3. Determine User-Specific Week Number
    # Find the user's very first workout plan start date
    first_workout = db.query(UserWorkout).filter(
        UserWorkout.user_email == email
    ).order_by(UserWorkout.week_start.asc()).first()

    if not first_workout:
        # This is the user's first ever plan
        user_week_number = 1
    else:
        # Calculate week number relative to the first plan
        # If the first plan started on Jan 1st, and today is Jan 8th, that's Week 2.
        delta_days = (start_of_week - first_workout.week_start).days
        # Ensure we don't get negative or zero if something is weird, though delta should be >= 0
        if delta_days < 0:
            user_week_number = 1 # Should not happen if logic is correct
        else:
            user_week_number = (delta_days // 7) + 1

    # 4. Check for existing plan for THIS specific user week number
    # We check if a plan exists with the calculated user_week_number OR the current calendar start_of_week
    # Using week_start is safer to avoid duplicates if user generates multiple times in one week
    existing_plan = db.query(UserWorkout).filter(
        UserWorkout.user_email == email,
        UserWorkout.week_start == start_of_week
    ).first()

    # Helper function to sort plan days
    def sort_plan(plan):
        ordered_days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]
        sorted_dict = {}
        for day in ordered_days:
            if day in plan:
                sorted_dict[day] = plan[day]
        # Include any extra keys (like if Sunday was accidentally returned)
        for k, v in plan.items():
            if k not in ordered_days:
                sorted_dict[k] = v
        return sorted_dict

    if existing_plan:
        # If plan exists, return its stored week number (which should match our calculation)
        return {
            "status": "existing",
            "week_start": existing_plan.week_start,
            "week_end": existing_plan.week_end,
            "week_number": existing_plan.week_number,
            "workout_plan": sort_plan(existing_plan.workout_plan)
        }

    # 5. Generate New Plan
    user_data = {
        "age": profile.age,
        "gender": profile.gender,
        "height": profile.height,
        "weight": profile.weight,
        "goal": profile.goal,
        "activity_level": profile.activity_level,
        "medical_conditions": profile.medical_conditions,
        "injuries": profile.injuries,
        "workout_time": profile.workout_time,
        "budget": profile.budget
    }

    assistant = WorkoutAssistant()
    try:
        workout_plan = assistant.get_workout_suggestion(user_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Generation failed: {str(e)}")

    # 6. Save to DB with User-Based Week Number
    new_workout = UserWorkout(
        user_email=email,
        workout_plan=workout_plan,
        week_start=start_of_week,
        week_end=end_of_week,
        week_number=user_week_number
    )
    db.add(new_workout)
    db.commit()
    db.refresh(new_workout)

    return {
        "status": "created",
        "week_start": new_workout.week_start,
        "week_end": new_workout.week_end,
        "week_number": new_workout.week_number,
        "workout_plan": sort_plan(workout_plan)
    }


@router.post('/pdf-download')
def download_workout_pdf(data: dict, db: Session = Depends(get_db)):
    """Generate and return a PDF for the user's workout plan.

    Accepts JSON body with at least `email` and optional `week_start` (YYYY-MM-DD).
    If `week_start` is omitted the most recent workout plan for the user is used.
    """
    email = data.get('email')
    week_start_str = data.get('week_start')

    if not email:
        raise HTTPException(status_code=400, detail="email is required")

    # Find requested plan
    query = db.query(UserWorkout).filter(UserWorkout.user_email == email)

    if week_start_str:
        try:
            week_start_date = datetime.strptime(week_start_str, "%Y-%m-%d").date()
        except Exception:
            raise HTTPException(status_code=400, detail="week_start must be YYYY-MM-DD")
        query = query.filter(UserWorkout.week_start == week_start_date)

    workout = query.order_by(UserWorkout.created_at.desc()).first()

    if not workout:
        raise HTTPException(status_code=404, detail="No workout found for this user/week")

    # Optional user profile lookup to get name
    profile = db.query(UserProfile).filter(UserProfile.email == email).first()
    user_name = profile.name if profile else email

    # Build PDF bytes
    try:
        pdf_bytes = workout_plan_to_pdf_bytes(
        user_name=user_name,
        week_start=str(workout.week_start),
        week_end=str(workout.week_end),
        week_number=workout.week_number or 0,
        workout_plan=workout.workout_plan
        )
    except Exception as e:
        # If PDF generation fails, return an internal error
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")

    # Validate that bytes look like a PDF
    if not pdf_bytes or not getattr(pdf_bytes, '__len__', lambda: 0)():
        raise HTTPException(status_code=500, detail="PDF generation returned empty bytes")
    if not (isinstance(pdf_bytes, (bytes, bytearray)) and len(pdf_bytes) >= 4 and pdf_bytes[:4] == b"%PDF"):
        raise HTTPException(status_code=500, detail="PDF generation returned invalid PDF content")

    return StreamingResponse(io.BytesIO(pdf_bytes), media_type='application/pdf',
                             headers={"Content-Disposition": f"attachment; filename=workout_{email}_{workout.week_start}.pdf"})
