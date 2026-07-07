# Quickstart Validation Guide: Running Training Web App

This guide documents the verification scenarios for proving the functionality of the running training web application end-to-end.

## Prerequisites

1.  **Backend Dependencies**:
    - Python 3.12+
    - `pip install fastapi uvicorn sqlalchemy pydantic google-genai httpx pytest`
2.  **Frontend Dependencies**:
    - Node.js 20+
    - `npm install` inside the frontend directory
3.  **Environment Setup**:
    - A `.env` file in the backend directory containing:
      ```env
      GEMINI_API_KEY=your_google_gemini_api_key_here
      STRAVA_CLIENT_ID=your_strava_client_id
      STRAVA_CLIENT_SECRET=your_strava_client_secret
      DATABASE_URL=sqlite:///./running_coach.db
      ```

## Validation Scenarios

### Scenario 1: Initial Local Server Run

*   **Setup Commands**:
    1. Start the Python backend (which serves both the APIs and the frontend static assets):
       ```bash
       cd backend
       uvicorn src.main:app --reload --port 8000
       ```
*   **Verification Steps**:
    1. Open a browser and navigate to `http://localhost:8000/`.
    2. Verify the landing page displays correctly in the premium sporty visual layout (dark mode gradient, custom font).
    3. Access the API documentation at `http://localhost:8000/docs` and confirm the Swagger UI loads.

### Scenario 2: Register, Onboard, and Generate Plan

*   **Verification Steps**:
    1. Click "Sign Up" on the landing page and register a test user `runner_test@example.com` (using password `SecurePassword123!`).
    2. Complete the running profile wizard (Volume: 25 miles/week, Goal: Half Marathon, Preferred days: Tuesday, Thursday, Sunday).
    3. Click "Generate Training Plan" and wait for the Gemini model to build the calendar.
*   **Expected Outcome**:
    - The plan is created in under 10 seconds.
    - User is redirected to the dashboard showing a 12-week calendar with training runs, rest days, and strength sessions properly distributed.
    - SQLite database now contains a record in `training_plan` and 12 * 4 runs in `training_session`.

### Scenario 3: Calendar Drag-and-Drop and Warning Trigger

*   **Verification Steps**:
    1. Go to the dashboard calendar.
    2. Drag an "Interval Run" from Tuesday to Wednesday (right next to Thursday's "Tempo Run").
*   **Expected Outcome**:
    - A warning dialog displays: *"Moving intervals to Wednesday creates two hard sessions back-to-back. I recommend moving Thursday tempo to Saturday or changing it to an easy run."*
    - The calendar updates Wednesday to display the intervals, and Wednesday's move is logged in the `plan_change_log` table.

### Scenario 4: Dynamic Unit Switcher and Detail Conversion

*   **Verification Steps**:
    1. Click the "Unit: mi" switcher button in the navigation header.
    2. Open a calendar workout card (e.g. "Threshold Intervals").
*   **Expected Outcome**:
    - The button text changes to "Unit: km".
    - Target pace range converts from min/mile to min/km (e.g., displaying `7:25-7:40 /mi` as `4:36-4:46 /km`).
    - The workout step descriptions dynamically convert mileage mentions to kilometers (e.g. `"Run 1.5 miles easy"` converts to `"Run 2.4 km easy"`).
    - The Coach's "Training Benefits" card displays the primary purpose and adaptations for that specific session type.

### Scenario 5: User Settings and GDPR Controls

*   **Verification Steps**:
    1. Click your name in the navigation header to open the Profile Settings.
    2. Scroll down to the Danger Zone.
    3. Test "Export Personal Data" and "Revoke Strava Access".
*   **Expected Outcome**:
    - Clicking export downloads a `.json` file containing all profile metrics, activities, and plan tables.
    - Disconnecting Strava updates the connected status dynamically.
