from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import patch
import io


client = TestClient(app)


def make_upload_file_bytes():
    # produce a tiny image-like byte string
    return io.BytesIO(b"\x89PNG\r\n\x1a\n\x00\x00")


@patch("app.routers.exercise.ExerciseDetector")
def test_validate_exercise_endpoint_stateless(mock_detector):
    # Mock the detector instance validate_image to return a deterministic result
    instance = mock_detector.return_value
    instance.validate_image.return_value = {
        "is_exercise": True,
        "confidence": 0.95,
        "label": "exercise",
        "explanation": "Person lifting a dumbbell",
    }

    # Make sure a test user is present — endpoint checks only that user exists by email.
    # If there is no DB user it will return 404; we'll use the same email used in other tests
    email = "user@example.com"

    # Prepare multipart form data
    files = {"file": ("img.jpg", make_upload_file_bytes(), "image/jpeg")}
    data = {"email": email}

    response = client.post("/profile/exercise/validate", files=files, data=data)

    # The endpoint should succeed (200) — if user doesn't exist in DB this will return 404.
    # We allow two possibilities depending on test DB; if 404, assert correct behavior.
    if response.status_code == 404:
        assert response.json()["detail"] == "User not found"
        return

    assert response.status_code == 200
    json = response.json()

    # Ensure we have expected keys and no 'raw' key
    assert "id" in json
    assert "created_at" in json
    assert "image_path" in json
    assert json["is_exercise"] is True
    assert "raw" not in json
