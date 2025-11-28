from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import UserProfile, UserExerciseFollowUp, UserExerciseAnalysis
from app.ai.exercise_analysis import ExerciseAnalysis
from typing import List
from datetime import datetime, timedelta, date

router = APIRouter(prefix="/profile/analysis", tags=["Exercise Analysis"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _iter_dates(start_str: str, end_str: str) -> List[str]:
    start = datetime.strptime(start_str, "%Y-%m-%d").date()
    end = datetime.strptime(end_str, "%Y-%m-%d").date()
    out = []
    cur = start
    while cur <= end:
        out.append(cur.isoformat())
        cur = cur + timedelta(days=1)
    return out


@router.post("", response_model=dict)
def analyze_week(data: dict, db: Session = Depends(get_db)):
    """Aggregate follow-ups for the requested week and return daily stats plus AI advice.

    Expected input: {"email": "...", "week_start": "YYYY-MM-DD", "week_end": "YYYY-MM-DD"}
    If a day is missing, completed_exercises defaults to 0 and total_exercises defaults to 0.
    """
    email = data.get("email")
    week_start = data.get("week_start")
    week_end = data.get("week_end")

    if not email or not week_start or not week_end:
        raise HTTPException(status_code=400, detail="email, week_start and week_end are required")

    # Verify user exists
    profile = db.query(UserProfile).filter(UserProfile.email == email).first()
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")

    # Query follow-ups for the date range. We store dates as strings 'YYYY-MM-DD', so string comparison works
    followups = db.query(UserExerciseFollowUp).filter(
        UserExerciseFollowUp.user_email == email,
        UserExerciseFollowUp.date >= week_start,
        UserExerciseFollowUp.date <= week_end
    ).all()

    # Build a map date->followup
    followup_map = {getattr(f, "date", None): f for f in followups if getattr(f, "date", None) is not None}

    ordered_dates = _iter_dates(week_start, week_end)

    # Prepare daily_stats
    daily_stats = []
    today_date = date.today()


    for day_iso in ordered_dates:
        day_date = datetime.strptime(day_iso, "%Y-%m-%d").date()

        # For days after today, default to zeros (we still include all week days)
        if day_date > today_date:
            total = 0
            completed = 0
        else:
            f = followup_map.get(day_iso)
            # If entry exists, use stored numbers; otherwise default to zeros
            total = int(getattr(f, "total_exercises", 0) or 0)
            completed = int(getattr(f, "completed_exercises", 0) or 0)

        entry = {
            "day": day_date.strftime("%A"),
            "date": day_iso,
            "total_exercises": total,
            "completed_exercises": completed,
        }
        daily_stats.append(entry)

    week_summary = {
        "week_start": week_start,
        "week_end": week_end,
        "daily_stats": daily_stats
    }

    # Prepare minimal profile dict for AI use
    profile_dict = {
        "email": profile.email,
        "name": getattr(profile, "name", None),
        "age": getattr(profile, "age", None),
        "goal": getattr(profile, "goal", None),
        "activity_level": getattr(profile, "activity_level", None),
    }

    # 2. Check if an analysis already exists for this user/week — return cached if present
    existing_analysis = db.query(UserExerciseAnalysis).filter(
        UserExerciseAnalysis.user_email == email,
        UserExerciseAnalysis.week_start == week_start,
        UserExerciseAnalysis.week_end == week_end,
    ).first()

    if existing_analysis:
        # Return cached analysis but ensure future days are present and set to zeros
        existing_daily = existing_analysis.daily_stats or []
        # Build a lookup from stored daily_stats by date
        stored_map = {d.get("date"): d for d in existing_daily if isinstance(d, dict) and d.get("date")}

        # Build full-week representation: for each date in ordered_dates, use stored entry up to today, future days zero
        returned_daily = []
        for day_iso in ordered_dates:
            day_date = datetime.strptime(day_iso, "%Y-%m-%d").date()
            if day_date > today_date:
                returned_daily.append({
                    "day": day_date.strftime("%A"),
                    "date": day_iso,
                    "total_exercises": 0,
                    "completed_exercises": 0,
                })
            else:
                stored = stored_map.get(day_iso)
                if stored:
                    returned_daily.append(stored)
                else:
                    returned_daily.append({
                        "day": day_date.strftime("%A"),
                        "date": day_iso,
                        "total_exercises": 0,
                        "completed_exercises": 0,
                    })

        return {
            "id": str(existing_analysis.analysis_id),
            "created_at": existing_analysis.created_at.isoformat() if existing_analysis.created_at is not None else None,
            "week_start": existing_analysis.week_start,
            "week_end": existing_analysis.week_end,
            "daily_stats": returned_daily,
            "advice": existing_analysis.advice,
        }

    # 3. Call AI to generate weekly advice
    try:
        analyzer = ExerciseAnalysis()
        ai_out = analyzer.analyze_week(profile_dict, week_summary)
        # Expect ai_out to be a dict — it should contain 'advice' and optionally daily_stats
        advice = ai_out.get("advice") if isinstance(ai_out, dict) else None
        ai_daily = ai_out.get("daily_stats") if isinstance(ai_out, dict) else None
        # If AI returned daily_stats, we'll use them for days up to today; future days will be set to zeros.
        if ai_daily and isinstance(ai_daily, list):
            # Create a map of AI entries by date for quick lookup
            ai_map = {getattr(item, 'get', lambda k, d=None: None)('date') if not isinstance(item, dict) else item.get('date'): item for item in ai_daily}
        else:
            ai_map = {}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

    # Save analysis to DB
    try:
        # Build final result_daily for the whole week (inclusive). For dates after today, set zeros.
        result_daily = []
        for day_iso in ordered_dates:
            day_date = datetime.strptime(day_iso, "%Y-%m-%d").date()
            if day_date > today_date:
                # future date: include with zeros
                result_daily.append({
                    "day": day_date.strftime("%A"),
                    "date": day_iso,
                    "total_exercises": 0,
                    "completed_exercises": 0,
                })
            else:
                # Use AI-provided entry if present, otherwise server aggregated followup
                ai_item = ai_map.get(day_iso)
                if ai_item and isinstance(ai_item, dict):
                    total = int(ai_item.get("total_exercises", 0) or 0)
                    completed = int(ai_item.get("completed_exercises", 0) or 0)
                else:
                    f = followup_map.get(day_iso)
                    total = int(getattr(f, "total_exercises", 0) or 0)
                    completed = int(getattr(f, "completed_exercises", 0) or 0)

                result_daily.append({
                    "day": day_date.strftime("%A"),
                    "date": day_iso,
                    "total_exercises": total,
                    "completed_exercises": completed,
                })
        result_advice = advice or (ai_out if isinstance(ai_out, str) else "No advice generated")

        new_analysis = UserExerciseAnalysis(
            user_email=email,
            week_start=week_start,
            week_end=week_end,
            daily_stats=result_daily,
            advice=result_advice,
        )
        db.add(new_analysis)
        db.commit()
        db.refresh(new_analysis)
    except Exception:
        # If saving fails, continue and return response (do not block on DB write)
        new_analysis = None

    return {
        "id": str(new_analysis.analysis_id) if new_analysis else None,
        "week_start": week_start,
        "week_end": week_end,
        "daily_stats": result_daily,
        "advice": result_advice
    }
