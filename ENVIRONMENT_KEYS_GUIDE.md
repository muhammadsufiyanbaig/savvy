# Savvy — Environment Keys & Configuration Guide

All keys you need, where to get them, and which `.env` file to put them in.

---

## 1. Master Root File — `microservices/.env`

This file feeds Docker Compose. All services inherit from it.

```
microservices/.env
```

### 1.1 JWT Secret Key

| Variable | `SECRET_KEY` |
|----------|-------------|
| **Used by** | ALL 7 services (must be identical everywhere) |
| **Where to get** | Generate yourself — run this in terminal: |

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Set same value in:
- `microservices/.env` → `SECRET_KEY=<generated>`
- `microservices/api-gateway/.env` → `SECRET_KEY=<same>`
- `microservices/user-service/.env` → `SECRET_KEY=<same>`
- `microservices/finance-service/.env` → `SECRET_KEY=<same>`
- `microservices/notification-service/.env` → `SECRET_KEY=<same>`

> **IMPORTANT:** All services share one SECRET_KEY. If they differ, JWT auth breaks — users get 401 on every request.

---

### 1.2 Anthropic API Key (Claude AI)

| Variable | `ANTHROPIC_API_KEY` |
|----------|---------------------|
| **Used by** | `ai-recommendation-service`, `statement-analysis-service` |
| **How to get** | Go to: https://console.anthropic.com → API Keys → Create Key |
| **Cost** | Pay-per-token. Sonnet ~$3/MTok input, $15/MTok output |

Set in:
- `microservices/.env` → `ANTHROPIC_API_KEY=sk-ant-api03-...`

Features disabled without this key:
- AI spending recommendations
- Budget optimization insights
- Statement transaction extraction (falls back to rule-based)

---

### 1.3 AWS S3 (Bank Statement Storage)

| Variable | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`, `AWS_S3_BUCKET` |
|----------|-------------|
| **Used by** | `statement-analysis-service` |
| **How to get** | AWS Console → IAM → Users → Create User → Attach `AmazonS3FullAccess` policy → Security credentials → Create access key |
| **S3 Bucket** | AWS Console → S3 → Create bucket → name it `savvy-bank-statements` (or any name, then set `AWS_S3_BUCKET` to match) |

```
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI...
AWS_REGION=us-east-1
AWS_S3_BUCKET=savvy-bank-statements
```

Set in: `microservices/.env`

Features disabled without this:
- Bank statement PDF/CSV upload
- Statement storage and retrieval

---

### 1.4 OpenAI API Key (Optional fallback)

| Variable | `OPENAI_API_KEY` |
|----------|-----------------|
| **Used by** | `statement-analysis-service`, `ai-recommendation-service` (fallback only) |
| **How to get** | https://platform.openai.com → API Keys → Create new |
| **Optional?** | YES — only used if `AI_PROVIDER=openai` in statement service config |

Set in: `microservices/.env`

---

### 1.5 Alpha Vantage (Stock Market Data — Optional)

| Variable | `ALPHA_VANTAGE_API_KEY` |
|----------|------------------------|
| **Used by** | `ai-recommendation-service` (investment tips feature) |
| **How to get** | https://www.alphavantage.co/support/#api-key → Free tier available |
| **Optional?** | YES — without it, investment tips use basic Yahoo Finance only |

Set in: `microservices/.env` (not currently in file, add manually)  
Also set in: `microservices/ai-recommendation-service` `.env` if running locally

---

## 2. Email / SMTP — `notification-service`

| Variable | Where |
|----------|-------|
| `SMTP_HOST` | `microservices/.env` + `microservices/notification-service/.env` |
| `SMTP_PORT` | Same — default `587` |
| `SMTP_USERNAME` | Your email address |
| `SMTP_PASSWORD` | App password (NOT your login password) |
| `SMTP_FROM_EMAIL` | Sender address shown to users |

### Option A — Gmail SMTP

1. Google Account → Security → 2-Step Verification → ON
2. Google Account → Security → App Passwords → Generate
3. Use the 16-char app password as `SMTP_PASSWORD`

```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your.email@gmail.com
SMTP_PASSWORD=abcd efgh ijkl mnop    ← 16-char app password (no spaces)
SMTP_FROM_EMAIL=your.email@gmail.com
SMTP_FROM_NAME=Savvy
```

### Option B — Mailtrap (dev/testing only, free)

1. https://mailtrap.io → Sign up → Email Testing → Inbox → SMTP Settings

```
SMTP_HOST=sandbox.smtp.mailtrap.io
SMTP_PORT=2525
SMTP_USERNAME=<from mailtrap dashboard>
SMTP_PASSWORD=<from mailtrap dashboard>
```

Features disabled without SMTP:
- Budget alert emails
- Weekly spending summaries
- Email verification on register

---

## 3. Push Notifications — OneSignal (Optional)

| Variable | `ONESIGNAL_APP_ID`, `ONESIGNAL_API_KEY` |
|----------|----------------------------------------|
| **Used by** | `notification-service` |
| **How to get** | https://onesignal.com → Create app → Settings → Keys & IDs |
| **Optional?** | YES — notifications still work in-app without this (push to mobile/browser disabled) |

Set in: `microservices/.env` + `microservices/notification-service/.env`

---

## 4. Frontend — `frontend/.env.local`

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

| Variable | Value | Notes |
|----------|-------|-------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` (dev) | Change to your domain in prod e.g. `https://api.savvy.app` |

---

## 5. Summary Table — What's Required vs Optional

| Key | Required? | Without it... |
|-----|-----------|---------------|
| `SECRET_KEY` | **REQUIRED** | All auth breaks — 401 everywhere |
| `ANTHROPIC_API_KEY` | **Needed for AI features** | AI recommendations disabled, statement parsing falls to basic rules |
| `AWS_ACCESS_KEY_ID/SECRET` | **Needed for statements** | Bank statement upload fails |
| `AWS_S3_BUCKET` | **Needed for statements** | Same as above |
| `SMTP_*` | Optional | No email notifications |
| `OPENAI_API_KEY` | Optional | Claude used instead |
| `ALPHA_VANTAGE_API_KEY` | Optional | No investment tips |
| `ONESIGNAL_APP_ID/KEY` | Optional | No browser/mobile push |

---

## 6. Quick Setup Checklist (Minimum to Run)

```
[ ] Generate SECRET_KEY → set in ALL .env files (same value)
[ ] Get ANTHROPIC_API_KEY → set in microservices/.env
[ ] Set NEXT_PUBLIC_API_URL=http://localhost:8000 in frontend/.env.local
```

That's it for local dev. AI features work, auth works, expenses/budgets/savings work.

Optional for full feature set:
```
[ ] AWS keys → enables statement upload
[ ] SMTP config → enables email notifications
```

---

## 7. File Locations Quick Reference

```
Savvy/
├── microservices/
│   ├── .env                          ← MASTER (feeds docker-compose, all services)
│   ├── api-gateway/.env              ← gateway-specific overrides
│   ├── user-service/.env             ← user service local dev
│   ├── finance-service/.env          ← finance service local dev
│   └── notification-service/.env     ← SMTP / push keys here too
└── frontend/
    └── .env.local                    ← API URL for Next.js
```

> **Note:** `microservices/.env` is used by Docker Compose and overrides the per-service `.env` files when running via `docker compose up`. The per-service `.env` files are only used when running services directly with `uvicorn` outside Docker.
