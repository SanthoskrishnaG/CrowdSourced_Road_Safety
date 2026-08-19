# AI-Powered Crowdsourced Road Infrastructure Monitoring & Management Platform

A modern, production-oriented web platform that empowers citizens to report public infrastructure issues (potholes, broken streetlights, blocked roads, garbage, flooding, etc.) and enables authorities to verify, assign, track, prioritize, and resolve them.

---

## Purpose & Problem Statement
Poorly maintained infrastructure leads to traffic accidents, economic delays, and general safety hazards. Currently, reporting mechanisms are fragmented and manual. 
This platform acts as a centralized crowdsourced hub, leveraging community reports to flag hazards, merging duplicate reports into canonical issues, and calculating priority scores to optimize municipal repair workflows.

---

## Core Architecture: Reports vs Canonical Issues
The platform establishes a strict architectural boundary between citizen submissions and underlying municipal problems:
- **`RoadReport`**: An individual submission from a citizen containing title, description, timestamp, coordinates, and photo evidence.
- **`Issue`**: The canonical underlying road problem tracked by authorities. Multiple citizen reports regarding the same problem automatically merge into one canonical `Issue`.

---

## Intelligent Duplicate Detection (Phase 6)
When a citizen creates a report, the system evaluates active issues within proximity using a multi-factor deterministic scoring engine:

$$\text{Score} = \frac{w_{\text{loc}} \cdot S_{\text{loc}} + w_{\text{cat}} \cdot S_{\text{cat}} + w_{\text{time}} \cdot S_{\text{time}} + w_{\text{img}} \cdot S_{\text{img}}}{w_{\text{total}}}$$

1. **Geographic Proximity ($S_{\text{loc}}$)**: Haversine distance calculations ($d \le 15\text{m} \to 1.0$, linear decay to $0.0$ at $50\text{m}$).
2. **Category Taxonomy ($S_{\text{cat}}$)**: Exact matches ($1.0$), related taxonomy pairs ($0.4 - 0.6$, e.g. `POTHOLE` $\leftrightarrow$ `ROAD_DAMAGE`), or distinct ($0.0$).
3. **Time Proximity ($S_{\text{time}}$)**: Recency scoring ($1.0$ within 24h, decaying to $0.1$ at 30 days).
4. **Perceptual Image Hashing ($S_{\text{img}}$)**: 64-bit difference hashing (dHash) with Hamming distance comparison via Pillow.

