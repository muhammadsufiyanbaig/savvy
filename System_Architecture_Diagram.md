# System Architecture — Savvy
**Version:** 2.0 | **Updated:** 2026-06-20

---

## Full Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          CLIENT LAYER                                    │
│                                                                          │
│              ┌────────────────────────────────────┐                     │
│              │    Next.js 14 Frontend  :3000       │                     │
│              │  Zustand · Recharts · Framer Motion │                     │
│              └─────────────────┬──────────────────┘                     │
└────────────────────────────────┼─────────────────────────────────────────┘
                                 │  HTTPS
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                       GATEWAY LAYER  :8000                               │
│                                                                          │
│    ┌──────────────────────────────────────────────────────────────┐     │
│    │                   API Gateway (FastAPI)                       │     │
│    │  • JWT validation (HS256, shared SECRET_KEY)                 │     │
│    │  • Rate limiting  (300 auth / 60 anon per minute)            │     │
│    │  • Request routing by URL prefix                             │     │
│    │  • Security headers injection                                │     │
│    │  • Body size limit (10 MB)                                   │     │
│    │  Redis /4 ──────────────────────────── (rate limit cache)    │     │
│    └──────────────────────────────────────────────────────────────┘     │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 │  Internal HTTP (ClusterIP)
          ┌──────────────────────┼──────────────────────┐
          │                      │                      │
          ▼                      ▼                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        MICROSERVICES LAYER                              │
