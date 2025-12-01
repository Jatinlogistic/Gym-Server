from typing import Optional, List, Any
from datetime import datetime
from pydantic import BaseModel, Field


class ExerciseItem(BaseModel):
    name: str
    sets: Optional[int] = None
    reps: Optional[int] = None
    rest: Optional[int] = None
    completed: Optional[bool] = None


class FollowUpPayload(BaseModel):
    email: str
    date: str
    day: Optional[str] = None
    completed_exercises: Optional[int] = None
    completion_rate: Optional[float] = None
    total_exercises: Optional[int] = None
    exercises: Optional[List[ExerciseItem] | List[Any]] = None


class FollowUpResponse(BaseModel):
    id: str
    created_at: Optional[datetime] = None
    date: Optional[str] = None
    day: Optional[str] = None
    completed_exercises: Optional[int] = None
    completion_rate: Optional[float] = None
    total_exercises: Optional[int] = None
    exercises: Optional[List[ExerciseItem] | List[Any]] = None
