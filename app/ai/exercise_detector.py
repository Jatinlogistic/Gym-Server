import base64
import json
import os
import re
from groq import Groq 
from app.config import settings


class ExerciseDetector:
    """Use Groq vision-capable model to decide whether an image depicts exercise.

    The model is asked to return only valid JSON in the following format:
    {
      "is_exercise": true|false,
      "confidence": 0.0-1.0,
      "label": "exercise"|"not_exercise",
      "explanation": "short explanation string"
    }
    """

    def __init__(self):
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.model_name = "meta-llama/llama-4-scout-17b-16e-instruct"

    def encode_image(self, image_path: str) -> str:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def validate_image(self, image_path: str) -> dict:
        """Return parsed JSON with keys: is_exercise, confidence, label, explanation.

        Raises ValueError when LLM output cannot be parsed.
        """

        # Load prompt
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        prompt_path = os.path.join(base_dir, "prompt", "exercise_detect.txt")

        try:
            with open(prompt_path, "r") as fh:
                system_prompt = fh.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"Prompt file not found at {prompt_path}")

        # Encode image into data URL so the multimodal LLM can inspect it
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
                            "image_url": {"url": data_url},
                        },
                    ],
                }
            ],
            temperature=0.0,
            max_tokens=256,
            top_p=1,
            stream=False,
        )

        raw_output = response.choices[0].message.content
        if not raw_output:
            raise ValueError("LLM returned empty content")

        # Strip markdown fences and search for JSON
        cleaned = raw_output.replace("```json", "").replace("```", "").strip()
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)

        if match:
            json_text = match.group()
        else:
            if cleaned.startswith("{") and cleaned.endswith("}"):
                json_text = cleaned
            else:
                raise ValueError(f"No JSON found in AI output: {raw_output}")

        try:
            parsed = json.loads(json_text)
        except json.JSONDecodeError:
            raise ValueError("Failed to parse AI output as JSON")

        # Normalise result and ensure required keys exist
        if not isinstance(parsed, dict):
            raise ValueError("Parsed AI output is not a JSON object")

        # Set defaults and validate expected keys
        if "is_exercise" not in parsed:
            raise ValueError("AI output missing 'is_exercise' key")

        # Provide a safe return object with normalized types
        return {
            "is_exercise": bool(parsed.get("is_exercise")),
            "confidence": float(parsed.get("confidence", 0.0)),
            "label": str(parsed.get("label", "exercise" if parsed.get("is_exercise") else "not_exercise")),
            "explanation": str(parsed.get("explanation", "")),
            "raw": parsed,
        }
