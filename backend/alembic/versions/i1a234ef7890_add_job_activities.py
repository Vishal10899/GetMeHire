"""add_job_activities

Revision ID: i1a234ef7890
Revises: h1a234ef6789
Create Date: 2026-11-16 22:25:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'i1a234ef7890'
down_revision: Union[str, Sequence[str], None] = 'h1a234ef6789'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS job_activities (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
            activity_type VARCHAR(50) NOT NULL,
            company_id INTEGER REFERENCES companies(id) ON DELETE SET NULL,
            company_name VARCHAR(255),
            job_title VARCHAR(255),
            source_platform VARCHAR(100),
            application_url VARCHAR(1000),
            redirect_result VARCHAR(50),
            ip_address VARCHAR(50),
            user_agent VARCHAR(500),
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        );

        CREATE INDEX IF NOT EXISTS ix_job_activities_user_id ON job_activities(user_id);
        CREATE INDEX IF NOT EXISTS ix_job_activities_job_id ON job_activities(job_id);
        CREATE INDEX IF NOT EXISTS ix_job_activities_activity_type ON job_activities(activity_type);
        CREATE INDEX IF NOT EXISTS ix_job_activities_company_id ON job_activities(company_id);
        CREATE INDEX IF NOT EXISTS ix_job_activities_created_at ON job_activities(created_at);
        CREATE INDEX IF NOT EXISTS ix_job_activities_user_type_created ON job_activities(user_id, activity_type, created_at);
        CREATE INDEX IF NOT EXISTS ix_job_activities_job_type ON job_activities(job_id, activity_type);
    """)

def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS job_activities CASCADE;")
