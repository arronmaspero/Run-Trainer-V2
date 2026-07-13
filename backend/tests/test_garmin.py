import json
from datetime import datetime, timedelta, date
from unittest.mock import patch, MagicMock
from src.services.garmin_formatter import format_garmin_workout
from src.services.garmin_service import encrypt_password, decrypt_password
from src.models.activity import ConnectedAccount
from src.models.plan import TrainingPlan, TrainingSession

def test_format_garmin_workout_success():
    name = "Tempo Threshold Intervals"
    warm_up = ["Jog 10 minutes slowly", "Execute 3x100m strides"]
    main_set = ["Repeat 3 times: Run 6 mins at tempo, recovery 2 mins jog"]
    cool_down = ["Jog 5 minutes slowly"]
    
    result = format_garmin_workout(
        name=name,
        warm_up=warm_up,
        main_set=main_set,
        cool_down=cool_down,
        target_pace_range="7:25-7:40",
        target_hr_zone="Zone 3",
        target_rpe=7
    )
    
    assert "Tempo Threshold Intervals" in result
    assert "Jog 10 minutes slowly" in result
    assert "Repeat 3 times: Run 6 mins at tempo" in result
    assert "7:25-7:40" in result
    assert "Zone 3" in result
    assert "RPE" in result

def test_format_garmin_workout_empty_sets():
    result = format_garmin_workout(
        name="Easy Run",
        warm_up=[],
        main_set=[],
        cool_down=[]
    )
    assert "Warm Up: 5-10 minutes easy jogging." in result
    assert "Run: Steady pace." in result
    assert "Cool Down: 5-10 minutes easy recovery jog." in result

# -------------------------------------------------------------
# Garmin Service Integration Tests
# -------------------------------------------------------------

def test_garmin_encryption_decryption():
    raw_password = "SecretGarminPassword123!"
    encrypted = encrypt_password(raw_password)
    assert encrypted != raw_password
    
    decrypted = decrypt_password(encrypted)
    assert decrypted == raw_password

