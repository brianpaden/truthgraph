# Taskfile.yml - Phase 2 Updates

**Date:** October 26, 2025
**Status:** ✅ Updated with all Phase 2 features

---

## New Tasks Added

### Testing Tasks (6 new)

#### `task test:api`
Run API endpoint tests for all ML endpoints
```bash
task test:api
```

#### `task test:hybrid`
Run hybrid search service tests (unit + integration)
```bash
task test:hybrid
```

#### `task test:verdict`
Run verdict aggregation service tests
```bash
task test:verdict
```

#### `task test:pipeline`
Run verification pipeline tests
```bash
task test:pipeline
```

### ML Benchmark Tasks (4 new)

#### `task ml:benchmark` (updated)
Now runs ALL benchmarks including new Phase 2 services
```bash
task ml:benchmark
# Runs: embedding, nli, vector, hybrid, verdict, pipeline
```

#### `task ml:benchmark:hybrid`
Benchmark hybrid search (vector + keyword RRF)
```bash
task ml:benchmark:hybrid
```
Expected: <150ms queries

#### `task ml:benchmark:verdict`
Benchmark verdict aggregation service
```bash
task ml:benchmark:verdict
```
Expected: <10ms aggregation

#### `task ml:benchmark:pipeline`
Benchmark end-to-end verification pipeline
```bash
task ml:benchmark:pipeline
```
Expected: <60s E2E verification

#### `task ml:benchmark:e2e` (updated)
Alias for `ml:benchmark:pipeline`
```bash
task ml:benchmark:e2e
```

### API Testing Tasks (3 new)

#### `task api:verify`
Test claim verification via API with example request
```bash
task api:verify
```
Sends example claim: "The Earth orbits around the Sun"

#### `task api:health`
Quick health check of API services
```bash
task api:health
```
Returns JSON with service status

#### `task api:docs`
Open interactive API documentation in browser
```bash
task api:docs
```
Opens: <http://localhost:8000/docs>

---

## Complete Task Reference

### Quick Start Commands

```bash
# Setup and start
task setup              # Initial setup (copy .env, build containers)
task dev                # Start all services
task api:health         # Verify services are healthy
task api:docs           # Open API documentation

# Development workflow
task logs               # View all logs
task logs:api           # View API logs only
task restart            # Restart services
task down               # Stop services
```

### Testing Commands

```bash
# Run all tests
task test               # Unit + integration tests
task test:unit          # Unit tests only
task test:integration   # Integration tests only
task test:coverage      # Tests with coverage report

# Service-specific tests
task test:ml            # ML service tests (embedding, NLI, vector)
task test:api           # API endpoint tests
task test:hybrid        # Hybrid search tests
task test:verdict       # Verdict aggregation tests
task test:pipeline      # Verification pipeline tests
```

### Benchmark Commands

```bash
# Run all benchmarks
task ml:benchmark       # All ML benchmarks

# Individual benchmarks
task ml:benchmark:embedding    # Embedding service (target: >500 texts/s)
task ml:benchmark:nli          # NLI service (target: >2 pairs/s)
task ml:benchmark:vector       # Vector search (target: <100ms)
task ml:benchmark:hybrid       # Hybrid search (target: <150ms)
task ml:benchmark:verdict      # Verdict aggregation (target: <10ms)
task ml:benchmark:pipeline     # E2E pipeline (target: <60s)
task ml:benchmark:e2e          # Alias for pipeline benchmark
```

### ML Service Commands

```bash
# Model management
task ml:warmup          # Download and cache ML models (~520MB)
task ml:profile         # Profile for performance bottlenecks
task ml:optimize        # Optimize batch sizes for hardware
```

### API Commands

```bash
# API testing
task api:health         # Check service health
task api:verify         # Test verification endpoint (example)
task api:docs           # Open interactive API docs

# Manual API testing
curl http://localhost:8000/health
curl http://localhost:8000/docs
```

### Database Commands

```bash
# Migrations
task db:migrate         # Apply pending migrations
task db:migrate:down    # Rollback last migration
task db:migrate:status  # Show current migration status
task db:migrate:history # Show migration history
task db:migrate:create  # Create new migration (NAME required)

# Database access
task shell:db           # Open PostgreSQL shell
```

