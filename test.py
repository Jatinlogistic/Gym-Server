import requests
import sys

resp = requests.post(
    "http://localhost:8000/profile/workout-plan/pdf-download",
    json={"email": ""}
)

if resp.status_code != 200:
    print("Error fetching PDF:", resp.status_code, resp.headers.get('content-type'))
    try:
        print(resp.json())
    except Exception:
        print(resp.text)
    sys.exit(1)

ct = resp.headers.get('content-type', '')
if 'application/pdf' not in ct:
    print('Server did not return PDF; content-type:', ct)
    print(resp.text[:400])
    sys.exit(1)

with open("workout.pdf", "wb") as f:
    f.write(resp.content)
print('Saved workout.pdf (%d bytes)' % len(resp.content))