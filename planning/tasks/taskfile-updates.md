# Taskfile.yml Updates - Phase 2 ML Features

This document summarizes the new tasks added to `Taskfile.yml` for Phase 2 ML functionality.

## New Task Categories

### 1. Database Tasks

| Command | Description |
|---------|-------------|
| `task db:migrate` | Run database migrations (Alembic) |
| `task db:migrate:down` | Rollback last database migration |
| `task db:migrate:status` | Show current migration status |
| `task db:migrate:history` | Show migration history |
| `task db:migrate:create MIGRATION_NAME="description"` | Create a new migration |

**Example Usage:**
```bash
# Apply all pending migrations
task db:migrate

# Check current migration version
task db:migrate:status

# Rollback the last migration
task db:migrate:down

# Create a new migration
task db:migrate:create MIGRATION_NAME="add_user_roles"
```

---

### 2. Testing Tasks

| Command | Description |
|---------|-------------|
| `task test` | Run all tests (unit + integration) |
| `task test:unit` | Run unit tests only |
| `task test:integration` | Run integration tests only |
| `task test:ml` | Run ML service tests (embedding, NLI, vector search) |
| `task test:coverage` | Run tests with coverage report |

**Example Usage:**
```bash
# Run all tests
task test

# Run only unit tests (fast, no model downloads)
task test:unit

# Run only ML-related tests
task test:ml

# Generate coverage report
task test:coverage
```

---

### 3. ML Service Tasks

| Command | Description |
|---------|-------------|
| `task ml:warmup` | Warmup ML models (download and cache) |
| `task ml:benchmark` | Run all ML performance benchmarks |
| `task ml:benchmark:embedding` | Benchmark embedding service |
| `task ml:benchmark:nli` | Benchmark NLI service |
| `task ml:benchmark:vector` | Benchmark vector search |
| `task ml:benchmark:e2e` | Benchmark end-to-end pipeline |
| `task ml:profile` | Profile ML services for bottlenecks |
| `task ml:optimize` | Optimize batch sizes for current hardware |

**Example Usage:**
```bash
# First-time setup: download and cache all ML models
task ml:warmup

# Run all benchmarks
task ml:benchmark

# Profile for performance bottlenecks
task ml:profile

# Find optimal batch sizes for your hardware
task ml:optimize

# Benchmark just the embedding service
task ml:benchmark:embedding
```

---

### 4. GPU Support Tasks

| Command | Description |
|---------|-------------|
| `task dev:gpu` | Start development environment with GPU support |
| `task gpu:check` | Check GPU availability in container |

**Example Usage:**
```bash
# Start services with GPU acceleration (requires NVIDIA Docker)
task dev:gpu

# Verify GPU is available
task gpu:check

# Expected output if GPU is working:
# CUDA available: True
# Device: NVIDIA GeForce RTX 3090
```

---

## Quick Reference Guide

### First-Time Setup

```bash
# 1. Setup environment
task setup

# 2. Start services
task dev

# 3. Run migrations
task db:migrate

# 4. Download ML models (takes 2-5 minutes)
task ml:warmup

# 5. Verify everything works
task test:ml
```

### Daily Development Workflow

```bash
# Start services
task dev

# Run tests after making changes
task test:unit

# Check linting
task lint

# Auto-fix issues
task lint:fix
```

### Performance Tuning Workflow

```bash
# Profile to find bottlenecks
task ml:profile

# Optimize batch sizes
task ml:optimize

# Run benchmarks to validate
task ml:benchmark

# Test end-to-end performance
task ml:benchmark:e2e
```

### Migration Workflow

```bash
# Create a new migration
task db:migrate:create MIGRATION_NAME="add_new_table"

# Apply migrations
task db:migrate

# Check status
task db:migrate:status

# Rollback if needed
task db:migrate:down
```

---

## Performance Targets

When running benchmarks, these are the expected targets:

| Benchmark | Target | Command |
|-----------|--------|---------|
| Embedding throughput | >500 texts/second | `task ml:benchmark:embedding` |
| NLI throughput | >2 pairs/second | `task ml:benchmark:nli` |
| Vector search latency | <100ms | `task ml:benchmark:vector` |
| End-to-end pipeline | <60 seconds | `task ml:benchmark:e2e` |
| Memory usage | <4GB | Check during `task ml:profile` |

---

## Troubleshooting

### "Models not found" errors

```bash
# Download and cache models
task ml:warmup
```

### "Database not migrated" errors

```bash
# Apply migrations
task db:migrate
```

### Slow performance

```bash
# Profile to find bottlenecks
task ml:profile

# Optimize batch sizes
task ml:optimize

# Consider GPU acceleration
task dev:gpu
```

### GPU not detected

```bash
# Check GPU availability
task gpu:check

# Ensure NVIDIA Docker runtime is installed
# See: DOCKER_README.md "GPU Support" section
```

---

## All Available Tasks

Run `task --list` to see all available tasks:

```bash
task --list
```

Or run `task` with no arguments to see the help menu:

```bash
task
```

---

## Changes Summary

**Added 23 new tasks** across 4 categories:

- **5 database tasks** - Migration management
- **5 testing tasks** - Unit, integration, ML, coverage
- **8 ML service tasks** - Warmup, benchmarking, profiling, optimization
- **2 GPU tasks** - GPU-enabled development, GPU checking
- **Updated 3 existing tasks** - Database migration, testing

**Removed 0 tasks** - All existing tasks preserved for backward compatibility

---

## Integration with Phase 2

These tasks support the Phase 2 Core Features implementation:

- **Feature 1** (Embedding): `ml:benchmark:embedding`, `ml:warmup`
- **Feature 2** (Vector Search): `ml:benchmark:vector`, `db:migrate`
- **Feature 4** (NLI): `ml:benchmark:nli`, `ml:warmup`
- **Feature 8** (Database): `db:migrate`, `db:migrate:*`
- **Feature 9** (Testing): `test`, `test:ml`, `test:coverage`
- **Feature 10** (Performance): `ml:profile`, `ml:optimize`, `ml:benchmark:e2e`
- **Feature 11** (Docker): `dev:gpu`, `gpu:check`

---

## Documentation References

- **Database Migrations**: See `docs/PHASE2_DATABASE_MIGRATION.md`
- **ML Services**: See `docs/PERFORMANCE_OPTIMIZATION.md`
- **Docker Setup**: See `DOCKER_README.md`
- **Testing**: See `tests/README.md` (to be created in Phase 2)
- **GPU Support**: See `DOCKER_README.md` "GPU Support" section

---

**Last Updated**: 2025-10-25
**Phase**: 2 (Core Features)
**Status**: Active
