# API Contracts: Running Training App

This document defines the HTTP endpoints for the Running Training Web App backend. All endpoints are relative to the `/api/v1` base URL.

## 1. Authentication Endpoints

### `POST /auth/register`
Creates a new user account.
*   **Request Body**:
    ```json
    {
      "name": "Jane Doe",
      "email": "jane@example.com",
      "password": "SecurePassword123!"
    }
    ```
*   **Response (201 Created)**:
    ```json
    {
      "user_id": "a6b7c8d9-e1f2-3a4b-5c6d-7e8f9a0b1c2d",
      "name": "Jane Doe",
      "email": "jane@example.com"
    }
    ```

### `POST /auth/login`
Authenticates a user and establishes a session.
*   **Request Body**:
    ```json
    {
      "email": "jane@example.com",
      "password": "SecurePassword123!"
    }
    ```
*   **Response (200 OK)**:
    ```json
    {
      "session_token": "token_xyz123abc456",
      "user": {
        "id": "a6b7c8d9-e1f2-3a4b-5c6d-7e8f9a0b1c2d",
        "email": "jane@example.com"
      }
    }
    ```

---

## 2. Strava Integration Endpoints

### `GET /strava/auth-url`
Retrieves the Strava OAuth authorization URL to redirect the user to.
*   **Response (200 OK)**:
    ```json
    {
      "url": "https://www.strava.com/oauth/authorize?client_id=12345&redirect_uri=http://localhost:8000/api/v1/strava/callback&response_type=code&scope=activity:read_all"
    }
    ```

### `POST /strava/callback`
Exchanges the authorization code from Strava callback for tokens.
*   **Request Body**:
    ```json
    {
      "code": "strava_auth_code_here",
      "scope": "activity:read_all"
    }
    ```
*   **Response (200 OK)**:
    ```json
    {
      "status": "connected",
      "athlete_name": "Jane Runner"
    }
    ```

---

## 3. Training Plan Endpoints

### `POST /plans/generate`
Generates a new training plan using Google Gemini.
*   **Request Body**:
    ```json
    {
      "race_name": "Boston Marathon",
      "race_date": "2026-10-12",
      "race_distance": "marathon",
      "target_time": "03:30:00",
      "training_days_per_week": 4,
      "style": "balanced"
    }
    ```
*   **Response (200 OK)**:
    ```json
    {
      "plan_id": "b8c9d0e1-f2a3-4b5c-6d7e-8f9a0b1c2d3e",
      "race_name": "Boston Marathon",
      "weeks_count": 16,
      "total_mileage": 420.5
    }
    ```

### `POST /plans/sessions/move`
Drags and drops a session to a different date.
*   **Request Body**:
    ```json
    {
      "session_id": "c9d0e1f2-a3b4-5c6d-7e8f-9a0b1c2d3e4f",
      "new_date": "2026-07-01"
    }
    ```
*   **Response (200 OK)**:
    ```json
    {
      "success": true,
      "session_id": "c9d0e1f2-a3b4-5c6d-7e8f-9a0b1c2d3e4f",
      "new_date": "2026-07-01",
      "warning": "Moving intervals to Wednesday creates consecutive hard days with Thursday's long run. Would you like to rebalance?",
      "requires_rebalance": true
    }
    ```
