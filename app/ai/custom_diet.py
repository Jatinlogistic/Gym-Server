import os
import re
import json
from datetime import date
from groq import Groq
from app.config import settings


class CustomDietAssistant:
    """Generate a custom ingredient-driven diet plan using a dedicated prompt file.
    This mirrors the parsing logic used by DietAssistant but uses a special prompt that
    prioritizes available ingredients and returns deterministic output for a date.
    """

    def __init__(self):
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.model_name = "meta-llama/llama-4-scout-17b-16e-instruct"

    def get_custom_plan(self, user_data: dict, ingredients, current_date: date | None = None) -> dict:
        if current_date is None:
            current_date = date.today()

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        prompt_path = os.path.join(base_dir, "prompt", "custom_diet_prompt.txt")

        try:
            with open(prompt_path, "r") as f:
                prompt_template = f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"Prompt file not found at {prompt_path}")

        # Ensure ingredients passed to prompt is a human-readable list string
        raw_ings = ingredients or user_data.get('ingredients', 'None')
        if isinstance(raw_ings, (list, tuple)):
            ingredients_for_prompt = ", ".join(raw_ings)
        else:
            ingredients_for_prompt = str(raw_ings)

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
            "yesterday_plan": user_data.get('yesterday_plan', 'None'),
            "ingredients": ingredients_for_prompt,
        }

        prompt = prompt_template.format(**format_data)

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": "You are a fitness and nutrition AI assistant."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=3000,
            temperature=0.3,
        )

        raw_output = response.choices[0].message.content

        if not raw_output or not isinstance(raw_output, str):
            raise ValueError("LLM returned empty or invalid content")

        cleaned = raw_output.replace("```json", "").replace("```", "").strip()
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not match:
            raise ValueError("No JSON found in LLM output")

        json_data = match.group()
        json_data = json_data.replace("'", '"')

        try:
            parsed = json.loads(json_data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse AI output as JSON: {e}")

        # Ensure the structure is normalized, convert date to string and
        # explicitly remove any top-level 'ingredients' key so the caller
        # (the router) can manage and store ingredients separately and avoid duplication.
        if isinstance(parsed, dict):
            if "date" in parsed:
                parsed["date"] = str(parsed["date"])
            # Remove duplicated top-level ingredients for custom diet plan
            if "ingredients" in parsed:
                parsed.pop("ingredients", None)

        return parsed