If $\text{Score} \ge 0.65$, the report merges into the existing canonical `Issue`, incrementing `report_count` and upgrading severity if applicable. Otherwise, a new canonical `Issue` is spawned. Detailed documentation is available in [docs/duplicate_detection.md](file:///c:/Users/Santhoskrishna/Documents/Crowdsourced%20Road%20Safety/docs/duplicate_detection.md).

---

## Authentication & Authorization Architecture
- **Password Security**: Passwords are secure-hashed using `bcrypt` and are never saved or exposed in plain text.
- **JWT Authentication**: Secure Bearer tokens are produced upon login using `PyJWT` (algorithm `HS256`).
- **Role-Based Access Control (RBAC)**: Fine-grained permissions are enforced server-side.

### System Roles
1. **`CITIZEN`**: Can submit reports, view own submitted reports, upload evidence photos, and browse public issues.
2. **`AUTHORITY`**: Can view assigned issues, verify reporting accuracy, assign tasks, attach evidence, and update statuses.
3. **`ADMIN`**: Full platform control, authority profile provisioning, image/report administration, and user management.

---

## API Endpoints

### Canonical Issues (Phase 6)
- `GET /api/v1/issues`: List canonical road issues with pagination (`page`, `page_size`) and filters (`category`, `severity`, `status`).
- `GET /api/v1/issues/{id}`: Detailed view of a canonical issue including `report_count` and nested contributing reports list.

### Public Map
- `GET /api/v1/reports/map`: Lightweight geospatial report feed. Supports attribute filters (`category`, `severity`, `status`) and viewport bounding box filters (`min_lat`, `max_lat`, `min_lon`, `max_lon`).

### Authentication
- `POST /api/v1/auth/register`: Create a new user account.
- `POST /api/v1/auth/login`: Authenticate credentials and receive a JWT.
- `POST /api/v1/auth/logout`: Log out and confirm token invalidation request.
- `GET /api/v1/auth/me`: Get the current logged-in user profile (Requires Bearer Token).

### Road Reports
- `POST /api/v1/reports`: Create a new road report and trigger duplicate detection (Requires Bearer Token).
- `GET /api/v1/reports`: Get a list of reports. Supports pagination (`page`, `page_size`) and filters (`category`, `severity`, `status`).
- `GET /api/v1/reports/my`: Get all reports submitted by the current authenticated citizen.
- `GET /api/v1/reports/{id}`: Get detailed view of a report by UUID, including attached images and `issue_id`.
- `PATCH /api/v1/reports/{id}`: Modify report attributes.
- `DELETE /api/v1/reports/{id}`: Delete a report.

### Photographic Evidence
- `POST /api/v1/reports/{id}/images`: Upload one or more evidence photos (multipart form data).
- `GET /api/v1/reports/{id}/images`: Retrieve list of all images and thumbnails attached to a report.
- `DELETE /api/v1/reports/{id}/images/{image_id}`: Remove an image attachment from a report.

### Static Assets
- `GET /uploads/...`: Direct access to uploaded evidence images and generated thumbnails.

### Diagnostics
- `GET /api/v1/health`: Server status and DB accessibility checks.

---

## Technology Stack
- **Backend**: Python 3.12, FastAPI, SQLAlchemy, Alembic, PostgreSQL, Pydantic, Uvicorn, bcrypt, PyJWT, email-validator, Pillow, python-multipart
- **Frontend**: HTML5, Vanilla CSS (Glassmorphism / Dark Theme), Vanilla JavaScript, Leaflet.js, OpenStreetMap, Leaflet.markercluster
- **Development & Testing**: pytest, python-dotenv, Docker, Docker Compose, Git

---

## Project Architecture
```text
├── backend/
│   ├── alembic/              # Database migration history
│   ├── app/
│   │   ├── api/              # Versioned API routes (v1) & global dependencies
│   │   ├── core/             # Application config, security helpers, and DB engines
│   │   ├── models/           # SQLAlchemy Models (User, RoadReport, ReportImage, Issue)
│   │   ├── schemas/          # Pydantic validation schemas (User, Report, Image, Map, Issue)
│   │   ├── services/         # Duplicate detection and business logic handlers
│   │   ├── repositories/     # Database querying layer
│   │   ├── db/               # Helper DB scripts/utilities
│   │   ├── utils/            # Helper modules (security, geo, image processing)
│   │   └── main.py           # Application entrypoint
│   ├── tests/                # Automated pytest suites (auth, reports, geo, images, map, duplicates)
│   ├── alembic.ini           # Alembic Configuration settings
│   ├── Dockerfile            # Backend Docker instructions
│   └── requirements.txt      # Python dependencies
├── frontend/                 # Interactive Map & Diagnostic Portal
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   └── app.js
│   └── index.html
├── uploads/                  # User image upload volume & static storage
├── scripts/                  # Management scripts
├── docs/                     # Documentation (duplicate_detection.md)
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
- `DUPLICATE_SCORE_THRESHOLD`: Minimum similarity threshold for merging reports (default `0.65`).
- `DUPLICATE_DISTANCE_THRESHOLD_METERS`: Max search radius for duplicates in meters (default `50.0`).
- `WEIGHT_LOCATION`: Location score weight (default `0.40`).
- `WEIGHT_CATEGORY`: Category taxonomy weight (default `0.30`).
- `WEIGHT_TIME`: Time decay weight (default `0.15`).
- `WEIGHT_IMAGE`: Perceptual dHash weight (default `0.15`).

---

## Running Tests
Run tests inside the active running backend Docker container:
```bash
docker compose exec backend pytest
```
*Tests verify application startup, database connectivity, authentication, reports lifecycle, image processing pipelines, geospatial calculations, public map feeds, and automatic duplicate detection workflows.*