│                                                                         │
│  ┌─────────────────────┐   ┌──────────────────────────────────────────┐ │
│  │  User Service :8001 │   │         Finance Service :8002            │ │
│  │  ─────────────────  │   │  ──────────────────────────────────────  │ │
│  │  • Registration     │   │  EXPENSES     BUDGETS     SAVINGS GOALS  │ │
│  │  • JWT auth/refresh │   │  SPENDING     CASH        ASSETS         │ │
│  │  • Profile mgmt     │   │  LIMITS       SAVINGS     ZAKAT          │ │
│  │  • Email verify     │   │  QURBANI      SADAQAH     LIABILITIES    │ │
│  │  • Password reset   │   │  HAJJ/UMRAH   NET WORTH   HEALTH SCORE   │ │
│  │                     │   │                                          │ │
│  │  PostgreSQL user_db │   │  PostgreSQL finance_db                   │ │
│  │  Redis /0           │   │  Redis /1                                │ │
│  │  Kafka consumer     │   │  Kafka consumer                          │ │
│  └─────────────────────┘   └──────────────────────────────────────────┘ │
│                                                                         │
│  ┌─────────────────────┐   ┌──────────────────────┐                    │
│  │  Bank Service :8003 │   │ Notification Svc :8006│                   │
│  │  ─────────────────  │   │  ──────────────────── │                   │
│  │  • Bank accounts    │   │  • In-app notifs      │                   │
│  │  • Statement upload │   │  • Email (SMTP)       │                   │
│  │  • AWS S3 storage   │   │  • Push (OneSignal)   │                   │
│  │  • Pre-signed URLs  │   │  • Dedup (60s window) │                   │
│  │                     │   │  • Auto-expire 30d    │                   │
│  │  PostgreSQL bank_db │   │  PostgreSQL notif_db  │                   │
│  │  Kafka consumer     │   │  Redis /3             │                   │
│  └─────────────────────┘   │  Kafka consumer       │                   │
│                            └──────────────────────┘                    │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │          AI / Analysis Services                                  │  │
│  │                                                                  │  │
│  │  ┌──────────────────────────┐  ┌──────────────────────────────┐  │  │
│  │  │ Statement Analysis :8004 │  │ AI Recommendation Svc :8005  │  │  │
│  │  │  ────────────────────    │  │  ──────────────────────────   │  │  │
│  │  │  • Parse PDF/CSV/XLSX   │  │  • Financial recommendations  │  │  │
│  │  │  • Extract transactions │  │  • LangGraph workflow engine  │  │  │
│  │  │  • AI categorisation    │  │  • Cached responses (1h TTL)  │  │  │
│  │  │  • Confidence scoring   │  │  • Context-aware (spending,   │  │  │
│  │  │                         │  │    savings, debt, goals)      │  │  │
│  │  │  Claude API (Anthropic) │  │  Claude API (Anthropic)       │  │  │
│  │  │  AWS S3 (read)          │  │  ChromaDB (vector store)      │  │  │
│  │  │  Redis /5               │  │  Redis /6                     │  │  │
│  │  │  ChromaDB               │  │  Kafka consumer               │  │  │
│  │  └──────────────────────────┘  └──────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        INFRASTRUCTURE LAYER                             │
│                                                                         │
│  ┌──────────────────────┐  ┌──────────────────────┐                    │
│  │  PostgreSQL ×4       │  │  Redis (shared) ×1   │                    │
│  │  ─────────────────── │  │  ──────────────────── │                    │
│  │  user_db       :5433 │  │  DB /0 user-service   │                    │
│  │  finance_db    :5434 │  │  DB /1 finance-svc    │                    │
│  │  bank_db       :5435 │  │  DB /3 notification   │                    │
│  │  notification  :5436 │  │  DB /4 api-gateway    │                    │
│  │                      │  │  DB /5 stmt-analysis  │                    │
│  │  Alembic migrations  │  │  DB /6 ai-recommend   │                    │
│  │  (initContainers)    │  └──────────────────────┘                    │
│  └──────────────────────┘                                               │
│                                                                         │
│  ┌──────────────────────┐  ┌──────────────────────┐                    │
│  │  Apache Kafka        │  │  ChromaDB            │                    │
│  │  + Zookeeper         │  │  ──────────────────── │                    │
│  │  ─────────────────── │  │  Vector store for    │                    │
│  │  Async event bus     │  │  AI embeddings and   │                    │
│  │  Budget alerts       │  │  transaction pattern │                    │
│  │  Notification events │  │  matching            │                    │
│  │  Cross-service sync  │  │  :8100 (local)       │                    │
│  └──────────────────────┘  └──────────────────────┘                    │
└─────────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     EXTERNAL SERVICES                                   │
│                                                                         │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐  │
│  │  Anthropic       │  │  AWS S3          │  │  SMTP Server         │  │
│  │  Claude API      │  │  ──────────────── │  │  (optional)          │  │
│  │  ──────────────  │  │  Statement files │  │  Email notifications │  │
│  │  claude-sonnet   │  │  PDF/CSV/XLSX    │  └──────────────────────┘  │
│  │  -4-6 (primary)  │  │  Pre-signed URLs │                            │
│  └──────────────────┘  └──────────────────┘  ┌──────────────────────┐  │
│                                               │  OneSignal           │  │
│  ┌──────────────────┐                         │  (optional)          │  │
│  │  Alpha Vantage   │                         │  Push notifications  │  │
│  │  (optional)      │                         └──────────────────────┘  │
│  │  Market data     │                                                   │
│  └──────────────────┘                                                   │
└─────────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      OBSERVABILITY LAYER                                │
│                                                                         │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐  │
│  │  Prometheus      │  │  Grafana         │  │  Service Logs        │  │
│  │  Metrics scrape  │  │  Dashboard       │  │  stdout → collector  │  │
│  │  /metrics on     │  │  FastAPI         │  │  (ELK / Loki)        │  │
│  │  all services    │  │  Observability   │  └──────────────────────┘  │
│  └──────────────────┘  │  ID: 17175       │                            │
│                        └──────────────────┘                            │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Request Flow

### Standard API Request
```
Browser → Gateway :8000
  → JWT validation (Redis /4 rate check)
  → Route match (/api/v1/expenses → finance-service:8002)
  → Forward request (internal HTTP)
  → Finance service queries PostgreSQL finance_db
  → Response returned to browser
  Total: ~50–200ms
```

