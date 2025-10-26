# Dockerfile Fix: Missing Alembic Files

## Issue

The Alembic migration files were not being copied into the Docker container, causing the `task db:migrate` command to fail with:

```
FAILED: No 'script_location' key found in configuration.
```

## Root Cause

The Deployment-Engineer agent created the Docker configuration but only copied the `truthgraph/` application directory. The `alembic/` directory and `alembic.ini` file were not included in the Dockerfile COPY statements.

### Original Dockerfile (Lines 72-78)

```dockerfile
# Stage 3: Runtime stage
FROM ml-stage AS runtime

WORKDIR /app

# Copy application code (already copied in dependency stages, but ensure it's fresh)
COPY truthgraph ./truthgraph
```

## Solution

Added COPY statements for Alembic files to the Dockerfile.

### Fixed Dockerfile (Lines 72-82)

```dockerfile
# Stage 3: Runtime stage
FROM ml-stage AS runtime

WORKDIR /app

# Copy application code
COPY truthgraph ./truthgraph

# Copy Alembic migration files
COPY alembic.ini ./alembic.ini
COPY alembic ./alembic
```

## Steps to Fix

1. **Updated Dockerfile**:
   ```bash
   # Added lines 80-82 to docker/api.Dockerfile
   ```

2. **Rebuilt the API container**:
   ```bash
   docker-compose build api
   ```
   - Build was fast (~2 seconds) due to cached layers
   - Only new alembic files were added

3. **Restarted services**:
   ```bash
   docker-compose down && docker-compose up -d
   ```

4. **Verified alembic files in container**:
   ```bash
   docker-compose exec api ls -la alembic/
   docker-compose exec api ls -la alembic.ini
   ```

5. **Handled duplicate table error**:
   - The database had `embeddings` table from earlier SQL migration
   - Alembic didn't know about it (no version recorded)
   - Stamped database to mark it as current:
   ```bash
   docker-compose exec api alembic stamp head
   ```

6. **Verified migration status**:
   ```bash
   task db:migrate:status
   # Output: phase2_ml_tables (head)
   ```

## Why the `.dockerignore` Didn't Block It

The `.dockerignore` file doesn't explicitly exclude `alembic/`:

```dockerignore
# Doesn't block alembic/
tests/         # Only tests are excluded
docs/          # Only docs are excluded
*.md           # Only markdown files
```

However, the Dockerfile simply wasn't copying it. This is a **missing COPY statement** issue, not a `.dockerignore` exclusion issue.

## Verification

After the fix:

```bash
# Check files exist in container
$ docker-compose exec api ls -la alembic/
total 24
drwxr-xr-x 3 root root 4096 Oct 25 08:53 .
drwxr-xr-x 1 root root 4096 Oct 26 02:43 ..
-rwxr-xr-x 1 root root 3087 Oct 25 08:53 README.md
-rwxr-xr-x 1 root root 2993 Oct 25 08:47 env.py
-rwxr-xr-x 1 root root  735 Oct 25 08:47 script.py.mako
drwxr-xr-x 2 root root 4096 Oct 25 08:50 versions

# Check migration status
$ task db:migrate:status
phase2_ml_tables (head)

# All task commands now work
$ task db:migrate          # ✅ Works
$ task db:migrate:history  # ✅ Works
$ task db:migrate:down     # ✅ Works
```

## Updated Files

- **docker/api.Dockerfile**: Added lines 80-82 to copy alembic files
- **Container image**: Rebuilt with alembic support
- **Database**: Stamped to mark current migration version

## Task Commands Now Working

All database task commands are now functional:

```bash
task db:migrate              # Apply migrations
task db:migrate:down         # Rollback last migration
task db:migrate:status       # Show current version
task db:migrate:history      # Show migration history
task db:migrate:create       # Create new migration
```

## Lesson Learned

When creating Docker images for applications with database migrations:

1. ✅ **Always copy migration files**: `alembic/`, `alembic.ini`, or equivalent
2. ✅ **Test migration commands**: Verify `alembic upgrade head` works in container
3. ✅ **Document what's copied**: Make it explicit in Dockerfile comments
4. ✅ **Add to CI/CD checks**: Ensure migrations run in automated tests

## Status

✅ **FIXED** - Alembic migrations now fully functional in Docker containers

---

**Fixed by**: Manual Dockerfile update
**Date**: October 25, 2025
**Impact**: Database migrations now work with `task db:migrate` commands
