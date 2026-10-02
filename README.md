# NovaPulse Multi-Tenant SaaS Platform (Production FastAPI Masterclass)

A complete, production-grade Multi-Tenant Software-as-a-Service (SaaS) backend built with **FastAPI**, **Async SQLAlchemy 2.0**, **Pydantic v2**, **Alembic**, **Argon2 + JWT Authentication**, **Hierarchical RBAC Dependency Injection**, and **Real-Time WebSockets**.

> 📖 **Full Engineering Specification & Master Guide**: For the complete **Business Requirements Document (BRD)**, **Technical Specifications (TSD)**, **System Architecture Diagrams**, **Component Map**, and **Micro-to-Macro Build Guide**, see [DOCUMENTATION.md](DOCUMENTATION.md).

---

## 🏗️ Architectural Overview & Design Decisions

In real-world production engineering, putting database queries, route handlers, and business logic into single files creates technical debt. NovaPulse follows a strict **Clean Layered Architecture**:

```
fastAPI/
├── app/
│   ├── api/                     # 🌐 Presentation Layer (HTTP & WebSockets)
│   │   ├── deps.py              # FastAPI Dependency Injection (Auth, Tenant, RBAC)
│   │   └── v1/                  # API Version 1 Routers
│   │       ├── api_router.py    # Master router aggregation
│   │       ├── auth.py          # /auth (Register, Login, Refresh, Me)
│   │       ├── tenants.py       # /workspaces (CRUD, Member Management)
│   │       ├── projects.py      # /projects (Tenant-isolated Projects)
│   │       ├── tasks.py         # /tasks (Tasks with real-time push)
│   │       ├── websockets.py    # /ws/{tenant_id} (Real-time Workspace feed)
│   │       └── audit_logs.py    # /audit-logs (Security & compliance audit trail)
│   ├── core/                    # ⚙️ Infrastructure & Configuration
│   │   ├── config.py            # Pydantic v2 BaseSettings (Type-safe .env parsing)
│   │   ├── database.py          # Async SQLAlchemy 2.0 engine & get_db generator
│   │   ├── security.py          # Argon2id hashing & JWT encode/decode
│   │   ├── exceptions.py        # Centralized domain exception handlers
│   │   └── logging.py           # Structured logging configuration
│   ├── models/                  # 🗄️ Persistence Layer (SQLAlchemy 2.0 Declarative)
│   │   ├── base.py              # TimestampedBase with UUIDv4 Primary Keys
│   │   ├── user.py              # Users table
│   │   ├── tenant.py            # Tenants (Workspaces) table
│   │   ├── membership.py        # TenantMember table & TenantRole enum hierarchy
│   │   ├── project.py           # Projects and Tasks tables
│   │   └── audit_log.py         # AuditLogs table
│   ├── schemas/                 # 📐 Contract & Validation Layer (Pydantic v2)
│   │   ├── auth.py              # Auth request & token schemas
│   │   ├── user.py              # User read/update schemas
│   │   ├── tenant.py            # Workspace & membership schemas
│   │   ├── project.py           # Project & Task validation schemas
│   │   └── audit_log.py         # AuditLog output schemas
│   ├── services/                # 💼 Domain & Business Logic Layer
│   │   ├── auth_service.py      # Registration & authentication workflows
│   │   ├── tenant_service.py    # Tenant lifecycle & member permissions
│   │   ├── project_service.py   # Tenant-isolated business queries
│   │   ├── audit_service.py     # Asynchronous event auditing
│   │   └── notification_service.py # In-memory WebSocket manager with tenant channels
│   └── main.py                  # 🚀 FastAPI App Factory, Lifespan, CORS, Middleware
├── alembic/                     # 🔄 Alembic Async Migrations
├── scripts/
│   └── seed_demo_data.py        # Initial mock tenant dataset
├── tests/                       # 🧪 Automated Test Suite (Pytest + HTTPX)
│   ├── conftest.py              # In-memory async SQLite fixtures & TestClient
│   ├── test_auth.py             # Auth & profile verification
│   ├── test_multi_tenancy.py    # Tenant isolation & RBAC boundary tests
│   └── test_tasks_and_audit.py  # Task workflows & audit verification
├── requirements.txt
└── .env
```

---

## 🔑 Key Concepts You Learn in this Project

### 1. Modern Dependency Injection (`Depends`)
- **`get_current_user`**: Decodes JWT, validates active account, injects user object.
- **`get_current_membership`**: Intercepts `X-Tenant-ID` header or path parameter and verifies the user belongs to that workspace.
- **`require_role(min_role)`**: A dependency factory enforcing RBAC rank (`VIEWER` < `MEMBER` < `ADMIN` < `OWNER`).

### 2. Multi-Tenant Data Isolation (Preventing Data Leaks)
In multi-tenant SaaS, the #1 vulnerability is cross-tenant leakage. In NovaPulse:
- Every query is scoped to `tenant_id` from the verified membership dependency.
- Even if an attacker knows a project UUID, querying with their own tenant ID returns `404 Not Found`.

### 3. Async SQLAlchemy 2.0 with Session Lifecycle
- Uses `async_sessionmaker(bind=engine, expire_on_commit=False)`
- The `get_db()` async generator commits automatically if no exception occurs, rolls back upon any error, and guarantees connection return to the pool in `finally`.

### 4. Real-Time WebSockets Scoped by Workspace
- Connect via `ws://127.0.0.1:8000/api/v1/ws/{tenant_id}?token=<jwt>`
- Broadcasts updates (such as task state changes) strictly to clients connected to that workspace.

### 5. Production Observability
- Every request passes through a custom ASGI middleware that injects an `X-Request-ID` and measures exact elapsed latency in `X-Process-Time`.

---

## 🚀 Quickstart Guide

### 1. Activate Virtual Environment
```powershell
.venv\Scripts\Activate.ps1
```

### 2. Run Database Migrations
```powershell
.venv\Scripts\alembic.exe upgrade head
```

### 3. Seed Demo Data
```powershell
.venv\Scripts\python.exe scripts/seed_demo_data.py
```
This populates:
- **Owner**: `owner@novapulse.io` / `Password123!`
- **Admin**: `admin@novapulse.io` / `Password123!`
- **Member**: `dev@novapulse.io` / `Password123!`
- Workspace: **Acme Corporation**

### 4. Start the Production Server
```powershell
.venv\Scripts\uvicorn.exe app.main:app --reload --port 8000
```

### 5. Explore Swagger Interactive Docs
Navigate in your browser to:
- **Interactive OpenAPI Documentation**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc Alternative Docs**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **Health Check Probe**: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

---

## 🧪 Running Automated Tests
Run the complete asynchronous test suite:
```powershell
.venv\Scripts\pytest.exe -v
```
All tests execute against an isolated in-memory async SQLite engine with zero side-effects.
