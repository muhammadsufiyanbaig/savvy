# Savvy — Cost & Load Analysis
**Version:** 1.0 | **Updated:** 2026-06-20

---

## Table of Contents
1. [Load Analysis](#1-load-analysis)
2. [Service Performance Profile](#2-service-performance-profile)
3. [Bottleneck Analysis](#3-bottleneck-analysis)
4. [Scaling Thresholds](#4-scaling-thresholds)
5. [Cost Analysis — Deployment Options](#5-cost-analysis--deployment-options)
6. [Cost by User Count](#6-cost-by-user-count)
7. [AI API Cost Breakdown](#7-ai-api-cost-breakdown)
8. [Cost Optimisation Strategies](#8-cost-optimisation-strategies)
9. [Recommendations](#9-recommendations)

---

## 1. Load Analysis

### 1.1 Request Distribution

Not all services receive equal traffic. Based on usage patterns:

```
Total incoming requests = 100%

API Gateway           100%  ← every request passes through
Finance Service        52%  ← most-used: expenses, budgets, savings, assets, health score
User Service           18%  ← login, token refresh, profile
Bank Service            8%  ← statement upload (infrequent but heavy)
Notification Service    8%  ← read/mark notifications
AI Recommendation       7%  ← 1h cache reduces real calls significantly
Statement Analysis      4%  ← triggered by upload only
                            ← (Kafka async, not direct request)
```

### 1.2 Requests per Second — by User Tier

Assumptions:
- Active user = makes ~30 API calls/day (mix of reads and writes)
- Peak multiplier = 5× average (morning/evening usage spike)
- Read:Write ratio = 70:30

| Concurrent Users | Avg RPS (Gateway) | Peak RPS | Finance DB QPS | Notes                     |
|-----------------|-------------------|----------|----------------|---------------------------|
| 100             | 0.04              | 0.2      | ~3             | Development / MVP         |
| 500             | 0.17              | 0.9      | ~14            | Early launch              |
| 1,000           | 0.35              | 1.7      | ~28            | Small SaaS                |
| 5,000           | 1.7               | 8.7      | ~139           | Growth stage              |
| 10,000          | 3.5               | 17.4     | ~278           | Scale-up needed           |
| 50,000          | 17.4              | 87       | ~1,390         | Full horizontal scale     |
| 100,000         | 34.7              | 174      | ~2,780         | Enterprise — managed DB   |

> RPS stays low because finance apps have lower request frequency than social/e-commerce apps.
> The DB is the bottleneck — not the app layer.

### 1.3 Payload Sizes

| Operation                    | Avg Request | Avg Response | Notes                       |
|------------------------------|-------------|--------------|------------------------------|
| Login / Token refresh        | 0.3 KB      | 0.5 KB       | Small                        |
| Create expense               | 0.2 KB      | 0.4 KB       | Small                        |
| List expenses (30 items)     | —           | 8 KB         | Paginated                    |
| Financial Health Score       | —           | 3 KB         | 6 components, computed live  |
| Net Worth                    | —           | 2 KB         | Computed from assets+debts   |
| AI Recommendation (cached)   | —           | 5 KB         | From Redis cache             |
| AI Recommendation (fresh)    | 2 KB        | 5 KB         | Claude API roundtrip         |
| Statement upload             | 1–50 MB     | 0.5 KB       | File to S3, heavy upload     |
| Statement analysis result    | —           | 20–100 KB    | Many extracted transactions  |

### 1.4 Database Write Load (Finance Service — heaviest)

Finance DB has 13 tables. Write patterns:

| Table                | Write Frequency          | Rows/User/Month |
|----------------------|--------------------------|-----------------|
| expenses             | Daily                    | ~30             |
| savings_transactions | Weekly                   | ~8              |
| sadaqah_records      | Weekly                   | ~4              |
| hajj_umrah_deposits  | Monthly                  | ~2              |
| notifications        | Event-driven             | ~20             |
| budgets              | Monthly setup            | ~5              |
| assets               | Occasional               | ~2              |
| liabilities          | Occasional               | ~1              |

Total finance DB: ~72 writes/user/month = ~2.4 writes/user/day  
At 1,000 users: ~2,400 writes/day = 0.03 writes/sec (very low)  
At 50,000 users: ~120,000 writes/day = 1.4 writes/sec (still manageable single node)

---

## 2. Service Performance Profile

### 2.1 Response Time Budget

| Service              | P50    | P95    | P99    | Timeout | Type      |
|----------------------|--------|--------|--------|---------|-----------|
| API Gateway (routing)| <5ms   | <20ms  | <50ms  | —       | Proxy     |
| User Service (login) | 80ms   | 200ms  | 500ms  | 30s     | Sync      |
| User Service (me)    | 20ms   | 80ms   | 200ms  | 30s     | Sync      |
| Finance CRUD         | 30ms   | 100ms  | 300ms  | 30s     | Sync      |
| Finance Health Score | 100ms  | 300ms  | 600ms  | 30s     | Sync+DB   |
| Finance Net Worth    | 80ms   | 250ms  | 500ms  | 30s     | Sync+DB   |
| AI Recommend (cache) | <10ms  | <20ms  | <50ms  | —       | Redis hit |
| AI Recommend (fresh) | 5–15s  | 20s    | 40s    | 60s     | Claude API|
| Statement Analysis   | 10–30s | 45s    | 55s    | 60s     | Claude API|
| Notification list    | 20ms   | 80ms   | 200ms  | 30s     | Sync      |

### 2.2 Memory Footprint per Container (idle)

| Service              | RAM (idle) | RAM (under load) |
|----------------------|------------|------------------|
| API Gateway          | 80 MB      | 150 MB           |
| User Service         | 100 MB     | 200 MB           |
| Finance Service      | 120 MB     | 250 MB           |
| Bank Service         | 90 MB      | 200 MB           |
| Statement Analysis   | 200 MB     | 450 MB           |
| AI Recommendation    | 200 MB     | 450 MB           |
| Notification Service | 90 MB      | 180 MB           |
| PostgreSQL (each)    | 100 MB     | 500 MB           |
| Redis                | 30 MB      | 200 MB           |
| Kafka + Zookeeper    | 400 MB     | 800 MB           |
| ChromaDB             | 150 MB     | 400 MB           |

**Total minimum RAM for all services:** ~2.0 GB idle, ~4.5 GB under moderate load

---

## 3. Bottleneck Analysis

### 3.1 Critical Path Bottlenecks

```
RANK  BOTTLENECK                 WHY                        MITIGATION
────  ─────────────────────────  ─────────────────────────  ──────────────────────────
 1    Anthropic API rate limits  5 req/min free tier        Cache 1h, batch requests
      & latency (5–20s)          $3–15/M tokens billed      Use haiku for simple tasks
 2    Finance DB (postgres)      Most tables + most writes  Connection pooling (pgBouncer)
      under high write load      Single node limit          Read replicas for analytics
 3    Kafka consumer lag         Statement analysis slow     Increase consumer partitions
      during burst uploads       Single consumer thread     Add statement-analysis replicas
 4    Health Score computation   Queries 8 tables per call  Cache result 5min per user
      (8 DB queries per request) No pre-computation         Background pre-compute
 5    JWT token refresh          Every 30min per user       Access token TTL tuning
      thundering herd            All tokens expire at once  Staggered expiry (random ±5min)
```

### 3.2 Non-Critical Bottlenecks

| Bottleneck                   | Impact  | When triggered              | Fix                              |
|------------------------------|---------|-----------------------------|----------------------------------|
| ChromaDB query latency       | Medium  | >10k vectors stored         | Index tuning, HNSW params        |
| Redis memory at scale        | Low     | >100k users                 | Eviction policy, Redis Cluster   |
| Notification fan-out         | Low     | Broadcast events            | Batch processing, async queue    |
| S3 upload bandwidth          | Low     | Many concurrent uploads     | Multipart upload, direct S3 PUT  |

---

## 4. Scaling Thresholds

When to scale each service (add replicas or upgrade instance):

| Service              | Scale trigger                      | Action                          |
|----------------------|------------------------------------|---------------------------------|
| API Gateway          | CPU > 70% OR p95 latency > 100ms   | Add replicas (stateless)        |
| Finance Service      | CPU > 60% OR DB connections > 80   | Add replicas + pgBouncer        |
| User Service         | CPU > 60%                          | Add replicas (stateless)        |
| Finance DB           | CPU > 50% OR connections > 100     | Read replica OR upgrade node    |
| Statement Analysis   | Queue lag > 30s                    | Add replicas (Kafka partitions) |
| AI Recommendation    | Cache miss rate > 30%              | Extend TTL OR add replicas      |
| Redis                | Memory > 70%                       | Upgrade OR Redis Cluster        |
| Kafka                | Consumer lag > 1000 msgs           | Add partitions + consumers      |

---

## 5. Cost Analysis — Deployment Options

### Option A: Self-Managed VPS (Hetzner) — Cheapest

Best for: Startups, <5,000 users, cost-sensitive

```
Infrastructure:
  3× CX21 App Nodes  (2 vCPU / 4 GB RAM)   €12.49/mo each  = €37.47/mo
  1× CX31 DB Node    (2 vCPU / 8 GB RAM)   €17.49/mo       = €17.49/mo
  1× CX21 Infra Node (Kafka + ChromaDB)     €12.49/mo       = €12.49/mo
  Hetzner Load Balancer                      €5.39/mo        =  €5.39/mo
  Hetzner Volume 50GB (backups)              €2.50/mo        =  €2.50/mo
                                                               ──────────
  Infrastructure subtotal                                     €75.34/mo
  ≈ $82/mo

Third-party APIs (variable):
  Anthropic Claude API        see Section 7
  AWS S3 (statements)         ~$2/mo (10GB storage + transfers)
  SMTP (Gmail / Sendgrid free tier)  $0
  OneSignal (free tier 10k subs)     $0
                                               ──────────
  API subtotal (light usage)                   ~$2/mo

TOTAL (light usage, <500 active users):       ~$84/mo
TOTAL (moderate, 1,000–2,000 active users):   ~$100–130/mo
```

**Pros:** Cheapest raw cost, full control  
**Cons:** You manage upgrades, backups, SSL certs, monitoring setup

---

### Option B: DigitalOcean Managed — Easy Mid-tier

Best for: 500–10,000 users, want managed DB/Redis

```
App Platform / Droplets:
  3× Basic Droplets  (2 vCPU / 4 GB)        $24/mo each     = $72/mo
  1× Droplet         (2 vCPU / 4 GB, Kafka)  $24/mo         = $24/mo

Managed Services:
  DO Managed PostgreSQL (Basic, 1 vCPU/1GB)  $15/mo × 4 DBs = $60/mo
  DO Managed Redis      (Basic, 1 GB)         $15/mo         = $15/mo
  DO Load Balancer                             $12/mo         = $12/mo
  DO Spaces (S3-compatible, 250GB)             $5/mo          =  $5/mo
                                                               ──────────
  Infrastructure subtotal                                      $188/mo

APIs:
  Anthropic Claude API        see Section 7
  SMTP Sendgrid (100/day free)               $0–$20/mo
                                               ──────────
  API subtotal                                ~$5–25/mo

TOTAL (light usage):          ~$193/mo
TOTAL (moderate, ~2,000 users): ~$210–250/mo
```

**Pros:** Managed DB backups, SSL auto-renew, simple scaling  
**Cons:** More expensive than Hetzner; still need to manage K8s or Compose

---

### Option C: AWS EKS — Enterprise

Best for: >10,000 users, compliance requirements, enterprise

```
Compute:
  EKS Cluster Control Plane                  $0.10/hr        = $72/mo
  3× t3.medium nodes (2 vCPU / 4 GB)        $0.0416/hr ×3   = $89.9/mo
  1× t3.large node   (2 vCPU / 8 GB, infra) $0.0832/hr      = $59.9/mo

Managed Databases:
  RDS PostgreSQL db.t3.micro × 4             $0.017/hr ×4    = $48.9/mo
  RDS Multi-AZ upgrade (HA) × 4             ×2 multiplier   = $97.9/mo
  ElastiCache Redis cache.t3.micro            $0.017/hr       = $12.2/mo

Messaging / Storage:
  Amazon MSK (Kafka) kafka.t3.small          $0.096/hr       = $69.1/mo
  S3 (50GB + 10GB transfer)                                  =  $1.5/mo
  ALB Load Balancer                           $0.008/hr+LCU  = ~$18/mo

Networking:
  NAT Gateway                                $0.045/hr       = $32.4/mo
  Data Transfer (100GB/mo)                   $0.09/GB        =  $9/mo
                                                               ──────────
  Infrastructure subtotal (without HA DB)                     $413/mo
  Infrastructure subtotal (with HA DB)                        $511/mo

APIs:
  Anthropic Claude API        see Section 7
  SES Email (1k emails/mo)                   $0.10/1k        = ~$0.10/mo
                                               ──────────
TOTAL (without HA):           ~$420/mo
TOTAL (with HA Multi-AZ DB):  ~$520/mo
TOTAL (2,000 users, moderate): ~$450–550/mo
```

**Pros:** Best reliability, compliance, auto-scaling, managed everything  
**Cons:** Most expensive; complex billing; hard to predict costs

---

### Option D: Vercel (Frontend) + Railway/Render (Backend) — Simplest

Best for: Solo developer, MVP, proof of concept

```
Frontend:
  Vercel Pro                                  $20/mo

Backend (Railway):
  7 services × ~$5–15/mo each                ~$50–100/mo
  4× Postgres DB (Railway managed)            ~$20–40/mo
  Redis (Railway)                              $5/mo
  Note: Kafka not available — use Redis pub/sub or NATS instead
  ChromaDB (self-host on Railway or skip)     $5–10/mo

APIs:
  Anthropic                   see Section 7
                                               ──────────
TOTAL:                        ~$100–175/mo
```

**Pros:** Zero ops, deploy from git, great for MVP  
**Cons:** Kafka not native (needs replacement); vendor lock-in; limited control

---

## 6. Cost by User Count

Estimated total monthly cost (infrastructure + APIs) across options:

| Active Users | Option A (Hetzner) | Option B (DO)  | Option C (AWS) | Option D (Railway) |
|-------------|-------------------|----------------|----------------|--------------------|
| 100         | $84               | $193           | $420           | $110               |
| 500         | $95               | $200           | $430           | $130               |
| 1,000       | $110              | $215           | $450           | $155               |
| 2,000       | $130              | $240           | $470           | $185               |
| 5,000       | $200*             | $350*          | $530           | —                  |
| 10,000      | $350*             | $550*          | $650           | —                  |
| 50,000      | $900*             | $1,400*        | $1,800         | —                  |

*Requires adding nodes / upgrading DB tier  
API costs (Anthropic) not included — see Section 7

**Cost per user per month:**

| Active Users | Option A | Option B | Option C |
|-------------|----------|----------|----------|
| 100         | $0.84    | $1.93    | $4.20    |
| 1,000       | $0.11    | $0.22    | $0.45    |
| 10,000      | $0.035   | $0.055   | $0.065   |
| 50,000      | $0.018   | $0.028   | $0.036   |

Infrastructure unit cost drops sharply with scale — typical SaaS pattern.

---

## 7. AI API Cost Breakdown

### 7.1 Anthropic Claude Pricing (as of 2026)

Model used: **claude-sonnet-4-6**

| Token type   | Price             |
|--------------|-------------------|
| Input tokens | $3.00 / 1M tokens |
| Output tokens| $15.00 / 1M tokens|

### 7.2 AI Usage per Feature

| Feature                    | Service            | Input tokens | Output tokens | Cost/call |
|----------------------------|--------------------|-------------|---------------|-----------|
| Statement analysis (10pg PDF) | statement-analysis | ~8,000    | ~3,000        | $0.069    |
| Statement analysis (2pg PDF)  | statement-analysis | ~2,000    | ~800          | $0.018    |
| AI Recommendations (fresh) | ai-recommendation  | ~2,500      | ~1,500        | $0.030    |
| AI Recommendations (cached)| ai-recommendation  | 0           | 0             | $0.000    |

### 7.3 Monthly AI Cost by Usage Pattern

**Assumptions:**
- Statement analysis: 20% of users upload 1 statement/month
- AI recommendations: 40% of users generate fresh (cache miss) once/week
- Cache hit rate: 70% (users share same daily recommendation window)

| Active Users | Stmt Analysis/mo | Reco calls/mo (fresh) | Monthly AI Cost |
|-------------|------------------|-----------------------|-----------------|
| 100         | 20 calls         | 17 calls              | $1.89           |
| 500         | 100 calls        | 83 calls              | $9.43           |
| 1,000       | 200 calls        | 165 calls             | $18.87          |
| 5,000       | 1,000 calls      | 827 calls             | $94.3           |
| 10,000      | 2,000 calls      | 1,653 calls           | $188.6          |
| 50,000      | 10,000 calls     | 8,267 calls           | $943            |

### 7.4 AI Cost Optimisation

| Strategy                           | Savings | Implementation                              |
|------------------------------------|---------|---------------------------------------------|
| Use `claude-haiku-4-5` for simple reco | 95% | Switch model for low-complexity queries    |
| Extend recommendation cache to 24h    | 70% | Change `RECOMMENDATION_CACHE_TTL=86400`    |
| Batch statement analysis               | 20% | Process off-peak, queue multiple pages     |
| Per-user cache key (not global)        | —   | Already implemented (per user_id)          |
| Prompt compression                     | 15% | Reduce context sent to AI                  |

**With haiku model for recommendations + 24h cache:**

| Active Users | Monthly AI Cost (default) | Monthly AI Cost (optimised) |
|-------------|--------------------------|------------------------------|
| 1,000       | $18.87                   | $4.20                        |
| 10,000      | $188.6                   | $42.0                        |
| 50,000      | $943                     | $210                         |

---

## 8. Cost Optimisation Strategies

### 8.1 Infrastructure

| Strategy                              | Savings   | Complexity | When to apply           |
|---------------------------------------|-----------|------------|-------------------------|
| Use Hetzner over AWS                  | 60–75%    | Medium     | Before product-market fit|
| Spot/Preemptible instances (stateless)| 50–70%    | High       | >5,000 users             |
| Single shared PostgreSQL (dev/staging)| $45/mo    | Low        | Non-prod only            |
| Combine Kafka + ChromaDB on one node  | $15–20/mo | Low        | <5,000 users             |
| Reserved instances (1yr AWS)          | 30–40%    | Low        | Steady state at scale    |
| Disable unused services (staging)     | 30%       | Low        | Always for staging       |

### 8.2 Application Level

| Strategy                              | Savings   | Implementation                        |
|---------------------------------------|-----------|---------------------------------------|
| Cache Health Score per user (5 min)   | DB queries| Add Redis cache key per user_id       |
| Cache Net Worth per user (5 min)      | DB queries| Same pattern                          |
| Paginate expense list (default 20)    | Response  | Already paginated                     |
| Background analytics pre-compute      | Latency   | Cron job at midnight per user         |
| Compress Kafka messages               | Bandwidth | Enable `compression.type=lz4`         |
| S3 lifecycle policy (archive >90d)    | Storage   | S3 Glacier after 90 days              |

### 8.3 Quick Wins (implement now, zero cost)

1. **`RECOMMENDATION_CACHE_TTL=86400`** in `.env` — 24h cache instead of 1h → 70% fewer Anthropic calls
2. **Health Score Redis cache** — 5-minute cache per user prevents 8-query DB hit on every page load
3. **S3 lifecycle rule** — auto-archive statements older than 90 days to Glacier ($0.004/GB vs $0.023/GB)
4. **Kafka message retention** — set `retention.ms=604800000` (7 days) instead of default (no limit)
5. **PostgreSQL `idle_in_transaction_session_timeout=30000`** — kills abandoned transactions

---

## 9. Recommendations

### 9.1 Startup Phase (0–500 users)

**Use Option D (Railway/Render) or Option A (Hetzner)**

```
Monthly budget target:  $80–130
Recommended stack:
  ✅ Hetzner CX21 ×2 (all services via Docker Compose)
  ✅ Hetzner Managed Postgres (or CX31 self-hosted)
  ✅ Redis on same node
  ✅ Skip Kafka — use polling / direct calls (simplify)
  ✅ Skip ChromaDB — use basic AI without vector memory
  ✅ Vercel for frontend (free tier)
  ✅ Anthropic haiku model for AI

Estimated cost:  $70–90/mo + Anthropic $2–5/mo = ~$80–95/mo
```

### 9.2 Growth Phase (500–5,000 users)

**Use Option B (DigitalOcean Managed) or Option A with more nodes**

```
Monthly budget target:  $200–400
Recommended stack:
  ✅ 3× Hetzner CX21 OR DigitalOcean Droplets
  ✅ Managed PostgreSQL (DO or Hetzner)
  ✅ Managed Redis
  ✅ Introduce Kafka (self-hosted on dedicated node)
  ✅ ChromaDB (on infra node)
  ✅ Switch to Kubernetes (K3s or full K8s)
  ✅ Add Prometheus + Grafana monitoring

Estimated cost:  $180–220/mo infra + $15–50/mo Anthropic = ~$200–270/mo
```

### 9.3 Scale Phase (5,000+ users)

**Use Option C (AWS EKS)**

```
Monthly budget target:  $500–2,000+
Recommended stack:
  ✅ AWS EKS with auto-scaling node groups
  ✅ RDS PostgreSQL Multi-AZ (High Availability)
  ✅ ElastiCache Redis Cluster mode
  ✅ Amazon MSK (managed Kafka)
  ✅ CloudFront CDN for frontend
  ✅ WAF for API Gateway
  ✅ Separate read replicas for analytics queries

Estimated cost:  $500–800/mo infra + $100–500/mo Anthropic
```

### 9.4 Priority Optimisations (implement in order)

```
Priority  Action                           Savings   Effort
────────  ───────────────────────────────  ────────  ──────
   1      Set RECOMMENDATION_CACHE_TTL     $15/mo    5 min
          to 86400 in .env                           (env var change)

   2      Add Health Score Redis cache     DB load   2 hours
          (5-min per-user TTL)                       (code change)

   3      Switch AI reco to haiku model    70–90%    30 min
          for low-complexity insights      on AI     (env var change)

   4      Hetzner instead of AWS           60%       1–2 days
          for first 2,000 users            infra     (migration)

   5      S3 lifecycle → Glacier 90d       80%       30 min
          for old statements               storage   (AWS console)

   6      pgBouncer connection pooling     DB        1 day
          before adding DB replicas        headroom  (config)
```

---

## Summary Table

| Scenario              | Users  | Infra/mo | AI API/mo | Total/mo |
|-----------------------|--------|----------|-----------|----------|
| MVP (Hetzner)         | <500   | $82      | $5        | **$87**  |
| Growth (DO Managed)   | ~2,000 | $210     | $20       | **$230** |
| Scale (AWS EKS)       | ~10,000| $470     | $90       | **$560** |
| Scale (AWS, HA DB)    | ~10,000| $570     | $90       | **$660** |
| Enterprise (AWS)      | ~50,000| $1,200   | $450      | **$1,650**|
| Enterprise (optimised)| ~50,000| $900     | $100      | **$1,000**|

> All costs in USD. Anthropic pricing may change.  
> "Optimised" = haiku model for recommendations + 24h cache + spot instances.

---

*For infrastructure setup details see `DEPLOYMENT_STRATEGY.md`.*  
*For service architecture see `System_Architecture_Diagram.md`.*
