# Production Cloud Deployment Guide

This guide provides step-by-step deployment instructions for hosting the **AI-Powered Crowdsourced Road Infrastructure Monitoring & Management Platform** across various cloud and container platforms.

---

## 1. Docker Compose Deployment (Self-Hosted VPS / EC2 / DigitalOcean)

### Prerequisites
- Docker (>= 24.0) & Docker Compose (>= 2.20)
- Domain with SSL certificate (e.g. via Nginx + Certbot or Caddy)

### Steps
1. **Clone Repository & Prepare Environment**:
   ```bash
   git clone https://github.com/SanthoskrishnaG/CrowdSourced_Road_Safety.git
   cd CrowdSourced_Road_Safety
   cp .env.example .env
   ```

2. **Configure Production `.env`**:
   ```ini
   ENVIRONMENT=production
   DEBUG=false
   SECRET_KEY=generate_a_secure_64_char_random_string_here
   DATABASE_URL=postgresql://postgres:secure_db_password@db:5432/road_safety
   UPLOAD_DIRECTORY=/app/uploads
   CORS_ORIGINS=["https://your-domain.com"]
   ```

3. **Start Services**:
   ```bash
   docker compose up -d --build
   ```

4. **Verify Health**:
   ```bash
   curl -f http://localhost:8000/api/v1/health/healthz
   ```

---

## 2. Render Deployment (PaaS)

### Architecture
- **Web Service**: FastAPI Python backend
- **Managed Database**: Render PostgreSQL
- **Disk**: Persistent Disk for `/app/uploads` (or AWS S3)

### Steps
1. **Create Managed PostgreSQL Database**:
   - Go to Render Dashboard -> **New** -> **PostgreSQL**.
   - Copy the internal database connection string `postgres://...`.

2. **Create Web Service**:
   - Select **New** -> **Web Service** and link your Git repository.
   - **Root Directory**: `backend`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2`

3. **Configure Environment Variables**:
   - `ENVIRONMENT` = `production`
   - `SECRET_KEY` = `[Generated 64-char key]`
   - `DATABASE_URL` = `[Render PostgreSQL Connection String]`
   - `UPLOAD_DIRECTORY` = `uploads`

4. **Mount Persistent Disk**:
   - Mount a 5GB persistent disk at path `/app/uploads`.

---

## 3. Railway Deployment

1. **Deploy PostgreSQL**:
   - Click **New** -> **Database** -> **Add PostgreSQL**.
2. **Deploy Backend Service**:
   - Click **New** -> **GitHub Repo** -> select `CrowdSourced_Road_Safety`.
   - Set Root Directory to `/backend`.
   - Add reference variable: `DATABASE_URL` = `${{Postgres.DATABASE_URL}}`.
   - Add `SECRET_KEY`, `ENVIRONMENT=production`, `PORT=8000`.
3. **Deploy Frontend**:
   - Deploy `/frontend` as a static site or host via FastAPI static mount.

---

## 4. AWS Deployment (ECS Fargate + RDS PostgreSQL)

### Architecture
- **Amazon RDS**: PostgreSQL 16 (Multi-AZ in private subnet)
- **Amazon ECS Fargate**: Containerized FastAPI tasks behind an Application Load Balancer (ALB)
- **Amazon S3 / EFS**: Media upload storage for report evidence photos
- **AWS Secrets Manager**: Secure credential injection (`SECRET_KEY`, `DATABASE_URL`)

### Steps
1. **Build & Push Image to Amazon ECR**:
   ```bash
   aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com
   docker build -t road-safety-backend backend/
   docker tag road-safety-backend:latest <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/road-safety-backend:latest
   docker push <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/road-safety-backend:latest
   ```
2. **Configure Task Definition**:
   - Allocate 1 vCPU, 2GB Memory.
   - Point container port to `8000`.
   - Set Healthcheck endpoint to `/api/v1/health/healthz`.
3. **Run ECS Service**:
   - Attach Target Group to Application Load Balancer with HTTPS (ACM Certificate).

---

## 5. Security & Maintenance Checklist

- [x] **HTTPS / TLS 1.3** enforced on all external endpoints.
- [x] **No secrets in source control**: All keys loaded via environment variables.
- [x] **Database Automated Backups**: Daily snapshot retention enabled.
- [x] **Health Monitoring**: Regular ping to `/api/v1/health/healthz`.
- [x] **Log Rotation**: Stdout captured by Docker/CloudWatch with log retention limits.
