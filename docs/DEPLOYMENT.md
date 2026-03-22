# Deployment Guide — AI Scraping Platform

## Docker Compose (Quickstart)

The fastest way to run the platform locally or self-hosted.

### Prerequisites
- Docker 24+ and Docker Compose v2
- At least 2 GB RAM available

### Steps

```bash
# Clone the repository
git clone https://github.com/haqeeqiazadee-ux/Scraper-app.git
cd Scraper-app

# Copy and edit environment file
cp .env.example .env
# Edit .env: set GEMINI_API_KEY, change SECRET_KEY

# Start the stack
docker compose -f infrastructure/docker/docker-compose.yml up --build -d

# Verify
curl http://localhost:8000/health
# {"status":"healthy","version":"0.1.0","database":"connected"}
```

### Services Started
| Service | Port | Description |
|---------|------|-------------|
| control-plane | 8000 | FastAPI REST API |
| postgres | 5432 | PostgreSQL 15 metadata store |
| redis | 6379 | Queue and cache |

### Stopping

```bash
docker compose -f infrastructure/docker/docker-compose.yml down
# Add -v to also remove data volumes
```

---

## Kubernetes (Production)

For production deployments with high availability and auto-scaling.

### Prerequisites
- Kubernetes 1.27+
- Helm 3.12+
- External PostgreSQL and Redis (or deploy in-cluster)
- Container registry with built images

### Build and Push Images

```bash
# Build all service images
docker build -f infrastructure/docker/Dockerfile.control-plane -t your-registry/control-plane:latest .
docker build -f infrastructure/docker/Dockerfile.worker-http -t your-registry/worker-http:latest .
docker build -f infrastructure/docker/Dockerfile.worker-browser -t your-registry/worker-browser:latest .
docker build -f infrastructure/docker/Dockerfile.worker-ai -t your-registry/worker-ai:latest .

# Push to registry
docker push your-registry/control-plane:latest
docker push your-registry/worker-http:latest
docker push your-registry/worker-browser:latest
docker push your-registry/worker-ai:latest
```

### Deploy with Helm

```bash
# Add custom values
cat > my-values.yaml <<EOF
global:
  imageRegistry: your-registry

controlPlane:
  replicas: 2

database:
  host: your-rds-endpoint.amazonaws.com
  port: 5432
  name: scraper_db
  existingSecret: scraper-db-credentials

redis:
  host: your-redis-endpoint.cache.amazonaws.com
  port: 6379

secrets:
  existingSecret: scraper-secrets

ingress:
  enabled: true
  className: nginx
  hosts:
    - host: scraper.yourdomain.com
      paths:
        - path: /
          pathType: Prefix

autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
  targetCPU: 70
EOF

# Install
helm install scraper-platform infrastructure/helm/scraper-platform \
  -f my-values.yaml \
  -n scraper --create-namespace

# Verify
kubectl get pods -n scraper
helm test scraper-platform -n scraper
```

### Helm Chart Structure

```
infrastructure/helm/scraper-platform/
  Chart.yaml              # Chart metadata (appVersion: 0.1.0)
  values.yaml             # Default configuration
  templates/
    _helpers.tpl           # Template helpers
    configmap.yaml         # Non-sensitive config
    secret.yaml            # Sensitive config (conditional)
    deployment-control-plane.yaml
    deployment-worker-http.yaml
    deployment-worker-browser.yaml
    deployment-worker-ai.yaml
    service-control-plane.yaml
    ingress.yaml           # Conditional ingress
    hpa.yaml               # Conditional auto-scaling
    pvc.yaml               # Artifact storage PVC
```

---

## AWS (Terraform)

Full AWS infrastructure with ECS Fargate, RDS, ElastiCache, and S3.

### Prerequisites
- Terraform 1.5+
- AWS CLI configured with appropriate permissions
- Route 53 hosted zone (for DNS)
- ACM certificate (for HTTPS)

### Deploy

```bash
cd infrastructure/terraform/aws

# Copy and configure variables
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values

# Initialize and apply
terraform init
terraform plan
terraform apply
```

