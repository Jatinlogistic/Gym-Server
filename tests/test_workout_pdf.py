from app.utils.pdf import workout_plan_to_pdf_bytes


def make_sample_workout():
    return {
        "monday": {"focus": "Upper Body", "exercises": [
            {"name": "Push-ups", "reps": "12", "rest": "60", "sets": "3", "notes": ""},
            {"name": "Bodyweight rows", "reps": "12", "rest": "60", "sets": "3", "notes": "Assisted"}
        ]},
        "tuesday": {"focus": "Lower Body", "exercises": [
            {"name": "Bodyweight squats", "reps": "12", "rest": "60", "sets": "3", "notes": ""}
        ]},
        "wednesday": {"focus": "Rest or Active Recovery", "exercises": []}
    }


def test_workout_pdf_bytes_generated():
    pdf = workout_plan_to_pdf_bytes(user_name="Test User", week_start="2025-11-24", week_end="2025-11-30", week_number=1, workout_plan=make_sample_workout())
    assert isinstance(pdf, (bytes, bytearray))
    # PDF files typically start with %PDF
    assert pdf[:4] == b"%PDF"
    assert len(pdf) > 100


def test_long_notes_wrap_ok():
    long_note = "This is a very long note intended to test wrapping. " * 30
    plan = {
        "monday": {"focus": "Upper Body", "exercises": [
            {"name": "Push-ups", "reps": "12", "rest": "60", "sets": "3", "notes": long_note},
        ]}
    }
    pdf = workout_plan_to_pdf_bytes(user_name="Long Note User", week_start="2025-11-24", week_end="2025-11-30", week_number=1, workout_plan=plan)
    assert isinstance(pdf, (bytes, bytearray))
    assert pdf[:4] == b"%PDF"
    # PDF should be larger due to long content
    assert len(pdf) > 2000


def test_integer_fields_are_handled():
    # Historically the PDF generator failed when fields were integers (e.g. reps=12)
    plan = {
        "monday": {"focus": "Upper Body", "exercises": [
            {"name": 123, "reps": 12, "rest": 60, "sets": 3, "notes": 456},
        ]}
    }
    pdf = workout_plan_to_pdf_bytes(user_name="Int User", week_start="2025-11-24", week_end="2025-11-30", week_number=1, workout_plan=plan)
    assert isinstance(pdf, (bytes, bytearray))
    assert pdf[:4] == b"%PDF"
    assert len(pdf) > 500
