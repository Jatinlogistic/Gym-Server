from fastapi.testclient import TestClient
from app.main import app
import app.routers.exercise as exercise_module

client = TestClient(app)


def test_followup_missing_user_returns_404():
    payload = {
        "email": "nonexistent@example.com",
        "date": "2025-11-28",
        "completed_exercises": 1,
    }

    resp = client.post("/profile/exercise/follow-up", json=payload)
    assert resp.status_code == 404
    assert resp.json()["detail"] == "User not found"


def test_followup_saved_with_fake_db(monkeypatch):
    # Create a fake DB with minimal behavior to emulate add/commit/refresh
    class FakeDB:
        def __init__(self):
            self.added = []

        def query(self, model):
            class Q:
                def __init__(self, db):
                    self.db = db

                def filter(self, *args, **kwargs):
                    return self

                def first(self):
                    class P:
                        email = "user@example.com"

                    return P()

            return Q(self)

        def add(self, obj):
            # simulate DB really creating an id
            setattr(obj, "followup_id", 99)
            self.added.append(obj)

        def commit(self):
            return

        def refresh(self, obj):
            import datetime

            setattr(obj, "created_at", datetime.datetime.utcnow())

        def close(self):
            return

    def fake_get_db():
        db = FakeDB()
        try:
            yield db
        finally:
            db.close()

    # Override dependency
    app.dependency_overrides[exercise_module.get_db] = fake_get_db

    payload = {
        "email": "user@example.com",
        "date": "2025-11-28",
        "completed_exercises": 1,
        "exercises": [
            {"name": "Push-ups", "sets": 3, "reps": 12, "rest": 60, "completed": True}
        ],
    }

    resp = client.post("/profile/exercise/follow-up", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == "99"
    assert "created_at" in body
    assert body["date"] == "2025-11-28"
    assert body["completed_exercises"] == 1
    assert isinstance(body["exercises"], list)
    assert body["exercises"][0]["name"] == "Push-ups"

    # Cleanup
    app.dependency_overrides.pop(exercise_module.get_db, None)
