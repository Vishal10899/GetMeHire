"""add_early_career_category_and_metadata

Revision ID: l3c456hi0123
Revises: k2b345gh9012
Create Date: 2026-11-18 03:40:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = 'l3c456hi0123'
down_revision: Union[str, Sequence[str], None] = 'k2b345gh9012'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.execute("""
        ALTER TABLE jobs
        ADD COLUMN IF NOT EXISTS early_career_category VARCHAR(50),
        ADD COLUMN IF NOT EXISTS early_career_metadata JSONB DEFAULT '{}'::jsonb;

        CREATE INDEX IF NOT EXISTS ix_jobs_early_career_category ON jobs (early_career_category);
    """)

def downgrade() -> None:
    op.execute("""
        DROP INDEX IF EXISTS ix_jobs_early_career_category;

        ALTER TABLE jobs
        DROP COLUMN IF EXISTS early_career_metadata,
        DROP COLUMN IF EXISTS early_career_category;
    """)
