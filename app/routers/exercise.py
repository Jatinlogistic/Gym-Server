from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from sqlalchemy.orm import Session
from typing import Any
from app.database import SessionLocal
from app.models import UserProfile, UserExerciseFollowUp
from app.schemas.exercise_schema import FollowUpPayload, FollowUpResponse
from app.ai.exercise_detector import ExerciseDetector
import shutil
import os
import uuid

router = APIRouter(prefix="/profile/exercise", tags=["Exercise Validation"])

# Ensure upload directory exists (shared with calorie route)
UPLOAD_DIR = "app/static/images"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def get_image_url(path: Any, request: Request | None = None):
    """Convert file system path to accessible URL path (same helper used elsewhere)."""
    if not path:
        return None
    path = str(path)
    path = path.replace("\\", "/")

    url_path = path
    if "app/static" in path:
        url_path = path.replace("app/static", "/static")
    elif path.startswith("static"):
        url_path = "/" + path

    if request:
        base_url = str(request.base_url).rstrip("/")
        if not url_path.startswith("/"):
            url_path = "/" + url_path
        return f"{base_url}{url_path}"

    return url_path


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/validate", response_model=dict)
def validate_exercise(
    request: Request,
    email: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Accept an image plus user email, validate whether the image depicts exercise using the ExerciseDetector AI model,
    store the result and return a consolidated JSON response.
    """

    # 1. Verify User exists
    profile = db.query(UserProfile).filter(UserProfile.email == email).first()
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")

    # 2. Save Image Locally
    filename = file.filename or "unknown.jpg"
    file_extension = filename.split(".")[-1]
    unique_filename = f"{uuid.uuid4()}.{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save image: {str(e)}")

    # 3. Validate image using AI
    detector = ExerciseDetector()
    try:
        abs_path = os.path.abspath(file_path)
        result = detector.validate_image(abs_path)
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"AI Validation failed: {str(e)}")

    # 4. We will NOT persist this result to the DB — the endpoint is stateless for this task.
    # Return a transient id and timestamp so callers can track the response easily.
    from datetime import datetime
    import uuid as _uuid

    response_payload = {
        "id": str(_uuid.uuid4()),
        "created_at": datetime.utcnow().isoformat() + "Z",
        "image_path": get_image_url(file_path, request),
        "is_exercise": result.get("is_exercise"),
        "confidence": result.get("confidence"),
        "label": result.get("label"),
        "explanation": result.get("explanation"),
    }

    return response_payload


@router.post("/follow-up", response_model=FollowUpResponse)
def create_follow_up(payload: FollowUpPayload, db: Session = Depends(get_db)):
    """
    Store a follow-up payload for a user's exercise session. Expected to receive a JSON object containing
    at minimum an "email" field and the rest of the follow-up data (e.g. completed_exercises, exercises, etc.).
    """
    email = payload.email
    if not email:
        raise HTTPException(status_code=400, detail="email is required in payload")

    # Verify the user exists
    profile = db.query(UserProfile).filter(UserProfile.email == email).first()
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")

    # Extract structured fields and persist them into dedicated columns to assist analytics
    # Pydantic model ensures these fields exist (date and email required) and optional
    date = payload.date
    day = payload.day
    completed_exercises = payload.completed_exercises
    completion_rate = payload.completion_rate
    total_exercises = payload.total_exercises
    exercises = payload.exercises

    try:
        new_followup = UserExerciseFollowUp(
            user_email=email,
            date=date,
            day=day,
            completed_exercises=completed_exercises,
            completion_rate=completion_rate,
            total_exercises=total_exercises,
            exercises=exercises,
        )
        db.add(new_followup)
        db.commit()
        db.refresh(new_followup)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save follow-up: {str(e)}")

    # Build response using primitive Python values (avoid passing SQLAlchemy Column objects to Pydantic)
    responce = {
        "id": str(getattr(new_followup, "followup_id", None)),
        "created_at": getattr(new_followup, "created_at", None),
        "date": getattr(new_followup, "date", None),
        "day": getattr(new_followup, "day", None),
        "completed_exercises": getattr(new_followup, "completed_exercises", None),
        "completion_rate": getattr(new_followup, "completion_rate", None),
        "total_exercises": getattr(new_followup, "total_exercises", None),
        "exercises": getattr(new_followup, "exercises", None),
    }

    # Let FastAPI / Pydantic validate the returned dict via response_model
    return responce
