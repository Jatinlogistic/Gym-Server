import os
import base64
from app.ai.exercise_detector import ExerciseDetector


def test_encode_image_encodes_bytes(tmp_path):
    # Create a small binary file
    p = tmp_path / "sample.jpg"
    data = b"\x89PNG\r\n\x1a\n" + b"12345"
    p.write_bytes(data)

    # Create an object without calling __init__ to avoid creating real Groq client
    ed = ExerciseDetector.__new__(ExerciseDetector)

    encoded = ed.encode_image(str(p))
    assert isinstance(encoded, str)

    decoded = base64.b64decode(encoded)
    assert decoded == data


def test_prompt_file_exists_and_requires_json():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    prompt_path = os.path.join(base_dir, "app", "prompt", "exercise_detect.txt")
    assert os.path.exists(prompt_path), "Prompt file should exist"

    text = open(prompt_path, "r").read()
    assert "ONLY return a single JSON object" in text or "ONLY return" in text