### Statement Upload + Analysis
```
Browser → Gateway :8000 → Bank Service :8003
  → Validate file type/size
  → Upload to AWS S3
  → Publish Kafka event: "statement.uploaded"
  → Statement Analysis :8004 consumes event
  → Download from S3
  → Send to Claude API (Anthropic)
  → Parse transactions, assign categories
  → Store results
  → Publish Kafka event: "statement.analyzed"
  Total: 5–30s (async)
```

### AI Recommendation Request
```
Browser → Gateway → AI Recommendation :8005
  → Check Redis cache (key: user:{id}:recommendations)
  → Cache hit: return cached (sub-100ms)
  → Cache miss: LangGraph workflow
      → Fetch user financial context
      → Build prompt with expenses, savings, debt, goals
      → Call Claude API
      → Parse structured recommendations
      → Cache in Redis (1h TTL)
  Total: 5–20s (first call), <100ms (cached)
```

---

## Kafka Topics

| Topic                        | Producer          | Consumer(s)               |
|------------------------------|-------------------|---------------------------|
| `financial_user.registered`  | user-service      | notification-service      |
| `financial_expense.created`  | finance-service   | notification-service      |
| `financial_budget.alert`     | finance-service   | notification-service      |
| `financial_statement.uploaded`| bank-service     | statement-analysis-service|
| `financial_statement.analyzed`| stmt-analysis    | finance-service           |

---

## Technology Stack

| Layer         | Technology              | Version   | Purpose                       |
|---------------|-------------------------|-----------|-------------------------------|
| Frontend      | Next.js                 | 14        | React SSR framework           |
| Frontend      | TypeScript              | 5.x       | Type safety                   |
| Frontend      | Zustand                 | 4.x       | State management              |
| Frontend      | Zod                     | 3.x       | Schema validation             |
| Frontend      | Recharts                | 2.x       | Data visualisation            |
| Frontend      | Framer Motion           | 11.x      | Animations                    |
| Frontend      | react-hook-form         | 7.x       | Form management               |
| Backend       | Python                  | 3.11      | Runtime                       |
| Backend       | FastAPI                 | 0.104+    | Async web framework           |
| Backend       | SQLAlchemy              | 2.x       | ORM                           |
| Backend       | Alembic                 | 1.x       | DB migrations                 |
| Backend       | Pydantic                | v2        | Schema validation             |
| Backend       | pydantic-settings       | 2.x       | Config from env vars          |
| Database      | PostgreSQL              | 15        | Primary RDBMS (×4 instances)  |
| Cache         | Redis                   | 7         | Cache + rate limiting         |
| Messaging     | Apache Kafka            | 7.4 (CP)  | Async event bus               |
| Vector DB     | ChromaDB                | latest    | AI embeddings                 |
| AI            | Anthropic Claude        | sonnet-4-6| Statement analysis + advice   |
| AI Framework  | LangGraph               | latest    | AI workflow orchestration     |
| Storage       | AWS S3                  | —         | Bank statement files          |
| Containers    | Docker                  | 24+       | Containerisation              |
| Orchestration | Kubernetes              | 1.28+     | Production deployment         |
| Monitoring    | Prometheus + Grafana    | —         | Metrics + dashboards          |
| CI/CD         | GitHub Actions          | —         | Build, test, deploy           |

---

## Port Reference

| Component          | Local Port | Container Port |
|--------------------|-----------|----------------|
| Frontend           | 3000      | 3000           |
| API Gateway        | 8000      | 8000           |
| User Service       | 8001      | 8001           |
| Finance Service    | 8002      | 8002           |
| Bank Service       | 8003      | 8003           |
| Statement Analysis | 8004      | 8004           |
| AI Recommendation  | 8005      | 8005           |
| Notification Svc   | 8006      | 8006           |
| user-db            | 5433      | 5432           |
| finance-db         | 5434      | 5432           |
| bank-db            | 5435      | 5432           |
| notification-db    | 5436      | 5432           |
| Redis              | 6379      | 6379           |
| Kafka (external)   | 29092     | 29092          |
| Kafka (internal)   | 9092      | 9092           |
| ChromaDB           | 8100      | 8000           |
| Zookeeper          | 2181      | 2181           |
