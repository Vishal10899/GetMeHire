"""add_company_discovery_v2_tiers

Revision ID: k2b345gh9012
Revises: j1a234fg8901
Create Date: 2026-11-17 04:10:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = 'k2b345gh9012'
down_revision: Union[str, Sequence[str], None] = 'j1a234fg8901'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.execute("""
        ALTER TABLE companies
        ADD COLUMN IF NOT EXISTS domain VARCHAR(255),
        ADD COLUMN IF NOT EXISTS verification_status VARCHAR(50) DEFAULT 'DISCOVERED',
        ADD COLUMN IF NOT EXISTS last_verified_at TIMESTAMP WITH TIME ZONE,
        ADD COLUMN IF NOT EXISTS verification_notes TEXT,
        ADD COLUMN IF NOT EXISTS aliases JSONB DEFAULT '[]'::jsonb;

        CREATE INDEX IF NOT EXISTS ix_companies_domain ON companies(domain);
        CREATE INDEX IF NOT EXISTS ix_companies_verification_status ON companies(verification_status);
        CREATE INDEX IF NOT EXISTS ix_companies_last_verified_at ON companies(last_verified_at);

        -- Initialize verification_status for existing companies that already have active jobs
        UPDATE companies
        SET verification_status = 'ACTIVE_JOB_SOURCE',
            last_verified_at = NOW()
        WHERE id IN (
            SELECT DISTINCT company_id FROM jobs WHERE status = 'ACTIVE'
        );

        -- For existing companies without active jobs but with verified identity
        UPDATE companies
        SET verification_status = 'SOURCE_VERIFIED',
            last_verified_at = NOW()
        WHERE verification_status IS NULL OR verification_status = 'DISCOVERED';
    """)

def downgrade() -> None:
    op.execute("""
        DROP INDEX IF EXISTS ix_companies_last_verified_at;
        DROP INDEX IF EXISTS ix_companies_verification_status;
        DROP INDEX IF EXISTS ix_companies_domain;

        ALTER TABLE companies
        DROP COLUMN IF EXISTS aliases,
        DROP COLUMN IF EXISTS verification_notes,
        DROP COLUMN IF EXISTS last_verified_at,
        DROP COLUMN IF EXISTS verification_status,
        DROP COLUMN IF EXISTS domain;
    """)
