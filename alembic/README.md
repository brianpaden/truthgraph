# Alembic Database Migrations

This directory contains Alembic database migrations for TruthGraph v0.

## Structure

```text
alembic/
├── versions/                          # Migration files
│   └── 20251025_0000_phase2_ml_tables.py  # Phase 2 ML tables migration
├── env.py                             # Alembic environment configuration
├── script.py.mako                     # Template for new migrations
└── README.md                          # This file
```

## Creating New Migrations

### Auto-generate from model changes

```bash
# After modifying truthgraph/schemas.py
alembic revision --autogenerate -m "Description of changes"
```

### Create empty migration

```bash
alembic revision -m "Description of changes"
```

## Running Migrations

### Upgrade to latest

```bash
alembic upgrade head
```

### Upgrade to specific revision

```bash
alembic upgrade <revision_id>
```

### Downgrade one revision

```bash
alembic downgrade -1
```

### Downgrade to specific revision

```bash
alembic downgrade <revision_id>
```

## Migration History

```bash
# View migration history
alembic history

# Show current revision
alembic current

# Show pending migrations
alembic current --verbose
```

## Environment Variables

The migration system uses the following environment variables:

- `DATABASE_URL` - Database connection string (default: postgresql+asyncpg://truthgraph:changeme@localhost:5432/truthgraph)

Set in `.env` file or export before running migrations:

```bash
export DATABASE_URL="postgresql+asyncpg://user:pass@host:port/dbname"
```

## Migration Best Practices

1. **Always test migrations** on a development database first
2. **Backup production database** before running migrations
3. **Review auto-generated migrations** - they may need manual adjustment
4. **Test both upgrade and downgrade** paths
5. **Document complex migrations** with comments
6. **Use transactions** for data migrations when possible

## Existing Migrations

### phase2_ml_tables (2025-10-25)

Adds ML-enhanced verification tables:
- `embeddings` - Vector embeddings with pgvector support
- `nli_results` - NLI verification pairs
- `verification_results` - Aggregated verdicts

**Features**:
- IVFFlat index for vector similarity search
- Foreign key constraints with CASCADE delete
- Comprehensive indexing for query performance
- Tenant isolation support

See `docs/PHASE2_DATABASE_MIGRATION.md` for full documentation.

## Troubleshooting

### "Target database is not up to date"

```bash
alembic stamp head
```

### "Multiple heads detected"

```bash
alembic merge heads -m "Merge migrations"
```

### "Can't locate revision identified by 'xxxxx'"

Check that all migration files are in `alembic/versions/` and the revision IDs match.

## Resources

- Alembic Documentation: <https://alembic.sqlalchemy.org/>
- SQLAlchemy 2.0 Docs: <https://docs.sqlalchemy.org/en/20/>
- pgvector Documentation: <https://github.com/pgvector/pgvector>