@patch("src.services.garmin_service.Garmin")
def test_connect_garmin_endpoint_success(mock_garmin, client, db):
    # Mock Garmin Connect client login
    mock_instance = MagicMock()
    mock_garmin.return_value = mock_instance
    
    # Register and login user
    client.post(
        "/api/v1/auth/register",
        json={"name": "Steve", "email": "steve@example.com", "password": "SecurePassword123!"}
    )
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "steve@example.com", "password": "SecurePassword123!"}
    )
    token = login_resp.json()["session_token"]
    user_id = login_resp.json()["user"]["id"]
    
    # Test POST connect credentials
    resp = client.post(
        "/api/v1/settings/garmin",
        json={"email": "steve@example.com", "password": "GarminPassword123"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"
    
    # Verify DB record
    account = db.query(ConnectedAccount).filter(
        ConnectedAccount.user_id == user_id,
        ConnectedAccount.provider == "garmin"
    ).first()
    
    assert account is not None
    assert account.access_token == "steve@example.com"
    assert decrypt_password(account.refresh_token) == "GarminPassword123"

@patch("src.services.garmin_service.Garmin")
def test_connect_garmin_endpoint_failure(mock_garmin, client):
    # Simulate a login exception
    mock_garmin.side_effect = Exception("Invalid username or password")
    
    client.post(
        "/api/v1/auth/register",
        json={"name": "Steve", "email": "steve@example.com", "password": "SecurePassword123!"}
    )
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "steve@example.com", "password": "SecurePassword123!"}
    )
    token = login_resp.json()["session_token"]
    
    resp = client.post(
        "/api/v1/settings/garmin",
        json={"email": "steve@example.com", "password": "WrongPassword"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 400
    assert "Invalid username or password" in resp.json()["detail"]

def test_disconnect_garmin_endpoint(client, db):
    client.post(
        "/api/v1/auth/register",
        json={"name": "Steve", "email": "steve@example.com", "password": "SecurePassword123!"}
    )
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "steve@example.com", "password": "SecurePassword123!"}
    )
    token = login_resp.json()["session_token"]
    user_id = login_resp.json()["user"]["id"]
    
    # Setup record manually
    account = ConnectedAccount(
        user_id=user_id,
        provider="garmin",
        access_token="steve@example.com",
        refresh_token=encrypt_password("Garmin123"),
        expires_at=datetime.utcnow() + timedelta(days=365)
    )
    db.add(account)
    db.commit()
    
    # Revoke credentials
    resp = client.delete(
        "/api/v1/settings/garmin",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"
    
    # Verify deletion
    acc = db.query(ConnectedAccount).filter(
        ConnectedAccount.user_id == user_id,
        ConnectedAccount.provider == "garmin"
    ).first()
    assert acc is None

@patch("src.services.garmin_service.Garmin")
@patch("src.services.garmin_service.get_gemini_client")
def test_sync_to_garmin_endpoint_success(mock_get_gemini, mock_garmin, client, db):
    # Mock Garmin client
    mock_instance = MagicMock()
    mock_instance.upload_workout.return_value = {"workoutId": 9999}
    mock_instance.get_scheduled_workouts.return_value = [
        {
            "calendarDate": (date.today() + timedelta(days=1)).isoformat(),
            "workoutScheduleId": 8888,
            "description": "AuraRun: 30 mins recovery run"
        }
    ]
    mock_instance.unschedule_workout.return_value = {}
    mock_garmin.return_value = mock_instance
    
    # Mock Gemini client
    mock_client_instance = MagicMock()
    mock_get_gemini.return_value = mock_client_instance
    
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "workouts": [
            {
                "session_id": "session-1",
                "workoutName": "EasyRun",
                "description": "30 mins recovery run",
                "estimatedDurationInSecs": 1800,
                "steps": [
                    {
                        "is_repeat_group": False,
                        "step_type": "warmup",
                        "end_condition": "lap_button",
                        "end_condition_value": 0.0,
                        "target_type": "no_target",
                        "target_value_low": 0.0,
                        "target_value_high": 0.0,
                        "description": "Warmup"
                    },
                    {
                        "is_repeat_group": False,
                        "step_type": "interval",
                        "end_condition": "time",
                        "end_condition_value": 1800.0,
                        "target_type": "no_target",
                        "target_value_low": 0.0,
                        "target_value_high": 0.0,
                        "description": "Steady run"
                    }
                ]
            }
        ]
    })
    
    mock_model_service = MagicMock()
    mock_model_service.generate_content.return_value = mock_response
    mock_client_instance.models = mock_model_service
    
    # Setup user
    client.post(
        "/api/v1/auth/register",
        json={"name": "Steve", "email": "steve@example.com", "password": "SecurePassword123!"}
    )
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "steve@example.com", "password": "SecurePassword123!"}
    )
    token = login_resp.json()["session_token"]
    user_id = login_resp.json()["user"]["id"]
    
    # Save Garmin Credentials in DB
    account = ConnectedAccount(
        user_id=user_id,
        provider="garmin",
        access_token="steve@example.com",
        refresh_token=encrypt_password("Garmin123"),
        expires_at=datetime.utcnow() + timedelta(days=365)
    )
    db.add(account)
    
    # Add active plan & future session
    plan = TrainingPlan(
        id="plan-1",
        user_id=user_id,
        race_name="Local 10K",
        race_distance_miles=6.2,
        start_date=date.today(),
        end_date=date.today() + timedelta(weeks=12),
        status="active"
    )
    db.add(plan)
    
    session = TrainingSession(
        id="session-1",
        plan_id="plan-1",
        date=date.today() + timedelta(days=1),
        type="Intervals",
        name="Easy Run",
        description="Run easy for 30 minutes",
        duration_minutes=30,
        distance_miles=3.0,
        status="planned"
    )
    db.add(session)
    db.commit()
    
    # Sync plan workouts to Garmin Connect calendar
    resp = client.post(
        "/api/v1/plans/push-garmin",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"
    assert resp.json()["synced_count"] == 1
    assert "Successfully pushed 1 structured running workouts" in resp.json()["message"]
    
    # Assert calendar cleaning unscheduled old AuraRun workouts
    # (called multiple times as we sweep all months of the plan)
    mock_instance.unschedule_workout.assert_called_with(8888)
