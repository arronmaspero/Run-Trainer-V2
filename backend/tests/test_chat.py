from datetime import date, timedelta
from unittest.mock import patch, MagicMock
from src.models.plan import TrainingPlan, TrainingSession

@patch("src.services.coach_chat_service.get_gemini_client")
def test_coach_chat_endpoints(mock_get_gemini, client, db):
    # 1. Register and login user
    client.post(
        "/api/v1/auth/register",
        json={"name": "ChatRunner", "email": "chat@example.com", "password": "SecurePassword123!"}
    )
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "chat@example.com", "password": "SecurePassword123!"}
    )
    token = login_resp.json()["session_token"]
    user_id = login_resp.json()["user"]["id"]

    # 2. Add an active plan
    plan = TrainingPlan(
        id="plan-chat-1",
        user_id=user_id,
        race_name="City 10K",
        race_distance_miles=6.2,
        start_date=date.today(),
        end_date=date.today() + timedelta(weeks=4),
        status="active"
    )
    db.add(plan)

    session = TrainingSession(
        id="session-chat-1",
        plan_id="plan-chat-1",
        date=date.today() + timedelta(days=1),
        type="Tempo",
        name="Tempo Run",
        description="Run 4 miles at tempo pace",
        duration_minutes=40,
        distance_miles=4.0,
        status="planned"
    )
    db.add(session)
    db.commit()

    # 3. Test empty chat history GET
    hist_resp = client.get(
        "/api/v1/chat/history",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert hist_resp.status_code == 200
    assert hist_resp.json()["status"] == "success"
    assert hist_resp.json()["messages"] == []

    # 4. Mock Gemini response
    mock_response = MagicMock()
    mock_response.text = "Great job! I propose we adjust your Thursday workouts to be 20% lighter to aid recovery."
    mock_model_service = MagicMock()
    mock_model_service.generate_content.return_value = mock_response
    mock_client_instance = MagicMock()
    mock_client_instance.models = mock_model_service
    mock_get_gemini.return_value = mock_client_instance

    # 5. Send chat message POST
    msg_resp = client.post(
        "/api/v1/chat/message",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "I feel tired on Thursdays, can we make Thursdays lighter?"}
    )
    assert msg_resp.status_code == 200
    res_data = msg_resp.json()
    assert res_data["status"] == "success"
    assert res_data["reply"]["sender"] == "coach"
    assert "Thursday" in res_data["reply"]["text"]
    assert res_data["reply"]["has_proposed_changes"] is True

    # 6. Verify history now contains 2 messages (user + coach)
    hist_resp2 = client.get(
        "/api/v1/chat/history",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert hist_resp2.status_code == 200
    assert len(hist_resp2.json()["messages"]) == 2
    assert hist_resp2.json()["messages"][0]["sender"] == "user"
    assert hist_resp2.json()["messages"][1]["sender"] == "coach"
