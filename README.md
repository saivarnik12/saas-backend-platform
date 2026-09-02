# SaaS Backend Platform

A production-ready, multi-tenant SaaS backend built with **FastAPI**, **PostgreSQL**, **JWT authentication**, and **Stripe billing**. Every organization (tenant) that signs up gets its own isolated users, roles, and subscription — the core pattern behind most B2B SaaS products.

## Features

- **Multi-tenancy** — each signup creates an isolated `Tenant` (organization); all data is scoped to it.
- **JWT authentication** — short-lived access tokens + long-lived refresh tokens.
- **Role-based access control** — `owner` / `admin` / `member` roles enforced on protected endpoints.
- **Stripe billing** — hosted Checkout sessions for Pro/Enterprise plans, with webhook handling to keep subscription status in sync.
- **Alembic migrations** — versioned, reproducible schema changes.
- **Dockerized** — one command to run the full stack (API + PostgreSQL) locally or in production.
- **CI pipeline** — GitHub Actions runs the full test suite and validates migrations on every push.
- **19 passing automated tests** covering auth, RBAC, tenants, and billing (Stripe calls are mocked — no real network calls in tests).

## Tech Stack

| Layer      | Technology                          |
|------------|--------------------------------------|
| API        | FastAPI + Uvicorn                   |
| Database   | PostgreSQL (SQLite works for quick local testing) |
| ORM        | SQLAlchemy 2.0 + Alembic            |
| Auth       | JWT (python-jose) + bcrypt (passlib) |
| Billing    | Stripe Checkout + Webhooks          |
| Testing    | pytest + httpx TestClient           |
| Containers | Docker + Docker Compose             |
| CI         | GitHub Actions                      |

## Project Structure

```
app/
├── main.py                # FastAPI app, middleware, exception handlers
├── core/
│   ├── config.py           # Settings (env-driven)
│   ├── database.py         # SQLAlchemy engine/session
│   └── security.py         # Password hashing + JWT
├── models/                 # SQLAlchemy ORM models (Tenant, User, Subscription)
├── schemas/                 # Pydantic request/response schemas
├── services/                # Business logic (auth, users, billing)
└── api/
    ├── deps.py              # Auth dependencies + RBAC guard
    └── routes/               # auth, users, tenants, billing routers
alembic/                    # Migration environment + versions
tests/                      # Full pytest suite (19 tests)
```

## Quick Start (Docker — recommended)

```bash
git clone <your-repo-url>
cd saas-backend-platform
cp .env.example .env        # edit values, especially SECRET_KEY and Stripe keys
docker compose up --build
```

The API will be available at `http://localhost:8000`, with interactive docs at `http://localhost:8000/docs`. Migrations run automatically on container start.

## Quick Start (local, without Docker)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# For a quick local run without Postgres, set in .env:
# DATABASE_URL=sqlite:///./app.db

alembic upgrade head
uvicorn app.main:app --reload
```

## Running Tests

```bash
pip install -r requirements.txt
pytest -v
```

All Stripe calls are mocked in tests (`unittest.mock.patch`), so the suite runs offline with no real Stripe account needed.

## API Overview

| Method | Endpoint                              | Description                              | Auth required |
|--------|----------------------------------------|-------------------------------------------|----------------|
| POST   | `/api/v1/auth/signup`                  | Create a new tenant + owner user          | No             |
| POST   | `/api/v1/auth/login`                   | Log in, get access + refresh tokens       | No             |
| POST   | `/api/v1/auth/refresh`                 | Exchange a refresh token for a new access token | No       |
| GET    | `/api/v1/users/me`                     | Get the current user                      | Yes            |
| GET    | `/api/v1/users`                        | List all users in your tenant             | Yes            |
| POST   | `/api/v1/users/invite`                 | Invite a new user to your tenant          | Owner/Admin    |
| POST   | `/api/v1/users/{id}/deactivate`        | Deactivate a user                         | Owner/Admin    |
| GET    | `/api/v1/tenants/me`                   | Get current tenant/organization info      | Yes            |
| POST   | `/api/v1/billing/checkout-session`     | Create a Stripe Checkout session          | Owner/Admin    |
| GET    | `/api/v1/billing/subscription`         | Get current subscription status           | Yes            |
| POST   | `/api/v1/billing/webhook`               | Stripe webhook receiver                   | Stripe only (signature-verified) |
| GET    | `/health`                              | Health check                              | No             |

Full interactive documentation (request/response schemas, try-it-out) is auto-generated at `/docs` (Swagger UI) and `/redoc`.

## Configuring Stripe

1. Create a [Stripe account](https://dashboard.stripe.com) and switch to **test mode**.
2. Create two recurring Prices (Products → Add Product) for your Pro and Enterprise plans; copy their price IDs into `.env` as `STRIPE_PRICE_ID_PRO` / `STRIPE_PRICE_ID_ENTERPRISE`.
3. Copy your test **Secret key** into `STRIPE_SECRET_KEY`.
4. For webhooks locally, use the [Stripe CLI](https://stripe.com/docs/stripe-cli): `stripe listen --forward-to localhost:8000/api/v1/billing/webhook`, then copy the printed signing secret into `STRIPE_WEBHOOK_SECRET`.

## Deploying to Production

This repo is deployable as-is to any container platform:

- **Railway / Render / Fly.io**: point the platform at this repo, it will build the `Dockerfile`. Provision a managed Postgres add-on and set `DATABASE_URL` accordingly. Migrations run automatically via the container's `CMD`.
- **AWS ECS / GCP Cloud Run**: build and push the image (`docker build -t your-registry/saas-backend .`), provision a managed Postgres instance (RDS / Cloud SQL), and set the environment variables from `.env.example` as secrets.
- **Any VPS**: `docker compose up -d --build` and put a reverse proxy (Caddy/Nginx) in front for TLS.

Before going to production, make sure you:
- Set a strong random `SECRET_KEY` (`openssl rand -hex 32`).
- Use your live Stripe keys (not test keys) and register your production webhook URL in the Stripe dashboard.
- Restrict `CORS_ORIGINS` to your actual frontend domain(s).
- Put the API behind HTTPS.

## License

MIT — see [LICENSE](LICENSE).

## License

Copyright � 2026 Kammari Sai Varnik.

This project is proprietary and provided for portfolio and evaluation purposes only.

Viewing the source code is permitted for evaluation purposes.
You may not copy, modify, distribute, publish, sublicense,
or use this code or substantial portions of it in another
project without explicit written permission from the author.
