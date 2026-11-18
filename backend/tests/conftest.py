import os
import sys
import datetime
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.core.database import Base
import app.core.database as core_db
import app.api.deps as api_deps
import app.main as main_mod
from app.models import User, Profile, Company, Source, Job, IngestionRun
from app.core.security import get_password_hash
from fastapi.testclient import TestClient
from app.main import app
from app.api.deps import get_db

TEST_DB_NAME = os.getenv("POSTGRES_TEST_DB", "job_discovery_test")
TEST_DATABASE_URL = f"postgresql+psycopg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/{TEST_DB_NAME}"

test_engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

def seed_test_database():
    Base.metadata.create_all(bind=test_engine)
    with test_engine.connect() as conn:
        conn.execute(text("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS country_code VARCHAR(10);"))
        conn.execute(text("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS work_arrangement VARCHAR(50) DEFAULT 'ONSITE';"))
        conn.execute(text("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS remote_eligibility VARCHAR(50) DEFAULT 'UNSPECIFIED';"))
        conn.execute(text("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS early_career_category VARCHAR(50);"))
        conn.execute(text("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS early_career_metadata JSONB DEFAULT '{}'::jsonb;"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_jobs_country_code ON jobs (country_code);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_jobs_work_arrangement ON jobs (work_arrangement);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_jobs_remote_eligibility ON jobs (remote_eligibility);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_jobs_early_career_category ON jobs (early_career_category);"))
        conn.execute(text("""
            ALTER TABLE companies ADD COLUMN IF NOT EXISTS industry VARCHAR(100);
            ALTER TABLE companies ADD COLUMN IF NOT EXISTS country VARCHAR(100);
            ALTER TABLE companies ADD COLUMN IF NOT EXISTS operating_region VARCHAR(100);
            ALTER TABLE companies ADD COLUMN IF NOT EXISTS ats_provider VARCHAR(50);
            ALTER TABLE companies ADD COLUMN IF NOT EXISTS ats_board_id VARCHAR(255);
            ALTER TABLE companies ADD COLUMN IF NOT EXISTS discovery_source VARCHAR(255);
            ALTER TABLE companies ADD COLUMN IF NOT EXISTS company_metadata JSONB DEFAULT '{}'::jsonb;
            ALTER TABLE companies ADD COLUMN IF NOT EXISTS domain VARCHAR(255);
            ALTER TABLE companies ADD COLUMN IF NOT EXISTS verification_status VARCHAR(50) DEFAULT 'DISCOVERED';
            ALTER TABLE companies ADD COLUMN IF NOT EXISTS last_verified_at TIMESTAMP WITH TIME ZONE;
            ALTER TABLE companies ADD COLUMN IF NOT EXISTS verification_notes TEXT;
            ALTER TABLE companies ADD COLUMN IF NOT EXISTS aliases JSONB DEFAULT '[]'::jsonb;
        """))
        conn.execute(text("""
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
        """))
        conn.commit()

    with TestSessionLocal() as db:
        admin = db.query(User).filter(User.email == "admin@jobplatform.com").first()
        if not admin:
            admin = User(
                email="admin@jobplatform.com",
                hashed_password=get_password_hash("Admin@123456"),
                role="ADMIN",
                account_status="ACTIVE",
                is_verified=True
            )
            db.add(admin)

        candidate = db.query(User).filter(User.email == "candidate@example.com").first()
        if not candidate:
            candidate = User(
                email="candidate@example.com",
                hashed_password=get_password_hash("Candidate@123456"),
                role="USER",
                account_status="ACTIVE",
                is_verified=True
            )
            db.add(candidate)
            db.flush()

            profile = Profile(
                user_id=candidate.id,
                full_name="Alex Mercer",
                headline="Senior Full Stack & Python Engineer",
                skills=["Python", "FastAPI", "React"],
                preferred_roles=["Senior Software Engineer"],
                total_experience_years=5.0,
                profile_completion_pct=85
            )
            db.add(profile)

        comp = db.query(Company).filter(Company.canonical_name == "Stripe").first()
        if not comp:
            comp = Company(
                canonical_name="Stripe",
                website="https://stripe.com",
                career_page_url="https://stripe.com/jobs",
                identity_status="VERIFIED",
                industry="Software & IT",
                country="United States",
                ats_provider="GREENHOUSE",
                ats_board_id="stripe"
            )
            db.add(comp)
            db.flush()
        else:
            if not comp.industry:
                comp.industry = "Software & IT"
                comp.country = "United States"
                comp.ats_provider = "GREENHOUSE"
                comp.ats_board_id = "stripe"
                db.flush()

        src = db.query(Source).filter(Source.company_id == comp.id).first()
        if not src:
            src = Source(
                company_id=comp.id,
                source_name="Stripe Greenhouse ATS",
                source_type="GREENHOUSE",
                canonical_source_url="https://boards.greenhouse.io/stripe",
                external_board_id="stripe",
                access_classification="PUBLIC_API",
                sync_schedule_cron="0 */4 * * *",
                configuration={"board_token": "stripe"},
                health_status="HEALTHY",
                is_active=True
            )
            db.add(src)
            db.flush()

        # Seed 7 baseline demo jobs so ID sequence aligns with production (IDs 1-7 reserved for demo seeds)
        job_count = db.query(Job).count()
        if job_count < 7:
            now = datetime.datetime.now(datetime.timezone.utc)
            for i in range(job_count + 1, 8):
                job = Job(
                    company_id=comp.id,
                    source_id=src.id,
                    external_job_id=f"test-seed-{i:03d}",
                    title=f"Sample Seed Job {i} - Infrastructure",
                    normalized_title=f"Sample Seed Job {i}",
                    description="Standard test seed description.",
                    profession="ENGINEERING",
                    location="San Francisco, CA",
                    city="San Francisco",
                    country="United States",
                    country_code="US",
                    remote_type="HYBRID",
                    employment_type="FULL_TIME",
                    experience_level="SENIOR",
                    skills=["Python", "FastAPI", "PostgreSQL"],
                    posting_date=now,
                    first_seen_at=now,
                    last_seen_at=now,
                    last_verified_at=now,
                    status="ACTIVE",
                    application_url=f"https://stripe.com/jobs/test-seed-{i:03d}",
                    content_fingerprint=f"fp-test-seed-{i:03d}"
                )
                db.add(job)

        # Ensure any existing jobs have country_code populated safely
        from app.ingestion.normalizer import normalize_location_full
        for job in db.query(Job).filter(Job.country_code.is_(None)).all():
            clean_loc, city, region, country, country_code, remote_type = normalize_location_full(job.location, job.title)
            if country_code:
                job.country_code = country_code
                job.country = country
                job.city = city
                job.region = region
            else:
                job.country_code = "US"
                job.country = "United States"

        comp_canonical = db.query(Company).filter(Company.canonical_name == "Canonical").first()
        if not comp_canonical:
            comp_canonical = Company(
                canonical_name="Canonical",
                website="https://canonical.com",
                career_page_url="https://canonical.com/careers",
                identity_status="VERIFIED"
            )
            db.add(comp_canonical)
            db.flush()

            src_can = Source(
                company_id=comp_canonical.id,
                source_name="Canonical Greenhouse",
                source_type="GREENHOUSE",
                canonical_source_url="https://boards.greenhouse.io/canonical",
                external_board_id="canonical",
                access_classification="PUBLIC_API",
                sync_schedule_cron="0 */4 * * *",
                configuration={"board_token": "canonical"},
                health_status="HEALTHY",
                is_active=True
            )
            db.add(src_can)
            db.flush()

            now = datetime.datetime.now(datetime.timezone.utc)
            for idx, title in enumerate(["Linux Kernel Engineer", "Cloud Solutions Architect", "Security Operations Engineer"]):
                job = Job(
                    company_id=comp_canonical.id,
                    source_id=src_can.id,
                    external_job_id=f"canonical-seed-{idx+1:03d}",
                    title=f"{title} - Canonical",
                    normalized_title=title,
                    description="Systems software development and Linux.",
                    profession="ENGINEERING",
                    location="London, UK",
                    city="London",
                    country="United Kingdom",
                    country_code="GB",
                    remote_type="REMOTE",
                    employment_type="FULL_TIME",
                    experience_level="SENIOR",
                    skills=["Linux", "Python", "Go"],
                    posting_date=now,
                    first_seen_at=now,
                    last_seen_at=now,
                    last_verified_at=now,
                    status="ACTIVE",
                    application_url=f"https://canonical.com/careers/{idx+1}",
                    content_fingerprint=f"fp-canonical-seed-{idx+1:03d}"
                )
                db.add(job)

            job_in = Job(
                company_id=comp_canonical.id,
                source_id=src_can.id,
                external_job_id="canonical-seed-india-001",
                title="Frontend React Specialist - Bengaluru",
                normalized_title="Frontend React Specialist",
                description="Modern React and TypeScript UI development in Bengaluru.",
                profession="ENGINEERING",
                location="Bengaluru, Karnataka, India",
                city="Bengaluru",
                region="Karnataka",
                country="India",
                country_code="IN",
                remote_type="HYBRID",
                employment_type="FULL_TIME",
                experience_level="ENTRY",
                skills=["React", "TypeScript"],
                posting_date=now,
                first_seen_at=now,
                last_seen_at=now,
                last_verified_at=now,
                status="ACTIVE",
                application_url="https://canonical.com/careers/india-001",
                content_fingerprint="fp-canonical-seed-india-001"
            )
            db.add(job_in)

        db.commit()

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    # Ensure test tables and seed data exist
    seed_test_database()
    # Patch SessionLocal globally for the test suite
    core_db.SessionLocal = TestSessionLocal
    api_deps.SessionLocal = TestSessionLocal
    main_mod.SessionLocal = TestSessionLocal
    core_db.engine = test_engine
    main_mod.engine = test_engine

    def override_get_db():
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()

@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture(scope="function")
def db_session():
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture(scope="session")
def candidate_token(client):
    res = client.post("/api/v1/auth/login", json={
        "email": "candidate@example.com",
        "password": "Candidate@123456"
    })
    assert res.status_code == 200, res.text
    return res.json()["access_token"]

@pytest.fixture(scope="session")
def admin_token(client):
    res = client.post("/api/v1/auth/login", json={
        "email": "admin@jobplatform.com",
        "password": "Admin@123456"
    })
    assert res.status_code == 200, res.text
    return res.json()["access_token"]
