from pydantic import BaseModel
from typing import List, Any, Optional
    
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

class ProfileResponse(BaseModel):
    userid: int
    email: str
    
    name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    goal: Optional[str] = None
    activity_level: Optional[str] = None
    medical_conditions: Optional[str] = None
    injuries: Optional[str] = None
    diet_type: Optional[str] = None
    food_allergies: Optional[str] = None
    food_dislikes: Optional[str] = None
    wake_up_time: Optional[str] = None
    sleep_time: Optional[str] = None
    breakfast_time: Optional[str] = None
    lunch_time: Optional[str] = None
    dinner_time: Optional[str] = None
    workout_time: Optional[str] = None
    pincode: Optional[str] = None
    city: Optional[str] = None
    budget: Optional[str] = None

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
