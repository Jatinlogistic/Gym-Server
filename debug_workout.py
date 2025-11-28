from app.database import SessionLocal
from app.models import UserWorkout

db = SessionLocal()
email = "jatinsanchaniya9122@gmail.com"

workout = db.query(UserWorkout).filter(
    UserWorkout.user_email == email
).order_by(UserWorkout.created_at.desc()).first()

if workout:
    print("Workout Found!")
    print(workout.workout_plan)
else:
    print("No workout found.")
db.close()
