from fastapi.testclient import TestClient
from app.main import app
import app.routers.analysis as analysis_module
from unittest.mock import patch

client = TestClient(app)


class FakeFollowup:
    def __init__(self, date, total_exercises, completed_exercises):
        self.date = date
        self.total_exercises = total_exercises
        self.completed_exercises = completed_exercises


def make_fake_db(followups):
    class FakeDB:
        def __init__(self, followups):
            self._followups = followups

        def query(self, model):
            class Q:
                def __init__(self, followups):
                    self.followups = followups

                def filter(self, *args, **kwargs):
                    return self

                def all(self):
                    return self.followups

                def first(self):
                    return self.followups[0] if self.followups else None

            return Q(self._followups)

        def close(self):
            return

    return FakeDB(followups)


@patch("app.ai.exercise_analysis.ExerciseAnalysis.analyze_week")
def test_analysis_missing_days(mock_analyze, monkeypatch):
    # Single entry on Friday only
    followups = [FakeFollowup("2025-11-28", 3, 1)]

    def fake_get_db():
        db = make_fake_db(followups)
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[analysis_module.get_db] = fake_get_db

    mock_analyze.return_value = {"advice": "You did well, add a light mobility session on rest days."}

    payload = {"email": "user@example.com", "week_start": "2025-11-24", "week_end": "2025-11-30"}
    # Simulate today's date as 2025-11-28 so future days (29,30) are zeroed
    from datetime import date as _d
    monkeypatch.setattr(analysis_module.date, "today", lambda: _d(2025, 11, 28))

    resp = client.post("/profile/analysis", json=payload)

    # Reset override
    app.dependency_overrides.pop(analysis_module.get_db, None)

    assert resp.status_code == 200
    data = resp.json()
    assert data["week_start"] == "2025-11-24"
    # Include full week (Mon-Sun) but future days (29,30) are present with zeros
    assert len(data["daily_stats"]) == 7
    # Check Friday entry preserved
    friday = next((d for d in data["daily_stats"] if d["date"] == "2025-11-28"), None)
    assert friday is not None
    assert friday["total_exercises"] == 3
    assert friday["completed_exercises"] == 1

    # Check a missing day (e.g., Monday) shows zeros
    monday = next((d for d in data["daily_stats"] if d["date"] == "2025-11-24"), None)
    assert monday is not None
    assert monday["completed_exercises"] == 0

    # Future days (29, 30) should be present but zeroed because today = Nov 28
    day29 = next((d for d in data["daily_stats"] if d["date"] == "2025-11-29"), None)
    day30 = next((d for d in data["daily_stats"] if d["date"] == "2025-11-30"), None)
    assert day29 is not None and day29["completed_exercises"] == 0 and day29["total_exercises"] == 0
    assert day30 is not None and day30["completed_exercises"] == 0 and day30["total_exercises"] == 0

    assert "advice" in data and isinstance(data["advice"], str)


@patch("app.ai.exercise_analysis.ExerciseAnalysis.analyze_week")
def test_analysis_all_days(mock_analyze, monkeypatch):
    followups = [
        FakeFollowup("2025-11-24", 5, 4),
        FakeFollowup("2025-11-25", 4, 4),
        FakeFollowup("2025-11-26", 3, 2),
        FakeFollowup("2025-11-27", 3, 0),
        FakeFollowup("2025-11-28", 3, 1),
        FakeFollowup("2025-11-29", 5, 5),
        FakeFollowup("2025-11-30", 5, 5),
    ]

    def fake_get_db():
        db = make_fake_db(followups)
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[analysis_module.get_db] = fake_get_db
    mock_analyze.return_value = {"advice": "Solid week. Try keeping recovery days consistent."}

    payload = {"email": "user@example.com", "week_start": "2025-11-24", "week_end": "2025-11-30"}
    # Force today's date to 2025-11-28
    from datetime import date as _d
    monkeypatch.setattr(analysis_module.date, "today", lambda: _d(2025, 11, 28))
    resp = client.post("/profile/analysis", json=payload)

    # Cleanup
    app.dependency_overrides.pop(analysis_module.get_db, None)

    assert resp.status_code == 200
    data = resp.json()
    # Full week should be returned (Mon-Sun) but future days zeroed
    assert len(data["daily_stats"]) == 7
    # ensure Friday has the values provided
    friday = next((d for d in data["daily_stats"] if d["date"] == "2025-11-28"), None)
    assert friday["completed_exercises"] == 1
    assert data["advice"] == "Solid week. Try keeping recovery days consistent."
    # Future days (29 & 30) should be present but zeroed
    n29 = next((d for d in data["daily_stats"] if d["date"] == "2025-11-29"), None)
    n30 = next((d for d in data["daily_stats"] if d["date"] == "2025-11-30"), None)
    assert n29 is not None and n29["completed_exercises"] == 0 and n29["total_exercises"] == 0
    assert n30 is not None and n30["completed_exercises"] == 0 and n30["total_exercises"] == 0


