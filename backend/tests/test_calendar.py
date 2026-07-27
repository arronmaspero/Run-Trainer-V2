import json
from unittest.mock import patch, MagicMock
from datetime import date, timedelta
from src.models.plan import TrainingPlan, TrainingSession
from src.models.changelog import PlanChangeLog

@patch("src.services.planner_service.lookup_race_details")
@patch("src.services.planner_service.genai.Client")
def test_move_session_and_rebalance(mock_genai_client, mock_lookup, client):
    # Mock lookup
    mock_lookup.return_value = "Flat city race course."

    # Dynamic dates
    tomorrow = date.today() + timedelta(days=1)
    day_after = date.today() + timedelta(days=2)
    three_days_after = date.today() + timedelta(days=3)
    four_days_after = date.today() + timedelta(days=4)
    five_days_after = date.today() + timedelta(days=5)

    # Setup mock Gemini client response for generation
    mock_response = MagicMock()
    mock_response.text = f"""
    {{
      "weeks_count": 2,
      "total_mileage": 10.0,
      "sessions": [
        {{
          "date": "{tomorrow.isoformat()}",
          "type": "Easy",
          "name": "Easy Run",
          "description": "30 minutes easy run",
          "duration_minutes": 30,
          "distance_miles": 3.0,
          "target_pace_range": "9:00-10:00",
          "target_hr_zone": "Zone 2",
          "target_rpe": 4,
          "garmin_instructions_text": "Run 30 minutes easy"
        }},
        {{
          "date": "{day_after.isoformat()}",
          "type": "Intervals",
          "name": "Speedwork",
          "description": "4x400m intervals",
          "duration_minutes": 45,
          "distance_miles": 4.0,
          "target_pace_range": "7:00-7:30",
          "target_hr_zone": "Zone 4",
          "target_rpe": 8,
          "garmin_instructions_text": "Run 4x400m hard"
        }},
        {{
          "date": "{four_days_after.isoformat()}",
          "type": "Tempo",
          "name": "Tempo Run",
          "description": "20 minutes tempo pace",
          "duration_minutes": 40,
          "distance_miles": 3.0,
          "target_pace_range": "8:00-8:30",
          "target_hr_zone": "Zone 3",
          "target_rpe": 7,
          "garmin_instructions_text": "Run 20 minutes tempo"
        }}
      ]
    }}
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
    client.post(
        "/api/v1/plans/generate",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "weekly_volume_miles": 15.0,
            "runs_per_week": 3,
            "long_run_day": "Sunday",
            "unavailable_days": "Monday",
            "race_name": "Local 5K",
            "race_date": (date.today() + timedelta(days=15)).isoformat(),
            "race_distance": "5k",
            "style": "balanced"
        }
    )

    # Get active plan to retrieve session IDs
    active_resp = client.get(
        "/api/v1/plans/active",
        headers={"Authorization": f"Bearer {token}"}
    )
    sessions = active_resp.json()["sessions"]
    plan_id = active_resp.json()["plan"]["id"]
    
    intervals_session = next(s for s in sessions if s["type"] == "Intervals")
    tempo_session = next(s for s in sessions if s["type"] == "Tempo")

    # Move intervals session to make it consecutive with tempo session (to three_days_after)
    move_resp = client.post(
        "/api/v1/plans/sessions/move",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "session_id": intervals_session["id"],
            "new_date": three_days_after.isoformat()
        }
    )
    assert move_resp.status_code == 200
    move_data = move_resp.json()
    assert move_data["status"] == "success"
    # Should detect consecutive hard runs (Intervals on three_days_after and Tempo on four_days_after)
    assert move_data["is_imbalanced"] is True
    assert len(move_data["warnings"]) > 0

    # Get single session detail
    detail_resp = client.get(
        f"/api/v1/plans/sessions/{intervals_session['id']}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert detail_resp.status_code == 200
    detail_data = detail_resp.json()
    assert detail_data["name"] == "Speedwork"
    assert "safety_alternative" in detail_data
    assert "medical_disclaimer" in detail_data
    
    # Verify dynamic fallback parser from garmin instructions
    assert len(detail_data["main_set"]) > 0
    assert detail_data["main_set"][0] == "Run 4x400m hard"

    # Setup mock Gemini client response for rebalance
    mock_rebalance_response = MagicMock()
    mock_rebalance_response.text = json.dumps({
        "proposed_changes": [
            {"session_id": intervals_session["id"], "date": three_days_after.isoformat()},
            {"session_id": tempo_session["id"], "date": five_days_after.isoformat()}  # Shifted tempo run to five_days_after to avoid consecutive days
        ]
    })
    mock_model_service.generate_content.return_value = mock_rebalance_response

    # Call AI rebalance preview endpoint
    rebalance_resp = client.post(
        "/api/v1/plans/rebalance",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "plan_id": plan_id,
            "confirm": False
        }
    )
    assert rebalance_resp.status_code == 200
    rebalance_data = rebalance_resp.json()
    assert rebalance_data["status"] == "preview"
    assert len(rebalance_data["proposed_changes"]) > 0
    assert rebalance_data["proposed_changes"][0]["session_id"] == tempo_session["id"]
    assert rebalance_data["proposed_changes"][0]["new_date"] == five_days_after.isoformat()

    # Confirm the AI rebalance
    confirm_resp = client.post(
        "/api/v1/plans/rebalance",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "plan_id": plan_id,
            "confirm": True
        }
    )
    assert confirm_resp.status_code == 200
    assert confirm_resp.json()["status"] == "success"

    # Verify sessions dates updated
    active_resp_after = client.get(
        "/api/v1/plans/active",
        headers={"Authorization": f"Bearer {token}"}
    )
    sessions_after = active_resp_after.json()["sessions"]
    tempo_after = next(s for s in sessions_after if s["type"] == "Tempo")
    assert tempo_after["date"] == five_days_after.isoformat()

@patch("src.services.planner_service.lookup_race_details")
@patch("src.services.planner_service.genai.Client")
def test_move_session_swap(mock_genai_client, mock_lookup, client):
    # Mock lookup
    mock_lookup.return_value = "Flat city race course."

    # Dynamic dates
    tomorrow = date.today() + timedelta(days=1)
    day_after = date.today() + timedelta(days=2)

    # Setup mock Gemini client response for generation
    mock_response = MagicMock()
    mock_response.text = f"""
    {{
      "weeks_count": 1,
      "total_mileage": 6.0,
      "sessions": [
        {{
          "date": "{tomorrow.isoformat()}",
          "type": "Easy",
          "name": "Easy Run",
          "description": "30 minutes easy run",
          "duration_minutes": 30,
          "distance_miles": 3.0,
          "target_pace_range": "9:00-10:00",
          "target_hr_zone": "Zone 2",
          "target_rpe": 4,
          "garmin_instructions_text": "Run 30 minutes easy"
        }},
        {{
          "date": "{day_after.isoformat()}",
          "type": "Tempo",
          "name": "Tempo Run",
          "description": "20 minutes tempo pace",
          "duration_minutes": 40,
          "distance_miles": 3.0,
          "target_pace_range": "8:00-8:30",
          "target_hr_zone": "Zone 3",
          "target_rpe": 7,
          "garmin_instructions_text": "Run 20 minutes tempo"
        }}
      ]
    }}
    """
    
    mock_model_service = MagicMock()
    mock_model_service.generate_content.return_value = mock_response
    
    mock_client_instance = MagicMock()
    mock_client_instance.models = mock_model_service
    mock_genai_client.return_value = mock_client_instance

    # Register and login user
    # Note: Using different email since Bob was registered in the previous test
    client.post(
        "/api/v1/auth/register",
        json={"name": "Alice", "email": "alice@example.com", "password": "SecurePassword123!"}
    )
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "SecurePassword123!"}
    )
    token = login_resp.json()["session_token"]

    # Call generate plan API
    client.post(
        "/api/v1/plans/generate",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "weekly_volume_miles": 10.0,
            "runs_per_week": 2,
            "long_run_day": "Sunday",
            "unavailable_days": "Monday",
            "race_name": "Local 5K",
            "race_date": (date.today() + timedelta(days=15)).isoformat(),
            "race_distance": "5k",
            "style": "balanced"
        }
    )

    # Get active plan sessions
    active_resp = client.get(
        "/api/v1/plans/active",
        headers={"Authorization": f"Bearer {token}"}
    )
    sessions = active_resp.json()["sessions"]
    
    easy_session = next(s for s in sessions if s["type"] == "Easy")
    tempo_session = next(s for s in sessions if s["type"] == "Tempo")

    # Move easy session to the date of tempo session (which is day_after)
    # This should trigger a swap: easy session moves to day_after, tempo session moves to tomorrow
    swap_resp = client.post(
        "/api/v1/plans/sessions/move",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "session_id": easy_session["id"],
            "new_date": day_after.isoformat()
        }
    )
    assert swap_resp.status_code == 200
    swap_data = swap_resp.json()
    assert swap_data["status"] == "success"
    assert swap_data["swapped"] is True
    assert swap_data["swapped_session_id"] == tempo_session["id"]
    assert swap_data["swapped_session_new_date"] == tomorrow.isoformat()

    # Verify both dates updated in DB
    active_resp_after = client.get(
        "/api/v1/plans/active",
        headers={"Authorization": f"Bearer {token}"}
    )
    sessions_after = active_resp_after.json()["sessions"]
    easy_after = next(s for s in sessions_after if s["id"] == easy_session["id"])
    tempo_after = next(s for s in sessions_after if s["id"] == tempo_session["id"])
    
    assert easy_after["date"] == day_after.isoformat()
    assert tempo_after["date"] == tomorrow.isoformat()
