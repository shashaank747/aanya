# Aanya — Self-Hosted Personal AI Assistant (Foundation)

Aanya is a self-hosted personal AI assistant designed to run on private infrastructure, accessible securely from Android Chrome and desktop Chrome as an installable Progressive Web App (PWA).

This repository contains the **Initial Foundation Phase** of Aanya. It provides a clean, secure, modular monolith with FastAPI, PostgreSQL, Alembic migrations, APScheduler, Caddy reverse-proxying with automatic HTTPS, and a mobile-first PWA welcome dashboard.

---

## 1. System Architecture

```text
aanya/
├── backend/
│   ├── core/                  # Core infrastructure
│   │   ├── config.py          # Pydantic Settings & environment validation
│   │   ├── database.py        # SQLAlchemy 2.x engine, SessionLocal & health check
│   │   ├── coordinator.py     # Intent routing boundary for assistant requests
│   │   └── scheduler.py       # APScheduler lifecycle & persistence diagnostics
│   ├── schemas/               # Standard response envelopes and API schemas
│   ├── modules/               # Modular capability packages (placeholders)
│   │   ├── jobs/              # Job application tracking
│   │   ├── finance/           # Income & expense ledger
│   │   ├── ocr/               # Document and receipt scanning
│   │   ├── math_logic/        # Deterministic math and reasoning utilities
│   │   └── reminders/         # Scheduled alerts and push notifications
│   ├── tests/                 # Comprehensive automated test suite
│   ├── alembic/               # Alembic database migrations & versions
│   ├── alembic.ini            # Migration configuration
│   ├── app.py                 # FastAPI application & centralized exception handling
│   ├── Dockerfile             # Hardened container image running as non-root user
│   └── requirements.txt       # Pinned backend dependencies
├── frontend/                  # Mobile-first PWA frontend
│   ├── index.html             # Welcome dashboard with live health verification
│   ├── manifest.json          # Web app manifest for standalone mobile/desktop PWA
│   ├── service-worker.js      # Static asset cache with strict no-API-cache policy
│   └── static/
│       ├── css/styles.css     # Clean responsive styling (no unpinned 3rd-party CDN)
│       ├── js/app.js          # Health polling, coordinator routing preview & PWA install
│       └── icons/             # 192x192, 512x512 PNG and SVG application icons
├── Caddyfile                  # Reverse proxy, static file server & automatic HTTPS
├── docker-compose.yml         # Multi-container orchestration (db, backend, caddy)
├── .env.example               # Documented template for configuration & secrets
├── .gitignore                 # Exclusion rules for secrets, DBs, and Python caches
├── pytest.ini                 # Pytest configuration
└── README.md                  # Documentation and operations manual
```

---

## 2. Technology Stack

- **Backend:** Python 3.12+ with FastAPI.
- **Database:** PostgreSQL 16 with SQLAlchemy 2.x ORM and `psycopg` v3 driver.
- **Migrations:** Alembic.
- **Configuration & Validation:** Pydantic v2 and `pydantic-settings`.
- **Background Tasks:** APScheduler (with lifecycle management and persistence documentation).
- **Web & HTTPS Proxy:** Caddy 2 with automatic TLS certificate provisioning.
- **Frontend & PWA:** Semantic HTML5, modern vanilla CSS, vanilla JavaScript, web app manifest, and service worker.
- **Testing:** Pytest and HTTPX.

---

### 3. Quick Start with Docker Compose

> [!NOTE]
> Docker Compose deployment requires Docker Engine 24+ and Docker Compose v2. On environments lacking Docker, use the verified **Local Development / Direct Execution** commands in Section 4.

#### Step 1: Configure Environment
```bash
cp .env.example .env
```
Customize values in `.env`:
```env
ENVIRONMENT=production
SECRET_KEY=generate_a_secure_random_32_byte_hex_string
POSTGRES_USER=aanya_user
POSTGRES_PASSWORD=choose_a_strong_database_password
POSTGRES_DB=aanya_db
DOMAIN_NAME=localhost
```

#### Step 2: Build and Launch Containers
```bash
docker compose up -d --build
```

#### Step 3: Apply Database Migrations
```bash
docker compose exec backend alembic -c backend/alembic.ini upgrade head
```

---

## 4. Local Execution & Development Setup (Verified)

Both the FastAPI backend and the static PWA frontend can be executed directly in Python:

### 1. Virtual Environment Setup
```powershell
# Windows PowerShell
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r backend/requirements.txt
```

### 3. Run Automated Tests
```bash
pytest
```
*Verification status: All 21 automated unit and integration tests passing.*

