from unittest.mock import MagicMock, patch


def test_free_plan_rejects_checkout(client, auth_headers):
    response = client.post(
        "/api/v1/billing/checkout-session",
        headers=auth_headers,
        json={"plan": "free"},
    )
    assert response.status_code == 400


@patch("app.services.billing_service.stripe.checkout.Session.create")
@patch("app.services.billing_service.stripe.Customer.create")
def test_create_checkout_session_for_pro_plan(mock_customer_create, mock_session_create, client, auth_headers):
    mock_customer_create.return_value = {"id": "cus_test123"}
    mock_session_create.return_value = {"url": "https://checkout.stripe.com/test-session"}

    response = client.post(
        "/api/v1/billing/checkout-session",
        headers=auth_headers,
        json={"plan": "pro"},
    )
    assert response.status_code == 200
    assert response.json()["checkout_url"] == "https://checkout.stripe.com/test-session"
    mock_customer_create.assert_called_once()
    mock_session_create.assert_called_once()


def test_member_cannot_create_checkout_session(client, auth_headers):
    invite_response = client.post(
        "/api/v1/users/invite",
        headers=auth_headers,
        json={
            "email": "regular.member@acme.com",
            "full_name": "Regular Member",
            "password": "MemberSecret123",
            "role": "member",
        },
    )
    assert invite_response.status_code == 201

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "regular.member@acme.com", "password": "MemberSecret123"},
    )
    member_headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

    response = client.post(
        "/api/v1/billing/checkout-session",
        headers=member_headers,
        json={"plan": "pro"},
    )
    assert response.status_code == 403


@patch("app.services.billing_service.stripe.Webhook.construct_event")
def test_webhook_checkout_completed_upgrades_tenant_plan(mock_construct_event, client, auth_headers):
    tenant_response = client.get("/api/v1/tenants/me", headers=auth_headers)
    tenant_id = tenant_response.json()["id"]

    mock_construct_event.return_value = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "metadata": {"tenant_id": tenant_id, "plan": "pro"},
                "subscription": "sub_test123",
            }
        },
    }

    response = client.post(
        "/api/v1/billing/webhook",
        headers={"stripe-signature": "test_signature"},
        content=b"{}",
    )
    assert response.status_code == 200

    tenant_response = client.get("/api/v1/tenants/me", headers=auth_headers)
    assert tenant_response.json()["plan"] == "pro"

    sub_response = client.get("/api/v1/billing/subscription", headers=auth_headers)
    assert sub_response.json()["status"] == "active"


def test_webhook_missing_signature_rejected(client):
    response = client.post("/api/v1/billing/webhook", content=b"{}")
    assert response.status_code == 400
