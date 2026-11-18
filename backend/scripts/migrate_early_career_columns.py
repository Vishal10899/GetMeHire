import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import engine
from app.core.config import settings
from sqlalchemy import text, create_engine

def main():
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS early_career_category VARCHAR(50);"))
        conn.execute(text("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS early_career_metadata JSONB DEFAULT '{}'::jsonb;"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_jobs_early_career_category ON jobs (early_career_category);"))
    print("[OK] Master DB updated successfully.")

    test_db_url = f"postgresql+psycopg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/job_discovery_test"
    test_engine = create_engine(test_db_url)
    with test_engine.begin() as conn:
        conn.execute(text("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS early_career_category VARCHAR(50);"))
        conn.execute(text("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS early_career_metadata JSONB DEFAULT '{}'::jsonb;"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_jobs_early_career_category ON jobs (early_career_category);"))
    print("[OK] Test DB updated successfully.")

if __name__ == "__main__":
    main()
