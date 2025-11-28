import json
import os
from groq import Groq
from app.config import settings


class ExerciseAnalysis:
    def __init__(self):
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.model_name = "meta-llama/llama-4-scout-17b-16e-instruct"

    def analyze_week(self, profile: dict, week_summary: dict) -> dict:
        """Send a prompt to the AI to provide advice for a weekly summary.

        The method expects `profile` to contain user profile fields and `week_summary` a dict
        with week_start, week_end and daily_stats (list of objects).

        Returns a dict parsed from the model's JSON output, expected to include at least "advice".
        """

        # Load prompt
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        prompt_path = os.path.join(base_dir, "prompt", "exercise_analysis.txt")

        try:
            with open(prompt_path, "r") as fh:
                system_prompt = fh.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

        # Build user context to pass in the user content slot.
        content = {
            "profile": profile,
            "week_summary": week_summary
        }

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(content)}
                ],
                temperature=0.4,
                max_tokens=512
            )

            raw = response.choices[0].message.content
            if not raw:
                raise ValueError("AI returned empty content")

            cleaned = raw.replace("```json", "").replace("```", "").strip()

            # find JSON in the response
            try:
                parsed = json.loads(cleaned)
                # If parsed JSON does not contain required top-level keys, try to fill
                if not (isinstance(parsed, dict) and ("daily_stats" in parsed or "advice" in parsed)):
                    # If the model returned a simple string or a different object, wrap into advice
                    parsed = {"advice": cleaned}
                return parsed
            except json.JSONDecodeError:
                # Try to locate JSON block within text
                import re

                m = re.search(r"\{.*\}", cleaned, re.DOTALL)
                if m:
                    try:
                        parsed = json.loads(m.group())
                        # Ensure parsed has required shape; otherwise return as-is
                        if not (isinstance(parsed, dict) and ("daily_stats" in parsed or "advice" in parsed)):
                            return {"advice": cleaned}
                        return parsed
                    except json.JSONDecodeError:
                        # If we found a JSON-like block but still can't decode, fall through
                        pass

                # No JSON could be decoded — fallback: return the raw cleaned text as advice
                # Keep the advice reasonably sized
                advice_text = cleaned
                if len(advice_text) > 2000:
                    advice_text = advice_text[:2000] + "...[truncated]"

                # Return a safe JSON object the caller expects, using the raw content as advice
                return {"advice": advice_text, "week_start": week_summary.get("week_start"), "week_end": week_summary.get("week_end"), "daily_stats": week_summary.get("daily_stats")}

        except Exception as e:
            raise RuntimeError(f"AI analysis failed: {e}")
