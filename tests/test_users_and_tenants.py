def test_get_current_tenant(client, auth_headers):
    response = client.get("/api/v1/tenants/me", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Acme Corp"
    assert body["plan"] == "free"


def test_owner_can_invite_user(client, auth_headers):
    response = client.post(
        "/api/v1/users/invite",
        headers=auth_headers,
        json={
            "email": "grace@acme.com",
            "full_name": "Grace Hopper",
            "password": "AnotherSecret123",
            "role": "member",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["role"] == "member"
    assert body["email"] == "grace@acme.com"


def test_list_users_includes_invited_member(client, auth_headers):
    client.post(
        "/api/v1/users/invite",
        headers=auth_headers,
        json={
            "email": "grace@acme.com",
            "full_name": "Grace Hopper",
            "password": "AnotherSecret123",
            "role": "member",
        },
    )
    response = client.get("/api/v1/users", headers=auth_headers)
    assert response.status_code == 200
    emails = {u["email"] for u in response.json()}
    assert {"owner@acme.com", "grace@acme.com"} == emails


def test_member_cannot_invite_users(client, auth_headers):
    # Create a member user, then log in as them and confirm they lack invite permission.
    client.post(
        "/api/v1/users/invite",
        headers=auth_headers,
        json={
            "email": "regular.member@acme.com",
            "full_name": "Regular Member",
            "password": "MemberSecret123",
            "role": "member",
        },
    )
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "regular.member@acme.com", "password": "MemberSecret123"},
    )
    member_token = login_response.json()["access_token"]
    member_headers = {"Authorization": f"Bearer {member_token}"}

    response = client.post(
        "/api/v1/users/invite",
        headers=member_headers,
        json={
            "email": "someone.else@acme.com",
            "full_name": "Someone Else",
            "password": "SomeSecret123",
            "role": "member",
        },
    )
    assert response.status_code == 403


def test_deactivate_user(client, auth_headers):
    invite_response = client.post(
        "/api/v1/users/invite",
        headers=auth_headers,
        json={
            "email": "grace@acme.com",
            "full_name": "Grace Hopper",
            "password": "AnotherSecret123",
            "role": "member",
        },
    )
    user_id = invite_response.json()["id"]

    response = client.post(f"/api/v1/users/{user_id}/deactivate", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["is_active"] is False

    # Deactivated user can no longer log in.
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "grace@acme.com", "password": "AnotherSecret123"},
    )
    assert login_response.status_code == 403
