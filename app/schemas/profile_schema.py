from pydantic import BaseModel
from typing import List, Any
    
class ProfileCreate(BaseModel):
    name: str
    age: int
    gender: str
    height: float
    weight: float
    email: str
    goal: str
    activity_level: str
    medical_conditions: str | None = None
    injuries: str | None = None

    diet_type: str
    food_allergies: str
    food_dislikes: str | None = None

    wake_up_time: str
    sleep_time: str
    # meal_times: str
    breakfast_time: str
    lunch_time: str
    dinner_time: str
    workout_time: str

    # water_goal: str
    # water_reminder: str

    pincode: str
    city: str
    budget: str | None = None

class ProfileResponse(ProfileCreate):
    userid: int

    class Config:
        from_attributes = True

class ProfileUpdate(BaseModel):
    email: str 
    name: str | None = None
    age: int | None = None
    gender: str | None = None
    height: float | None = None
    weight: float | None = None
    goal: str | None = None
    activity_level: str | None = None
    medical_conditions: str | None = None
    injuries: str | None = None
    diet_type: str | None = None
    food_allergies: str | None = None
    food_dislikes: str | None = None
    wake_up_time: str | None = None
    sleep_time: str | None = None
    breakfast_time: str | None = None
    lunch_time: str | None = None
    dinner_time: str | None = None
    workout_time: str | None = None
    pincode: str | None = None
    city: str | None = None
    budget: str | None = None
