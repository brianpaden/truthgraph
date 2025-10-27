# Documentation Organization: Cheat Sheet

**Quick reference for daily use**

---

## Where Does It Go?

| Content Type | Location | Example |
|-------------|----------|---------|
| API endpoints | `docs/api/endpoints/` | `claims.md` |
| API schemas | `docs/api/schemas/` | `claim_schema.md` |
| Architecture decisions | `docs/architecture/decisions/` | `001-fastapi.md` |
| Service docs | `docs/services/` | `hybrid_search.md` |
| Database schema | `docs/database/` | `schema.md` |
| Deployment guide | `docs/deployment/` | `docker.md` |
| User guide | `docs/guides/` | `user_guide.md` |
| Quick start | `docs/guides/quickstart/` | `hybrid_search.md` |
| Feature (planned) | `planning/features/planned/` | `feature_14.md` |
| Feature (active) | `planning/features/in_progress/` | `feature_13.md` |
| Phase progress | `planning/phases/phase_N/` | `progress.md` |
| Technical debt | `planning/technical_debt/` | `test_fixes_needed.md` |
| Roadmap | `planning/roadmap/` | `v1/overview.md` |
| Completed feature | `archive/completed_features/` | `feature_5.md` |
| Completed phase | `archive/completed_phases/` | `phase_2.md` |
| Implementation summary | `archive/implementation_summaries/` | `api_integration.md` |

---

## Quick Commands

```bash
# Check root clutter
ls -1 *.md | grep -v -E '^(README|CONTRIBUTING|CHANGELOG)\.md$'

# Find documentation
find docs/ -name "*search*.md"
grep -r "vector search" docs/

# List active features
ls -1 planning/features/in_progress/

# List completed features
ls -1 archive/completed_features/

# Update phase progress
vim planning/phases/phase_2/progress.md

# Create new feature plan
cp planning/features/template.md planning/features/planned/feature_14.md
vim planning/features/planned/feature_14.md

# Start feature implementation
mv planning/features/planned/feature_14.md planning/features/in_progress/

# Complete feature
mv planning/features/in_progress/feature_14.md archive/completed_features/

# Create ADR
cp docs/architecture/decisions/template.md docs/architecture/decisions/005-new-decision.md
vim docs/architecture/decisions/005-new-decision.md
```

---

## Feature Lifecycle

```
1. CREATE   → planning/features/planned/feature_N.md
2. START    → mv to planning/features/in_progress/
3. DEVELOP  → update feature_N.md with progress
4. COMPLETE → mv to archive/completed_features/
```

---

## File Naming Rules

```bash
# Good ✓
docs/services/hybrid_search_service.md
docs/api/endpoints/claims.md
planning/features/in_progress/feature_13_webhooks.md
docs/architecture/decisions/004-caching-strategy.md

# Bad ✗
docs/HybridSearch.md                    # Use lowercase
docs/hs.md                              # Use descriptive names
planning/f13.md                         # Use full words
docs/architecture/decisions/caching.md  # ADRs need numbers
```

---

## README Indexes

Every major directory needs `README.md`:

```bash
# Required indexes
docs/README.md                  # All docs
docs/api/README.md              # API overview
docs/architecture/README.md     # Architecture overview
docs/services/README.md         # Services overview
planning/README.md              # Planning overview
archive/README.md               # Archive overview

# Create missing indexes
touch docs/subdirectory/README.md
```

---

## Status Indicators

```markdown
## Status: Stable ✓          # Permanent, production-ready
## Status: In Progress 🚧    # Currently being worked on
## Status: Planned 📋        # Not yet started
## Status: Completed ✓       # Done and archived
## Status: Deprecated ⚠️      # No longer valid
## Status: Experimental 🧪   # Research/proof-of-concept
```

---

## Daily Workflow

```bash
# Morning: Check status
cat planning/phases/phase_2/progress.md
ls planning/features/in_progress/
cat planning/phases/phase_2/blockers.md

# During work: Update feature
vim planning/features/in_progress/feature_13.md

# End of day: Update progress
vim planning/phases/phase_2/progress.md

# Weekly: Archive completed
mv planning/features/in_progress/done.md archive/completed_features/
```

---

## Search Patterns

```bash
# Find API documentation
find docs/api -name "*.md"

# Find service documentation
find docs/services -name "*.md"

# Find ADRs
find docs/architecture/decisions -name "*.md"

# Search content
grep -r "authentication" docs/
grep -r "vector search" docs/services/
grep -r "TODO" planning/

# Find active work
ls planning/features/in_progress/
cat planning/phases/*/progress.md
```

---

## Common Tasks

### Create New Feature Plan
```bash
vim planning/features/planned/feature_N_name.md
# Fill in requirements, architecture, implementation plan
```

### Start Feature Implementation
```bash
mv planning/features/planned/feature_N.md planning/features/in_progress/
vim planning/features/in_progress/feature_N.md
# Update status to "In Progress"
```

### Complete Feature
```bash
mv planning/features/in_progress/feature_N.md archive/completed_features/
vim archive/completed_features/feature_N.md
# Add completion date, lessons learned
```

### Create Architecture Decision
```bash
cp docs/architecture/decisions/template.md docs/architecture/decisions/NNN-title.md
vim docs/architecture/decisions/NNN-title.md
# Fill in context, decision, consequences, alternatives
```

### Document New Service
```bash
vim docs/services/new_service.md
# Use service documentation template from guide
```

### Update Phase Progress
```bash
vim planning/phases/phase_N/progress.md
# Add today's accomplishments, blockers, next steps
```

---

## Link References