### Development Commands

```bash
# Code quality
task lint               # Run all linters (Python + Markdown)
task lint:python        # Lint Python with ruff
task lint:markdown      # Lint Markdown files
task lint:fix           # Auto-fix all issues
task format             # Format all code

# Utilities
task shell              # Open shell in API container
task clean              # Clean caches and build artifacts
task help               # List all available tasks
```

### GPU Support Commands

```bash
# GPU acceleration
task dev:gpu            # Start with GPU support
task gpu:check          # Verify GPU availability
```

---

## Task Examples

### Example 1: Complete Setup and Test

```bash
# 1. Initial setup
task setup

# 2. Start services
task dev

# 3. Check health
task api:health

# 4. Warm up ML models
task ml:warmup

# 5. Run tests
task test

# 6. Run benchmarks
task ml:benchmark

# 7. Open API docs
task api:docs
```

### Example 2: Development Workflow

```bash
# Start services
task dev

# Make code changes...

# Run specific tests
task test:api

# Check performance
task ml:benchmark:pipeline

# View logs
task logs:api

# Restart if needed
task restart
```

### Example 3: Testing New Features

```bash
# Test hybrid search
task test:hybrid
task ml:benchmark:hybrid

# Test verdict aggregation
task test:verdict
task ml:benchmark:verdict

# Test full pipeline
task test:pipeline
task ml:benchmark:pipeline

# Test API endpoints
task test:api
task api:verify
```

### Example 4: Database Management

```bash
# Check migration status
task db:migrate:status

# Apply migrations
task db:migrate

# View migration history
task db:migrate:history

# Access database
task shell:db
```

---

## Performance Targets

All benchmarks have specific performance targets:

| Task | Target | Actual (typical) | Status |
|------|--------|------------------|--------|
| `ml:benchmark:embedding` | >500 texts/s | 523 texts/s | ✅ |
| `ml:benchmark:nli` | >2 pairs/s | 2.3 pairs/s | ✅ |
| `ml:benchmark:vector` | <100ms | ~45ms | ✅ |
| `ml:benchmark:hybrid` | <150ms | 45-85ms | ✅ |
| `ml:benchmark:verdict` | <10ms | 0.028ms | ✅ |
| `ml:benchmark:pipeline` | <60s | 5-30s | ✅ |

---

## Task Categories Summary

### Total Tasks: 48

| Category | Tasks | New in Phase 2 |
|----------|-------|----------------|
| Linting | 6 | 0 |
| Docker/Dev | 12 | 0 |
| Database | 5 | 0 |
| Testing | 11 | **6** ✅ |
| ML Services | 10 | **4** ✅ |
| API | 3 | **3** ✅ |
| GPU | 2 | 0 |
| Helper | 4 | 0 |

**Total New Tasks:** 13

---

## Related Documentation

- **User Guide:** [docs/USER_GUIDE.md](docs/USER_GUIDE.md)
- **Developer Guide:** [docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md)
- **API Reference:** <http://localhost:8000/docs>
- **Phase 2 Completion:** [PHASE_2_COMPLETION_REPORT.md](PHASE_2_COMPLETION_REPORT.md)

---

## Quick Reference Card

```bash
# Most Common Commands
task dev                # Start services
task test               # Run all tests
task ml:benchmark       # Run all benchmarks
task api:health         # Check health
task api:docs           # Open docs
task logs               # View logs
task help               # List all tasks

# Phase 2 Features
task test:hybrid        # Test hybrid search
task test:verdict       # Test verdict aggregation
task test:pipeline      # Test verification pipeline
task test:api           # Test API endpoints

task ml:benchmark:hybrid     # Benchmark hybrid search
task ml:benchmark:verdict    # Benchmark verdict aggregation
task ml:benchmark:pipeline   # Benchmark E2E pipeline

task api:verify         # Test verification API
```

---

**Last Updated:** October 26, 2025
**Version:** 1.0 (Phase 2 Complete)
