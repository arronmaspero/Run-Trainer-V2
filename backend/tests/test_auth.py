def test_register_user_success(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"name": "Alice", "email": "alice@example.com", "password": "SecurePassword123!"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Alice"
    assert data["email"] == "alice@example.com"
    assert "id" in data
    assert "password_hash" not in data

def test_register_duplicate_email_fails(client):
    # Register once
    client.post(
        "/api/v1/auth/register",
        json={"name": "Alice", "email": "alice@example.com", "password": "SecurePassword123!"}
    )
    # Register twice
    response = client.post(
        "/api/v1/auth/register",
        json={"name": "Alice Duplicate", "email": "alice@example.com", "password": "AnotherPassword456!"}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Email is already registered"

def test_login_success(client):
    # Register
    client.post(
        "/api/v1/auth/register",
        json={"name": "Alice", "email": "alice@example.com", "password": "SecurePassword123!"}
    )
    # Login
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "SecurePassword123!"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "session_token" in data
    assert data["user"]["name"] == "Alice"

def test_login_invalid_credentials_fails(client):
    # Login unregistered
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "wrong@example.com", "password": "BadPassword!"}
    )
    assert response.status_code == 401

def test_get_me_profile(client):
    # Register and login
    client.post(
        "/api/v1/auth/register",
        json={"name": "Alice", "email": "alice@example.com", "password": "SecurePassword123!"}
    )
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "SecurePassword123!"}
    )
    token = login_resp.json()["session_token"]
    
    # Get me
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["email"] == "alice@example.com"
