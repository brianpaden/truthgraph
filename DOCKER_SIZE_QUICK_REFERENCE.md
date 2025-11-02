# Docker Image Size Quick Reference

## Current Image: truthgraph-api:latest = 8.03 GB

### Size Breakdown

```
8.03 GB Total Image
│
├─ 7.48 GB (93%) - Python packages in /usr/local
│  │
│  ├─ 4.3 GB (54%) - NVIDIA CUDA libraries (unavoidable for ML inference)
│  ├─ 1.7 GB (21%) - PyTorch framework
│  ├─ 592 MB (7%) - Triton compiler
│  ├─ 490 MB (6%) - Other ML libraries (scipy, transformers, sklearn, etc.)
│  ├─ 100 MB (1%) - Development tools [REMOVABLE]
│  │   └─ mypy (12 MB), pytest suite (20+ MB), ruff (15 MB)
│  └─ 200 MB (2%) - Build artifacts not cleaned [REMOVABLE]
│
├─ 323 MB (4%) - APT packages (gcc, g++, build-essential) [PARTIALLY REMOVABLE]
├─ 107 MB (1%) - Python base image and runtime
├─ 78.6 MB (1%) - Debian filesystem
└─ 3.75 MB - Source code + tests + scripts
   └─ 2.75 MB in tests/ [REMOVABLE]
   └─ 980 kB in scripts/ [REMOVABLE]
```

### Problem Areas

| Issue | Size | Removable? | Difficulty |
|-------|------|-----------|-----------|
| Test files in production image | 2.75 MB | Yes | Easy |
| Development tools (pytest, mypy) | 100 MB | Yes | Easy |
| APT cache not fully cleaned | 100-150 MB | Yes | Easy |
| Build tools (gcc/g++) left in image | 600 MB | Partial | Medium |
| ML stack (PyTorch + CUDA) | 5.3 GB | No (needed for API) | N/A |

## Reduction Opportunities

### Quick Wins (Easy - 15 min)
```
Remove from docker/api.Dockerfile:
  - COPY tests ./tests           (-2.75 MB)
  - COPY scripts ./scripts       (-980 kB)
  - Pytest from ml dependencies  (-80 MB)

Remove APT cache more aggressively:
  - rm -rf /var/cache/apt/*      (-100 MB)

Result: 7.80 GB (-2.8% / -230 MB)
```

### Standard Approach (Medium - 1 hour)
```
Restructure Dockerfile:
  - Separate build stage with proper cleanup
  - Remove build-essential after compilation
  - Clean /var/lib/apt/lists after each RUN

Result: 6.2 GB (-23% / -1.8 GB)
```

### Advanced Solution (Hard - Architectural Change)
```
Split into two images:
  - api-core.Dockerfile      → 1.5-2.0 GB (no ML)
  - ml-inference.Dockerfile  → 5.0-6.0 GB (ML only, GPU nodes)

Result: 1.5-2.0 GB for core API (-75% / -6.0 GB)
        5.0-6.0 GB for ML service (separate, on-demand)
```

## Why So Large?

1. **PyTorch Framework = 5.3 GB** (not removable for ML API)
   - NVIDIA CUDA libraries: 4.3 GB
   - PyTorch itself: 1.7 GB
   - Triton compiler: 592 MB
   - Supporting ML libraries: 600 MB

2. **Build Artifacts = 600+ MB** (removable)
   - gcc and g++ compilers left in image
   - Build headers not cleaned up
   - APT cache not fully removed

3. **Development Tools = 100 MB** (removable)
   - pytest and plugins
   - mypy type checker
   - ruff linter

4. **Test & Script Files = 3.75 MB** (removable, bad practice)
   - Test files shouldn't be in production image
   - Performance scripts not needed at runtime

## Implementation Priority

### Priority 1: Do Today (5 min)
Remove test files and fix pyproject.toml:
- Edit `docker/api.Dockerfile` - remove test/script copies
- Edit `pyproject.toml` - remove pytest from ml deps
- **Savings: 100 MB**

### Priority 2: Do This Week (30 min)
Optimize Dockerfile for better layer caching:
- Create dedicated build stage
- Clean up build dependencies properly
- **Savings: 1.7 GB more**

### Priority 3: Future Planning (1-2 weeks)
Architectural refactoring:
- Separate core API from ML inference
- Deploy ML on GPU infrastructure only
- Core API remains lightweight
- **Savings: 6.0 GB**

## Files to Modify

### For Phase 1 (Quick Wins)

**1. Remove tests & scripts from docker/api.Dockerfile**

```dockerfile
# REMOVE these lines (currently at 101-107):
# COPY tests ./tests
# COPY scripts ./scripts
```

**2. Fix pyproject.toml ml dependencies**

```toml
# REMOVE these lines from ml dependencies:
# "pytest>=7.4.3",
# "pytest-asyncio>=0.21.1",
```

**3. Improve APT cleanup in base stage**

```dockerfile
# ADD after apt-get clean:
&& apt-get autoclean \
&& apt-get autoremove -y \
&& rm -rf /var/cache/apt/*
```

### For Phase 2 (Medium Effort)

Create new multi-stage structure in docker/api.Dockerfile:
- base stage: Python + system deps
- build stage: ML dependencies (with cleanup)
- runtime stage: Copy from build (no build tools)

### For Phase 3 (Long-term)

Create:
- `docker/api-core.Dockerfile` - Light API (1.5 GB)
- `docker/ml-inference.Dockerfile` - ML service (5 GB)
- `docker-compose.ml.yml` - Service composition

## Testing After Changes

```bash
# Build with changes
docker build -t truthgraph-api:v2 -f docker/api.Dockerfile .

# Check new size
docker images truthgraph-api:v2 --format "{{.Size}}"

# Verify functionality
docker run --rm truthgraph-api:v2 python -c "import torch; print(torch.__version__)"
docker run --rm truthgraph-api:v2 python -c "from truthgraph import __version__; print('OK')"
```

## Key Takeaway

**The 8 GB is 66% PyTorch (necessary for ML API) + 34% bloat (removable).**

If ML inference is needed: Target 4.0-4.3 GB (Phase 2)
If ML inference is optional: Target 1.5-2.0 GB core API (Phase 3)
