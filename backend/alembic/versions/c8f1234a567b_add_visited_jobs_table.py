"""add_visited_jobs_table

Revision ID: c8f1234a567b
Revises: b7e8d19a224f
Create Date: 2026-10-24 04:12:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c8f1234a567b'
down_revision: Union[str, Sequence[str], None] = 'b7e8d19a224f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS visited_jobs (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
            visited_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            last_visited_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            visit_count INTEGER NOT NULL DEFAULT 1,
            CONSTRAINT uq_user_job_visited UNIQUE (user_id, job_id)
        );
        CREATE INDEX IF NOT EXISTS ix_visited_jobs_id ON visited_jobs (id);
        CREATE INDEX IF NOT EXISTS ix_visited_jobs_user_id ON visited_jobs (user_id);
        CREATE INDEX IF NOT EXISTS ix_visited_jobs_job_id ON visited_jobs (job_id);
        CREATE INDEX IF NOT EXISTS ix_visited_jobs_user_visited ON visited_jobs (user_id, last_visited_at);
    """)

def downgrade() -> None:
    op.execute("""
        DROP TABLE IF EXISTS visited_jobs CASCADE;
    """)
