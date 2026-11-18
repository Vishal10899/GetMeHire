"""add_multi_profession_and_quality_fields

Revision ID: f1a234cd6789
Revises: e9a234bc5678
Create Date: 2026-10-25 04:35:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'f1a234cd6789'
down_revision: Union[str, Sequence[str], None] = 'e9a234bc5678'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. Add quality and taxonomy columns to jobs
    op.execute("""
        ALTER TABLE jobs ADD COLUMN IF NOT EXISTS normalized_title VARCHAR(255);
        CREATE INDEX IF NOT EXISTS ix_jobs_normalized_title ON jobs (normalized_title);
        ALTER TABLE jobs ADD COLUMN IF NOT EXISTS system_summary TEXT;
        ALTER TABLE jobs ADD COLUMN IF NOT EXISTS classification_confidence FLOAT DEFAULT 1.0;
        CREATE INDEX IF NOT EXISTS ix_jobs_classification_confidence ON jobs (classification_confidence);
    """)

    # 2. Add career_interests and recent_searches to profiles
    op.execute("""
        ALTER TABLE profiles ADD COLUMN IF NOT EXISTS career_interests JSONB DEFAULT '[]'::jsonb NOT NULL;
        ALTER TABLE profiles ADD COLUMN IF NOT EXISTS recent_searches JSONB DEFAULT '[]'::jsonb NOT NULL;
    """)

    # 3. Seed initial normalized_title and backfill career_interests
    op.execute("""
        UPDATE jobs SET normalized_title = title WHERE normalized_title IS NULL;

        UPDATE profiles
        SET career_interests = jsonb_build_array(
            jsonb_build_object(
                'profession', coalesce(profession, 'SOFTWARE_IT'),
                'preferred_roles', coalesce(preferred_roles, '[]'::jsonb),
                'skills', coalesce(skills, '[]'::jsonb),
                'experience_years', coalesce(relevant_experience_years, total_experience_years, 0)
            )
        )
        WHERE career_interests = '[]'::jsonb AND profession IS NOT NULL;
    """)

def downgrade() -> None:
    op.execute("""
        DROP INDEX IF EXISTS ix_jobs_classification_confidence;
        DROP INDEX IF EXISTS ix_jobs_normalized_title;
        ALTER TABLE jobs DROP COLUMN IF EXISTS classification_confidence;
        ALTER TABLE jobs DROP COLUMN IF EXISTS system_summary;
        ALTER TABLE jobs DROP COLUMN IF EXISTS normalized_title;
        ALTER TABLE profiles DROP COLUMN IF EXISTS recent_searches;
        ALTER TABLE profiles DROP COLUMN IF EXISTS career_interests;
    """)
