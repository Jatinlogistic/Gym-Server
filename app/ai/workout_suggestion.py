import re
import json
import os
from groq import Groq
from app.config import settings

class WorkoutAssistant:
    def __init__(self):
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.model_name = "meta-llama/llama-4-scout-17b-16e-instruct"

    def get_workout_suggestion(self, user_data: dict) -> dict:
        """
        Generate a weekly workout plan (Mon-Sat).
        """
        
        # Read prompt from file
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        prompt_path = os.path.join(base_dir, "prompt", "workout_prompt.txt")
        
        try:
            with open(prompt_path, "r") as f:
                prompt_template = f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"Prompt file not found at {prompt_path}")

        # Prepare data for formatting
        format_data = {
            "age": user_data.get('age', 25),
            "gender": user_data.get('gender', 'male'),
            "height": user_data.get('height', 170),
            "weight": user_data.get('weight', 70),
            "goal": user_data.get('goal', 'fitness'),
            "activity_level": user_data.get('activity_level', 'moderate'),
            "medical_conditions": user_data.get('medical_conditions', 'None'),
            "injuries": user_data.get('injuries', 'None'),
            "workout_time": user_data.get('workout_time', '30 mins'),
            "budget": user_data.get('budget', 'low'),
        }

        prompt = prompt_template.format(**format_data)

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": "You are a certified personal trainer AI."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=3000,
            temperature=0.7
        )

        raw_output = response.choices[0].message.content
        
        if not raw_output or not isinstance(raw_output, str):
            raise ValueError("LLM returned empty or invalid content")

        # Cleaning and Parsing Logic (Same as DietAssistant)
        cleaned = raw_output.replace("```json", "").replace("```", "").strip()
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        
        if not match:
             # If regex fails, try returning the whole cleaned string if it looks like JSON
            if cleaned.startswith("{") and cleaned.endswith("}"):
                json_data = cleaned
            else:
                raise ValueError("No JSON found in LLM output")
        else:
            json_data = match.group()

        json_data = json_data.replace("'", '"')

        try:
            return json.loads(json_data)
        except json.JSONDecodeError as e:
            print("❌ JSONDecodeError:", e)
            raise ValueError("Failed to parse AI output as JSON")
