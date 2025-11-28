import base64
import json
import os
import re
from groq import Groq
from app.config import settings

class CalorieDetector:
    def __init__(self):
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        # Using the vision-capable model
        self.model_name = "meta-llama/llama-4-scout-17b-16e-instruct" 

    def encode_image(self, image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def detect_calories(self, image_path: str) -> dict:
        """
        Analyze food image and return nutritional info.
        """
        
        # Read prompt from file
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        prompt_path = os.path.join(base_dir, "prompt", "calorie_detect.txt")
        
        try:
            with open(prompt_path, "r") as f:
                system_prompt = f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"Prompt file not found at {prompt_path}")

        # Encode image
        base64_image = self.encode_image(image_path)
        data_url = f"data:image/jpeg;base64,{base64_image}"

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": system_prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": data_url
                            }
                        }
                    ]
                }
            ],
            temperature=0.5,
            max_tokens=1024,
            top_p=1,
            stream=False,
            stop=None,
        )

        raw_output = response.choices[0].message.content
        if not raw_output:
             raise ValueError("LLM returned empty content")
        
        # Cleaning and Parsing Logic
        cleaned = raw_output.replace("```json", "").replace("```", "").strip()
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        
        if match:
            json_data = match.group()
        else:
             # Fallback if no clear JSON block found but content looks like JSON
            if cleaned.startswith("{") and cleaned.endswith("}"):
                json_data = cleaned
            else:
                raise ValueError(f"No JSON found in AI output: {raw_output}")

        try:
            return json.loads(json_data)
        except json.JSONDecodeError:
             raise ValueError("Failed to parse AI output as JSON")
