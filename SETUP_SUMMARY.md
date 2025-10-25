# TruthGraph v0 Phase 1 Docker Setup - Complete

## What Was Created

### Docker Infrastructure

1. **docker-compose.yml** - Multi-service stack:
   - PostgreSQL 16 with pgvector extension
   - FastAPI backend service
   - Flask + htmx frontend (primary)
   - React + Vite frontend (optional, via `--profile react`)

2. **Docker Configuration Files**:
   - `docker/api.Dockerfile` - FastAPI container with uv package manager
   - `docker/frontend.Dockerfile` - Flask container for htmx frontend
   - `docker/.dockerignore` - Optimized build context
   - `docker/init-db.sql` - Database initialization script

### Backend (FastAPI + PostgreSQL)

1. **Python Package Structure**:
   - `pyproject.toml` - Dependencies and project metadata
   - `truthgraph/__init__.py` - Package initialization
   - `truthgraph/main.py` - FastAPI application
   - `truthgraph/db.py` - Database connection and session management
   - `truthgraph/logger.py` - Structured logging with structlog
   - `truthgraph/models.py` - Pydantic models for API validation
   - `truthgraph/schemas.py` - SQLAlchemy ORM models
   - `truthgraph/api/routes.py` - API endpoints

2. **Database Schema**:
   - `claims` table - User-submitted claims
   - `evidence` table - Evidence documents
   - `verdicts` table - Verification results
   - `verdict_evidence` table - Links verdicts to evidence
   - Indexes for performance
   - Triggers for auto-updating timestamps

3. **API Endpoints** (Phase 1):
   - `POST /api/v1/claims` - Create new claim
   - `GET /api/v1/claims` - List claims (paginated)
   - `GET /api/v1/claims/{id}` - Get specific claim
   - `GET /health` - Health check for Docker
   - `GET /` - Root with service info
   - `GET /docs` - Auto-generated OpenAPI docs

### Frontend - htmx (Primary)

1. **Flask Application**:
   - `frontend/app.py` - Flask server
   - `frontend/requirements.txt` - Python dependencies

2. **Templates** (Jinja2 + htmx):
   - `frontend/templates/base.html` - Base layout
   - `frontend/templates/index.html` - Main page
   - `frontend/templates/claim_list.html` - Claims display
   - `frontend/templates/claim_submitted.html` - Success message
   - `frontend/templates/error.html` - Error display

3. **Static Assets**:
   - `frontend/static/css/style.css` - Modern, responsive styling

### Frontend - React (Optional)

1. **React + Vite Application**:
   - `frontend-react/package.json` - Node dependencies
   - `frontend-react/vite.config.js` - Vite configuration
   - `frontend-react/index.html` - HTML entry point
   - `frontend-react/src/main.jsx` - React entry point
   - `frontend-react/src/App.jsx` - Main app component
   - `frontend-react/src/components/ClaimForm.jsx` - Form component
   - `frontend-react/src/components/ClaimHistory.jsx` - History component
   - `frontend-react/src/App.css` - Styling (matches htmx)
   - `frontend-react/Dockerfile.dev` - Development container

### Developer Experience

1. **Taskfile.yml** - Updated with Docker tasks:
   - `task setup` - Initial environment setup
   - `task dev` - Start htmx stack
   - `task dev:react` - Start with React frontend
   - `task down` - Stop services
   - `task restart` - Restart all services
   - `task reset` - Reset everything (destructive)
   - `task logs` - View all logs
   - `task logs:api` - API logs only
   - `task logs:db` - Database logs only
   - `task shell` - API container shell
   - `task shell:db` - PostgreSQL shell
   - `task test:api` - Run API tests (Phase 2)

2. **Configuration**:
   - `.env.example` - Environment variable template
   - `.env` - Created during setup (git-ignored)
   - `.gitignore` - Updated for Docker volumes and node_modules

3. **Documentation**:
   - `DOCKER_SETUP.md` - Complete setup and usage guide
   - `SETUP_SUMMARY.md` - This file

## Technology Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| Database | PostgreSQL + pgvector | 16 |
| Backend | FastAPI | 0.104.1+ |
| Backend Runtime | Python | 3.12 |
| Package Manager | uv | latest |
| ORM | SQLAlchemy | 2.0.23+ |
| Validation | Pydantic | 2.5.0+ |
| Logging | structlog | 24.1.0+ |
| Frontend (Primary) | Flask + htmx | 3.0.0 / 1.9.10 |
| Frontend (Optional) | React + Vite | 18.2.0 / 5.0.8 |
| Container Runtime | Docker Compose | 3.8 |

## Quick Start

```bash
# 1. Setup (one-time)
task setup

# 2. Start services (htmx frontend)
task dev

# 3. Access the application
# - Frontend: http://localhost:5000
# - API: http://localhost:8000
# - API Docs: http://localhost:8000/docs

# 4. View logs
task logs

# 5. Stop services
task down
```

## Architecture

```text
User Browser
    │
    ├─→ http://localhost:5000 (htmx Frontend)
    │   └─→ Flask renders templates with htmx
    │
    └─→ http://localhost:5173 (React Frontend - optional)
        └─→ Vite serves React SPA

Both frontends →
    │
    ├─→ http://localhost:8000/api/v1/* (FastAPI Backend)
        │
        └─→ PostgreSQL:5432 (Database + pgvector)
```

## Data Flow

