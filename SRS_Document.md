# Software Requirements Specification (SRS)
## Savvy — Islamic Financial Management System

**Version:** 2.0  
**Date:** 2026-06-20  
**Status:** Current

---

## Table of Contents
1. [Introduction](#1-introduction)
2. [Overall Description](#2-overall-description)
3. [Functional Requirements](#3-functional-requirements)
4. [Non-Functional Requirements](#4-non-functional-requirements)
5. [System Architecture Summary](#5-system-architecture-summary)
6. [External Interface Requirements](#6-external-interface-requirements)
7. [Data Models](#7-data-models)

---

## 1. Introduction

### 1.1 Purpose
Savvy is an AI-powered Islamic financial management system. It provides complete personal finance management while remaining aligned with Islamic finance principles — tracking spending, savings, charity, and pilgrimage goals alongside standard financial planning.

### 1.2 Scope
Savvy enables users to:
- Track expenses with category-level budgets and spending limits
- Manage savings goals and cash savings
- Track investment assets (stocks, real estate, crypto, commodities)
- Monitor liabilities and compute real-time net worth
- Calculate and track Zakat obligations
- Plan Qurbani savings
- Record Sadaqah / charitable giving (7 Islamic categories)
- Plan Hajj or Umrah savings with deposit tracking
- Receive an Islamic Financial Health Score (6-component, A–F grade)
- Upload bank statements for AI-powered transaction analysis
- Receive AI recommendations via Claude (Anthropic) integration
- Get in-app and email notifications for budget alerts

### 1.3 Definitions
| Term         | Meaning                                                     |
|--------------|-------------------------------------------------------------|
| Zakat        | Obligatory annual Islamic wealth purification tax (2.5%)    |
| Qurbani      | Sacrifice during Eid al-Adha                                |
| Sadaqah      | Voluntary Islamic charity                                   |
| Lillah       | Donation given purely for Allah                             |
| Waqf         | Islamic endowment                                           |
| Fidya        | Compensation payment for missed fasts                       |
| Kaffarah     | Expiation payment for broken oaths                          |
| Riba         | Interest — prohibited in Islamic finance                    |
| Nisab        | Minimum wealth threshold that makes Zakat obligatory        |
| JWT          | JSON Web Token — used for stateless authentication          |
| API Gateway  | Single entry point reverse-proxying all backend services    |

### 1.4 Technology References
- FastAPI 0.104+ — Python async web framework
- Next.js 14 App Router — React SSR framework
- PostgreSQL 15 — Primary relational database
- Redis 7 — Caching and rate limiting
- Apache Kafka — Async event bus
- ChromaDB — Vector database for AI embeddings
- Claude (Anthropic) — AI provider for analysis and recommendations
- Alembic — Database migration tool
- SQLAlchemy 2.x — ORM
- Pydantic v2 — Schema validation

---

## 2. Overall Description

### 2.1 Product Perspective
Savvy is a web-based SaaS application following a microservices architecture. All client traffic enters through a single API Gateway. Seven backend FastAPI services handle distinct domains. A Next.js frontend communicates exclusively with the gateway.

### 2.2 User Classes
| Class               | Description                                               |
|---------------------|-----------------------------------------------------------|
| Individual User     | Primary user — manages own finances                       |
| Admin (future)      | Platform administrator — user management, system config   |

### 2.3 Operating Environment
- **Frontend**: Next.js 14, runs in Chromium/Firefox/Safari
- **Backend**: Python 3.11, FastAPI, Docker containers
- **Orchestration**: Kubernetes (production) / Docker Compose (local)
- **Cloud**: AWS (S3 for statements), any VPS or managed K8s
- **AI**: Anthropic Claude API (claude-sonnet-4-6)

### 2.4 Constraints
- All money amounts use `Numeric(15,2)` — never floats — to avoid precision loss
- Riba (interest) must be flagged on all interest-bearing liabilities
- Zakat calculations use current gold/silver nisab from live or cached values
- `SECRET_KEY` must be identical across all 7 backend services (shared JWT secret)
- Services never expose internal ports in production — all traffic via API Gateway

---

## 3. Functional Requirements

### 3.1 User Management (user-service)
| ID     | Requirement                                                           |
|--------|-----------------------------------------------------------------------|
| FR-1.1 | Users register with username, email, password, optional full name     |
| FR-1.2 | Login returns JWT access token (30 min) + refresh token (7 days)      |
| FR-1.3 | 401 responses trigger automatic silent token refresh before logout     |
| FR-1.4 | Email verification on registration                                    |
| FR-1.5 | Password reset via secure email link                                  |
| FR-1.6 | Users update profile (name, email, currency preference)               |
| FR-1.7 | Users change password with current password confirmation              |

### 3.2 Expense Tracking (finance-service)
| ID     | Requirement                                                           |
|--------|-----------------------------------------------------------------------|
| FR-2.1 | Users create, read, update, soft-delete expenses                      |
| FR-2.2 | Expenses have: amount, currency, category, date, description, tags    |
| FR-2.3 | Expense categories: food, transport, housing, utilities, healthcare, education, entertainment, shopping, business, zakat, sadaqah, other |
| FR-2.4 | Summary endpoint returns total by category and monthly trend          |
| FR-2.5 | Expense date cannot be in the future                                  |

### 3.3 Budgets (finance-service)
| ID     | Requirement                                                           |
|--------|-----------------------------------------------------------------------|
| FR-3.1 | Users create monthly budgets per category with limit amount           |
| FR-3.2 | `spent_amount` auto-updates from expense events via Kafka             |
| FR-3.3 | Budget status endpoint returns % used and over/under status           |
| FR-3.4 | Alert fires when budget reaches 80% threshold                         |

### 3.4 Spending Limits (finance-service)
| ID     | Requirement                                                           |
|--------|-----------------------------------------------------------------------|
| FR-4.1 | One active daily/weekly/monthly spending limit per user               |
| FR-4.2 | Status endpoint returns current spend vs limit with remaining amount  |

### 3.5 Savings Goals (finance-service)
| ID     | Requirement                                                           |
|--------|-----------------------------------------------------------------------|
| FR-5.1 | Users create savings goals with target amount and optional deadline   |
| FR-5.2 | Users deposit and withdraw against goals; full transaction history    |
| FR-5.3 | Progress percentage computed from current_amount / target_amount      |

### 3.6 Cash Savings (finance-service)
| ID     | Requirement                                                           |
|--------|-----------------------------------------------------------------------|
| FR-6.1 | Users track physical cash savings with label, amount, currency, location |
| FR-6.2 | Cash savings used in Financial Health Score (savings rate component)  |

### 3.7 Asset Portfolio (finance-service)
| ID     | Requirement                                                           |
|--------|-----------------------------------------------------------------------|
| FR-7.1 | Users add investment assets: equities, bonds, real estate, commodities, crypto, alternatives, cash equivalents |
| FR-7.2 | Asset has: name, ticker, quantity, purchase price, current price, location |
| FR-7.3 | Purchase date cannot be in future                                     |
| FR-7.4 | Analytics endpoint returns portfolio summary, category breakdown, gain/loss |
| FR-7.5 | Assets contribute to Net Worth (assets side)                          |

### 3.8 Zakat (finance-service)
| ID     | Requirement                                                           |
|--------|-----------------------------------------------------------------------|
| FR-8.1 | Calculate Zakat: gold nisab (87.48g) and silver nisab (612.36g)      |
| FR-8.2 | Calculation takes: cash, gold, silver, business goods, investments, receivables, minus liabilities |
| FR-8.3 | Records saved per calculation; mark as paid with date                 |
| FR-8.4 | Zakat compliance used in Financial Health Score                       |

### 3.9 Qurbani (finance-service)
| ID     | Requirement                                                           |
|--------|-----------------------------------------------------------------------|
| FR-9.1 | Animal prices per share (cow/goat) by currency                        |
| FR-9.2 | Users plan Qurbani with num_shares, year, contributions               |
| FR-9.3 | Contribution deposits track progress toward total cost                |

### 3.10 Sadaqah Tracker (finance-service)
| ID      | Requirement                                                          |
|---------|----------------------------------------------------------------------|
| FR-10.1 | Record donations: sadaqah, zakat_fitrah, lillah, waqf, fidya, kaffarah, general_charity |
| FR-10.2 | Each record: amount, currency, category, recipient, date, notes      |
| FR-10.3 | Date cannot be in the future; category validated against allowed list |
| FR-10.4 | Summary: total all-time, this year, this month; breakdown by category; 12-month trend |
| FR-10.5 | Sadaqah total used in Financial Health Score (charitable giving component) |

### 3.11 Liabilities & Net Worth (finance-service)
| ID      | Requirement                                                          |
|---------|----------------------------------------------------------------------|
| FR-11.1 | Users add liabilities: personal_loan, car_loan, home_loan, student_loan, credit_card, business_loan, family_loan, other |
| FR-11.2 | Each liability: name, original amount, amount owed, monthly payment, lender, `is_interest_bearing` flag |
| FR-11.3 | Riba (interest-bearing) flag — shown as warning; penalised in Health Score |
| FR-11.4 | Net worth = sum(asset current_price × quantity) − sum(liability amount_owed) |
| FR-11.5 | Response includes: assets_by_category, liabilities_by_category, riba_debt_total, halal_debt_total |

### 3.12 Hajj / Umrah Savings Plan (finance-service)
| ID      | Requirement                                                          |
|---------|----------------------------------------------------------------------|
| FR-12.1 | Users create Hajj or Umrah plans with target year, num persons, departure city, package type (economy/standard/premium/vip) |
| FR-12.2 | Computed fields: progress_pct, remaining_amount, months_remaining, monthly_target |
| FR-12.3 | Deposit endpoint adds to current_amount and creates deposit record    |
| FR-12.4 | Deposit history per plan, ordered by date descending                 |

### 3.13 Financial Health Score (finance-service)
| ID      | Requirement                                                          |
|---------|----------------------------------------------------------------------|
| FR-13.1 | Score computed on demand from existing user data — no new data entry needed |
| FR-13.2 | 6 components totalling 100 points: Savings Rate (25), Budget Adherence (20), Debt Ratio (20), Zakat Compliance (15), Charitable Giving (10), Goal Progress (10) |
| FR-13.3 | Grade assigned: A (85–100), B (70–84), C (55–69), D (40–54), F (0–39) |
| FR-13.4 | Per-component status (good/warning/poor), actionable tip, key identifier |
| FR-13.5 | Riba debt applies penalty to Debt Ratio component                    |
| FR-13.6 | Response includes `calculated_at` timestamp                          |

### 3.14 Bank Accounts & Statements (bank-service)
| ID      | Requirement                                                          |
|---------|----------------------------------------------------------------------|
| FR-14.1 | Users add bank accounts with name, bank name, account type, balance  |
| FR-14.2 | Upload PDF/CSV/XLSX statements (max 50 MB)                           |
| FR-14.3 | Statements stored in AWS S3 with pre-signed download URLs            |
| FR-14.4 | Content-type validated (415 on mismatch), size validated (413 on exceed) |

### 3.15 Statement Analysis (statement-analysis-service)
| ID      | Requirement                                                          |
|---------|----------------------------------------------------------------------|
| FR-15.1 | AI (Claude) reads uploaded statement, extracts transactions          |
| FR-15.2 | Transactions auto-categorised with confidence score                  |
| FR-15.3 | Results returned with per-transaction detail                         |

### 3.16 AI Recommendations (ai-recommendation-service)
| ID      | Requirement                                                          |
|---------|----------------------------------------------------------------------|
| FR-16.1 | Generate personalised financial recommendations using Claude          |
| FR-16.2 | Recommendations cached in Redis (1 hour TTL)                         |
| FR-16.3 | Context includes: spending patterns, savings rate, debt ratio, goals |
| FR-16.4 | LangGraph workflow orchestrates multi-step AI reasoning              |

### 3.17 Notifications (notification-service)
| ID      | Requirement                                                          |
|---------|----------------------------------------------------------------------|
| FR-17.1 | In-app notifications — list, mark read, mark all read, unread count  |
| FR-17.2 | Email notifications via SMTP (optional — disabled if SMTP not configured) |
| FR-17.3 | Push notifications via OneSignal (optional)                          |
| FR-17.4 | Notification preferences per user                                    |
| FR-17.5 | Duplicate suppression within 60-second dedup window                  |
| FR-17.6 | Auto-expire notifications after 30 days                              |

---

## 4. Non-Functional Requirements

### 4.1 Performance
| ID      | Requirement                                                          |
|---------|----------------------------------------------------------------------|
| NFR-1.1 | API responses < 500ms for standard CRUD (p95)                        |
| NFR-1.2 | AI endpoints (recommendations, analysis) < 60s timeout              |
| NFR-1.3 | Statement analysis < 30s for 10MB PDF                               |

### 4.2 Security
| ID      | Requirement                                                          |
|---------|----------------------------------------------------------------------|
| NFR-2.1 | All traffic HTTPS/TLS in production                                  |
| NFR-2.2 | JWT HS256 with minimum 32-char secret; services exit if secret is default in production |
| NFR-2.3 | API Gateway validates JWT on all routes except whitelist (login, register, etc.) |
| NFR-2.4 | Rate limiting: 300 req/min authenticated, 60 req/min unauthenticated |
| NFR-2.5 | Request body max 10 MB at gateway; 50 MB allowed only for file upload endpoint |
| NFR-2.6 | Security headers on all responses: X-Content-Type-Options, X-Frame-Options, X-XSS-Protection |
| NFR-2.7 | Soft delete (`deleted_at`) on all user data — no hard deletes        |
| NFR-2.8 | S3 pre-signed URLs for statement downloads — never expose bucket directly |

### 4.3 Reliability
| ID      | Requirement                                                          |
|---------|----------------------------------------------------------------------|
| NFR-3.1 | 99.9% uptime target                                                  |
| NFR-3.2 | Health endpoint on every service; returns 503 if DB unreachable      |
| NFR-3.3 | K8s liveness + readiness probes on all services                      |
| NFR-3.4 | Database migrations via Alembic initContainers — never `create_all`  |

### 4.4 Scalability
| ID      | Requirement                                                          |
|---------|----------------------------------------------------------------------|
| NFR-4.1 | All services are stateless — horizontal scaling via replica count    |
| NFR-4.2 | Redis DB isolation per service (see deployment strategy)             |
| NFR-4.3 | Kafka decouples services for async processing                        |

### 4.5 Maintainability
| ID      | Requirement                                                          |
|---------|----------------------------------------------------------------------|
| NFR-5.1 | Prometheus metrics exposed on all services (`/metrics`)              |
| NFR-5.2 | Grafana dashboard for service observability                          |
| NFR-5.3 | Structured logging on all services                                   |

---

## 5. System Architecture Summary

### 5.1 Services
| Service                   | Port | DB             | Redis DB | Responsibilities                        |
|---------------------------|------|----------------|----------|-----------------------------------------|
| API Gateway               | 8000 | None           | /4       | JWT auth, routing, rate limiting        |
| User Service              | 8001 | user_db        | /0       | Auth, profiles, tokens                 |
| Finance Service           | 8002 | finance_db     | /1       | All financial data (12 tables)         |
| Bank Service              | 8003 | bank_db        | None     | Accounts, statement upload to S3       |
| Statement Analysis        | 8004 | None           | /5       | AI statement parsing via Claude        |
| AI Recommendation         | 8005 | None           | /6       | AI recommendations via Claude          |
| Notification Service      | 8006 | notification_db| /3       | In-app, email, push notifications      |
| Frontend (Next.js)        | 3000 | —              | —        | Web UI                                  |

### 5.2 Finance Service Database Tables (12 tables)
```
expenses           budgets            savings_goals
savings_transactions  spending_limits  cash_savings
assets             zakat_records      qurbani_plans
sadaqah_records    liabilities        hajj_umrah_plans
hajj_umrah_deposits
```
*(13 total including hajj_umrah_deposits)*

### 5.3 API Routes (via Gateway at :8000)
```
/api/v1/users/*              → user-service
/api/v1/expenses/*           → finance-service
/api/v1/budgets/*            → finance-service
/api/v1/savings/*            → finance-service
/api/v1/spending-limits/*    → finance-service
/api/v1/cash-savings/*       → finance-service
/api/v1/assets/*             → finance-service
/api/v1/zakat/*              → finance-service
/api/v1/qurbani/*            → finance-service
/api/v1/sadaqah/*            → finance-service
/api/v1/liabilities/*        → finance-service
/api/v1/hajj-umrah/*         → finance-service
/api/v1/financial-health/*   → finance-service
/api/v1/banks/*              → bank-service
/api/v1/ai/*                 → ai-recommendation-service
/api/v1/notifications/*      → notification-service
```

---

## 6. External Interface Requirements

### 6.1 User Interface
- Next.js 14 App Router, glassmorphism dark theme
- Responsive for desktop and tablet
- Libraries: Zustand (state), Zod (validation), react-hook-form, Recharts (charts), Framer Motion (animations)

### 6.2 External APIs
| Service                | Provider    | Purpose                          |
|------------------------|-------------|----------------------------------|
| AI Analysis            | Anthropic   | Statement parsing, recommendations |
| File Storage           | AWS S3      | Bank statement storage           |
| Market Data (optional) | Alpha Vantage / Yahoo Finance | Asset price data |
| Email (optional)       | SMTP        | Notification emails              |
| Push (optional)        | OneSignal   | Mobile push notifications        |

### 6.3 Internal Communication
- **Sync**: REST HTTP between services via API Gateway
- **Async**: Kafka topics for events (budget updates, notifications trigger)
- **Cache**: Redis for rate limiting, sessions, recommendation cache

---

## 7. Data Models

### 7.1 Key Relationships
```
User (user-service)
  ├── Expenses
  ├── Budgets
  ├── SavingsGoals → SavingsTransactions
  ├── SpendingLimit
  ├── CashSavings
  ├── Assets
  ├── ZakatRecords
  ├── QurbaniPlans → QurbaniContributions
  ├── SadaqahRecords
  ├── Liabilities
  ├── HajjUmrahPlans → HajjUmrahDeposits
  └── Notifications (notification-service)

BankAccount (bank-service)
  └── BankStatements → (triggers) StatementAnalysis
```

### 7.2 Soft Delete Pattern
All user-owned models have `deleted_at TIMESTAMP` column.  
Active records: `deleted_at IS NULL`.  
All queries filter by `deleted_at.is_(None)` — data is never hard-deleted.

### 7.3 Amount Precision
All monetary columns use `Numeric(15, 2)` in PostgreSQL.  
Python uses `Decimal` type — never `float` for money.

---

*Document maintained alongside code. For deployment details see `DEPLOYMENT_STRATEGY.md`.*
