# TicketFlow Engine - Event & Ticket Management Backend

[![CI Pipeline](https://img.shields.io/badge/CI-GitHub_Actions-blue.svg)](.github/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.13-informational.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/Framework-FastAPI-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Asynchronous backend package for event scheduling and concurrent ticket sales. Built with Python using Clean Architecture principles, Data Mapper Pattern (Thin Repositories), and a custom Fluent API Query Builder.

The system features advanced asynchronous task queuing, strict data validation pipelines, infrastructure monitoring dashboards, and security isolation designed to handle high-load traffic during peak ticket sales windows.

## Technical Highlights

* **Clean Architecture and Thin Repository Pattern:** Business logic is fully decoupled from the HTTP layer (FastAPI) and Infrastructure layer (SQLAlchemy). Classes inherited from `GenericRepository` act as purely declarative wrappers, eliminating procedural SQL/ORM leaking into core domains.
* **Custom Fluent API Query Builder:** Features a robust DSL abstraction layer built on top of `RepositoryQuery`. It enables complex chainable operations (`.filter()`, `.update()`, `.delete()`, `.get()`, `.paginate()`) directly within the Service layer, ensuring 100% database engine swapability.
* **ORM-Agnostic Relationship Loading:** Advanced eager-loading engines (`with_joined`, `with_selectin`) accept standardized nested strings using double underscores (`items__category__event`) to resolve deep relation loops, hiding raw ORM attributes from business logic.
* **Distributed Idempotency Layer:** Real-time protection for financial and critical endpoints (`/pay`, `/book`) using atomic distributed locking and response-caching via a custom API decorator backed by Redis.
* **Sliding Window Rate Limiter:** High-performance rate limiting middleware preventing brute-force login attempts and DDoS attacks on checkout/check-in routes.
* **Cartesian Product Elimination:** Specialized subquery optimization utilizing strict `IN` array matching for nested updates and deletions, guaranteeing maximum execution speed on PostgreSQL without creating relational cartesian locks.
* **Asynchronous Background Processing:** Native integration with TaskIQ for non-blocking task orchestration and scheduled lock-releases for expired, unpaid ticket reservations.
* **High-Performance Telemetry System:** Real-time event view counter engine powered by memory-efficient Redis HyperLogLog (`PFADD`, `PFCOUNT`) structures, ensuring fast deduplication of unique visitor interactions.
* **Production Monitoring Stack:** Native Prometheus metrics engine paired with Grafana dashboards to track latency percentiles, error rates, and request throughput in real time.
* **Comprehensive Integration Testing & CI:** Automated GitHub Actions workflows executing linters (Ruff, Mypy), dependency vulnerability audits, and test suites with code coverage reporting.
* **Delayed Data Processing Via a Queue**: Parts of the system that do not require an immediate response to the user are processed via an Apache Kafka queue - this helps reduce the load on the server and database.
* **Promotional Discount Engine:** Integrated voucher validation system supporting percentage-based and fixed-amount price deductions with redemption quota limits.
* **Organizer Analytics & Data Export:** Real-time event sales summaries, attendee check-in rates, and instant CSV attendee list exports for event organizers.

## Tech Stack

* **Package Manager:** uv
* **Framework:** FastAPI
* **Database ORM:** SQLAlchemy 2.0 (AsyncIO) and Alembic (PostgreSQL)
* **Validation:** Pydantic v2
* **Task Queue:** TaskIQ and TaskIQ-Redis
* **Distributed Cache:** KeyDB (High-performance Redis multi-threaded alternative)
* **Telemetry Engine:** Prometheus Client & Grafana UI
* **Testing:** Pytest, Pytest-asyncio, and Httpx
* **Containerization:** Docker and Docker Compose

## Features

### User and Access Management
* Registration and authentication via cryptographically hashed passwords and JWT tokens.
* Weight-based role hierarchy including user, on_verification, verified_user, moderator, and admin.
* Automated ticket migration transferring anonymous ticket holdings to a user profile upon official registration.
* System Management CLI: Administrative commands executed within runtime containers to instantly seed privileged users or mock dataset.

### Event Orchestration
* Multi-level event categorization with parent path validation.
* Event drafts with complex cross-field validation rules restricting physical addresses to offline venues.
* Moderation workflows for newly submitted events and user verification applications.
* Scalable telemetry engine tracking dynamic view milestones across unique timeframes.

### Order Processing & High-Concurrency Ticket Sales
* Dynamic allocation of specialized ticket categories tied directly to specified event instances with strict total quantity boundaries.
* Atomic booking engine processing multi-ticket transactions under heavy concurrent load, preventing race conditions during checkout.
* Multi-state order lifecycle workflow tracking progression from initial reservation to formal verification and payment.
* Payment Gateway Integration supporting Stripe checkout sessions, mock payment sandbox, and asynchronous webhook verification.
* Automated task hooks releasing expired, unpaid order holdings and locked tickets back into available inventory after 15 minutes.
* Self-service order cancellation and ticket refund pipeline that dynamically restores category quotas and notifies customers.
* Asynchronous multilingual email notification engine (EN/RU) dispatching order confirmations and cancellation receipts.
* Ticket lifecycle controls with QR/ID ticket validation at venue check-in and peer-to-peer ticket transfer.

### Universal View Counting System

* The universal view counting system supports counting the number of views for any object in the project.
* Using queues and bulk inserts helps reduce the load on the database, reducing the number of queries by hundreds of times.
* The system counts views from any site visitor, filtering out duplicates and obvious fraud.
* The database is the single source of truth for viewings, preventing duplicate views from being registered by the same visitor.
* The view caching system reduces the load on the database by filtering out recent duplicate views.
* Storing views as immutable log entities speeds up the system and makes it independent of the actual state of objects.

## API Quick Reference

| Method | Endpoint | Description | Auth Required |
|---|---|---|:---:|
| `GET` | `/api/v1/health` | Subsystem health diagnostics & status | No |
| `POST` | `/api/v1/users` | Register a new user account | No |
| `POST` | `/api/v1/users/login` | Authenticate and obtain JWT access token | No |
| `GET` | `/api/v1/users/me` | Fetch authenticated user profile & roles | Yes |
| `POST` | `/api/v1/events` | Create new event draft (Organizer) | Yes (Verified) |
| `GET` | `/api/v1/events` | List all upcoming public events | No |
| `POST` | `/api/v1/orders` | Create ticket reservation order | Optional |
| `POST` | `/api/v1/orders/{id}/checkout` | Initialize Stripe / Mock payment session | Optional |
| `POST` | `/api/v1/orders/payment-webhook` | Payment gateway asynchronous webhook | No |
| `POST` | `/api/v1/orders/{id}/cancel` | Cancel order & process automated refund | Yes / Owner |
| `GET` | `/api/v1/tickets/{id}` | Inspect individual ticket details | Yes |
| `POST` | `/api/v1/tickets/{id}/check-in` | Validate ticket at entrance / venue | Yes (Organizer) |
| `POST` | `/api/v1/tickets/{id}/transfer` | Transfer ticket to another user | Yes (Owner) |

## File Structure

```text
.
├── docker-compose.yml                   # Core architecture foundation (API, DB, KeyDB, Workers & internal networks)
├── docker-compose.dev.yml               # Local development layer (Enables API hot-reload and local backend file mounts)
├── docker-compose.demo.yml              # Presentation layer (Deploys public Nginx reverse proxy routing)
├── docker-compose.test.yml              # Automated verification suite (Isolated containers for pytest, ruff, and mypy)
├── docker-compose.load.yml              # Load testing a project during local development or CI/CD (Container with locust)
├── docker-compose.telemetry.yml         # A metrics layer for analyzing server load and traffic (Prometheus and Graphana)
├── docker-compose.telemetry.dev.yml     # Forwards telemetry ports to the host machine for local development.
├── .env.example                         # Blueprint for required environment variables
├── .gitignore                           # Root Git exclusion rules
├── LICENSE                              # Project software license agreement
├── nginx.conf.template                  # Dynamic template for Nginx reverse proxy configurations
├── start.sh                             # A ready-made script for launching the required version of the project.
└── backend/                             # Core backend service directory
    ├── Dockerfile                       # Multi-stage container build rules (test, lint, backend) using uv
    ├── pyproject.toml                   # Main project metadata and tool configurations
    ├── uv.lock                          # Strict dependency lockfile
    ├── prometheus.yml                   # Prometheus config file
    ├── alembic.ini                      # Database migration configuration metadata
    ├── alembic/                         # Database migration scripts and environment
    ├── tests/                           # Integration test cases, fixtures, and conftest
    └── src/                             # Source root
        ├── app/                         # Application Assembly & Command Center
        │   ├── main.py                  # Main FastAPI application entrypoint and exception mapping
        │   ├── routes.py                # Global root router mounting point (/api/v1)
        │   ├── metrics.py               # Prometheus instrumentation and scrapers bootstrapper
        │   ├── exceptions.py            # Pure domain business exceptions hierarchy
        │   └── uow.py                   # Strict declaration of application-specific Unit of Work
        ├── workers/                     # Queue topic handlers.
        ├── cli/                         # Terminal-executable administration modules
        ├── domain/                      # Business Logic & Contracts (Pure Python)
        │   └── services/                # Base generic service implementation contracts
        ├── core/                        # App configuration, security and database infrastructure
        │   ├── settings.py              # Pydantic Settings global env state parsing
        │   ├── annotations.py           # Shared generic TypeVars for strict type checking
        │   ├── security/                # JWT token utilities and cryptographic password handlers
        │   └── infra/                   # Abstract Technical Framework Wrappers
        │       ├── cache/               # Lazy CacheManagerFactory (Redis / InMemory implementations)
        │       ├── tasks/               # Lazy TaskManagerFactory, configurations, and TaskIQ Broker
        │       ├── mail/                # Flat asynchronous email dispatcher domain (Jinja2, FastMail)
        │       └── transport/           # Transport components
        │           ├── http/            # HTTP transports components and middlewares
        │           └── queue/           # Queue Management Module
        │       └── database/            # A database module that includes a fluent Django-like interface built on top of SQLAlchemy.
        └── modules/                     # Isolated Domain Partitions (Business Features)
            ├── admin/                   # Administration and system control endpoints
            ├── event/                   # Venues, category mappings, and event routes
            ├── order/                   # Order placement, status workflows, and line item tracking
            ├── ticket/                  # Inventory allocation, checkout, and cleanup tasks
            ├── user/                    # User profiles, weight roles, and validation tasks
            └── views/                   # SSR views, template engines mounting, and page routers
```
## Infrastructure Design

The application separates concerns into distinct execution contexts via an optimized, modular multi-file container configuration:

* **Core Architecture Foundation (`docker-compose.yml`):** The baseline system topology containing the database, high-performance KeyDB cache, API layer, and TaskIQ async workers/scheduler. It establishes secure private virtual boundaries (`frontend_network`, `backend_network`) and disables background code polling for optimal production-grade CPU efficiency.
* **Local Development Overlay (`docker-compose.dev.yml`):** Stacks on top of the base layer during engineering cycles. It injects code mount points (`volumes`), binds interactive debugging portals directly to host ports (`3000`, `9090`), and safely toggles Uvicorn's active hot-reload mechanisms specifically for local machines.
* **Demonstration Setup (`docker-compose.demo.yml`):** An operational extension that mounts an enterprise **Nginx** reverse proxy inline with the frontend network loop. It secures application endpoints using real-time configuration templates and completely encapsulates underlying resources from raw host routing.
* **Optimized Multi-Stage Build (`Dockerfile`):** Implements specialized build target stages (`tests`, `lint`, `backend`) powered by `uv` for minimal image foot-printing. The production tier strips development utilities and verification suites out of final artifacts.
* **Telemetry & Dependency Guards:** Prometheus targets dynamically poll core operational parameters under static Bearer Token authentication mounted via Docker Secrets. Healthcheck cascades (`pg_isready`, `keydb-cli ping`, `urllib.request`) enforce linear service startups across execution groups.


## Installation and Setup

### 1. Clone the repository
```bash
git clone https://github.com
cd ticket-booking-system
```

### 2. Configure Environment Variables
Copy the template file to build your active configuration:
```bash
cp .env.example .env
```
Fill in the secure values inside the newly created `.env` file before booting up services.

### 3. Run Environments

The repository includes a unified automation script `start.sh` to assemble, launch, and teardown different environment stacks. The script automatically handles stale containers, tracks execution time, and supports integration flags.

```bash
# General usage syntax
./start.sh [ENVIRONMENT] [FLAGS]

# Display built-in help message
./start.sh --help
```

#### Available Stacks

* **Local Development Stack (With Hot-Reload)**
  Assembles the base foundation with development overrides, directory mounts, and live reload mechanisms.
  ```bash
  ./start.sh dev
  ```

* **Local Development with Full Telemetry Debugging**
  Stacks production telemetry components over the active development layer, exposing analytical dashboards locally.
  ```bash
  ./start.sh telemetry
  ```

* **Lightweight Demo Stack (Behind Nginx Proxy)**
  Deploys core microservices routed through an internal proxy gateway on strict HTTP/HTTPS boundaries without telemetry scrapers.
  ```bash
  ./start.sh demo
  ```

* **Hardened Production Stack (With Fully Isolated Telemetry)**
  The highest tier of environment assembly. Boots the main architecture and seals analytical collection ports inside a firewalled container loop.
  ```bash
  ./start.sh prod
  ```

* **Local Test Suite**
  Triggers a standalone verification routine to run integration test benches.
  ```bash
  ./start.sh test
  ```
  
* **Local Load Test Suite**
  Deploys a container with locust for load testing the project.
  ```bash
  ./start.sh load_test
  ```

* **Static Analysis & Linting**
  Executes formatters, linters, and static type checking without polluting global storage volumes.
  ```bash
  ./start.sh lint
  ```

#### Configuration Flags

* `--pull` — Executes `git pull` right before assembling the selected stack. Optimal for automated staging environments and CI/CD runners.
* `--clean` — Drops active containers and wipes all underlying database volumes (`down -v`) before initiating a fresh build.

## System Administration Command Line

Privileged user configuration and dataset generation bypasses raw database connection management through an abstracted CLI module inside the runtime engine. All operational procedures are standardized and routed through a single dispatch entrypoint.

### User Management Commands
To securely create administrative accounts with automatic cryptographic password hashing, execute the entrypoint module directly inside the active service container. The positional arguments must strictly follow the format: `<email> <password> <role>`.

```bash
# Create an Administrator account
docker exec -it api python -m src.cli.entrypoint create-user admin@ticket.com your_password admin

# Create a Moderator account
docker exec -it api python -m src.cli.entrypoint create-user moderator@ticket.com your_password moderator
```

#### Expected Terminal Output:
```text
[ START ] Running command: create-user...
  ✔ Checking user existence (0.0s)
  ✔ Hashing password (0.4s)
  ✔ Saving user to database cache (0.0s)
[ 100% ] create-user completed successfully in 0.45 seconds.
```

### Database Seeding Commands
To populate the database tables with structural mock dataset (including multi-level event categories, sample venues, ticket pricing tiers, customer orders, and transaction emissions) for rapid staging or volume testing, run the system seed pipeline. 

By default, the script generates a balanced baseline. You can configure data density using the `--users`, `--events`, and `--orders` flags. To completely wipe out all existing data and reset table state patterns before generation, append the `--clean` flag.

```bash
# Seed standard volume with cascading database cleanup
docker exec -it api python -m src.cli.entrypoint seed --clean

# Execute extreme volume stress testing
docker exec -it api python -m src.cli.entrypoint seed --clean --users 500 --events 2500 --orders 5000
```

#### Expected Terminal Output:
```text
[ START ] Running command: seed...
  ✔ Truncate existing database tables and sequences (0.2s)
  ✔ Create demonstration users and roles hierarchy (0.2s)
  ✔ Build multi-level event categories structure (0.0s)
  ✔ Generate historical and upcoming event baselines (1.0s)
  ✔ Process customer orders and emission workflows (0.7s)
  ✔ Collect anonymous and user unique view logs (0.0s)

  Database seeding completed successfully.

  Pipeline Profiling Metrics:
    Database Cleanup:   0.20s
    Users Generation:   0.20s
    Categories Build:   0.01s
    Events Blueprint:   1.07s
    Orders Workflow:    0.72s
    Traffic Analytics:  0.00s

  Generated Objects Summary:
    Users Registered:  501  (1 Admin, 0 Hosts, 0 Buyers)
    Leaf Categories:   25  
    Total Events:      2500 (500 Historical, 2000 Upcoming/Draft)
    Ticket Categories: 2385 Active pools
    Customer Orders:   5000

[ 100% ] seed completed successfully in 2.51 seconds.
```


## Testing Suite

The application implements a zero-network dependent testing suite using isolated database transactions, fully synchronized `InMemoryCacheManager` states, and TaskIQ in-memory scheduling.

### Running Containerized Tests
The testing infrastructure is completely separated into an isolated project context to prevent environment state mutation or pipeline data pollution.

To execute the full test pack with code coverage reporting within a self-terminating container loop:
```bash
docker compose -f docker-compose.test.yml up --build --abort-on-container-exit
```

## Implementation Notes

Core modules demonstrating engineering depth for review:

1. `src/core/infra/database/query/builder.py`: Chainable `QueryBuilder` engine providing dynamic filter mapping, safe execution context clones, and robust tuple/scalar conversions without `NoInspectionAvailable` side-effects. It handles relationship loading on top of SQLAlchemy using an isolated string-based `__` interface.
2. `src/core/infra/transport/http/idempotency.py`: Reusable API decorator utilizing atomic lock check/set routines and automated model serialization to guarantee transaction safety across high-load request loops.
3. `src/modules/order/services.py` & `src/modules/ticket/services.py`: Implements cascading transactions, state machine boundaries, and multi-ticket quota allocation using completely thin repositories that act as pure фасады to the query builder layer.
4. `src/app/uow.py` & `src/core/infra/database/uow.py`: Demonstrates decoupling patterns, enabling developers to fully swap out data infrastructures or mock network layers without breaking core features.
5. `src/core/infra/cache/managers/in_memory.py`: Custom isolated test-double caching module replicating standard production Redis operations, context locks, and HyperLogLog pipelines natively in volatile memory.