### Modules Deployed
| Module | Resources |
|--------|-----------|
| VPC | VPC, public/private subnets, NAT gateways, S3 endpoint |
| ECS | Fargate cluster, ALB, 4 services, auto-scaling, IAM |
| RDS | PostgreSQL 15 Multi-AZ, encrypted, automated backups |
| Redis | ElastiCache Redis 7.1, encrypted, automatic failover |
| S3 | Artifacts bucket, versioning, lifecycle rules, KMS encryption |

---

## Desktop App (Tauri v2)

Standalone Windows application with embedded control plane.

### Prerequisites
- Rust 1.70+ (for Tauri build)
- Node.js 18+ (for frontend build)
- Python 3.11+ (for embedded server)

### Development

```bash
cd apps/desktop
npm install
npm run tauri dev
```

### Build Installer

```bash
cd apps/desktop
npm run tauri build
# Output: src-tauri/target/release/bundle/
```

### Desktop Architecture
- Embedded FastAPI server runs on `localhost:8321`
- Uses SQLite for metadata, filesystem for artifacts, in-memory queue/cache
- Tauri manages server lifecycle (start/stop via system tray)
- No external dependencies required at runtime

---

## Chrome Extension

### Development

```bash
# Navigate to extension directory
cd apps/extension

# Load as unpacked extension:
# 1. Open chrome://extensions/
# 2. Enable "Developer mode"
# 3. Click "Load unpacked"
# 4. Select the apps/extension/ directory
```

### Production Build

The extension can operate in two modes:
1. **Cloud mode**: Connects to a remote control plane API
2. **Local mode**: Uses native messaging to communicate with the companion host

### Native Messaging Companion

```bash
# Install the companion host
cd apps/companion
python install.py --browser chrome

# This registers the native messaging manifest with Chrome
# The companion bridges the extension to a local Python scraping engine
```

---

## Environment Variables Reference

### Required

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://...` | Database connection string |
| `SECRET_KEY` | `change-me-in-production` | JWT signing key |

### Database and Storage

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection (empty = in-memory) |
| `STORAGE_TYPE` | `filesystem` | `filesystem` or `s3` |
| `STORAGE_PATH` | `./artifacts` | Local artifact directory |
| `S3_ENDPOINT` | -- | S3-compatible endpoint URL |
| `S3_BUCKET` | -- | S3 bucket name |
| `S3_ACCESS_KEY` | -- | S3 access key |
| `S3_SECRET_KEY` | -- | S3 secret key |
| `S3_REGION` | -- | S3 region |

### AI Providers

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | -- | Google Gemini API key |
| `GEMINI_MODEL` | `gemini-1.5-flash` | Gemini model name |
| `OPENAI_API_KEY` | -- | OpenAI API key (optional) |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI model name |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama local server |
| `OLLAMA_MODEL` | `llama3` | Ollama model name |

### Authentication

| Variable | Default | Description |
|----------|---------|-------------|
| `JWT_ALGORITHM` | `HS256` | JWT signing algorithm |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | Access token TTL |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token TTL |

### Server

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `0.0.0.0` | Bind address |
| `PORT` | `8000` | Bind port |
| `DEBUG` | `false` | Debug mode |
| `LOG_LEVEL` | `INFO` | Logging level |
| `WORKERS` | `4` | Uvicorn worker count |

### Proxy and CAPTCHA

| Variable | Default | Description |
|----------|---------|-------------|
| `PROXY_PROVIDER` | -- | `file`, `list`, or `api` |
| `PROXY_FILE` | -- | Path to proxy list file |
| `PROXY_API_URL` | -- | Proxy provider API URL |
| `PROXY_API_KEY` | -- | Proxy provider API key |
| `CAPTCHA_PROVIDER` | -- | `2captcha`, `anticaptcha`, or `capmonster` |
| `CAPTCHA_API_KEY` | -- | CAPTCHA service API key |

### Observability

| Variable | Default | Description |
|----------|---------|-------------|
| `OTEL_EXPORTER_OTLP_ENDPOINT` | -- | OpenTelemetry collector endpoint |
| `PROMETHEUS_ENABLED` | `true` | Enable Prometheus metrics |
