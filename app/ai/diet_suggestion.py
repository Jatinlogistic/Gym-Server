# app/ai/diet_suggestion.py
import re
import json
import os
from datetime import date
from groq import Groq
from app.config import settings

class DietAssistant:
    def __init__(self):
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.model_name = "meta-llama/llama-4-scout-17b-16e-instruct"

    def get_diet_suggestion(self, user_data: dict, current_date: date | None = None) -> dict:
        """
        Generate a goal-adaptive diet plan for breakfast, lunch, and dinner only.
        Safely parses JSON even if AI output contains extra text or code fences.
        """
        if current_date is None:
            current_date = date.today()
        print("DIET TYPE SENT TO AI:", user_data.get("diet_type"))  
        
        # Read prompt from file
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        prompt_path = os.path.join(base_dir, "prompt", "diet_prompt.txt")
        
        try:
            with open(prompt_path, "r") as f:
                prompt_template = f.read()
        except FileNotFoundError:
            # Fallback logic or error if file not found. 
            # Given the user asked to create it, we assume it exists.
            raise FileNotFoundError(f"Prompt file not found at {prompt_path}")

        # Prepare data for formatting
        format_data = {
            "current_date": current_date,
            "age": user_data.get('age', 25),
            "gender": user_data.get('gender', 'male'),
            "height": user_data.get('height', 170),
            "weight": user_data.get('weight', 70),
            "goal": user_data.get('goal', 'maintain weight'),
            "activity_level": user_data.get('activity_level', 'moderate'),
            "diet_type": user_data.get('diet_type', 'balanced'),
            "food_allergies": user_data.get('food_allergies', 'None'),
            "food_dislikes": user_data.get('food_dislikes', 'None'),
            "previous_date": user_data.get('previous_date', 'N/A'),
            "yesterday_plan": user_data.get('yesterday_plan', 'None')
        }

        prompt = prompt_template.format(**format_data)

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": "You are a fitness and nutrition AI assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=3000,  # increase to avoid truncation
            temperature=0.7
        )

        raw_output = response.choices[0].message.content
        print("\n🔍 RAW AI OUTPUT:\n", raw_output, "\n")  # debug

        if not raw_output or not isinstance(raw_output, str):
            raise ValueError("LLM returned empty or invalid content")

        # Step 1: Remove code fences
        cleaned = raw_output.replace("```json", "").replace("```", "").strip()

        # Step 2: Extract JSON object using regex
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not match:
            raise ValueError("No JSON found in LLM output")
        json_data = match.group()

        # Step 3: Replace single quotes with double quotes (common AI issue)
        json_data = json_data.replace("'", '"')

        # Step 4: Load JSON safely
        try:
            return json.loads(json_data)
        except json.JSONDecodeError as e:
            print("❌ JSONDecodeError:", e)
            raise ValueError("Failed to parse AI output as JSON")
