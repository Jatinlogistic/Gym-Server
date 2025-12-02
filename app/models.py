# app/models.py
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Date, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from .database import Base

class UserProfile(Base):
    __tablename__ = "user_profiles"

    userid = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    age = Column(Integer)
    gender = Column(String)
    height = Column(Float)
    weight = Column(Float)
    email = Column(String, unique=True, index=True)  # UNIQUE email
    goal = Column(String)
    activity_level = Column(String)
    medical_conditions = Column(String)
    injuries = Column(String)
    diet_type = Column(String)
    food_allergies = Column(String)
    food_dislikes = Column(String)
    wake_up_time = Column(String)
    sleep_time = Column(String)
    breakfast_time = Column(String)
    lunch_time = Column(String)
    dinner_time = Column(String)
    workout_time = Column(String)
    pincode = Column(String)
    city = Column(String)
    budget = Column(String)

class UserDiet(Base):
    __tablename__ = "user_diets"

    diet_planid = Column(Integer, primary_key=True, index=True)
    user_email = Column(String, ForeignKey("user_profiles.email"))  # link via email
    diet_plan = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class UserWorkout(Base):
    __tablename__ = "user_workouts"

    workout_id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String, ForeignKey("user_profiles.email"))
    workout_plan = Column(JSONB)
    
    # New Tracking Fields
    week_start = Column(Date)
    week_end = Column(Date)
    week_number = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class UserExerciseFollowUp(Base):
    __tablename__ = "user_exercise_followups"

    followup_id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String, ForeignKey("user_profiles.email"), index=True)
    # Store the date string provided in the payload (e.g. "2025-11-28")
    date = Column(String, nullable=True)
    # Optional day-of-week string (e.g. "friday")
    day = Column(String, nullable=True)
    # Store these numeric summary fields separately so analytics queries are straightforward
    completed_exercises = Column(Integer, nullable=True)
    completion_rate = Column(Float, nullable=True)
    total_exercises = Column(Integer, nullable=True)
    # Full `exercises` detail stored as JSONB for flexible querying
    exercises = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class UserExerciseAnalysis(Base):
    __tablename__ = "user_exercise_analyses"

    analysis_id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String, ForeignKey("user_profiles.email"), index=True)
    week_start = Column(Date, nullable=False)
    week_end = Column(Date, nullable=False)
    daily_stats = Column(JSONB, nullable=True)
    advice = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class UserFoodLog(Base):
    __tablename__ = "user_food_logs"

    log_id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String, ForeignKey("user_profiles.email"))
    image_path = Column(String)  # Path to stored image
    food_analysis = Column(JSONB) # AI Output: {"food_name": "...", "calories": 500, ...}
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# class UserExerciseLog(Base):
#     __tablename__ = "user_exercise_logs"

#     log_id = Column(Integer, primary_key=True, index=True)
#     user_email = Column(String, ForeignKey("user_profiles.email"))
#     image_path = Column(String)
#     validation = Column(JSONB)  # AI output: {is_exercise: bool, confidence: float, ...}
#     created_at = Column(DateTime(timezone=True), server_default=func.now())

class ChatHistory(Base):
    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String, ForeignKey("user_profiles.email"), index=True)
    role = Column(String)  # "user" or "assistant"
    content = Column(String)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

class GymSuggestion(Base):
    __tablename__ = "gym_suggestions"

    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String, index=True, nullable=False)
    suggestion = Column(JSONB, nullable=True)  # store parsed JSON when possible
    # raw_output can contain structured information or counters returned by the AI; store as JSONB
    raw_output = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    suggestion_id = Column(String, nullable=True)  # optional external id


class UserCustomDiet(Base):
    __tablename__ = "user_custom_diets"

    custom_diet_id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String, ForeignKey("user_profiles.email"), index=True)
    ingredients = Column(JSONB, nullable=False)
    diet_plan = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    

class UserAuth(Base):
    """Authentication / signup table.

    Stores basic signup information. We hash passwords before storing and do
    NOT persist plaintext confirmation passwords. Email is unique.
    """

    __tablename__ = "user_auth"

    auth_id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, index=True, nullable=True)
    # Storing only the password hash
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

