def test_signup_creates_tenant_and_owner(client, signup_payload):
    response = client.post("/api/v1/auth/signup", json=signup_payload)
    assert response.status_code == 201
    body = response.json()
    assert "access_token" in body
    assert "refresh_token" in body


def test_signup_duplicate_email_rejected(client, signup_payload):
    client.post("/api/v1/auth/signup", json=signup_payload)
    response = client.post("/api/v1/auth/signup", json=signup_payload)
    assert response.status_code == 409


def test_signup_weak_password_rejected(client, signup_payload):
    signup_payload["password"] = "short"
    response = client.post("/api/v1/auth/signup", json=signup_payload)
    assert response.status_code == 422


def test_login_success(client, signup_payload):
    client.post("/api/v1/auth/signup", json=signup_payload)
    response = client.post(
        "/api/v1/auth/login",
        json={"email": signup_payload["email"], "password": signup_payload["password"]},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_wrong_password(client, signup_payload):
    client.post("/api/v1/auth/signup", json=signup_payload)
    response = client.post(
        "/api/v1/auth/login",
        json={"email": signup_payload["email"], "password": "WrongPassword123"},
    )
    assert response.status_code == 401


def test_refresh_token_returns_new_access_token(client, signup_payload):
    signup_response = client.post("/api/v1/auth/signup", json=signup_payload)
    refresh_token = signup_response.json()["refresh_token"]

    response = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_refresh_rejects_access_token(client, signup_payload):
    signup_response = client.post("/api/v1/auth/signup", json=signup_payload)
    access_token = signup_response.json()["access_token"]

    # Using an access token where a refresh token is expected must fail.
    response = client.post("/api/v1/auth/refresh", json={"refresh_token": access_token})
    assert response.status_code == 401


def test_me_requires_auth(client):
    response = client.get("/api/v1/users/me")
    assert response.status_code in (401, 403)


def test_me_returns_current_user(client, auth_headers):
    response = client.get("/api/v1/users/me", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "owner@acme.com"
    assert body["role"] == "owner"
