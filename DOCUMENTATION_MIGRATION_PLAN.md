# Documentation Migration Plan

This document maps current documentation locations to the new structure.

## Migration Mapping

### Root Level → New Locations

#### Permanent Documentation (to docs/)
```bash
# API Documentation
mv API_QUICK_REFERENCE.md docs/guides/api_quick_reference.md

# Deployment Documentation
mv DOCKER_README.md docs/deployment/docker.md
mv DOCKER_SETUP.md docs/deployment/docker_setup_guide.md
mv docs/DOCKER_ML_SETUP.md docs/deployment/docker_ml.md

# Quick Start Guides
mv HYBRID_SEARCH_QUICKSTART.md docs/guides/quickstart/hybrid_search.md
mv EMBEDDING_SERVICE_QUICKSTART.md docs/guides/quickstart/embedding_service.md
mv MIGRATION_QUICKSTART.md docs/guides/quickstart/migration.md
mv DOCKER_QUICK_CHECKLIST.md docs/guides/quickstart/docker_checklist.md

# Service Documentation
mv docs/HYBRID_SEARCH_SERVICE.md docs/services/hybrid_search.md
mv docs/verification_pipeline.md docs/services/verification_pipeline.md
mv docs/VECTOR_SEARCH_IMPLEMENTATION.md docs/services/vector_search.md

# Operations Documentation
mv docs/PERFORMANCE_OPTIMIZATION.md docs/operations/performance_tuning.md

# Developer Guides
mv docs/DEVELOPER_GUIDE.md docs/guides/developer_guide.md
mv docs/USER_GUIDE.md docs/guides/user_guide.md

# Reference Documentation
mv VECTOR_SEARCH_QUICK_REF.md docs/guides/quickstart/vector_search_reference.md
```

#### Active Planning (to planning/)
```bash
# Phase Planning
mkdir -p planning/phases/phase_2
mv PHASE_2_IMPLEMENTATION_PLAN.md planning/phases/phase_2/plan.md
mv PHASE_2_README.md planning/phases/phase_2/README.md
mv PHASE_2_QUICK_REFERENCE.md planning/phases/phase_2/quick_reference.md

# Task Management
mkdir -p planning/tasks
mv TASKFILE_PHASE2_UPDATES.md planning/tasks/taskfile_phase2_updates.md
mv TASKFILE_UPDATES.md planning/tasks/taskfile_updates.md

# Technical Debt
mkdir -p planning/technical_debt
mv TEST_FIXES_NEEDED.md planning/technical_debt/test_fixes_needed.md

# Roadmap
mv docs/roadmap planning/roadmap

# Planning Index
mv PLANNING_DOCUMENTATION_INDEX.md planning/README.md
```

#### Historical Archive (to archive/)
```bash
# Completed Features
mkdir -p archive/completed_features
mv FEATURE_5_VERDICT_AGGREGATION_SUMMARY.md archive/completed_features/feature_5_verdict_aggregation.md
mv IMPLEMENTATION_SUMMARY_FEATURE6.md archive/completed_features/feature_6_implementation.md
mv docs/FEATURE_10_IMPLEMENTATION_SUMMARY.md archive/completed_features/feature_10_implementation.md
mv FEATURE_11_DELIVERY_REPORT.md archive/completed_features/feature_11_docker_delivery.md

# Completed Phases
mkdir -p archive/completed_phases
mv PHASE_2_COMPLETION_REPORT.md archive/completed_phases/phase_2_completion.md
mv PHASE_2_EXECUTION_SUMMARY.md archive/completed_phases/phase_2_execution.md

# Implementation Summaries
mkdir -p archive/implementation_summaries
mv API_INTEGRATION_SUMMARY.md archive/implementation_summaries/api_integration_summary.md
mv DOCKER_IMPLEMENTATION_SUMMARY.md archive/implementation_summaries/docker_implementation_summary.md
mv HYBRID_SEARCH_IMPLEMENTATION_SUMMARY.md archive/implementation_summaries/hybrid_search_summary.md
mv EMBEDDING_SERVICE_IMPLEMENTATION_REPORT.md archive/implementation_summaries/embedding_service_summary.md
mv NLI_SERVICE_IMPLEMENTATION_REPORT.md archive/implementation_summaries/nli_service_summary.md
mv IMPLEMENTATION_SUMMARY.md archive/implementation_summaries/general_implementation_summary.md
mv SETUP_SUMMARY.md archive/implementation_summaries/setup_summary.md
mv SUBAGENT_IMPLEMENTATION_PLAN_SUMMARY.md archive/implementation_summaries/subagent_implementation_summary.md
mv SWARM_EXECUTION_SUMMARY.md archive/implementation_summaries/swarm_execution_summary.md
mv VECTOR_SEARCH_SUMMARY.md archive/implementation_summaries/vector_search_summary.md
mv DOCKER_TEST_SETUP_COMPLETE.md archive/implementation_summaries/docker_test_setup.md
mv DOCKERFILE_FIX_ALEMBIC.md archive/implementation_summaries/dockerfile_alembic_fix.md

# Test Completion Reports
mv TEST_FIXES_COMPLETE.md archive/implementation_summaries/test_fixes_complete.md
```

