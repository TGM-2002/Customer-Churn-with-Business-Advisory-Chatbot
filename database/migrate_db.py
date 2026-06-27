#database/migrate_db.py
"""
Generic Postgres -> Postgres migration: creates the schema (via Base.metadata)
and copies all rows from one DB to another, in either direction.

Setup (.env):
    SOURCE_DATABASE_URL=<the DB you're copying FROM>
    TARGET_DATABASE_URL=<the DB you're copying TO, must be empty>

    For this run:
        SOURCE_DATABASE_URL=postgresql://neondb_owner:npg_PiCEDS8KdN4L@ep-long-math-atfs1yn1.c-9.us-east-1.aws.neon.tech/neondb?sslmode=require
        TARGET_DATABASE_URL=postgresql+psycopg2://trinity:trinity@localhost:5432/customer_churn

Usage:
    python -m database.migrate_db
    python -m database.migrate_db --source "<url>" --target "<url>"
    python -m database.migrate_db --force   # skip the "target not empty" guard
"""

import os
import sys
import argparse
import logging

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect as sa_inspect
from sqlalchemy.orm import sessionmaker

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

from database.schemas import (
    Base, Customer, ProductHolding, SupportInteraction,
    BehavioralSignal, ChurnScore,
)

# Parents before children — FK order matters for insert.
MODELS_IN_ORDER = [
    Customer,
    ProductHolding,
    SupportInteraction,
    BehavioralSignal,
    ChurnScore,
]

BATCH_SIZE = 1000


def row_to_dict(obj) -> dict:
    """Plain dict of column -> value for one ORM instance (no relationships)."""
    return {c.key: getattr(obj, c.key) for c in sa_inspect(obj).mapper.column_attrs}


def chunked(seq, size):
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


def migrate(source_url: str, target_url: str, force: bool = False):
    if not source_url:
        log.error("No source URL given (set SOURCE_DATABASE_URL or pass --source).")
        sys.exit(1)
    if not target_url:
        log.error("No target URL given (set TARGET_DATABASE_URL or pass --target).")
        sys.exit(1)

    source_engine = create_engine(source_url, pool_pre_ping=True)
    target_engine = create_engine(target_url, pool_pre_ping=True)

    SourceSession = sessionmaker(bind=source_engine)
    TargetSession = sessionmaker(bind=target_engine)

    log.info("Creating schema on target database...")
    Base.metadata.create_all(bind=target_engine)
    log.info("Schema created.")

    src = SourceSession()
    tgt = TargetSession()

    try:
        existing = tgt.query(Customer).first()
        if existing and not force:
            log.error(
                "Target DB already has customer rows. Re-running would create "
                "duplicates. Pass --force to override."
            )
            sys.exit(1)

        for model in MODELS_IN_ORDER:
            log.info(f"Migrating table: {model.__tablename__} ...")
            rows = src.query(model).all()
            log.info(f"  found {len(rows)} rows in source")

            if not rows:
                continue

            mappings = [row_to_dict(r) for r in rows]
            inserted = 0
            for batch in chunked(mappings, BATCH_SIZE):
                tgt.bulk_insert_mappings(model, batch)
                tgt.commit()
                inserted += len(batch)
            log.info(f"  inserted {inserted} rows into target")

        log.info("Migration complete. Verifying row counts...")
        for model in MODELS_IN_ORDER:
            src_count = src.query(model).count()
            tgt_count = tgt.query(model).count()
            status = "OK" if src_count == tgt_count else "MISMATCH"
            log.info(f"  {model.__tablename__:<22} source={src_count:<6} target={tgt_count:<6} [{status}]")

    except Exception as e:
        tgt.rollback()
        log.error(f"Migration failed: {e}")
        raise
    finally:
        src.close()
        tgt.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate one Postgres DB to another.")
    parser.add_argument("--source", default=os.getenv("SOURCE_DATABASE_URL"), help="Source DB URL")
    parser.add_argument("--target", default=os.getenv("TARGET_DATABASE_URL"), help="Target DB URL (must be empty)")
    parser.add_argument("--force", action="store_true", help="Proceed even if target already has rows.")
    args = parser.parse_args()

    migrate(source_url=args.source, target_url=args.target, force=args.force)