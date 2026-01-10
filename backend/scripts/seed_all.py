"""
Master Database Seeding Script for GrantRadar
Runs all seed scripts in the correct order with error handling.

This script is idempotent - it can be run multiple times safely.
Existing data will be skipped (not duplicated).

Usage:
    python -m backend.scripts.seed_all [options]

Options:
    --force         Force re-seed even if data exists (where supported)
    --skip-check    Skip database connection check
    --dry-run       Print what would be seeded without making changes
    --verbose       Enable verbose output
"""

import argparse
import asyncio
import logging
import sys
from datetime import datetime, timezone
from typing import List, Tuple, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class SeedResult:
    """Result of a seeding operation."""

    def __init__(self, name: str, success: bool, message: str, count: Optional[int] = None):
        self.name = name
        self.success = success
        self.message = message
        self.count = count
        self.timestamp = datetime.now(timezone.utc)


async def check_database_connection() -> bool:
    """Check if the database is accessible."""
    try:
        from backend.database import check_db_connection

        result = await check_db_connection()
        if result.get("status") == "healthy":
            logger.info("Database connection: OK")
            return True
        else:
            logger.error(f"Database connection failed: {result.get('error', 'Unknown error')}")
            return False
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False


async def check_migrations() -> Tuple[bool, str]:
    """Check if migrations are up to date."""
    try:
        from backend.database import get_async_session
        from sqlalchemy import text

        async with get_async_session() as session:
            # Check if alembic_version table exists
            result = await session.execute(
                text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_name = 'alembic_version'
                    )
                """)
            )
            table_exists = result.scalar()

            if not table_exists:
                return False, "Alembic version table not found. Run 'alembic upgrade head' first."

            # Get current version
            result = await session.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
            version = result.scalar()

            if version:
                return True, f"Current migration version: {version}"
            else:
                return False, "No migration version found. Run 'alembic upgrade head' first."

    except Exception as e:
        return False, f"Migration check failed: {e}"


async def seed_mechanisms(dry_run: bool = False) -> SeedResult:
    """Seed grant mechanisms data."""
    name = "Grant Mechanisms"
    try:
        if dry_run:
            return SeedResult(name, True, "Would seed grant mechanisms (NIH R01, R21, NSF CAREER, etc.)")

        from backend.scripts.seed_mechanisms import seed_mechanisms as do_seed

        await do_seed()
        return SeedResult(name, True, "Seeded grant mechanisms successfully")
    except Exception as e:
        return SeedResult(name, False, f"Error: {e}")


async def seed_budget_templates(dry_run: bool = False, clear: bool = False) -> SeedResult:
    """Seed budget template data."""
    name = "Budget Templates"
    try:
        if dry_run:
            return SeedResult(name, True, "Would seed budget templates for various mechanisms")

        from backend.scripts.seed_budget_templates import seed_budget_templates as do_seed, clear_budget_templates

        if clear:
            await clear_budget_templates()

        await do_seed()
        return SeedResult(name, True, "Seeded budget templates successfully")
    except Exception as e:
        return SeedResult(name, False, f"Error: {e}")


async def seed_compliance_requirements(dry_run: bool = False) -> SeedResult:
    """Seed compliance requirements and templates."""
    name = "Compliance Requirements"
    try:
        if dry_run:
            return SeedResult(name, True, "Would seed compliance requirements for NIH, NSF, foundations")

        from backend.scripts.seed_compliance_requirements import seed_compliance_requirements as do_seed

        await do_seed()
        return SeedResult(name, True, "Seeded compliance requirements successfully")
    except Exception as e:
        return SeedResult(name, False, f"Error: {e}")


async def seed_templates(dry_run: bool = False) -> SeedResult:
    """Seed template categories and system templates."""
    name = "Document Templates"
    try:
        if dry_run:
            return SeedResult(name, True, "Would seed document templates (Specific Aims, Abstract, etc.)")

        from backend.services.seed_templates import seed_templates as do_seed

        await do_seed()
        return SeedResult(name, True, "Seeded document templates successfully")
    except Exception as e:
        return SeedResult(name, False, f"Error: {e}")


async def seed_checklists(dry_run: bool = False, reset: bool = False) -> SeedResult:
    """Seed checklist templates."""
    name = "Checklist Templates"
    try:
        if dry_run:
            return SeedResult(name, True, "Would seed checklist templates for NIH R01, R21, NSF grants")

        from backend.services.seed_checklists import (
            seed_checklist_templates as do_seed,
            reset_and_seed_checklist_templates,
        )

        if reset:
            await reset_and_seed_checklist_templates()
        else:
            await do_seed()

        return SeedResult(name, True, "Seeded checklist templates successfully")
    except Exception as e:
        return SeedResult(name, False, f"Error: {e}")


async def seed_compliance_rules(dry_run: bool = False, force: bool = False) -> SeedResult:
    """Seed compliance rules."""
    name = "Compliance Rules"
    try:
        if dry_run:
            return SeedResult(name, True, "Would seed compliance rules for NIH and NSF formatting requirements")

        from backend.services.seed_compliance_rules import seed_compliance_rules as do_seed
        from backend.database import get_async_session

        async with get_async_session() as session:
            result = await do_seed(session, force=force)

        return SeedResult(
            name,
            True,
            f"Created: {result.get('created', 0)}, Skipped: {result.get('skipped', 0)}, Updated: {result.get('updated', 0)}",
        )
    except Exception as e:
        return SeedResult(name, False, f"Error: {e}")


async def seed_demo_data(dry_run: bool = False, clean: bool = False) -> SeedResult:
    """Seed demo/development data (users, grants, applications, teams)."""
    name = "Demo Data"
    try:
        if dry_run:
            return SeedResult(name, True, "Would seed demo users, grants, applications, and teams")

        from backend.scripts.seed_data import run_seed

        await run_seed(clean=clean, dry_run=dry_run, verbose=False)
        return SeedResult(name, True, "Seeded demo data successfully (3 users, 20+ grants, applications, team)")
    except Exception as e:
        return SeedResult(name, False, f"Error: {e}")


async def get_table_counts() -> dict:
    """Get counts of seeded data from various tables."""
    try:
        from backend.database import get_async_session
        from sqlalchemy import text

        counts = {}
        tables = [
            ("grant_mechanisms", "Grant Mechanisms"),
            ("budget_templates", "Budget Templates"),
            ("funder_requirements", "Funder Requirements"),
            ("compliance_templates", "Compliance Templates"),
            ("template_categories", "Template Categories"),
            ("templates", "Document Templates"),
            ("checklist_templates", "Checklist Templates"),
            ("compliance_rules", "Compliance Rules"),
            ("users", "Users"),
            ("grants", "Grants"),
            ("grant_applications", "Applications"),
            ("lab_members", "Team Members"),
            ("notifications", "Notifications"),
        ]

        async with get_async_session() as session:
            for table_name, display_name in tables:
                try:
                    result = await session.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                    count = result.scalar()
                    counts[display_name] = count
                except Exception:
                    counts[display_name] = "Table not found"

        return counts
    except Exception as e:
        logger.error(f"Error getting table counts: {e}")
        return {}


async def run_all_seeds(
    force: bool = False,
    skip_check: bool = False,
    dry_run: bool = False,
    verbose: bool = False,
    include_demo: bool = False,
) -> List[SeedResult]:
    """Run all seed operations in order."""

    results: List[SeedResult] = []

    print("\n" + "=" * 60)
    print("GrantRadar Database Seeding")
    print("=" * 60)

    if dry_run:
        print("\n[DRY RUN MODE - No changes will be made]\n")

    # Step 1: Check database connection
    if not skip_check:
        print("\n[Step 1/3] Checking database connection...")
        if not await check_database_connection():
            print("\nDatabase connection failed. Please ensure:")
            print("  1. PostgreSQL is running")
            print("  2. DATABASE_URL in .env is correct")
            print("  3. The database exists")
            print("\nTo start PostgreSQL on macOS: brew services start postgresql")
            print("To create the database: createdb grantradar")
            return results
    else:
        print("\n[Skipping database connection check]")

    # Step 2: Check migrations
    if not skip_check:
        print("\n[Step 2/3] Checking migration status...")
        migrations_ok, migration_msg = await check_migrations()
        print(f"  {migration_msg}")
        if not migrations_ok:
            print("\nMigrations not applied. Run: alembic upgrade head")
            return results
    else:
        print("\n[Skipping migration check]")

    # Step 3: Run seeds
    print("\n[Step 3/3] Running seed scripts...")
    print("-" * 60)

    # Define seed operations in order (respecting dependencies)
    seed_operations = [
        ("Grant Mechanisms", lambda: seed_mechanisms(dry_run)),
        ("Budget Templates", lambda: seed_budget_templates(dry_run, clear=force)),
        ("Compliance Requirements", lambda: seed_compliance_requirements(dry_run)),
        ("Document Templates", lambda: seed_templates(dry_run)),
        ("Checklist Templates", lambda: seed_checklists(dry_run, reset=force)),
        ("Compliance Rules", lambda: seed_compliance_rules(dry_run, force)),
    ]

    # Optionally include demo data
    if include_demo:
        seed_operations.append(("Demo Data", lambda: seed_demo_data(dry_run, clean=force)))

    for name, seed_func in seed_operations:
        print(f"\n  Seeding {name}...")
        try:
            result = await seed_func()
            results.append(result)

            status = "OK" if result.success else "FAILED"
            print(f"    [{status}] {result.message}")

            if not result.success and verbose:
                logger.error(f"Failed to seed {name}: {result.message}")

        except Exception as e:
            result = SeedResult(name, False, f"Unexpected error: {e}")
            results.append(result)
            print(f"    [FAILED] {result.message}")

    # Print summary
    print("\n" + "=" * 60)
    print("SEEDING SUMMARY")
    print("=" * 60)

    successful = sum(1 for r in results if r.success)
    failed = sum(1 for r in results if not r.success)

    print(f"\nTotal operations: {len(results)}")
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")

    if not dry_run and successful > 0:
        print("\nData counts after seeding:")
        counts = await get_table_counts()
        for table_name, count in counts.items():
            print(f"  {table_name}: {count}")

    print("\n" + "=" * 60)

    if failed > 0:
        print("\nSome seeding operations failed. Check the errors above.")
        print("You can re-run this script - it is idempotent.")
    else:
        print("\nSeeding completed successfully!")

    print()
    return results


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Seed the GrantRadar database with initial data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m backend.scripts.seed_all              # Normal seeding
  python -m backend.scripts.seed_all --dry-run    # Preview what would be seeded
  python -m backend.scripts.seed_all --force      # Force re-seed (updates existing)
  python -m backend.scripts.seed_all --skip-check # Skip DB/migration checks
  python -m backend.scripts.seed_all --demo       # Include demo data (users, grants, apps)
        """,
    )
    parser.add_argument(
        "--force", "-f", action="store_true", help="Force re-seed even if data exists (where supported)"
    )
    parser.add_argument("--skip-check", "-s", action="store_true", help="Skip database connection and migration checks")
    parser.add_argument(
        "--dry-run", "-n", action="store_true", help="Print what would be seeded without making changes"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    parser.add_argument(
        "--demo", "-d", action="store_true", help="Include demo data (users, grants, applications, teams)"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        results = asyncio.run(
            run_all_seeds(
                force=args.force,
                skip_check=args.skip_check,
                dry_run=args.dry_run,
                verbose=args.verbose,
                include_demo=args.demo,
            )
        )

        # Exit with error code if any seed failed
        failed = sum(1 for r in results if not r.success)
        sys.exit(1 if failed > 0 else 0)

    except KeyboardInterrupt:
        print("\n\nSeeding interrupted by user.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Seeding failed with unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
