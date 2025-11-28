# Workout Plan PDF Download Endpoint

This FastAPI project includes an endpoint to fetch a user's stored weekly workout plan from the `user_workouts` table and produce a downloadable PDF.

## Endpoint

- POST /profile/workout-plan/pdf-download

### Request body

JSON object with the following fields:

- `email` (required) — user email used in user_workouts.user_email
- `week_start` (optional) — date string `YYYY-MM-DD`. If omitted the most recent plan for the user is used.

Example request body:

```json
{
  "email": "user@example.com",
  "week_start": "2025-11-24"
}
```

### Response

Returns a PDF file as a streaming response with `Content-Type: application/pdf` and an `attachment` Content-Disposition header.

### Common issue: "Failed to load PDF document"

- If your client saved a file that fails to open as a PDF, it likely received an error JSON (for example the endpoint returned 404 when no saved workout was found).
- Make sure you pass a valid `email` for which a workout exists in `user_workouts`, or pass the `week_start` for a specific week.
- The example client script `test.py` now checks the response status and content-type before saving to avoid writing error JSON to a `.pdf` file.

## Developer notes

- PDF generation uses the `reportlab` library; the requirement has been added to `requirements.txt`.
- The PDF builder lives in `app/utils/pdf.py` as `workout_plan_to_pdf_bytes()`.

## Example curl

```bash
curl -X POST "http://localhost:8000/profile/workout-plan/pdf-download" -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","week_start":"2025-11-24"}' --output workout.pdf
```
