import json
from datetime import datetime, timedelta
from src.models.user import User, AthleteProfile
from src.models.activity import ConnectedAccount

def test_revoke_strava_success(client, db):
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

    # Setup a ConnectedAccount record in DB
    account = ConnectedAccount(
        user_id=user_id,
        provider="strava",
        access_token="fake_access",
        refresh_token="fake_refresh",
        expires_at=datetime.utcnow() + timedelta(hours=1)
    )
    db.add(account)
    db.commit()

    # Call revoke endpoint
    revoke_resp = client.delete(
        "/api/v1/settings/strava",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert revoke_resp.status_code == 200
    assert revoke_resp.json()["status"] == "success"

    # Verify ConnectedAccount is deleted from DB
    remaining_accounts = db.query(ConnectedAccount).filter(
        ConnectedAccount.user_id == user_id
    ).all()
    assert len(remaining_accounts) == 0

def test_export_data_success(client):
    client.post(
        "/api/v1/auth/register",
        json={"name": "Steve", "email": "steve@example.com", "password": "SecurePassword123!"}
    )
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "steve@example.com", "password": "SecurePassword123!"}
    )
    token = login_resp.json()["session_token"]

    export_resp = client.get(
        "/api/v1/settings/export",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert export_resp.status_code == 200
    data = export_resp.json()
    assert "user" in data
    assert data["user"]["name"] == "Steve"
    assert data["user"]["email"] == "steve@example.com"
    assert "profile" in data
    assert "connected_accounts" in data
    assert "activities" in data
    assert "plans" in data

def test_delete_account_success(client, db):
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

    delete_resp = client.delete(
        "/api/v1/settings/account",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert delete_resp.status_code == 200
    assert delete_resp.json()["status"] == "success"

    # Verify user record is deleted
    deleted_user = db.query(User).filter(User.id == user_id).first()
    assert deleted_user is None