@patch("app.ai.exercise_analysis.ExerciseAnalysis.analyze_week")
def test_returns_cached_analysis(mock_analyze, monkeypatch):
    # Prepare a stored analysis record (should be returned directly)
    class FakeAnalysisObj:
        def __init__(self):
            from datetime import datetime

            self.analysis_id = 77
            self.user_email = "user@example.com"
            self.week_start = "2025-11-24"
            self.week_end = "2025-11-30"
            self.daily_stats = [
                {"day": "Monday", "date": "2025-11-24", "total_exercises": 1, "completed_exercises": 1},
            ]
            self.advice = "Keep consistent"
            self.created_at = datetime.utcnow()

    stored = FakeAnalysisObj()

    # fake DB: return stored analysis for analysis model, and no followups
    class FakeDB2:
        def query(self, model):
            class Q:
                def __init__(self, model):
                    self.model = model

                def filter(self, *args, **kwargs):
                    return self

                def first(self):
                    # If asking for analysis return stored object, otherwise None
                    if getattr(self.model, "__name__", "") == "UserExerciseAnalysis":
                        return stored
                    return None

                def all(self):
                    return []

            return Q(model)

        def close(self):
            return

    def fake_get_db():
        db = FakeDB2()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[analysis_module.get_db] = fake_get_db

    # analyzer shouldn't be called when cached value exists
    payload = {"email": "user@example.com", "week_start": "2025-11-24", "week_end": "2025-11-30"}
    resp = client.post("/profile/analysis", json=payload)

    app.dependency_overrides.pop(analysis_module.get_db, None)

    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == "77"
    assert body["advice"] == "Keep consistent"
    assert isinstance(body["daily_stats"], list)
    # Cached result should include full week; missing days should be zeroed
    assert len(body["daily_stats"]) == 7
    assert not mock_analyze.called


@patch("app.ai.exercise_analysis.ExerciseAnalysis.analyze_week")
def test_cached_with_future_entries_trimmed(mock_analyze, monkeypatch):
    # Prepare stored analysis with full week including future days
    class FakeAnalysisObj2:
        def __init__(self):
            from datetime import datetime

            self.analysis_id = 88
            self.user_email = "user@example.com"
            self.week_start = "2025-11-24"
            self.week_end = "2025-11-30"
            self.daily_stats = [
                {"day": "Monday", "date": "2025-11-24", "total_exercises": 1, "completed_exercises": 1},
                {"day": "Friday", "date": "2025-11-28", "total_exercises": 3, "completed_exercises": 1},
                {"day": "Saturday", "date": "2025-11-29", "total_exercises": 4, "completed_exercises": 2},
                {"day": "Sunday", "date": "2025-11-30", "total_exercises": 5, "completed_exercises": 3},
            ]
            self.advice = "Keep consistent"
            self.created_at = datetime.utcnow()

    stored2 = FakeAnalysisObj2()

    class FakeDB3:
        def query(self, model):
            class Q:
                def __init__(self, model):
                    self.model = model

                def filter(self, *args, **kwargs):
                    return self

                def first(self):
                    if getattr(self.model, "__name__", "") == "UserExerciseAnalysis":
                        return stored2
                    return None

                def all(self):
                    return []

            return Q(model)

        def close(self):
            return

    def fake_get_db2():
        db = FakeDB3()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[analysis_module.get_db] = fake_get_db2

    # Simulate today as 2025-11-28
    from datetime import date as _d
    monkeypatch.setattr(analysis_module.date, "today", lambda: _d(2025, 11, 28))

    payload = {"email": "user@example.com", "week_start": "2025-11-24", "week_end": "2025-11-30"}
    resp = client.post("/profile/analysis", json=payload)

    app.dependency_overrides.pop(analysis_module.get_db, None)

    assert resp.status_code == 200
    body = resp.json()
    # Future days should be present but zeroed
    assert any(d["date"] == "2025-11-29" for d in body["daily_stats"]) and any(d["date"] == "2025-11-30" for d in body["daily_stats"])
    assert not any(d for d in body["daily_stats"] if d["date"] in {"2025-11-29", "2025-11-30"} and d["completed_exercises"] != 0)