### 4. Apply Database Migrations
```powershell
# Using SQLite for local testing:
$env:DATABASE_URL="sqlite:///./aanya_dev.db"
alembic -c backend/alembic.ini upgrade head
```

### 5. Start Server
```bash
uvicorn backend.app:app --host 127.0.0.1 --port 8000 --reload
```
Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser:
* **Frontend UI & PWA Shell:** `http://127.0.0.1:8000/`
* **API Health Check:** `http://127.0.0.1:8000/api/health`
* **PWA Web App Manifest:** `http://127.0.0.1:8000/manifest.json`
* **Service Worker:** `http://127.0.0.1:8000/service-worker.js`
* **API Documentation:** `http://127.0.0.1:8000/docs` (in non-production mode)

---

## 5. Security Baseline

1. **Non-Root Execution:** The backend container runs under a dedicated unprivileged user (`aanya`, UID 1000).
2. **Database Isolation:** PostgreSQL port `5432` is attached strictly to the internal Docker bridge network (`aanya_internal`) and is **never exposed to the public internet**.
3. **No Hardcoded Secrets:** All secrets, database URLs, and cryptographic keys are loaded dynamically via `pydantic-settings`. `.gitignore` prevents inadvertent commits of `.env` or certificates.
4. **Service Worker Data Policy:** The PWA Service Worker explicitly bypasses `/api/*` requests (`network-only`). No user queries, authentication tokens, or AI responses are stored in browser caches.
5. **CORS Restrictions:** Configured via `ALLOWED_ORIGINS` in `.env`, restricting API access to designated origins.
6. **Authentication Warning:** Authentication is **not implemented in this foundation phase**. Do not expose this service to the public internet without an upstream reverse-proxy authentication layer (e.g., Authelia, Cloudflare Access) until native authentication is implemented.

---

## 6. Architecture Boundaries & Future Roadmap

### Coordinator (`backend/core/coordinator.py`)
Provides the single routing entry point for incoming user queries. It decouples the user-facing interface from the underlying execution logic:
- In this foundation phase, it utilizes deterministic pattern matching and schema validation.
- In future phases, it will integrate intent classification models and dispatch requests directly to the feature modules.

### Feature Modules (`backend/modules/`)
1. **`finance` (ACTIVE FIRST MODULE):** Complete income & expense tracking with PostgreSQL `NUMERIC(12, 2)` precision, deterministic SQL monthly totals, net balance, category breakdown, paginated transactions, and a natural-language parsing engine with explicit confirmation workflows:
   - `GET /api/finance/dashboard`: Authoritative monthly totals & category breakdown
   - `POST /api/finance/transactions`: Create new income/expense transaction
   - `GET /api/finance/transactions`: Filtered, paginated transaction history
   - `GET /api/finance/transactions/{id}`: Single transaction details
   - `PUT /api/finance/transactions/{id}`: Partial/full transaction update
   - `DELETE /api/finance/transactions/{id}`: Delete transaction
   - `POST /api/finance/parse-natural-language`: Natural-language entry parser (returns draft requiring user confirmation)
   - `GET /api/finance/categories` & `GET /api/finance/payment-methods`: Standard configuration lists
2. `jobs`: Application pipelines, company trackers, interview notes (`/api/jobs`).
3. `ocr`: Document and receipt text extraction (`/api/ocr`).
4. `math_logic`: High-precision deterministic calculation utilities and equation parsing (`/api/math-logic`).
5. `reminders`: Time-based alerts and WebPush notifications (`/api/reminders`).

### Scheduler & Reminders Persistence Notice
The scheduler runs APScheduler's `BackgroundScheduler` in an in-memory mode during this initial phase.
- **In-memory jobs do NOT survive container or service restarts.**
- Before reminders and push notifications are production-ready:
  1. A persistent job store must be enabled via `SQLAlchemyJobStore(url=settings.DATABASE_URL)`.
  2. The `apscheduler_jobs` table migration must be applied.
  3. WebPush / VAPID keys must be configured for background push delivery.

---

## 7. Backup and Recovery Strategy

To ensure persistent data preservation:
1. **Docker Volume:** Database files reside in the named volume `aanya_db_data`.
2. **Automated Logical Backups:**
   ```bash
   # Create a timestamped compressed database backup
   docker compose exec -T db pg_dump -U aanya_user aanya_db | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz
   ```
3. **Database Restore:**
   ```bash
   # Restore from backup
   gunzip < backup_YYYYMMDD_HHMMSS.sql.gz | docker compose exec -T db psql -U aanya_user aanya_db
   ```
