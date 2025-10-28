#!/usr/bin/env python3
"""Migration runner script with safety checks and validation.

This script provides a safe way to run the Phase 2 database migration
with automatic validation and rollback on failure.

Usage:
    python scripts/run_migration.py upgrade
    python scripts/run_migration.py downgrade
    python scripts/run_migration.py status
    python scripts/run_migration.py test

Environment Variables:
    DATABASE_URL - Database connection string (optional)
"""

import asyncio
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def run_command(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run a shell command and return the result."""
    print(f"Running: {' '.join(cmd)}")
    return subprocess.run(cmd, check=check, capture_output=True, text=True)


def check_prerequisites() -> tuple[bool, list[str]]:
    """Check that all prerequisites are met."""
    errors = []

    # Check Python version
    if sys.version_info < (3, 12):
        errors.append(f"Python 3.12+ required, got {sys.version_info.major}.{sys.version_info.minor}")

    # Check Alembic is installed
    try:
        import alembic  # noqa: F401
    except ImportError:
        errors.append("Alembic not installed. Run: uv pip install alembic")

    # Check pgvector is installed
    try:
        import pgvector  # noqa: F401
    except ImportError:
        errors.append("pgvector not installed. Run: uv pip install pgvector")

    # Check asyncpg is installed
    try:
        import asyncpg  # noqa: F401
    except ImportError:
        errors.append("asyncpg not installed. Run: uv pip install asyncpg")

    # Check database connection
    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        errors.append("DATABASE_URL environment variable not set")

    return len(errors) == 0, errors


async def test_database_connection() -> bool:
    """Test that we can connect to the database."""
    try:
        from sqlalchemy import text

        from truthgraph.db_async import async_engine

        async with async_engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            result.scalar()
            print("✓ Database connection successful")
            return True
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False


def get_current_revision() -> Optional[str]:
    """Get the current migration revision."""
    try:
        result = run_command(["alembic", "current"], check=False)
        if result.returncode == 0:
            output = result.stdout.strip()
            if output:
                # Extract revision ID from output
                return output.split()[0] if output else None
        return None
    except Exception as e:
        print(f"Error getting current revision: {e}")
        return None


def backup_database() -> bool:
    """Create a database backup before migration."""
    print("\n📦 Creating database backup...")

    db_url = os.getenv("DATABASE_URL", "")
    if not db_url:
        print("⚠ DATABASE_URL not set, skipping backup")
        return False

    # Parse database URL to get connection parameters
    # Format: postgresql+asyncpg://user:pass@host:port/dbname
    try:
        from urllib.parse import urlparse
        parsed = urlparse(db_url)

        # Create backup filename
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"backup_pre_migration_{timestamp}.sql"

        # Build pg_dump command
        cmd = [
            "pg_dump",
            "-h", parsed.hostname or "localhost",
            "-p", str(parsed.port or 5432),
            "-U", parsed.username or "truthgraph",
            "-d", parsed.path.lstrip("/") if parsed.path else "truthgraph",
            "-f", backup_file,
        ]

        # Set password if available
        if parsed.password:
            env = os.environ.copy()
            env["PGPASSWORD"] = parsed.password
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        else:
            result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            print(f"✓ Backup created: {backup_file}")
            return True
        else:
            print(f"⚠ Backup failed: {result.stderr}")
            return False

    except Exception as e:
        print(f"⚠ Backup failed: {e}")
        return False


def run_migration_upgrade() -> bool:
    """Run the migration upgrade."""
    print("\n🚀 Running migration upgrade...")

    try:
        result = run_command(["alembic", "upgrade", "head"])
        if result.returncode == 0:
            print("✓ Migration upgrade successful")
            print(result.stdout)
            return True
        else:
            print("✗ Migration upgrade failed")
            print(result.stderr)
            return False
    except Exception as e:
        print(f"✗ Migration upgrade failed: {e}")
        return False


def run_migration_downgrade() -> bool:
    """Run the migration downgrade."""
    print("\n⬇ Running migration downgrade...")

    try:
        result = run_command(["alembic", "downgrade", "-1"])
        if result.returncode == 0:
            print("✓ Migration downgrade successful")
            print(result.stdout)
            return True
        else:
            print("✗ Migration downgrade failed")
            print(result.stderr)
            return False
    except Exception as e:
        print(f"✗ Migration downgrade failed: {e}")
        return False


def verify_migration() -> bool:
    """Verify the migration was successful."""
    print("\n🔍 Verifying migration...")

    try:
        # Check current revision
        current = get_current_revision()
        if current:
            print(f"✓ Current revision: {current}")
        else:
            print("⚠ Could not determine current revision")
            return False

        # Run migration tests
        print("\n🧪 Running migration tests...")
        result = run_command(["pytest", "tests/test_migrations.py", "-v"], check=False)

        if result.returncode == 0:
            print("✓ All migration tests passed")
            return True
        else:
            print("✗ Some migration tests failed")
            print(result.stdout)
            print(result.stderr)
            return False

    except Exception as e:
        print(f"✗ Verification failed: {e}")
        return False


def show_status():
    """Show migration status."""
    print("\n📊 Migration Status\n")

    # Current revision
    current = get_current_revision()
    if current:
        print(f"Current revision: {current}")
    else:
        print("No migrations applied yet")

    # Migration history
    print("\n📜 Migration History:")
    result = run_command(["alembic", "history"], check=False)
    if result.returncode == 0:
        print(result.stdout)
    else:
        print("Could not retrieve migration history")


async def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/run_migration.py {upgrade|downgrade|status|test}")
        sys.exit(1)

    command = sys.argv[1].lower()

    print("=" * 60)
    print("TruthGraph Phase 2 Migration Runner")
    print("=" * 60)

    # Check prerequisites
    print("\n🔍 Checking prerequisites...")
    prereqs_ok, errors = check_prerequisites()

    if not prereqs_ok:
        print("\n✗ Prerequisites not met:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)

    print("✓ All prerequisites met")

    # Test database connection
    if not await test_database_connection():
        print("\n✗ Cannot connect to database. Check DATABASE_URL and ensure PostgreSQL is running.")
        sys.exit(1)

    # Execute command
    if command == "status":
        show_status()

    elif command == "test":
        print("\n🧪 Running migration tests only...")
        verify_migration()

    elif command == "upgrade":
        # Confirm before proceeding
        print("\n⚠ This will upgrade the database to Phase 2 schema.")
        response = input("Create backup before proceeding? [Y/n]: ").strip().lower()

        if response != "n":
            backup_database()

        response = input("\nProceed with migration? [y/N]: ").strip().lower()
        if response != "y":
            print("Migration cancelled.")
            sys.exit(0)

        # Run upgrade
        if run_migration_upgrade():
            if verify_migration():
                print("\n✓ Migration completed successfully!")
            else:
                print("\n⚠ Migration completed but verification failed.")
                print("Review test output above for details.")
        else:
            print("\n✗ Migration failed!")
            sys.exit(1)

    elif command == "downgrade":
        print("\n⚠ This will rollback the last migration.")
        response = input("Proceed with downgrade? [y/N]: ").strip().lower()

        if response != "y":
            print("Downgrade cancelled.")
            sys.exit(0)

        if run_migration_downgrade():
            print("\n✓ Downgrade completed successfully!")
        else:
            print("\n✗ Downgrade failed!")
            sys.exit(1)

    else:
        print(f"Unknown command: {command}")
        print("Valid commands: upgrade, downgrade, status, test")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
