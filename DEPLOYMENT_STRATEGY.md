# Savvy — Deployment Strategy
**Version:** 1.0  
**Updated:** 2026-06-20  

---

## Table of Contents
1. [Architecture Overview](#1-architecture-overview)
2. [Infrastructure Requirements](#2-infrastructure-requirements)
3. [Environment Variables — Complete Reference](#3-environment-variables--complete-reference)
4. [Secret Management](#4-secret-management)
5. [Local Development (Docker Compose)](#5-local-development-docker-compose)
6. [Production (Kubernetes)](#6-production-kubernetes)
7. [Database Migration Strategy](#7-database-migration-strategy)
8. [Service Startup Order](#8-service-startup-order)
9. [Health Checks](#9-health-checks)
10. [CI/CD Pipeline](#10-cicd-pipeline)

---

## 1. Architecture Overview

```
Internet
    │
    ▼
[Nginx / Load Balancer]  :443 / :80
    │
    ▼
[API Gateway]            :8000   ← single entry point, JWT validation, rate limiting
    │
    ├──▶ [User Service]          :8001  PostgreSQL + Redis/0 + Kafka
    ├──▶ [Finance Service]       :8002  PostgreSQL + Redis/1 + Kafka
    ├──▶ [Bank Service]          :8003  PostgreSQL + Kafka + S3
    ├──▶ [Statement Analysis]    :8004  Redis/5 + Kafka + ChromaDB + S3 + Claude AI
    ├──▶ [AI Recommendation]     :8005  Redis/6 + Kafka + ChromaDB + Claude AI
    └──▶ [Notification Service]  :8006  PostgreSQL + Redis/3 + Kafka + SMTP

[Frontend — Next.js]     :3000   (separate deployment / Vercel)

Infrastructure:
  PostgreSQL ×4    → user-db, finance-db, bank-db, notification-db
  Redis ×1         → shared, DB isolation per service (see DB mapping below)
  Kafka ×1         → shared message bus
  ChromaDB ×1      → vector store for AI services
```

**Redis DB Assignment (never change — services depend on these):**
| Service                   | Redis DB |
|---------------------------|----------|
| user-service              | /0       |
| finance-service           | /1       |
| notification-service      | /3       |
| api-gateway               | /4       |
| statement-analysis        | /5       |
| ai-recommendation         | /6       |

---

## 2. Infrastructure Requirements

### Minimum Production (single node)
| Component    | CPU   | RAM   | Storage |
|--------------|-------|-------|---------|
| API Gateway  | 0.2c  | 256Mi | —       |
| User Service | 0.2c  | 256Mi | —       |
| Finance Svc  | 0.3c  | 256Mi | —       |
| Bank Service | 0.2c  | 256Mi | —       |
| Stmt Analysis| 0.5c  | 512Mi | —       |
| AI Recommend | 0.5c  | 512Mi | —       |
| Notification | 0.2c  | 256Mi | —       |
| Frontend     | 0.2c  | 256Mi | —       |
| PostgreSQL×4 | 0.5c  | 1Gi   | 20Gi SSD|
| Redis        | 0.2c  | 512Mi | 5Gi     |
| Kafka+ZK     | 0.5c  | 1Gi   | 10Gi    |
| ChromaDB     | 0.2c  | 512Mi | 10Gi    |

### Recommended Production (HA)
- 3× app nodes (2 replicas each service)
- Managed PostgreSQL (RDS / CloudSQL) — NOT self-hosted in prod
- Managed Redis (ElastiCache / Upstash) — NOT self-hosted in prod
- Managed Kafka (Confluent Cloud / MSK)

---

## 3. Environment Variables — Complete Reference

> **Legend:**  
> 🔴 Required · 🟡 Optional but recommended · 🟢 Has safe default

---

### 3.1 Shared Variables (same value in ALL services)

| Variable     | Description                              | How to generate                                  |
|--------------|------------------------------------------|--------------------------------------------------|
| `SECRET_KEY` 🔴 | JWT signing secret (HS256). Min 32 chars. **Same across all services.** | `python -c "import secrets; print(secrets.token_hex(32))"` |
| `ALGORITHM`  🟢 | JWT algorithm. Default: `HS256`          | Keep default unless switching to RS256           |
| `ENVIRONMENT`🟢 | `development` / `staging` / `production` | Set `production` in prod — triggers SECRET_KEY guard |

---

### 3.2 API Gateway (:8000)

| Variable                  | Default                         | Description                              | Required |
|---------------------------|---------------------------------|------------------------------------------|----------|
| `SECRET_KEY`              | insecure default                | JWT decode secret — **same as all svcs** | 🔴        |
| `ENVIRONMENT`             | `development`                   | Set `production` in prod                 | 🔴        |
| `REDIS_URL`               | `redis://redis:6379/4`          | Rate limiter cache — must use DB /4      | 🔴        |
| `ALLOWED_ORIGINS`         | `["http://localhost:3000"]`     | CORS origins. In prod: `["https://app.savvy.com"]` | 🔴 |
| `USER_SERVICE_URL`        | `http://user-service:8001`      | Internal service URL                     | 🔴        |
| `FINANCE_SERVICE_URL`     | `http://finance-service:8002`   | Internal service URL                     | 🔴        |
| `BANK_SERVICE_URL`        | `http://bank-service:8003`      | Internal service URL                     | 🔴        |
| `STATEMENT_SERVICE_URL`   | `http://statement-analysis-service:8004` | Internal service URL            | 🔴        |
| `AI_SERVICE_URL`          | `http://ai-recommendation-service:8005` | Internal service URL             | 🔴        |
| `NOTIFICATION_SERVICE_URL`| `http://notification-service:8006` | Internal service URL                  | 🔴        |
| `RATE_LIMIT_AUTH`         | `300`                           | Requests/window for authenticated users  | 🟢        |
| `RATE_LIMIT_ANON`         | `60`                            | Requests/window for unauthenticated      | 🟢        |
| `RATE_LIMIT_WINDOW`       | `60`                            | Rate limit window in seconds             | 🟢        |

---

### 3.3 User Service (:8001)

| Variable                          | Default                                                      | Description                  | Required |
|-----------------------------------|--------------------------------------------------------------|------------------------------|----------|
| `SECRET_KEY`                      | insecure default                                             | JWT signing secret           | 🔴        |
| `ENVIRONMENT`                     | `development`                                                | Prod triggers key guard      | 🔴        |
| `DATABASE_URL`                    | `postgresql://user_service:user_password@user-db:5432/user_db` | Postgres connection string | 🔴        |
| `REDIS_URL`                       | `redis://redis:6379/0`                                       | Session/cache — must use /0  | 🔴        |
| `KAFKA_BOOTSTRAP_SERVERS`         | `kafka:9092`                                                 | Kafka broker address         | 🔴        |
| `KAFKA_TOPIC_PREFIX`              | `financial_`                                                 | Prefix for all topics        | 🟢        |
| `KAFKA_GROUP_ID`                  | `user-service-group`                                         | Consumer group ID            | 🟢        |
| `ACCESS_TOKEN_EXPIRE_MINUTES`     | `30`                                                         | JWT access token TTL         | 🟢        |
| `REFRESH_TOKEN_EXPIRE_DAYS`       | `7`                                                          | JWT refresh token TTL        | 🟢        |
| `EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS` | `24`                                                   | Email verify token TTL       | 🟢        |
| `ALLOWED_ORIGINS`                 | `["http://localhost:3000"]`                                  | CORS                         | 🔴        |

---

### 3.4 Finance Service (:8002)

| Variable                     | Default                                                             | Description                  | Required |
|------------------------------|---------------------------------------------------------------------|------------------------------|----------|
| `SECRET_KEY`                 | insecure default                                                    | JWT decode secret            | 🔴        |
| `ENVIRONMENT`                | `development`                                                       | Prod triggers key guard      | 🔴        |
| `DATABASE_URL`               | `postgresql://finance_service:finance_password@finance-db:5432/finance_db` | Postgres             | 🔴        |
| `REDIS_URL`                  | `redis://redis:6379/1`                                              | Cache — must use /1          | 🔴        |
| `KAFKA_BOOTSTRAP_SERVERS`    | `kafka:9092`                                                        | Kafka broker                 | 🔴        |
| `KAFKA_TOPIC_PREFIX`         | `financial_`                                                        | Topic prefix                 | 🟢        |
| `KAFKA_GROUP_ID`             | `finance-service-group`                                             | Consumer group               | 🟢        |
| `USER_SERVICE_URL`           | `http://user-service:8001`                                          | Internal URL                 | 🔴        |
| `NOTIFICATION_SERVICE_URL`   | `http://notification-service:8006`                                  | Internal URL                 | 🔴        |
| `AI_SERVICE_URL`             | `http://ai-recommendation-service:8005`                             | Internal URL                 | 🔴        |
| `DEFAULT_CURRENCY`           | `USD`                                                               | Default currency code        | 🟢        |
| `BUDGET_ALERT_THRESHOLD`     | `80.0`                                                              | Alert at X% of budget used   | 🟢        |
| `SPENDING_LIMIT_ALERT_THRESHOLD` | `80.0`                                                          | Alert at X% of limit used    | 🟢        |

---

### 3.5 Bank Service (:8003)

| Variable               | Default                                                      | Description                       | Required |
|------------------------|--------------------------------------------------------------|-----------------------------------|----------|
| `SECRET_KEY`           | insecure default                                             | JWT decode secret                 | 🔴        |
| `DATABASE_URL`         | `postgresql://bank_service:bank_password@bank-db:5432/bank_db` | Postgres                       | 🔴        |
| `KAFKA_BOOTSTRAP_SERVERS` | `kafka:9092`                                              | Kafka broker                      | 🔴        |
| `AWS_ACCESS_KEY_ID`    | —                                                            | AWS credentials for S3 uploads    | 🔴        |
| `AWS_SECRET_ACCESS_KEY`| —                                                            | AWS credentials for S3 uploads    | 🔴        |
| `AWS_REGION`           | `us-east-1`                                                  | S3 bucket region                  | 🔴        |
| `AWS_S3_BUCKET`        | `financial-statements`                                       | S3 bucket name for statements     | 🔴        |
| `S3_PRESIGNED_URL_EXPIRES` | `3600`                                                   | Pre-signed URL TTL (seconds)      | 🟢        |
| `USER_SERVICE_URL`     | `http://user-service:8001`                                   | Internal URL                      | 🔴        |

---

### 3.6 Statement Analysis Service (:8004)

| Variable                  | Default                                    | Description                        | Required |
|---------------------------|--------------------------------------------|------------------------------------|----------|
| `SECRET_KEY`              | insecure default                           | JWT decode secret                  | 🔴        |
| `REDIS_URL`               | `redis://redis:6379/5`                     | Cache — must use /5                | 🔴        |
| `KAFKA_BOOTSTRAP_SERVERS` | `kafka:9092`                               | Kafka broker                       | 🔴        |
| `ANTHROPIC_API_KEY`       | —                                          | Claude API key (primary AI)        | 🔴        |
| `OPENAI_API_KEY`          | —                                          | OpenAI fallback (optional)         | 🟡        |
| `AI_PROVIDER`             | `claude`                                   | `claude` or `openai`               | 🟢        |
| `AI_MODEL`                | `claude-sonnet-4-6`                        | Claude model ID                    | 🟢        |
| `AI_MAX_RETRIES`          | `3`                                        | Retries on AI API failure          | 🟢        |
| `AI_TIMEOUT_SECONDS`      | `60`                                       | AI call timeout                    | 🟢        |
| `AWS_ACCESS_KEY_ID`       | —                                          | S3 read access for statements      | 🔴        |
| `AWS_SECRET_ACCESS_KEY`   | —                                          | S3 read access for statements      | 🔴        |
| `AWS_REGION`              | `us-east-1`                                | S3 region                          | 🔴        |
| `S3_BUCKET_NAME`          | `savvy-statements`                         | Must match bank-service bucket     | 🔴        |
| `CHROMA_HOST`             | `localhost`                                | ChromaDB host                      | 🔴        |
| `CHROMA_PORT`             | `8000`                                     | ChromaDB port                      | 🔴        |
| `CHROMA_COLLECTION`       | `transaction_patterns`                     | Vector collection name             | 🟢        |
| `REDIS_CACHE_TTL`         | `3600`                                     | Cache TTL seconds                  | 🟢        |
| `MAX_FILE_SIZE_MB`        | `10`                                       | Max statement file size            | 🟢        |
| `CONFIDENCE_THRESHOLD`    | `0.7`                                      | AI categorisation confidence floor | 🟢        |

---

### 3.7 AI Recommendation Service (:8005)

| Variable                  | Default               | Description                        | Required |
|---------------------------|-----------------------|------------------------------------|----------|
| `SECRET_KEY`              | insecure default      | JWT decode secret                  | 🔴        |
| `ANTHROPIC_API_KEY`       | —                     | Claude API key                     | 🔴        |
| `OPENAI_API_KEY`          | —                     | OpenAI fallback (optional)         | 🟡        |
| `CLAUDE_MODEL`            | `claude-sonnet-4-6`   | Claude model ID                    | 🟢        |
| `REDIS_URL`               | `redis://redis:6379/6`| Cache — must use /6                | 🔴        |
| `RECOMMENDATION_CACHE_TTL`| `3600`                | Recommendation cache TTL           | 🟢        |
| `KAFKA_BOOTSTRAP_SERVERS` | `kafka:9092`          | Kafka broker                       | 🔴        |
| `CHROMA_HOST`             | `localhost`           | ChromaDB host                      | 🔴        |
| `CHROMA_PORT`             | `8000`                | ChromaDB port                      | 🔴        |
| `ALPHA_VANTAGE_API_KEY`   | —                     | Market data API (optional)         | 🟡        |
| `LANGGRAPH_ENABLED`       | `true`                | Use LangGraph workflow engine      | 🟢        |
| `WORKFLOW_TIMEOUT`        | `60`                  | Max seconds per AI workflow        | 🟢        |
| `CONFIDENCE_THRESHOLD`    | `0.75`                | Min confidence for recommendations | 🟢        |

---

### 3.8 Notification Service (:8006)

| Variable                  | Default                                                                          | Description                    | Required |
|---------------------------|----------------------------------------------------------------------------------|--------------------------------|----------|
| `SECRET_KEY`              | insecure default                                                                 | JWT decode secret              | 🔴        |
| `DATABASE_URL`            | `postgresql://notification_service:notification_password@notification-db:5432/notification_db` | Postgres | 🔴 |
| `REDIS_URL`               | `redis://redis:6379/3`                                                           | Cache — must use /3            | 🔴        |
| `KAFKA_BOOTSTRAP_SERVERS` | `kafka:9092`                                                                     | Kafka broker                   | 🔴        |
| `SMTP_HOST`               | —                                                                                | Email SMTP server hostname     | 🟡        |
| `SMTP_PORT`               | `587`                                                                            | SMTP port (587=TLS, 465=SSL)   | 🟡        |
| `SMTP_USERNAME`           | —                                                                                | SMTP auth username             | 🟡        |
| `SMTP_PASSWORD`           | —                                                                                | SMTP auth password             | 🟡        |
| `SMTP_FROM_EMAIL`         | `notifications@savvy.com`                                                        | Sender email address           | 🟡        |
| `SMTP_FROM_NAME`          | `Savvy`                                                                          | Sender display name            | 🟢        |
| `SMTP_USE_TLS`            | `true`                                                                           | Use STARTTLS                   | 🟢        |
| `ONESIGNAL_APP_ID`        | —                                                                                | OneSignal push notifications   | 🟡        |
| `ONESIGNAL_API_KEY`       | —                                                                                | OneSignal REST API key         | 🟡        |
| `NOTIFICATION_TTL_DAYS`   | `30`                                                                             | Auto-expire old notifications  | 🟢        |
| `DEDUP_WINDOW_SECONDS`    | `60`                                                                             | Suppress duplicate notifications | 🟢      |

---

### 3.9 Frontend (Next.js :3000)

| Variable               | Example                      | Description                            | Required |
|------------------------|------------------------------|----------------------------------------|----------|
| `NEXT_PUBLIC_API_URL`  | `https://api.savvy.com`      | API Gateway public URL (browser-side)  | 🔴        |

> All `NEXT_PUBLIC_*` vars are baked into the JS bundle at build time — you cannot change them after build without rebuilding.

---

## 4. Secret Management

### What qualifies as a secret
- `SECRET_KEY` (JWT) — **single most critical secret**
- All `DATABASE_URL` values (contain passwords)
- `ANTHROPIC_API_KEY`
- `OPENAI_API_KEY`
- `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY`
- `SMTP_PASSWORD`
- `ONESIGNAL_API_KEY`

### Docker Compose (local / staging)
Create `microservices/.env` (never commit this file):

```bash
# microservices/.env
# ── REQUIRED ──────────────────────────────────────────────
SECRET_KEY=<generate with: python -c "import secrets; print(secrets.token_hex(32))">

# ── AWS (required for bank-service + statement-analysis) ──
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1
AWS_S3_BUCKET=savvy-statements

# ── AI (required for statement-analysis + ai-recommendation) ──
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...           # optional fallback

# ── SMTP (optional — notifications work without it) ────────
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your@email.com
SMTP_PASSWORD=app-specific-password

# ── Push notifications (optional) ──────────────────────────
ONESIGNAL_APP_ID=...
ONESIGNAL_API_KEY=...

# ── CORS (override in staging) ─────────────────────────────
ALLOWED_ORIGINS=["http://localhost:3000"]
```

```bash
# frontend/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Kubernetes (production)
All secrets live in a single K8s `Secret` object `savvy-secrets` in namespace `savvy`:

```bash
# One-time setup — never store this command in version control
kubectl create secret generic savvy-secrets \
  --namespace=savvy \
  --from-literal=SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')" \
  --from-literal=DATABASE_URL_USER="postgresql://user_service:<PASSWORD>@user-db:5432/user_db" \
  --from-literal=DATABASE_URL_FINANCE="postgresql://finance_service:<PASSWORD>@finance-db:5432/finance_db" \
  --from-literal=DATABASE_URL_BANK="postgresql://bank_service:<PASSWORD>@bank-db:5432/bank_db" \
  --from-literal=DATABASE_URL_NOTIFICATION="postgresql://notification_service:<PASSWORD>@notification-db:5432/notification_db" \
  --from-literal=REDIS_BASE_URL="redis://redis:6379" \
  --from-literal=ANTHROPIC_API_KEY="sk-ant-..." \
  --from-literal=OPENAI_API_KEY="sk-..." \
  --from-literal=AWS_ACCESS_KEY_ID="AKIA..." \
  --from-literal=AWS_SECRET_ACCESS_KEY="..." \
  --from-literal=SMTP_PASSWORD="..." \
  --from-literal=ONESIGNAL_API_KEY="..."
```

Reference in deployment YAML:
```yaml
env:
- name: SECRET_KEY
  valueFrom:
    secretKeyRef:
      name: savvy-secrets
      key: SECRET_KEY
- name: DATABASE_URL
  valueFrom:
    secretKeyRef:
      name: savvy-secrets
      key: DATABASE_URL_FINANCE
- name: REDIS_URL
  value: "$(REDIS_BASE_URL)/1"   # append DB number here, not in secret
```

> **Never put secrets in ConfigMaps.** ConfigMaps are not encrypted at rest.  
> **Rotate `SECRET_KEY`** by updating the K8s secret + rolling restart all services simultaneously — old JWTs will immediately be invalid.

---

## 5. Local Development (Docker Compose)

### Prerequisites
```
Docker Desktop ≥ 24
Python 3.11 (for scripts)
Node.js 20 (for frontend)
```

### Steps

```bash
# 1. Clone and enter project
cd microservices

# 2. Create .env (see section 4)
cp .env.example .env
# fill in SECRET_KEY at minimum

# 3. Start infrastructure first
docker compose up -d user-db finance-db bank-db notification-db redis zookeeper kafka chromadb

# 4. Wait for health checks, then start services
docker compose up -d

# 5. Verify all healthy
docker compose ps

# 6. Check logs if anything fails
docker compose logs -f api-gateway

# 7. Start frontend separately (hot reload)
cd ../frontend
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
npm install
npm run dev
```

### Port Map (local)
| Service              | URL                          |
|----------------------|------------------------------|
| Frontend             | http://localhost:3000        |
| API Gateway          | http://localhost:8000        |
| User Service         | http://localhost:8001        |
| Finance Service      | http://localhost:8002        |
| Bank Service         | http://localhost:8003        |
| Statement Analysis   | http://localhost:8004        |
| AI Recommendation    | http://localhost:8005        |
| Notification Service | http://localhost:8006        |
| user-db (Postgres)   | localhost:5433               |
| finance-db (Postgres)| localhost:5434               |
| bank-db (Postgres)   | localhost:5435               |
| notification-db      | localhost:5436               |
| Redis                | localhost:6379               |
| Kafka                | localhost:29092 (external)   |
| ChromaDB             | http://localhost:8100        |

---

## 6. Production (Kubernetes)

### Namespace setup
```bash
kubectl create namespace savvy
```

### Apply secrets (section 4 kubectl command)

### Apply all manifests
```bash
# Infrastructure (run once — or use managed services instead)
kubectl apply -f k8s/infrastructure/

# Services
kubectl apply -f k8s/services/
```

### K8s manifest structure
```
k8s/
├── infrastructure/
│   ├── postgres/        ← 4× StatefulSets (or point to managed DB)
│   ├── redis/           ← StatefulSet (or Elasticache)
│   ├── kafka/           ← StatefulSet (or Confluent Cloud)
│   └── chromadb/        ← StatefulSet
└── services/
    ├── api-gateway/
    │   ├── deployment.yaml
    │   └── service.yaml     ← LoadBalancer or NodePort
    ├── user-service/
    ├── finance-service/
    ├── bank-service/
    ├── statement-analysis-service/
    ├── ai-recommendation-service/
    ├── notification-service/
    └── frontend/
```

### Service types
| Service              | K8s Type        | Why                                         |
|----------------------|-----------------|---------------------------------------------|
| API Gateway          | LoadBalancer    | Single external entry point                 |
| All other services   | ClusterIP       | Internal only — never expose directly       |
| Frontend             | Separate (Vercel recommended) | Better CDN + preview deploys   |

### Replica counts
| Service              | Min Replicas | Notes                                   |
|----------------------|--------------|-----------------------------------------|
| API Gateway          | 2            | Stateless — safe to scale freely        |
| User Service         | 2            | Stateless                               |
| Finance Service      | 2            | Stateless                               |
| Bank Service         | 2            | Stateless                               |
| Statement Analysis   | 1–2          | AI calls are expensive; don't over-scale|
| AI Recommendation    | 1–2          | Same as above                           |
| Notification Service | 2            | Stateless                               |

### Resource limits (current K8s defaults)
| Service              | CPU Request | CPU Limit | RAM Request | RAM Limit |
|----------------------|-------------|-----------|-------------|-----------|
| API Gateway          | 100m        | 300m      | 128Mi       | 256Mi     |
| User Service         | 100m        | 300m      | 128Mi       | 256Mi     |
| Finance Service      | 100m        | 300m      | 128Mi       | 256Mi     |
| Bank Service         | 100m        | 300m      | 128Mi       | 256Mi     |
| Statement Analysis   | 200m        | 500m      | 256Mi       | 512Mi     |
| AI Recommendation    | 200m        | 500m      | 256Mi       | 512Mi     |
| Notification Service | 100m        | 300m      | 128Mi       | 256Mi     |

---

## 7. Database Migration Strategy

### How it works
All DB-backed services use **Alembic** for migrations.  
Migrations run via **K8s initContainers** before the main container starts.

### Migration chain (finance-service)
```
001_initial_schema.py
  └── 002_add_assets_table.py
        └── 003_add_sadaqah_liabilities_hajj.py
```

### Running migrations manually
```bash
# Docker Compose — inside running container
docker compose exec finance-service alembic upgrade head

# K8s — one-off job
kubectl exec -it deploy/finance-service -n savvy -- alembic upgrade head

# Local — directly (needs DATABASE_URL env var set)
cd microservices/finance-service
DATABASE_URL=postgresql://finance_service:finance_password@localhost:5434/finance_db \
  alembic upgrade head
```

### Services with migrations
| Service              | Migration Tool | Alembic Versions  |
|----------------------|----------------|-------------------|
| user-service         | Alembic        | 001               |
| finance-service      | Alembic        | 001 → 002 → 003   |
| bank-service         | Alembic        | 001               |
| notification-service | Alembic        | 001               |

### Rolling back
```bash
# Roll back one step
alembic downgrade -1

# Roll back to specific revision
alembic downgrade 002
```

> **Never run `Base.metadata.create_all()` in production.** This was removed from all services. Always use Alembic.

---

## 8. Service Startup Order

Infrastructure must be healthy before services start. Services must be healthy before API Gateway starts.

```
Tier 0 (infrastructure):
  user-db, finance-db, bank-db, notification-db → wait for pg_isready
  redis → wait for redis-cli ping
  zookeeper → wait for port
  kafka → depends on zookeeper
  chromadb → no hard dependency

Tier 1 (DB-backed services — run migrations first):
  user-service       → needs user-db + redis + kafka
  finance-service    → needs finance-db + redis + kafka
  bank-service       → needs bank-db + kafka
  notification-service → needs notification-db + redis + kafka

Tier 2 (stateless services):
  statement-analysis → needs redis + kafka + chromadb
  ai-recommendation  → needs redis + kafka + chromadb

Tier 3 (entry point):
  api-gateway        → needs redis + all Tier 1/2 services started

Tier 4 (frontend):
  frontend           → needs api-gateway
```

---

## 9. Health Checks

Every service exposes `GET /health`.

| Service              | URL                               | DB check | Expected response            |
|----------------------|-----------------------------------|----------|------------------------------|
| API Gateway          | http://api-gateway:8000/health    | No       | `{"status":"ok"}`            |
| User Service         | http://user-service:8001/health   | Yes      | `{"status":"ok"}`            |
| Finance Service      | http://finance-service:8002/health| Yes      | `{"status":"ok"}`            |
| Bank Service         | http://bank-service:8003/health   | Yes      | `{"status":"ok"}`            |
| Stmt Analysis        | http://stmt-svc:8004/health       | No       | `{"status":"ok"}`            |
| AI Recommendation    | http://ai-svc:8005/health         | No       | `{"status":"ok"}`            |
| Notification Service | http://notif-svc:8006/health      | Yes      | `{"status":"ok"}`            |

Returns HTTP 503 if the DB is unreachable (finance, user, bank, notification services only).

K8s probes:
```yaml
readinessProbe:
  httpGet: { path: /health, port: <port> }
  initialDelaySeconds: 10
  periodSeconds: 5
livenessProbe:
  httpGet: { path: /health, port: <port> }
  initialDelaySeconds: 30
  periodSeconds: 15
```

---

## 10. CI/CD Pipeline

### Recommended: GitHub Actions

```yaml
# .github/workflows/deploy.yml (outline)
on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: cd microservices && pytest --tb=short

  build-push:
    needs: test
    steps:
      - uses: docker/build-push-action@v5
        with:
          context: microservices
          file: microservices/<service>/Dockerfile
          tags: ghcr.io/YOUR_ORG/savvy-<service>:${{ github.sha }}
          push: true

  deploy:
    needs: build-push
    steps:
      - run: |
          kubectl set image deployment/<service> \
            <service>=ghcr.io/YOUR_ORG/savvy-<service>:${{ github.sha }} \
            -n savvy
          kubectl rollout status deployment/<service> -n savvy
```

### Image naming convention
```
ghcr.io/YOUR_ORG/savvy-api-gateway:<sha>
ghcr.io/YOUR_ORG/savvy-user-service:<sha>
ghcr.io/YOUR_ORG/savvy-finance-service:<sha>
ghcr.io/YOUR_ORG/savvy-bank-service:<sha>
ghcr.io/YOUR_ORG/savvy-statement-analysis:<sha>
ghcr.io/YOUR_ORG/savvy-ai-recommendation:<sha>
ghcr.io/YOUR_ORG/savvy-notification-service:<sha>
ghcr.io/YOUR_ORG/savvy-frontend:<sha>
```

### Replace `YOUR_ORG` with your GitHub organisation name in:
- All `k8s/services/*/deployment.yaml` (`image:` field)
- GitHub Actions workflow
- Any `docker pull` scripts

---

## Quick Reference: Minimum `.env` to start locally

```bash
# microservices/.env  — bare minimum
SECRET_KEY=changeme_at_least_32_characters_long_here!!

# Optional but needed for full functionality:
# ANTHROPIC_API_KEY=sk-ant-...   (AI features)
# AWS_ACCESS_KEY_ID=...           (bank statement upload)
# AWS_SECRET_ACCESS_KEY=...
# AWS_S3_BUCKET=savvy-statements
```

```bash
# frontend/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
```