1. **Claim Submission**:
   - User fills form → htmx POST → Flask `/claims/submit`
   - Flask → API `POST /api/v1/claims`
   - API validates with Pydantic → SQLAlchemy saves to PostgreSQL
   - API returns claim object → Flask renders success template
   - htmx swaps HTML in-place (no page reload)

2. **Claim List**:
   - Page loads → htmx GET → Flask `/claims`
   - Flask → API `GET /api/v1/claims`
   - API queries PostgreSQL → Returns paginated JSON
   - Flask renders claim list template → htmx displays

## File Structure

```text
truthgraph/
├── docker-compose.yml           # Service orchestration
├── .env.example                 # Environment template
├── .env                         # Local config (git-ignored)
├── Taskfile.yml                 # Task runner commands
├── pyproject.toml               # Python dependencies
├── DOCKER_SETUP.md              # Setup guide
├── SETUP_SUMMARY.md             # This file
│
├── docker/                      # Docker configuration
│   ├── api.Dockerfile           # FastAPI container
│   ├── frontend.Dockerfile      # Flask container
│   ├── init-db.sql              # Database schema
│   └── .dockerignore            # Build context exclusions
│
├── truthgraph/                  # Python backend package
│   ├── __init__.py
│   ├── main.py                  # FastAPI app
│   ├── db.py                    # Database connection
│   ├── logger.py                # Structured logging
│   ├── models.py                # Pydantic models
│   ├── schemas.py               # SQLAlchemy models
│   └── api/
│       ├── __init__.py
│       └── routes.py            # API endpoints
│
├── frontend/                    # htmx frontend (Flask)
│   ├── app.py                   # Flask application
│   ├── requirements.txt         # Python dependencies
│   ├── templates/               # Jinja2 templates
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── claim_list.html
│   │   ├── claim_submitted.html
│   │   └── error.html
│   └── static/
│       └── css/
│           └── style.css        # Modern CSS
│
├── frontend-react/              # React frontend (optional)
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   ├── Dockerfile.dev
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       ├── App.css
│       ├── index.css
│       └── components/
│           ├── ClaimForm.jsx
│           └── ClaimHistory.jsx
│
└── .volumes/                    # Docker volumes (git-ignored)
    └── postgres/                # Database data
```

## Phase 1 Completion Status

### ✅ Completed

- [x] Docker Compose setup with all services
- [x] PostgreSQL with pgvector extension
- [x] Database schema with all tables
- [x] FastAPI backend with core endpoints
- [x] Pydantic models for validation
- [x] SQLAlchemy ORM models
- [x] Structured logging with structlog
- [x] htmx frontend with Flask
- [x] React frontend (optional)
- [x] Developer-friendly Taskfile commands
- [x] Environment configuration
- [x] Health check endpoints
- [x] CORS configuration
- [x] Hot reload for development
- [x] Comprehensive documentation

### 🔄 Ready to Test

- [ ] `docker-compose up -d` brings up all services
- [ ] POST /api/v1/claims creates a claim
- [ ] GET /api/v1/claims lists claims
- [ ] GET /api/v1/claims/{id} retrieves a claim
- [ ] Frontend can submit claims
- [ ] Frontend displays claim history
- [ ] Database persists data across restarts

### 📋 Phase 2 (Next Steps)

- [ ] Embedding generation (sentence-transformers)
- [ ] Evidence retrieval (pgvector search)
- [ ] NLI-based verification
- [ ] Verdict generation
- [ ] ML model integration
- [ ] Tests (pytest)

## Testing the Setup

### 1. Start Services

```bash
task setup
task dev
```

### 2. Test API

```bash
# Health check
curl http://localhost:8000/health

# Create claim
curl -X POST http://localhost:8000/api/v1/claims \
  -H "Content-Type: application/json" \
  -d '{"text": "Python is a programming language"}'

# List claims
curl http://localhost:8000/api/v1/claims
```

### 3. Test Frontend

1. Open <http://localhost:5000>
2. Submit a claim in the form
3. Verify it appears in the history
4. Refresh page - claim should persist

### 4. Test Database Persistence

```bash
# Restart services
task restart

# Check claim still exists
curl http://localhost:8000/api/v1/claims
```

## Next Steps

1. **Test the setup** (see above)
2. **Verify all Phase 1 requirements** from [phase_01_foundation.md](docs/roadmap/v0/phase_01_foundation.md)
3. **Begin Phase 2**: ML features, embeddings, verification
4. **Add tests**: pytest for API, integration tests

## Developer Notes

### Why htmx + React?

- **htmx (Primary)**: Faster development, no build tools, server-side rendering
- **React (Optional)**: For teams familiar with React, or when moving to Phase 2 with complex interactive features

### Why uv?

- Faster than pip/poetry (10-100x)
- Single tool for dependencies and virtual environments
- Better lock file management
- Standardized in Phase 1 spec

### Why .volumes/ instead of named volumes?

- Easier access to data files
- Simpler backup/restore
- Better developer experience (can inspect data directly)

### Port Configuration

Default ports (configurable in `.env`):

- 5432: PostgreSQL
- 8000: FastAPI
- 5000: htmx frontend (Flask)
- 5173: React frontend (Vite)

## Support

- See `DOCKER_SETUP.md` for troubleshooting
- Check `task --list` for all available commands
- API documentation: <http://localhost:8000/docs>
- Phase 1 spec: `docs/roadmap/v0/phase_01_foundation.md`