### Internal Links
```markdown
# Relative links
[API Documentation](../api/README.md)
[Service Documentation](vector_search.md)

# Anchors
[Installation](#installation)
[Configuration](#configuration)
```

### Cross-References
```markdown
## Related Documentation
- [API Endpoints](../api/endpoints/ml.md)
- [Architecture Decision](../architecture/decisions/003-ml-integration.md)
- [Database Schema](../database/schema.md)
```

---

## Migration Quick Start

```bash
# 1. Backup
git add . && git commit -m "backup before reorg"
git branch backup-before-docs-reorg

# 2. Create structure
mkdir -p docs/{api,architecture,services,database,deployment,development,operations,guides,research,integration}
mkdir -p planning/{features,phases,technical_debt,tasks,roadmap}
mkdir -p planning/features/{in_progress,planned,backlog}
mkdir -p archive/{completed_features,completed_phases,implementation_summaries,deprecated}

# 3. Move files (see DOCUMENTATION_MIGRATION_PLAN.md)
# 4. Create indexes
# 5. Commit
git add . && git commit -m "docs: reorganize structure"
```

---

## Validation Checks

```bash
# Check root is clean
ls -1 *.md | wc -l  # Should be ≤ 3

# Check indexes exist
test -f docs/README.md && echo "✓ docs/README.md exists"
test -f planning/README.md && echo "✓ planning/README.md exists"
test -f archive/README.md && echo "✓ archive/README.md exists"

# Find broken links
# npm install -g markdown-link-check
find . -name "*.md" -exec markdown-link-check {} \;
```

---

## Taskfile Tasks

```yaml
tasks:
  docs:check:
    desc: Check documentation structure
    cmds:
      - task: docs:check-root
      - task: docs:check-indexes
      - task: docs:check-links

  docs:check-root:
    desc: Check for root clutter
    cmds:
      - |
        COUNT=$(ls -1 *.md | grep -v -E '^(README|CONTRIBUTING|CHANGELOG)\.md$' | wc -l)
        if [ $COUNT -gt 0 ]; then
          echo "ERROR: Found $COUNT extra markdown files in root"
          exit 1
        fi
        echo "✓ Root is clean"

  docs:review:
    desc: Weekly documentation review
    cmds:
      - echo "Active features:"
      - ls -1 planning/features/in_progress/
      - echo "\nMove completed to archive/"
```

---

## Documentation Templates

### Feature Template
```markdown
# Feature N: [Name]
## Status: [Planned | In Progress | Completed]
## Overview
## Requirements
## Architecture
## Implementation Plan
## Timeline
## Related Documentation
```

### ADR Template
```markdown
# ADR NNN: [Title]
## Status: [Proposed | Accepted | Deprecated]
## Date: YYYY-MM-DD
## Context
## Decision
## Consequences
## Alternatives Considered
## Related Decisions
```

### Service Template
```markdown
# [Service Name] Service
## Overview
## Architecture
## API Contract
## Integration Patterns
## Configuration
## Observability
## Performance
## Testing
## Troubleshooting
```

---

## Maintenance Schedule

| Frequency | Task |
|-----------|------|
| **Daily** | Update `planning/phases/phase_N/progress.md` |
| **Daily** | Update feature docs in `planning/features/in_progress/` |
| **Weekly** | Move completed features to `archive/` |
| **Weekly** | Review technical debt in `planning/technical_debt/` |
| **Weekly** | Check for root clutter |
| **Monthly** | Review `docs/` for outdated content |
| **Monthly** | Update architecture diagrams |
| **Quarterly** | Comprehensive documentation audit |

---

## Key Rules

1. ✅ **DO**: Keep only 3 markdown files at root (README, CONTRIBUTING, CHANGELOG)
2. ✅ **DO**: Create README.md in every major directory
3. ✅ **DO**: Use descriptive lowercase filenames with underscores
4. ✅ **DO**: Move completed features to archive within 1 week
5. ✅ **DO**: Add cross-references to related documentation
6. ❌ **DON'T**: Create markdown files at root level
7. ❌ **DON'T**: Use abbreviations in filenames (e.g., `hs.md`)
8. ❌ **DON'T**: Leave completed work in `planning/`
9. ❌ **DON'T**: Edit archived documentation (it's historical)
10. ❌ **DON'T**: Skip README indexes

---

## Emergency Rollback

```bash
# If migration goes wrong
git checkout backup-before-docs-reorg

# Or revert last commit
git revert HEAD

# Or hard reset (destructive!)
git reset --hard HEAD~1
```

---

## Quick Reference Files

| File | Purpose |
|------|---------|
| **DOCUMENTATION_ORGANIZATION_GUIDE.md** | Comprehensive 8,000-word guide |
| **DOCUMENTATION_MIGRATION_PLAN.md** | Step-by-step migration |
| **DOCUMENTATION_REORGANIZATION_SUMMARY.md** | Executive summary |
| **DOCUMENTATION_STRUCTURE_VISUAL.md** | Visual diagrams |
| **DOCS_CHEAT_SHEET.md** | This file - quick reference |
| **ADR_TEMPLATE.md** | Architecture decision template |

---

## Getting Help

```bash
# Read the guides
cat DOCUMENTATION_ORGANIZATION_GUIDE.md
cat DOCUMENTATION_MIGRATION_PLAN.md

# Check examples
ls docs/architecture/decisions/
cat docs/services/hybrid_search.md

# Search for patterns
grep -r "## Status" planning/
grep -r "## Architecture" docs/
```

---

**Keep this cheat sheet handy for daily use!**

Print it, bookmark it, or pin it to your desktop.
