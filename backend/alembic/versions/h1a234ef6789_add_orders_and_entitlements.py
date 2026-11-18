"""add_orders_and_entitlements

Revision ID: h1a234ef6789
Revises: g1a234de5678
Create Date: 2026-11-16 20:25:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = 'h1a234ef6789'
down_revision: Union[str, Sequence[str], None] = 'g1a234de5678'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            target_job_id INTEGER REFERENCES jobs(id) ON DELETE SET NULL,
            resume_version_id INTEGER REFERENCES resume_versions(id) ON DELETE SET NULL,
            amount NUMERIC(10, 2) NOT NULL DEFAULT 9.99,
            currency VARCHAR(10) NOT NULL DEFAULT 'USD',
            status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
            provider VARCHAR(50) NOT NULL DEFAULT 'TEST_GATEWAY',
            transaction_id VARCHAR(255) UNIQUE,
            idempotency_key VARCHAR(255),
            payment_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        );

        CREATE INDEX IF NOT EXISTS ix_orders_user_id ON orders(user_id);
        CREATE INDEX IF NOT EXISTS ix_orders_target_job_id ON orders(target_job_id);
        CREATE INDEX IF NOT EXISTS ix_orders_resume_version_id ON orders(resume_version_id);
        CREATE INDEX IF NOT EXISTS ix_orders_status ON orders(status);
        CREATE INDEX IF NOT EXISTS ix_orders_transaction_id ON orders(transaction_id);
        CREATE INDEX IF NOT EXISTS ix_orders_idempotency_key ON orders(idempotency_key);

        CREATE TABLE IF NOT EXISTS entitlements (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            order_id INTEGER REFERENCES orders(id) ON DELETE SET NULL,
            target_job_id INTEGER REFERENCES jobs(id) ON DELETE CASCADE,
            resume_version_id INTEGER REFERENCES resume_versions(id) ON DELETE SET NULL,
            entitlement_type VARCHAR(50) NOT NULL DEFAULT 'JOB_SPECIFIC_RESUME',
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            granted_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            expires_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_user_job_entitlement UNIQUE (user_id, target_job_id)
        );

        CREATE INDEX IF NOT EXISTS ix_entitlements_user_id ON entitlements(user_id);
        CREATE INDEX IF NOT EXISTS ix_entitlements_order_id ON entitlements(order_id);
        CREATE INDEX IF NOT EXISTS ix_entitlements_target_job_id ON entitlements(target_job_id);
        CREATE INDEX IF NOT EXISTS ix_entitlements_is_active ON entitlements(is_active);
    """)

def downgrade() -> None:
    op.execute("""
        DROP TABLE IF EXISTS entitlements CASCADE;
        DROP TABLE IF EXISTS orders CASCADE;
    """)
