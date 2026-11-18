"""add_country_code_to_jobs

Revision ID: g1a234de5678
Revises: f1a234cd6789
Create Date: 2026-11-16 18:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'g1a234de5678'
down_revision: Union[str, Sequence[str], None] = 'f1a234cd6789'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.execute("""
        ALTER TABLE jobs ADD COLUMN IF NOT EXISTS country_code VARCHAR(10);
        CREATE INDEX IF NOT EXISTS ix_jobs_country_code ON jobs (country_code);
    """)

def downgrade() -> None:
    op.execute("""
        DROP INDEX IF EXISTS ix_jobs_country_code;
        ALTER TABLE jobs DROP COLUMN IF EXISTS country_code;
    """)
