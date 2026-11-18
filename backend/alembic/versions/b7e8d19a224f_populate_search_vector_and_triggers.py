"""populate_search_vector_and_triggers

Revision ID: b7e8d19a224f
Revises: 64432899c5fe
Create Date: 2026-10-24 01:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b7e8d19a224f'
down_revision: Union[str, Sequence[str], None] = '64432899c5fe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. Backfill existing jobs with search_vector
    op.execute("""
        UPDATE jobs j
        SET search_vector = to_tsvector('english', j.title || ' ' || coalesce(c.canonical_name, '') || ' ' || coalesce(j.department, '') || ' ' || substr(j.description, 1, 2000))
        FROM companies c
        WHERE j.company_id = c.id;
    """)

    # 2. Create trigger function to maintain search_vector automatically on INSERT or UPDATE
    op.execute("""
        CREATE OR REPLACE FUNCTION jobs_search_vector_update() RETURNS trigger AS $$
        DECLARE
            company_txt text := '';
        BEGIN
            SELECT coalesce(canonical_name, '') INTO company_txt FROM companies WHERE id = NEW.company_id;
            NEW.search_vector := to_tsvector('english', NEW.title || ' ' || company_txt || ' ' || coalesce(NEW.department, '') || ' ' || substr(NEW.description, 1, 2000));
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        DROP TRIGGER IF EXISTS trg_jobs_search_vector_update ON jobs;
        CREATE TRIGGER trg_jobs_search_vector_update
        BEFORE INSERT OR UPDATE OF title, description, department, company_id
        ON jobs
        FOR EACH ROW
        EXECUTE FUNCTION jobs_search_vector_update();
    """)

def downgrade() -> None:
    op.execute("""
        DROP TRIGGER IF EXISTS trg_jobs_search_vector_update ON jobs;
        DROP FUNCTION IF EXISTS jobs_search_vector_update();
    """)
