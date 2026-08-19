# AI-Powered Crowdsourced Road Infrastructure Monitoring & Management Platform

A modern, production-oriented web platform that empowers citizens to report public infrastructure issues (potholes, broken streetlights, blocked roads, garbage, flooding, etc.) and enables authorities to verify, assign, track, prioritize, and resolve them.

---

## Purpose & Problem Statement
Poorly maintained infrastructure leads to traffic accidents, economic delays, and general safety hazards. Currently, reporting mechanisms are fragmented and manual. 
This platform acts as a centralized crowdsourced hub, leveraging community reports to flag hazards and utilizing AI to categorize issues, remove duplicates, and calculate priority scores to optimize municipal repair workflows.

---

## Planned Features
- **Citizen Reporting Portal**: High-quality report submission with geo-coordinates and image attachments.
- **AI Classification**: Automated issue categorization (e.g., distinguishing between a pothole and a damaged sign).
- **Intelligent Priority Engine**: Automated risk-assessment scoring based on severity and location metadata.
- **Geospatial Analysis**: Map interfaces tracking reporting hot-spots.
- **Authority Console**: Admin dashboards for tracking reports, workflow assignments, and status updates.

> [!NOTE]
> *Advanced AI features, duplicate detection, and advanced geospatial maps will be introduced in subsequent development phases.*

---

## Authentication & Authorization Architecture
Phase 2 introduces a complete security stack for user registration, authentication, and role-based permissions access:
- **Password Security**: Passwords are secure-hashed using `bcrypt` and are never saved or exposed in plain text.
- **JWT Authentication**: Secure Bearer tokens are produced upon login using `PyJWT` (algorithm `HS256`).
- **Role-Based Access Control (RBAC)**: Fine-grained permissions are enforced server-side.

### System Roles
1. **`CITIZEN`**: Can submit reports, view own submitted reports, and browse public issues.
2. **`AUTHORITY`**: Can view assigned issues, verify reporting accuracy, assign tasks, and update statuses.
3. **`ADMIN`**: Full platform control, authority profile provisioning, and user administration.

---

## API Endpoints

### Authentication
- `POST /api/v1/auth/register`: Create a new user account.
- `POST /api/v1/auth/login`: Authenticate credentials and receive a JWT.
- `GET /api/v1/auth/me`: Get the current logged-in user profile (Requires Bearer Token).

### Diagnostics
- `GET /api/v1/health`: Server status and DB accessibility checks.

---

## Technology Stack
- **Backend**: Python 3.12, FastAPI, SQLAlchemy, Alembic, PostgreSQL, Pydantic, Uvicorn, bcrypt, PyJWT
- **Development & Testing**: pytest, python-dotenv, Docker, Docker Compose, Git
- **Frontend**: Minimal diagnostic CSS/JS test panel

---

## Project Architecture
```text
├── backend/
│   ├── alembic/              # Database migration history
│   ├── app/
│   │   ├── api/              # Versioned API routes (v1) & global dependencies
│   │   ├── core/             # Application config, security helpers, and DB engines
│   │   ├── models/           # SQLAlchemy Declarative Models (User, etc.)
│   │   ├── schemas/          # Pydantic validation schemas
│   │   ├── services/         # Core business logic handlers
│   │   ├── repositories/     # Database querying layer
│   │   ├── db/               # Helper DB scripts/utilities
│   │   ├── utils/            # Helper modules (security, parsing)
│   │   └── main.py           # Application entrypoint
│   ├── tests/                # Automated pytest suites
│   ├── alembic.ini           # Alembic Configuration settings
│   ├── Dockerfile            # Backend Docker instructions
│   └── requirements.txt      # Python dependencies
├── frontend/                 # Static asset test client
│   ├── css/
│   ├── js/
│   └── index.html
├── uploads/                  # User image upload volume
├── scripts/                  # Management scripts
├── docs/                     # Project documentation assets
├── docker-compose.yml        # Docker compose configuration
├── .env.example              # Environment variables template
└── README.md                 # Project handbook
```

---

## Environment Variables
The application reads settings using Pydantic Settings. Duplicate `.env.example` to `.env` and adjust properties:
- `ENVIRONMENT`: Core execution environment (`development` / `production`).
- `SECRET_KEY`: Security salt configuration.
- `DATABASE_URL`: Connection string for SQLAlchemy (PostgreSQL).
- `UPLOAD_DIRECTORY`: Root directory where report files are stored.

---

## Local Setup

### Prerequisite
Ensure you have **Docker** and **Docker Compose** installed.

### Setup Instructions

1. **Clone the repository and copy the env setup**:
   ```bash
   cp .env.example .env
   ```

2. **Spin up PostgreSQL & Backend using Docker Compose**:
   ```bash
   docker compose up --build
   ```
   *This commands builds the backend container, starts a PostgreSQL database container, performs necessary status checks, and boots the FastAPI server at `http://localhost:8000`.*

3. **Verify Health Check Endpoint**:
   - Access `http://localhost:8000/api/v1/health` via browser or test tools.
   - Response: `{"status": "healthy"}`

4. **Interactive API Documentation & Testing**:
   - OpenAPI documentation is served at `http://localhost:8000/docs`. You can register/login and test authorization directly through the Swagger UI using the "Authorize" button.

5. **Alembic Database Migrations**:
   If modifying base models, run migrations via:
   ```bash
   docker compose exec backend alembic revision --autogenerate -m "description"
   docker compose exec backend alembic upgrade head
   ```

---

## Running Tests
Run tests inside the active running backend Docker container:
```bash
docker compose exec backend pytest
```
*Tests verify backend application startup, health-check responsiveness, database engine connectivity, and authentication & authorization pathways.*
