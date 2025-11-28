import os
import json
from datetime import date, datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc
from groq import Groq
from app.config import settings
from app.models import UserProfile, UserDiet, UserWorkout, UserFoodLog, ChatHistory

class ChatbotAssistant:
    def __init__(self):
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.model_name = "meta-llama/llama-4-scout-17b-16e-instruct"

    def get_chat_response(self, user_email: str, question: str, db: Session) -> str:
        # 1. Fetch User Profile
        profile = db.query(UserProfile).filter(UserProfile.email == user_email).first()
        if not profile:
            return "I couldn't find your profile. Please set up your profile first."

        # 2. Fetch Context (Diet, Workout, Logs)
        today = date.today()
        today_str = today.strftime("%A, %Y-%m-%d") # e.g., "Tuesday, 2025-11-25"
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        
        # Determine Time of Day
        hour = now.hour
        if 5 <= hour < 12:
            time_of_day = "Morning"
        elif 12 <= hour < 17:
            time_of_day = "Afternoon"
        elif 17 <= hour < 21:
            time_of_day = "Evening"
        else:
            time_of_day = "Night"
        
        # Latest Diet
        latest_diet = db.query(UserDiet).filter(
            UserDiet.user_email == user_email
        ).order_by(UserDiet.created_at.desc()).first()
        
        # Latest Workout
        latest_workout = db.query(UserWorkout).filter(
            UserWorkout.user_email == user_email
        ).order_by(UserWorkout.created_at.desc()).first()
        
        # Recent Food Log (Last 3 items)
        recent_logs = db.query(UserFoodLog).filter(
            UserFoodLog.user_email == user_email
        ).order_by(UserFoodLog.created_at.desc()).limit(3).all()
        
        recent_calories = ", ".join(
            [f"{log.food_analysis.get('food_name', 'Unknown')}: {log.food_analysis.get('calories', 0)}kcal" 
             for log in recent_logs if log.food_analysis is not None]
        ) if recent_logs else "No recent logs"

        # 3. Fetch Chat History (Last 10 messages)
        history_records = db.query(ChatHistory).filter(
            ChatHistory.user_email == user_email
        ).order_by(ChatHistory.timestamp.desc()).limit(10).all()
        
        # Reverse to chronological order
        history_records.reverse()
        
        history_text = ""
        for msg in history_records:
            role_label = "User" if str(msg.role) == "user" else "Assistant"

            history_text += f"{role_label}: {msg.content}\n"

        # 4. Load Prompt Template
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        prompt_path = os.path.join(base_dir, "prompt", "chatbot_prompt.txt")
        
        try:
            with open(prompt_path, "r") as f:
                prompt_template = f.read()
        except FileNotFoundError:
            return "Error: Prompt file missing."

        # 5. Format Prompt
        # Safe handling of JSON fields
        diet_plan_summary = "No active plan"
        
        # Determine if we have a valid plan for today (Diet)
        has_today_plan = False
        
        if latest_diet is not None and latest_diet.created_at is not None:
            # Relaxed check: Is the diet plan from within the last 7 days?
            days_diff = (today - latest_diet.created_at.date()).days
            if 0 <= days_diff <= 7:
                 if latest_diet.diet_plan is not None:
                    has_today_plan = True
                    if isinstance(latest_diet.diet_plan, (dict, list)):
                        diet_plan_summary = json.dumps(latest_diet.diet_plan, indent=2)
                    else:
                        diet_plan_summary = str(latest_diet.diet_plan)

        if not has_today_plan:
            # If no plan for today, instruct the AI
            diet_plan_summary = (
                "No diet plan generated for this week. "
                "If the user asks for today's diet plan, strictly reply: "
                "'I haven't generated a diet plan for this week yet. You can generate one using the diet suggestion feature.' "
                "Do NOT provide any meal suggestions. Keep the response short."
            )
            
        # Determine if we have a valid workout for today
        has_today_workout = False
        workout_summary = "No active workout"

        if latest_workout is not None:
             # Check 1: Use week_start and week_end if available
             if latest_workout.week_start is not None and latest_workout.week_end is not None:
                 # Break down comparison to avoid Pylance confusion
                 start_valid = latest_workout.week_start <= today
                 end_valid = today <= latest_workout.week_end
                 if start_valid and end_valid:  # type: ignore
                     has_today_workout = True
             
             # Check 2: Fallback to created_at within last 7 days if no week_start
             elif latest_workout.created_at is not None:
                 days_diff = (today - latest_workout.created_at.date()).days
                 if 0 <= days_diff <= 7:
                     has_today_workout = True

             if has_today_workout and latest_workout.workout_plan is not None:
                 if isinstance(latest_workout.workout_plan, (dict, list)):
                     workout_summary = json.dumps(latest_workout.workout_plan, indent=2)
                 else:
                     workout_summary = str(latest_workout.workout_plan)
        
        if not has_today_workout:
             workout_summary = (
                 "No workout plan generated for this week. "
                 "If the user asks for today's workout, strictly reply: "
                 "'I haven't generated a workout plan for this week yet. You can generate one using the workout suggestion feature.' "
                 "Do NOT provide any exercise suggestions. Keep the response short."
             )

        # Truncate only if extremely large (e.g. > 6000 chars) to fit context
        if len(diet_plan_summary) > 6000:
            diet_plan_summary = diet_plan_summary[:6000] + "...[truncated]"
        if len(workout_summary) > 6000:
            workout_summary = workout_summary[:6000] + "...[truncated]"

        prompt = prompt_template.format(
            name=profile.name,
            age=profile.age,
            gender=profile.gender,
            height=profile.height,
            weight=profile.weight,
            goal=profile.goal,
            activity_level=profile.activity_level,
            diet_type=profile.diet_type,
            food_allergies=profile.food_allergies,
            medical_conditions=profile.medical_conditions,
            exercise_type="General Fitness",  # Default value as it's not in UserProfile
            # sleep_pattern=f"{profile.sleep_time} - {profile.wake_up_time}",
            wake_up_time=profile.wake_up_time,
            sleep_time=profile.sleep_time,
            sleep_pattern=f"{profile.sleep_time} - {profile.wake_up_time}", # Kept for backward compatibility if needed
            breakfast_time=profile.breakfast_time,
            current_date=today_str,
            current_time=current_time,
            time_of_day=time_of_day,
            today_diet=diet_plan_summary,
            current_workout=workout_summary,
            recent_calories=recent_calories,
            history=history_text,
            user_question=question
        )

        # 6. Call Groq AI
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are a helpful fitness assistant."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            answer = response.choices[0].message.content
            if not answer:
                answer = "I apologize, but I was unable to generate a response."
        except Exception as e:
            return f"AI Service Error: {str(e)}"

        # 7. Save Interaction to DB
        # User message
        db.add(ChatHistory(user_email=user_email, role="user", content=question))
        # Assistant message
        db.add(ChatHistory(user_email=user_email, role="assistant", content=answer))
        db.commit()

        return answer
