# TruthGraph v0 Docker Setup

Quick start guide for running TruthGraph v0 with Docker.

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows/Mac) or Docker Engine (Linux)
- [Task](https://taskfile.dev) - Task runner (`winget install Task.Task` on Windows)
- Git

## Quick Start

### 1. Initial Setup

```bash
# Clone repository (if not already done)
git clone <your-repo-url>
cd truthgraph

# Run setup (creates .env and builds containers)
task setup
```

### 2. Start Services

**Option A: htmx Frontend (Recommended - Faster, Simpler)**

```bash
task dev
```

This starts:

- PostgreSQL with pgvector (port 5432)
- FastAPI backend (port 8000)
- Flask + htmx frontend (port 5000)

**Option B: Both Frontends (htmx + React)**

```bash
task dev:react
```

This starts all services including React frontend on port 5173.

### 3. Access the Application

- **htmx Frontend**: <http://localhost:5000>
- **React Frontend**: <http://localhost:5173> (if started with `task dev:react`)
- **API**: <http://localhost:8000>
- **API Docs**: <http://localhost:8000/docs>

## Task Commands

### Development

```bash
task setup        # Initial setup (create .env, build containers)
task dev          # Start htmx frontend stack
task dev:react    # Start both htmx and React frontends
task down         # Stop all services
task restart      # Restart all services
task reset        # Reset everything (removes volumes - DESTRUCTIVE)
```

### Logs

```bash
task logs         # View all logs
task logs:api     # View API logs only
task logs:db      # View database logs only
```

### Shell Access

```bash
task shell        # Open bash in API container
task shell:db     # Open PostgreSQL shell
```

### Testing (Phase 2)

```bash
task test:api     # Run API tests (coming in Phase 2)
```

## Architecture

```text
┌──────────────────────────────────────────────┐
│         TruthGraph v0 Docker Stack           │
├──────────────────────────────────────────────┤
│                                              │
│  ┌─────────────────────────────────────┐   │
│  │  htmx Frontend (Flask) :5000        │   │
│  │  React Frontend (Vite) :5173        │   │
│  └──────────────┬──────────────────────┘   │
│                 │                           │
│  ┌──────────────▼──────────────────────┐   │
│  │  FastAPI Backend :8000              │   │
│  └──────────────┬──────────────────────┘   │
│                 │                           │
│  ┌──────────────▼──────────────────────┐   │
│  │  PostgreSQL + pgvector :5432        │   │
│  └─────────────────────────────────────┘   │
│                                              │
└──────────────────────────────────────────────┘
```

## Environment Variables

Configuration is in `.env` (created from `.env.example` during setup).

Key variables:

```bash
# Database
POSTGRES_DB=truthgraph
POSTGRES_USER=truthgraph
POSTGRES_PASSWORD=changeme_to_secure_password

# API
API_PORT=8000
LOG_LEVEL=INFO

# Frontend
FRONTEND_PORT=5000  # htmx
REACT_PORT=5173     # React
```

## Data Persistence

Database data is stored in `.volumes/postgres/` (git-ignored).

To reset the database:

```bash
task reset  # Warning: deletes all data!
task setup
task dev
```

## Development Workflow

### Making Changes

**Backend (Python/FastAPI)**:

1. Edit files in `truthgraph/`
2. API auto-reloads (uvicorn --reload)
3. Check logs: `task logs:api`

**Frontend (htmx)**:

1. Edit templates in `frontend/templates/`
2. Edit styles in `frontend/static/css/`
3. Flask auto-reloads in debug mode
4. Refresh browser

**Frontend (React)**:

1. Edit files in `frontend-react/src/`
2. Vite HMR reloads automatically
3. Check browser console

### Testing the API

```bash
# Health check
curl http://localhost:8000/health

# Create a claim
curl -X POST http://localhost:8000/api/v1/claims \
  -H "Content-Type: application/json" \
  -d '{"text": "The Earth is round", "source_url": "https://example.com"}'

# List claims
curl http://localhost:8000/api/v1/claims

# Get specific claim (replace {id} with actual UUID)
curl http://localhost:8000/api/v1/claims/{id}
```

## Troubleshooting

### Containers won't start

```bash
# Check Docker is running
docker --version

# View detailed logs
task logs

# Rebuild containers
task down
task setup
task dev
```

### Port already in use

Edit `.env` and change port numbers:

```bash
POSTGRES_PORT=5433  # Instead of 5432
API_PORT=8001       # Instead of 8000
FRONTEND_PORT=5001  # Instead of 5000
```

### Database connection errors

```bash
# Check PostgreSQL is healthy
docker-compose ps

# Access database shell
task shell:db

# Reset database
task reset
task setup
task dev
```

### API can't connect to database

1. Check `DATABASE_URL` in `.env`
2. Ensure services started in order (docker-compose handles this)
3. Check logs: `task logs:api`

## Next Steps

- See [phase_01_foundation.md](docs/roadmap/v0/phase_01_foundation.md) for Phase 1 requirements
- See [phase_02_core_features.md](docs/roadmap/v0/phase_02_core_features.md) for Phase 2 ML features
- Check API documentation at <http://localhost:8000/docs>

## Phase 1 Success Criteria

- [x] Docker Compose setup complete
- [x] PostgreSQL with pgvector running
- [x] FastAPI backend with health check
- [x] htmx frontend serving UI
- [x] React frontend (optional) serving UI
- [ ] Can create and list claims via API
- [ ] Can submit claims via UI
- [ ] Database persists data across restarts

Test these with:

```bash
task dev
# Visit http://localhost:5000
# Submit a claim
# Verify it appears in history
task restart
# Verify claim still exists
```