#### Database Documentation (to docs/database/)
```bash
mkdir -p docs/database
mkdir -p docs/database/migrations
mv docs/PHASE2_DATABASE_MIGRATION.md docs/database/migrations/phase2_migration.md
mv docs/roadmap/v0/database_schema.md docs/database/schema_v0.md
```

#### Architecture Documentation (to docs/architecture/)
```bash
mkdir -p docs/architecture
mv docs/roadmap/v0/backend_architecture.md docs/architecture/backend_architecture_v0.md
mv docs/roadmap/v0/tech_stack.md docs/architecture/tech_stack_v0.md
mv docs/roadmap/v1/tech_stack_and_tooling.md docs/architecture/tech_stack_v1.md
mv docs/roadmap/v1/cloud_ready_patterns.md docs/architecture/cloud_ready_patterns.md
```

#### Research Documentation (already in good location)
```bash
# These are already well-organized
# docs/concept/ → docs/research/concept/
# docs/experiments/ → docs/research/experiments/
mkdir -p docs/research
mv docs/concept docs/research/concept
mv docs/experiments docs/research/experiments
```

## Migration Script

```bash
#!/bin/bash
# Run this script from repository root: bash migrate_docs.sh

set -e

echo "Creating directory structure..."
mkdir -p docs/{api,architecture,services,database,deployment,development,operations,guides,research,integration}
mkdir -p docs/api/{endpoints,schemas}
mkdir -p docs/architecture/decisions
mkdir -p docs/guides/quickstart
mkdir -p docs/database/migrations
mkdir -p planning/{features,phases,technical_debt,tasks,roadmap}
mkdir -p planning/features/{in_progress,planned,backlog}
mkdir -p planning/phases/phase_2
mkdir -p archive/{completed_features,completed_phases,implementation_summaries,deprecated}

echo "Moving permanent documentation..."
# Deployment docs
[ -f DOCKER_README.md ] && mv DOCKER_README.md docs/deployment/docker.md
[ -f DOCKER_SETUP.md ] && mv DOCKER_SETUP.md docs/deployment/docker_setup_guide.md
[ -f docs/DOCKER_ML_SETUP.md ] && mv docs/DOCKER_ML_SETUP.md docs/deployment/docker_ml.md

# Quick starts
[ -f API_QUICK_REFERENCE.md ] && mv API_QUICK_REFERENCE.md docs/guides/api_quick_reference.md
[ -f HYBRID_SEARCH_QUICKSTART.md ] && mv HYBRID_SEARCH_QUICKSTART.md docs/guides/quickstart/hybrid_search.md
[ -f EMBEDDING_SERVICE_QUICKSTART.md ] && mv EMBEDDING_SERVICE_QUICKSTART.md docs/guides/quickstart/embedding_service.md
[ -f MIGRATION_QUICKSTART.md ] && mv MIGRATION_QUICKSTART.md docs/guides/quickstart/migration.md
[ -f DOCKER_QUICK_CHECKLIST.md ] && mv DOCKER_QUICK_CHECKLIST.md docs/guides/quickstart/docker_checklist.md
[ -f VECTOR_SEARCH_QUICK_REF.md ] && mv VECTOR_SEARCH_QUICK_REF.md docs/guides/quickstart/vector_search_reference.md

# Service docs
[ -f docs/HYBRID_SEARCH_SERVICE.md ] && mv docs/HYBRID_SEARCH_SERVICE.md docs/services/hybrid_search.md
[ -f docs/verification_pipeline.md ] && mv docs/verification_pipeline.md docs/services/verification_pipeline.md
[ -f docs/VECTOR_SEARCH_IMPLEMENTATION.md ] && mv docs/VECTOR_SEARCH_IMPLEMENTATION.md docs/services/vector_search.md

# Operations
[ -f docs/PERFORMANCE_OPTIMIZATION.md ] && mv docs/PERFORMANCE_OPTIMIZATION.md docs/operations/performance_tuning.md

# Guides
[ -f docs/DEVELOPER_GUIDE.md ] && mv docs/DEVELOPER_GUIDE.md docs/guides/developer_guide.md
[ -f docs/USER_GUIDE.md ] && mv docs/USER_GUIDE.md docs/guides/user_guide.md

echo "Moving active planning documentation..."
[ -f PHASE_2_IMPLEMENTATION_PLAN.md ] && mv PHASE_2_IMPLEMENTATION_PLAN.md planning/phases/phase_2/plan.md
[ -f PHASE_2_README.md ] && mv PHASE_2_README.md planning/phases/phase_2/README.md
[ -f PHASE_2_QUICK_REFERENCE.md ] && mv PHASE_2_QUICK_REFERENCE.md planning/phases/phase_2/quick_reference.md
[ -f TASKFILE_PHASE2_UPDATES.md ] && mv TASKFILE_PHASE2_UPDATES.md planning/tasks/taskfile_phase2_updates.md
[ -f TASKFILE_UPDATES.md ] && mv TASKFILE_UPDATES.md planning/tasks/taskfile_updates.md
[ -f TEST_FIXES_NEEDED.md ] && mv TEST_FIXES_NEEDED.md planning/technical_debt/test_fixes_needed.md
[ -f PLANNING_DOCUMENTATION_INDEX.md ] && mv PLANNING_DOCUMENTATION_INDEX.md planning/README.md
[ -d docs/roadmap ] && mv docs/roadmap planning/roadmap

echo "Moving historical documentation..."
# Completed features
[ -f FEATURE_5_VERDICT_AGGREGATION_SUMMARY.md ] && mv FEATURE_5_VERDICT_AGGREGATION_SUMMARY.md archive/completed_features/feature_5_verdict_aggregation.md
[ -f IMPLEMENTATION_SUMMARY_FEATURE6.md ] && mv IMPLEMENTATION_SUMMARY_FEATURE6.md archive/completed_features/feature_6_implementation.md
[ -f docs/FEATURE_10_IMPLEMENTATION_SUMMARY.md ] && mv docs/FEATURE_10_IMPLEMENTATION_SUMMARY.md archive/completed_features/feature_10_implementation.md
[ -f FEATURE_11_DELIVERY_REPORT.md ] && mv FEATURE_11_DELIVERY_REPORT.md archive/completed_features/feature_11_docker_delivery.md

# Completed phases
[ -f PHASE_2_COMPLETION_REPORT.md ] && mv PHASE_2_COMPLETION_REPORT.md archive/completed_phases/phase_2_completion.md
[ -f PHASE_2_EXECUTION_SUMMARY.md ] && mv PHASE_2_EXECUTION_SUMMARY.md archive/completed_phases/phase_2_execution.md

# Implementation summaries
[ -f API_INTEGRATION_SUMMARY.md ] && mv API_INTEGRATION_SUMMARY.md archive/implementation_summaries/api_integration_summary.md
[ -f DOCKER_IMPLEMENTATION_SUMMARY.md ] && mv DOCKER_IMPLEMENTATION_SUMMARY.md archive/implementation_summaries/docker_implementation_summary.md
[ -f HYBRID_SEARCH_IMPLEMENTATION_SUMMARY.md ] && mv HYBRID_SEARCH_IMPLEMENTATION_SUMMARY.md archive/implementation_summaries/hybrid_search_summary.md
[ -f EMBEDDING_SERVICE_IMPLEMENTATION_REPORT.md ] && mv EMBEDDING_SERVICE_IMPLEMENTATION_REPORT.md archive/implementation_summaries/embedding_service_summary.md
[ -f NLI_SERVICE_IMPLEMENTATION_REPORT.md ] && mv NLI_SERVICE_IMPLEMENTATION_REPORT.md archive/implementation_summaries/nli_service_summary.md
[ -f IMPLEMENTATION_SUMMARY.md ] && mv IMPLEMENTATION_SUMMARY.md archive/implementation_summaries/general_implementation_summary.md
[ -f SETUP_SUMMARY.md ] && mv SETUP_SUMMARY.md archive/implementation_summaries/setup_summary.md
[ -f SUBAGENT_IMPLEMENTATION_PLAN_SUMMARY.md ] && mv SUBAGENT_IMPLEMENTATION_PLAN_SUMMARY.md archive/implementation_summaries/subagent_implementation_summary.md
[ -f SWARM_EXECUTION_SUMMARY.md ] && mv SWARM_EXECUTION_SUMMARY.md archive/implementation_summaries/swarm_execution_summary.md
[ -f VECTOR_SEARCH_SUMMARY.md ] && mv VECTOR_SEARCH_SUMMARY.md archive/implementation_summaries/vector_search_summary.md
[ -f DOCKER_TEST_SETUP_COMPLETE.md ] && mv DOCKER_TEST_SETUP_COMPLETE.md archive/implementation_summaries/docker_test_setup.md
[ -f DOCKERFILE_FIX_ALEMBIC.md ] && mv DOCKERFILE_FIX_ALEMBIC.md archive/implementation_summaries/dockerfile_alembic_fix.md
[ -f TEST_FIXES_COMPLETE.md ] && mv TEST_FIXES_COMPLETE.md archive/implementation_summaries/test_fixes_complete.md

echo "Moving database documentation..."
[ -f docs/PHASE2_DATABASE_MIGRATION.md ] && mv docs/PHASE2_DATABASE_MIGRATION.md docs/database/migrations/phase2_migration.md

echo "Moving architecture documentation..."
[ -d docs/roadmap/v0 ] && {
  [ -f docs/roadmap/v0/database_schema.md ] && mv docs/roadmap/v0/database_schema.md docs/database/schema_v0.md
  [ -f docs/roadmap/v0/backend_architecture.md ] && mv docs/roadmap/v0/backend_architecture.md docs/architecture/backend_architecture_v0.md
  [ -f docs/roadmap/v0/tech_stack.md ] && mv docs/roadmap/v0/tech_stack.md docs/architecture/tech_stack_v0.md
}
[ -d docs/roadmap/v1 ] && {
  [ -f docs/roadmap/v1/tech_stack_and_tooling.md ] && mv docs/roadmap/v1/tech_stack_and_tooling.md docs/architecture/tech_stack_v1.md
  [ -f docs/roadmap/v1/cloud_ready_patterns.md ] && mv docs/roadmap/v1/cloud_ready_patterns.md docs/architecture/cloud_ready_patterns.md
}

echo "Moving research documentation..."
[ -d docs/concept ] && mv docs/concept docs/research/concept
[ -d docs/experiments ] && mv docs/experiments docs/research/experiments

echo "Creating README files..."
cat > docs/README.md << 'EOF'
# TruthGraph Documentation

Welcome to TruthGraph documentation.

## Quick Links
- [API Documentation](api/README.md) - REST API reference
- [Architecture](architecture/README.md) - System architecture and ADRs
- [Services](services/README.md) - Service documentation
- [Deployment](deployment/docker.md) - Docker deployment guide
- [Developer Guide](guides/developer_guide.md) - Development guide

## Documentation Structure
- `api/` - API documentation and schemas
- `architecture/` - Architecture decisions and system design
- `services/` - Service-specific documentation
- `database/` - Database schema and migrations
- `deployment/` - Deployment guides
- `development/` - Development setup and guides
- `operations/` - Operational runbooks
- `guides/` - User and developer guides
- `research/` - Experiments and concepts
- `integration/` - Integration guides

## For Active Planning
See [planning/](../planning/README.md) for current work tracking.

## For Historical Context
See [archive/](../archive/README.md) for completed features and phases.
EOF

cat > planning/README.md << 'EOF'
# Planning Documentation

Active project management and planning documentation.

## Current Work
- [Phase 2](phases/phase_2/README.md) - Current phase
- [Features In Progress](features/in_progress/) - Active features
- [Technical Debt](technical_debt/README.md) - Known issues

## Structure
- `features/` - Feature planning and tracking
  - `in_progress/` - Currently being implemented
  - `planned/` - Next up
  - `backlog/` - Future work
- `phases/` - Phase-based planning
- `technical_debt/` - Technical debt tracking
- `tasks/` - Task management
- `roadmap/` - Product roadmap

## Workflow
1. Plan features in `features/planned/`
2. Move to `features/in_progress/` when starting
3. Move to `archive/completed_features/` when done
4. Update phase progress regularly
EOF

cat > archive/README.md << 'EOF'
# Archive

Historical documentation for completed work.

## Structure
- `completed_features/` - Completed feature summaries
- `completed_phases/` - Phase completion reports
- `implementation_summaries/` - Implementation summaries
- `deprecated/` - Deprecated documentation

## Purpose
This archive preserves project history and provides context for:
- Understanding how features were implemented
- Learning from past decisions
- Tracking project evolution
- Onboarding new team members

## Archival Policy
- Move completed features within 1 week of completion
- Add completion summary and lessons learned
- Keep in archive indefinitely for historical context
EOF

echo "Documentation migration complete!"
echo ""
echo "Next steps:"
echo "1. Review the new structure: ls -R docs/ planning/ archive/"
echo "2. Update any broken links in documentation"
echo "3. Update README.md to reference new structure"
echo "4. Commit changes: git add . && git commit -m 'docs: reorganize documentation structure'"
```

## Post-Migration Tasks

1. **Update README.md**: Update root README.md to point to new locations
2. **Fix broken links**: Search for broken markdown links
3. **Update Taskfile**: Update any documentation-related tasks
4. **Team communication**: Notify team of new structure
5. **CI/CD updates**: Update any scripts that reference old paths

## Verification Checklist

- [ ] All root-level markdown files moved (except README.md, CONTRIBUTING.md, CHANGELOG.md)
- [ ] All docs have README.md indexes
- [ ] Planning structure created
- [ ] Archive structure created
- [ ] Service READMEs still in place (truthgraph/services/)
- [ ] No broken links
- [ ] Taskfile updated
- [ ] Team notified
