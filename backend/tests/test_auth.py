import uuid
import pytest

def test_login_success(client):
    res = client.post("/api/v1/auth/login", json={
        "email": "candidate@example.com",
        "password": "Candidate@123456"
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["user"]["email"] == "candidate@example.com"

def test_login_invalid_password(client):
    res = client.post("/api/v1/auth/login", json={
        "email": "candidate@example.com",
        "password": "WrongPassword999"
    })
    assert res.status_code == 401

def test_register_weak_password_rejected(client):
    res = client.post("/api/v1/auth/register", json={
        "email": "short_pw@test.com",
        "password": "123"  # too short (< 8 chars)
    })
    assert res.status_code == 422

def test_register_and_profile_flow(client):
    unique_email = f"user_{uuid.uuid4().hex[:8]}@test.com"
    res = client.post("/api/v1/auth/register", json={
        "email": unique_email,
        "password": "StrongPassword@123"
    })
    assert res.status_code == 201
    user_data = res.json()
    assert user_data["email"] == unique_email

    # Login with new account
    login_res = client.post("/api/v1/auth/login", json={
        "email": unique_email,
        "password": "StrongPassword@123"
    })
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]

    # Verify profile creation
    prof_res = client.get("/api/v1/profile", headers={"Authorization": f"Bearer {token}"})
    assert prof_res.status_code == 200
    profile = prof_res.json()
    assert profile["profile_completion_pct"] >= 10

    # Update profile
    update_res = client.patch("/api/v1/profile", headers={"Authorization": f"Bearer {token}"}, json={
        "full_name": "Test Tester",
        "headline": "Fullstack Cloud Dev",
        "skills": ["Python", "React", "Docker"]
    })
    assert update_res.status_code == 200
    updated_profile = update_res.json()
    assert updated_profile["full_name"] == "Test Tester"
    assert "Python" in updated_profile["skills"]
    assert updated_profile["profile_completion_pct"] > profile["profile_completion_pct"]

def test_password_reset_flow(client):
    # 1. Request reset
    req_res = client.post("/api/v1/auth/password-reset/request", json={
        "email": "candidate@example.com"
    })
    assert req_res.status_code == 200
    token = req_res.json()["token"]
    assert token

    # 2. Confirm reset
    conf_res = client.post("/api/v1/auth/password-reset/confirm", json={
        "token": token,
        "new_password": "Candidate@123456"  # restore password
    })
    assert conf_res.status_code == 200

    # 3. PRD 4.1 Security Acceptance: Token cannot be reused
    reuse_res = client.post("/api/v1/auth/password-reset/confirm", json={
        "token": token,
        "new_password": "HackerPassword@123"
    })
    assert reuse_res.status_code == 400
    assert "already been used" in reuse_res.json()["detail"].lower()

def test_oauth2_form_token_login_success(client):
    # Form data request as sent by Swagger UI Authorize dialog
    res = client.post("/api/v1/auth/token", data={
        "username": "candidate@example.com",
        "password": "Candidate@123456"
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "candidate@example.com"

    # Verify token can access protected endpoint
    me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {data['access_token']}"})
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "candidate@example.com"

def test_oauth2_form_token_login_invalid_password(client):
    res = client.post("/api/v1/auth/token", data={
        "username": "candidate@example.com",
        "password": "WrongPassword999"
    })
    assert res.status_code == 401
    assert "Incorrect email or password" in res.json()["detail"]

def test_openapi_security_scheme_token_url(client):
    # Verify Swagger /api/openapi.json points to /api/v1/auth/token
    res = client.get("/api/openapi.json")
    assert res.status_code == 200
    spec = res.json()
    schemes = spec.get("components", {}).get("securitySchemes", {})
    assert "OAuth2PasswordBearer" in schemes
    flow = schemes["OAuth2PasswordBearer"].get("flows", {}).get("password", {})
    assert flow.get("tokenUrl") == "/api/v1/auth/token"

def test_admin_oauth2_form_token_login_and_access(client):
    res = client.post("/api/v1/auth/token", data={
        "username": "admin@jobplatform.com",
        "password": "Admin@123456"
    })
    assert res.status_code == 200
    token = res.json()["access_token"]

    # Verify authorized admin access works
    admin_res = client.get("/api/v1/admin/health", headers={"Authorization": f"Bearer {token}"})
    assert admin_res.status_code == 200
