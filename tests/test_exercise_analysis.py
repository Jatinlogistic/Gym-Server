from app.ai.exercise_analysis import ExerciseAnalysis
from unittest.mock import MagicMock


def _make_resp(content_str: str):
    # Minimal fake object matching response.choices[0].message.content
    class M:
        def __init__(self, content):
            self.content = content

    class C:
        def __init__(self, message):
            self.message = message

    class Resp:
        def __init__(self, choices):
            self.choices = choices

    return Resp([C(M(content_str))])


def test_analyze_week_parses_plain_json(monkeypatch):
    analyzer = ExerciseAnalysis()

    # Mock client to return a plain JSON string
    analyzer.client = MagicMock()
    analyzer.client.chat.completions.create.return_value = _make_resp('{"advice":"Nice week"}')

    out = analyzer.analyze_week({"email":"a@b"}, {"week_start":"2025-11-24","week_end":"2025-11-30","daily_stats":[]})
    assert isinstance(out, dict)
    assert out.get("advice") == "Nice week"


def test_analyze_week_parses_fenced_json(monkeypatch):
    analyzer = ExerciseAnalysis()
    analyzer.client = MagicMock()
    # Response includes ```json fences and some commentary
    response = "Here is the analysis:\n```json\n{\"advice\": \"Keep going\"}\n```"
    analyzer.client.chat.completions.create.return_value = _make_resp(response)

    out = analyzer.analyze_week({}, {"week_start":"2025-11-24","week_end":"2025-11-30","daily_stats":[]})
    assert isinstance(out, dict)
    assert out.get("advice") == "Keep going"


def test_analyze_week_returns_fallback_for_text(monkeypatch):
    analyzer = ExerciseAnalysis()
    analyzer.client = MagicMock()

    # AI returns plain text advice (not JSON) — we should return {advice: <text>}
    analyzer.client.chat.completions.create.return_value = _make_resp("You're doing well — add more mobility on rest days.")

    out = analyzer.analyze_week({}, {"week_start":"2025-11-24","week_end":"2025-11-30","daily_stats":[]})
    assert isinstance(out, dict)
    assert "advice" in out
    assert "You're doing well" in out["advice"]


def test_analyze_week_parses_full_structure(monkeypatch):
    analyzer = ExerciseAnalysis()
    analyzer.client = MagicMock()

    # Model returns the full structured JSON as required by the prompt
    full_json = '{"week_start":"2025-11-24","week_end":"2025-11-30","daily_stats":[{"day":"Monday","date":"2025-11-24","total_exercises":5,"completed_exercises":4}],"advice":"Keep it up"}'
    analyzer.client.chat.completions.create.return_value = _make_resp(full_json)

    out = analyzer.analyze_week({}, {"week_start":"2025-11-24","week_end":"2025-11-30","daily_stats":[{"day":"Monday","date":"2025-11-24","total_exercises":5,"completed_exercises":4}]})
    assert isinstance(out, dict)
    assert out.get("week_start") == "2025-11-24"
    assert out.get("week_end") == "2025-11-30"
    assert isinstance(out.get("daily_stats"), list)
    assert out.get("advice") == "Keep it up"


def test_analyze_week_fallback_includes_week_info(monkeypatch):
    analyzer = ExerciseAnalysis()
    analyzer.client = MagicMock()
    analyzer.client.chat.completions.create.return_value = _make_resp("No JSON here, just a sentence.")

    week_summary = {"week_start":"2025-11-24","week_end":"2025-11-30","daily_stats":[{"day":"Monday","date":"2025-11-24","total_exercises":5,"completed_exercises":4}]}
    out = analyzer.analyze_week({}, week_summary)

    assert isinstance(out, dict)
    assert "advice" in out
    assert out.get("week_start") == week_summary["week_start"]
    assert out.get("week_end") == week_summary["week_end"]
    assert out.get("daily_stats") == week_summary["daily_stats"]
