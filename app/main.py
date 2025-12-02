from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routers.profile import router as profile_router
from app.routers.diet_history import router as diet_history_router
from app.routers.workout import router as workout_router
from app.routers.calorie import router as calorie_router
from app.routers.chatbot import router as chatbot_router
from app.routers.gym import router as gym_router
from app.routers.custom_diet import router as custom_diet_router
from app.routers.exercise import router as exercise_router
from app.routers.analysis import router as analysis_router
from app.routers.auth import router as auth_router

Base.metadata.create_all(bind=engine)

app = FastAPI()

# Serve static files (images)
from fastapi.staticfiles import StaticFiles
import os
os.makedirs("app/static/images", exist_ok=True)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(profile_router)
app.include_router(diet_history_router)
app.include_router(workout_router)
app.include_router(calorie_router)
app.include_router(chatbot_router)
app.include_router(gym_router)
app.include_router(custom_diet_router)
app.include_router(exercise_router)
app.include_router(analysis_router)
app.include_router(auth_router)

@app.get("/")
def home():
    return {"message": "Fitness AI Backend Running"}
