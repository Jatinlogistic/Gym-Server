from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Any
from app.database import SessionLocal
from app.models import UserProfile, UserFoodLog
from app.ai.calorie_detector import CalorieDetector
import shutil
import os
import uuid
from datetime import datetime

router = APIRouter(prefix="/profile/calorie", tags=["Calorie Detection"])

# Ensure upload directory exists
UPLOAD_DIR = "app/static/images"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def get_image_url(path: Any, request: Request | None = None):
    """Convert file system path to accessible URL path"""
    if not path:
        return None
    # Ensure path is a string before processing
    path = str(path)
    # Normalize path separators
    path = path.replace("\\", "/")
    
    url_path = path
    
    # If path starts with app/static, replace with /static
    if "app/static" in path:
        url_path = path.replace("app/static", "/static")
    # If path starts with static, ensure it has leading slash
    elif path.startswith("static"):
        url_path = "/" + path
    
    # If we have a request object, return a full URL
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

@router.post("/detect", response_model=dict)
def detect_calories(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload an image -> Detect Calories -> Save Log -> Return JSON.
    """
    # 1. Verify User
    profile = db.query(UserProfile).filter(
        UserProfile.name == name,
        UserProfile.email == email
    ).first()

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

    # 3. Detect Calories using AI
    detector = CalorieDetector()
    try:
        # We pass the absolute path to the AI
        abs_path = os.path.abspath(file_path)
        analysis_result = detector.detect_calories(abs_path)
    except Exception as e:
        # Clean up file if detection fails
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"AI Detection failed: {str(e)}")

    # 4. Save to DB
    # We store the relative path or a URL-accessible path
    # For this setup, we store the relative path 'app/static/images/...'
    new_log = UserFoodLog(
        user_email=email,
        image_path=file_path,
        food_analysis=analysis_result
    )
    db.add(new_log)
    db.commit()
    db.refresh(new_log)

    # 5. Return formatted response
    return {
        "id": str(new_log.log_id),
        "created_at": new_log.created_at.isoformat(),
        "image_path": get_image_url(file_path, request),
        "dish_name": analysis_result.get("dish_name"),
        "description": analysis_result.get("description"),
        "estimated_calories": analysis_result.get("estimated_calories"),
        "calorie_range": analysis_result.get("calorie_range"),
        "ingredients": analysis_result.get("ingredients"),
        "macronutrients": analysis_result.get("macronutrients"),
        "health_rating": analysis_result.get("health_rating"),
        "advice": analysis_result.get("advice"),
    }


@router.post("/history", response_model=list)
def get_calorie_history(data: dict, request: Request, db: Session = Depends(get_db)):
    """
    Fetch all past calorie logs for a user.
    """
    name = data.get("name")
    email = data.get("email")
    
    if not name or not email:
        raise HTTPException(status_code=400, detail="Name and email are required")

    logs = db.query(UserFoodLog).filter(
        UserFoodLog.user_email == email
    ).order_by(UserFoodLog.created_at.desc()).all()

    return [
        {
            "id": str(log.log_id),
            "created_at": log.created_at.isoformat(),
            "image_path": get_image_url(log.image_path, request),
            "dish_name": log.food_analysis.get("dish_name"),
            "estimated_calories": log.food_analysis.get("estimated_calories"),
            "food_analysis": log.food_analysis
        }
        for log in logs
    ]

@router.delete("/delete", response_model=dict)
def delete_calorie_log(data: dict, db: Session = Depends(get_db)):
    """
    Delete a specific calorie log by ID.
    Input: {"id": "log_id", "name": "user_name", "email": "user_email"}
    """
    log_id = data.get("id")
    name = data.get("name")
    email = data.get("email")

    if not log_id or not name or not email:
        raise HTTPException(status_code=400, detail="ID, name, and email are required")

    # Verify User
    profile = db.query(UserProfile).filter(
        UserProfile.name == name,
        UserProfile.email == email
    ).first()

    if not profile:
        raise HTTPException(status_code=404, detail="User not found")

    # Find the log entry
    log_entry = db.query(UserFoodLog).filter(
        UserFoodLog.log_id == log_id,
        UserFoodLog.user_email == email
    ).first()

    if not log_entry:
        raise HTTPException(status_code=404, detail="Calorie log not found")

    # Remove the image file if it exists
    image_path_str = str(log_entry.image_path) # Ensure it's a string
    if image_path_str and os.path.exists(image_path_str):
        try:
            os.remove(image_path_str)
        except Exception:
            pass  # Log deletion shouldn't fail if file is already gone

    # Delete from DB
    db.delete(log_entry)
    db.commit()

    return {"message": "Calorie log deleted successfully", "id": str(log_id)}
