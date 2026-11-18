"""add_profession_to_jobs_and_profiles

Revision ID: e9a234bc5678
Revises: c8f1234a567b
Create Date: 2026-10-25 04:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'e9a234bc5678'
down_revision: Union[str, Sequence[str], None] = 'c8f1234a567b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. Add column to jobs and index
    op.execute("""
        ALTER TABLE jobs ADD COLUMN IF NOT EXISTS profession VARCHAR(100);
        CREATE INDEX IF NOT EXISTS ix_jobs_profession ON jobs (profession);
    """)

    # 2. Add column to profiles
    op.execute("""
        ALTER TABLE profiles ADD COLUMN IF NOT EXISTS profession VARCHAR(100);
    """)

    # 3. Deterministically backfill existing jobs with profession
    op.execute("""
        UPDATE jobs
        SET profession = CASE
            -- 1. Product & Design
            WHEN lower(title) ~ '(product manager|product lead|head of product|vp of product|director of product|\\yux\\y|\\yui/ux\\y|product design|designer|graphic design|creative advisor)' 
                 OR lower(coalesce(department, '')) ~ '(product management|design)' 
            THEN 'PRODUCT_DESIGN'

            -- 2. Data & AI
            WHEN lower(title) ~ '(data scientist|data analyst|data engineer|machine learning|ai research|ml engineer|deep learning|nlp|computer vision|analytics engineer)' 
                 OR lower(coalesce(department, '')) ~ '(ai research|applied ai|security analytics)' 
            THEN 'DATA_AI'

            -- 3. Sales & Business Development
            WHEN lower(title) ~ '(account executive|sales|business development|\\ybdr\\y|\\ysdr\\y|partnerships|solutions engineer|sales engineer|account manager)' 
                 OR lower(coalesce(department, '')) ~ '(sales|business development)' 
            THEN 'SALES_BIZDEV'

            -- 4. Marketing & Growth
            WHEN lower(title) ~ '(marketing|growth lead|content writer|seo|brand|communications|demand gen|copywriter)' 
                 OR lower(coalesce(department, '')) ~ 'marketing' 
            THEN 'MARKETING_GROWTH'

            -- 5. Finance & Legal
            WHEN lower(title) ~ '(finance|accountant|accounting|counsel|legal|controller|treasury|tax|compliance|contracts manager)' 
                 OR lower(coalesce(department, '')) ~ '(finance|legal|tax)' 
            THEN 'FINANCE_LEGAL'

            -- 6. People & Operations
            WHEN lower(title) ~ '(people|\\yrecruiter\\y|recruiting|talent|human resources|\\yhr\\y|operations manager|workplace|coordinator|investigator|community manager)' 
                 OR lower(coalesce(department, '')) ~ '(people|human resources|operations|talent|safeguards)' 
            THEN 'OPERATIONS_PEOPLE'

            -- 7. Engineering (Default tech/dev roles)
            WHEN lower(title) ~ '(engineer|developer|software|infrastructure|backend|frontend|full stack|devops|sre|security|architect|\\yqa\\y|systems)' 
                 OR lower(coalesce(department, '')) ~ '(engineering|dev|compute|security)' 
            THEN 'ENGINEERING'

            ELSE 'OPERATIONS_PEOPLE'
        END
        WHERE profession IS NULL;
    """)

def downgrade() -> None:
    op.execute("""
        DROP INDEX IF EXISTS ix_jobs_profession;
        ALTER TABLE jobs DROP COLUMN IF EXISTS profession;
        ALTER TABLE profiles DROP COLUMN IF EXISTS profession;
    """)
