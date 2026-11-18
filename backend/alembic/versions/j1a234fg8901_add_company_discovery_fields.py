"""add_company_discovery_fields

Revision ID: j1a234fg8901
Revises: i1a234ef7890
Create Date: 2026-11-17 03:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = 'j1a234fg8901'
down_revision: Union[str, Sequence[str], None] = 'i1a234ef7890'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.execute("""
        ALTER TABLE companies
        ADD COLUMN IF NOT EXISTS industry VARCHAR(100),
        ADD COLUMN IF NOT EXISTS country VARCHAR(100),
        ADD COLUMN IF NOT EXISTS operating_region VARCHAR(100),
        ADD COLUMN IF NOT EXISTS ats_provider VARCHAR(50),
        ADD COLUMN IF NOT EXISTS ats_board_id VARCHAR(255),
        ADD COLUMN IF NOT EXISTS discovery_source VARCHAR(255),
        ADD COLUMN IF NOT EXISTS company_metadata JSONB DEFAULT '{}'::jsonb;

        CREATE INDEX IF NOT EXISTS ix_companies_industry ON companies(industry);
        CREATE INDEX IF NOT EXISTS ix_companies_country ON companies(country);
        CREATE INDEX IF NOT EXISTS ix_companies_ats_provider ON companies(ats_provider);
    """)

def downgrade() -> None:
    op.execute("""
        DROP INDEX IF EXISTS ix_companies_ats_provider;
        DROP INDEX IF EXISTS ix_companies_country;
        DROP INDEX IF EXISTS ix_companies_industry;

        ALTER TABLE companies
        DROP COLUMN IF EXISTS company_metadata,
        DROP COLUMN IF EXISTS discovery_source,
        DROP COLUMN IF EXISTS ats_board_id,
        DROP COLUMN IF EXISTS ats_provider,
        DROP COLUMN IF EXISTS operating_region,
        DROP COLUMN IF EXISTS country,
        DROP COLUMN IF EXISTS industry;
    """)
