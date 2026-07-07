from unittest.mock import patch, MagicMock
from src.models.plan import TrainingPlan, TrainingSession

@patch("src.services.planner_service.lookup_race_details")
@patch("src.services.planner_service.genai.Client")
def test_generate_plan_success(mock_genai_client, mock_lookup, client):
    # Mock search grounding lookup
    mock_lookup.return_value = "Flat city race course."

    # Setup mock Gemini client response
    mock_response = MagicMock()
    mock_response.text = """
    {
      "weeks_count": 1,
      "total_mileage": 3.0,
      "sessions": [
        {
          "date": "2026-07-01",
          "type": "Easy",
          "name": "Initial Easy Run",
          "description": "30 minutes recovery run",
          "duration_minutes": 30,
          "distance_miles": 3.0,
          "target_pace_range": "9:00-10:00",
          "target_hr_zone": "Zone 2",
          "target_rpe": 4,
          "garmin_instructions_text": "Run 30 minutes easy"
        }
      ]
    }
    """
    
    mock_model_service = MagicMock()
    mock_model_service.generate_content.return_value = mock_response
    
    mock_client_instance = MagicMock()
    mock_client_instance.models = mock_model_service
    mock_genai_client.return_value = mock_client_instance

    # Register and login user
    client.post(
        "/api/v1/auth/register",
        json={"name": "Bob", "email": "bob@example.com", "password": "SecurePassword123!"}
    )
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "bob@example.com", "password": "SecurePassword123!"}
    )
    token = login_resp.json()["session_token"]

    # Call generate plan API
    response = client.post(
        "/api/v1/plans/generate",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "weekly_volume_miles": 15.0,
            "runs_per_week": 3,
            "long_run_day": "Sunday",
            "unavailable_days": "Monday",
            "race_name": "Local 5K",
            "race_date": "2026-07-02",
            "race_distance": "5k",
            "style": "balanced"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["style"] == "balanced"
    assert data["status"] == "active"
    assert "id" in data

    # Call get active plan API
    active_resp = client.get(
        "/api/v1/plans/active",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert active_resp.status_code == 200
    active_data = active_resp.json()
    assert active_data["plan"]["race_name"] == "Local 5K"
    assert len(active_data["sessions"]) == 1
    assert active_data["sessions"][0]["name"] == "Initial Easy Run"


@patch("src.services.planner_service.lookup_race_details")
@patch("src.services.planner_service.genai.Client")
def test_generate_plan_with_notes_success(mock_genai_client, mock_lookup, client):
    mock_lookup.return_value = "Course info."
    mock_response = MagicMock()
    mock_response.text = """
    {
      "weeks_count": 1,
      "total_mileage": 5.0,
      "sessions": [
        {
          "date": "2026-07-01",
          "type": "Easy",
          "name": "Note Inspired Workout",
          "description": "Short easy run",
          "duration_minutes": 40,
          "distance_miles": 5.0,
          "target_pace_range": "8:30-9:30",
          "target_hr_zone": "Zone 2",
          "target_rpe": 5,
          "garmin_instructions_text": "Run easy"
        }
      ]
    }
    """
    mock_model_service = MagicMock()
    mock_model_service.generate_content.return_value = mock_response
    mock_client_instance = MagicMock()
    mock_client_instance.models = mock_model_service
    mock_genai_client.return_value = mock_client_instance

    client.post(
        "/api/v1/auth/register",
        json={"name": "Alice", "email": "alice@example.com", "password": "SecurePassword123!"}
    )
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "SecurePassword123!"}
    )
    token = login_resp.json()["session_token"]

    response = client.post(
        "/api/v1/plans/generate",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "weekly_volume_miles": 20.0,
            "runs_per_week": 4,
            "long_run_day": "Saturday",
            "unavailable_days": "Tuesday",
            "race_name": "Trail Run 10K",
            "race_date": "2026-07-02",
            "race_distance": "10k",
            "style": "balanced",
            "additional_notes": "I prefer trail running, please schedule off-road terrain workouts."
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["style"] == "balanced"
    
    # Verify that the mocked client was called with the additional notes
    args, kwargs = mock_model_service.generate_content.call_args
    prompt_sent = kwargs.get("contents") or args[0]
    assert "Additional Athlete Notes (treat these as high-priority constraints):" in prompt_sent
    assert "I prefer trail running, please schedule off-road terrain workouts." in prompt_sent


@patch("src.services.evaluation_service.sync_strava_activities")
@patch("src.services.planner_service.lookup_race_details")
@patch("google.genai.Client")
def test_evaluate_plan_progress_success(
    mock_genai_client, mock_lookup, mock_sync_strava, client
):
    # 1. Setup mock responses
    mock_lookup.return_value = "Race terrain info."
    mock_plan_response = MagicMock()
    mock_plan_response.text = """
    {
      "weeks_count": 1,
      "total_mileage": 3.0,
      "sessions": [
        {
          "date": "2026-07-01",
          "type": "Easy",
          "name": "Monday Recovery Run",
          "description": "30 mins easy pace",
          "duration_minutes": 30,
          "distance_miles": 3.0,
          "target_pace_range": "9:00-10:00",
          "target_hr_zone": "Zone 2",
          "target_rpe": 4,
          "garmin_instructions_text": "Run easy"
        }
      ]
    }
    """

    shared_session_id = [""]

    def generate_content_side_effect(*args, **kwargs):
        config = kwargs.get("config")
        if config and hasattr(config, "response_schema"):
            schema_name = config.response_schema.__name__
            if schema_name == "PlanEvaluationSchema":
                mock_eval_response = MagicMock()
                mock_eval_response.text = f"""
                {{
                  "weeks": [
                    {{
                      "week_number": 1,
                      "commentary": "Super week of running! You matched your recovery session perfectly.",
                      "matches": [
                        {{
                          "session_id": "{shared_session_id[0]}",
                          "strava_activity_id": "999888",
                          "status": "completed",
                          "explanation": "Matched Monday Recovery Run to Morning Run on Strava"
                        }}
                      ]
                    }}
                  ]
                }}
                """
                return mock_eval_response
        return mock_plan_response

    mock_model_service = MagicMock()
    mock_model_service.generate_content.side_effect = generate_content_side_effect
    mock_client_instance = MagicMock()
    mock_client_instance.models = mock_model_service
    mock_genai_client.return_value = mock_client_instance

    # 2. Register, Login, and Generate Plan
    client.post(
        "/api/v1/auth/register",
        json={"name": "Charlie", "email": "charlie@example.com", "password": "SecurePassword123!"}
    )
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "charlie@example.com", "password": "SecurePassword123!"}
    )
    token = login_resp.json()["session_token"]

    gen_resp = client.post(
        "/api/v1/plans/generate",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "weekly_volume_miles": 15.0,
            "runs_per_week": 3,
            "long_run_day": "Sunday",
            "unavailable_days": "Monday",
            "race_name": "5K Sprint",
            "race_date": "2026-07-02",
            "race_distance": "5k",
            "style": "balanced"
        }
    )
    assert gen_resp.status_code == 200, gen_resp.json()

    # 3. Retrieve plan details to get session ID
    active_resp = client.get(
        "/api/v1/plans/active",
        headers={"Authorization": f"Bearer {token}"}
    )
    active_data = active_resp.json()
    session_id = active_data["sessions"][0]["id"]
    shared_session_id[0] = session_id

    # 4. Setup Mock for Plan Evaluation
    mock_sync_strava.return_value = 1

    # 5. Call Evaluate Plan API
    eval_resp = client.post(
        "/api/v1/plans/evaluate",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert eval_resp.status_code == 200
    eval_data = eval_resp.json()
    assert eval_data["status"] == "success"
    assert len(eval_data["evaluations"]) == 1
    assert eval_data["evaluations"][0]["week_number"] == 1
    assert "Super week" in eval_data["evaluations"][0]["commentary"]

    # 6. Verify that session status was updated to completed in active plan GET
    active_resp2 = client.get(
        "/api/v1/plans/active",
        headers={"Authorization": f"Bearer {token}"}
    )
    active_data2 = active_resp2.json()
    assert active_data2["sessions"][0]["status"] == "completed"
    assert len(active_data2["weekly_evaluations"]) == 1
    assert active_data2["weekly_evaluations"][0]["commentary"] == eval_data["evaluations"][0]["commentary"]


@patch("src.services.planner_service.lookup_race_details")
@patch("src.services.planner_service.genai.Client")
def test_update_plan_workflow(mock_genai_client, mock_lookup, client):
    import uuid
    # 1. Setup mock registration and login
    email = f"update-{uuid.uuid4()}@example.com"
    reg_resp = client.post("/api/v1/auth/register", json={
        "name": "Updater Runner",
        "email": email,
        "password": "password123"
    })
    assert reg_resp.status_code == 201
    
    login_resp = client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "password123"
    })
    assert login_resp.status_code == 200
    token = login_resp.json()["session_token"]

    # Mock Plan Generation response
    mock_lookup.return_value = "Grounding course details"
    mock_gen_response = MagicMock()
    mock_gen_response.text = """
    {
      "weeks_count": 1,
      "total_mileage": 5.0,
      "sessions": [
        {
          "date": "2026-07-20",
          "type": "Easy",
          "name": "Initial Easy Run",
          "description": "Easy run",
          "duration_minutes": 30,
          "distance_miles": 3.0,
          "warm_up": [],
          "main_set": [],
          "cool_down": [],
          "target_pace_range": "9:00-9:30",
          "target_hr_zone": "Zone 2",
          "target_rpe": 5,
          "garmin_instructions_text": "Run easy"
        }
      ]
    }
    """
    
    mock_update_response = MagicMock()
    mock_update_response.text = """
    {
      "explanation": "I adapted your future plan by scaling down mileage and adjusting pace.",
      "sessions": [
        {
          "date": "2026-07-20",
          "type": "Easy",
          "name": "Adapted Easy Run",
          "description": "Short easy recovery run",
          "duration_minutes": 30,
          "distance_miles": 3.0,
          "warm_up": [],
          "main_set": [],
          "cool_down": [],
          "target_pace_range": "9:30-10:00",
          "target_hr_zone": "Zone 2",
          "target_rpe": 4,
          "garmin_instructions_text": "Run easy for 3 miles"
        }
      ]
    }
    """

    mock_model_service = MagicMock()
    # First call is generate, second is preview, third is apply
    mock_model_service.generate_content.side_effect = [mock_gen_response, mock_update_response, mock_update_response]
    
    mock_client_instance = MagicMock()
    mock_client_instance.models = mock_model_service
    mock_genai_client.return_value = mock_client_instance

    # Generate initial plan
    gen_resp = client.post(
        "/api/v1/plans/generate",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "weekly_volume_miles": 10.0,
            "runs_per_week": 3,
            "long_run_day": "Sunday",
            "unavailable_days": "Monday,Wednesday",
            "race_name": "Test Race",
            "race_date": "2026-07-20",
            "race_distance": "5k",
            "style": "balanced"
        }
    )
    assert gen_resp.status_code == 200, gen_resp.json()

    # 2. Call preview endpoint
    preview_resp = client.post(
        "/api/v1/plans/update/preview",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "difficulty_feedback": "hard",
            "user_comments": "Please make it easier"
        }
    )
    assert preview_resp.status_code == 200, preview_resp.json()
    preview_data = preview_resp.json()
    assert preview_data["status"] == "success"
    assert "adapted your future plan" in preview_data["explanation"]
    assert len(preview_data["sessions"]) == 1
    assert preview_data["sessions"][0]["name"] == "Adapted Easy Run"

    # 3. Call apply endpoint
    apply_resp = client.post(
        "/api/v1/plans/update/apply",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "difficulty_feedback": "hard",
            "user_comments": "Please make it easier"
        }
    )
    assert apply_resp.status_code == 200, apply_resp.json()
    assert apply_resp.json()["status"] == "success"

    # 4. Get active plan to verify sessions have been replaced
    active_resp = client.get(
        "/api/v1/plans/active",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert active_resp.status_code == 200
    active_data = active_resp.json()
    assert len(active_data["sessions"]) == 1
    assert active_data["sessions"][0]["name"] == "Adapted Easy Run"



