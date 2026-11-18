import sys
import os

# Auto-relaunch inside project virtual environment if running under an external interpreter lacking dependencies
try:
    import bcrypt
except ModuleNotFoundError:
    venv_python = os.path.join(os.path.dirname(os.path.abspath(__file__)), "venv", "Scripts", "python.exe")
    if os.path.exists(venv_python) and sys.executable != venv_python:
        import subprocess
        res = subprocess.run([venv_python] + sys.argv)
        sys.exit(res.returncode)
    raise

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import datetime
from sqlalchemy import text
from app.core.database import SessionLocal, engine, Base
from app.core.security import get_password_hash
from app.models import User, Profile, Company, Source, Job, SavedJob, Alert, IngestionRun
from app.ingestion.deduplication import compute_content_fingerprint
from app.ingestion.base import NormalizedJob

def seed():
    print("Creating tables in PostgreSQL...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # 1. Create or verify Users
        admin_user = db.query(User).filter(User.email == "admin@jobplatform.com").first()
        if not admin_user:
            admin_user = User(
                email="admin@jobplatform.com",
                hashed_password=get_password_hash("Admin@123456"),
                role="ADMIN",
                account_status="ACTIVE",
                is_verified=True
            )
            db.add(admin_user)
            db.flush()
            print("Admin user created: admin@jobplatform.com / Admin@123456")

        candidate_user = db.query(User).filter(User.email == "candidate@example.com").first()
        if not candidate_user:
            candidate_user = User(
                email="candidate@example.com",
                hashed_password=get_password_hash("Candidate@123456"),
                role="USER",
                account_status="ACTIVE",
                is_verified=True
            )
            db.add(candidate_user)
            db.flush()

            # Seed candidate profile
            profile = Profile(
                user_id=candidate_user.id,
                full_name="Alex Mercer",
                headline="Senior Full Stack & Python Engineer",
                skills=["Python", "FastAPI", "React", "TypeScript", "PostgreSQL", "Docker", "AWS"],
                preferred_roles=["Senior Software Engineer", "Full Stack Engineer", "Backend Developer"],
                total_experience_years=6.0,
                relevant_experience_years=5.0,
                preferred_countries=["United States", "United Kingdom", "Germany"],
                preferred_locations=["San Francisco", "London", "Berlin", "Remote"],
                work_arrangements=["REMOTE", "HYBRID"],
                employment_types=["FULL_TIME"],
                salary_expectation_min=140000,
                salary_expectation_max=190000,
                salary_currency="USD",
                salary_period="YEAR",
                profile_completion_pct=85
            )
            db.add(profile)
            print("Demo candidate created: candidate@example.com / Candidate@123456")

        # 2. Companies
        companies_data = [
            {"name": "Stripe", "website": "https://stripe.com", "career": "https://stripe.com/jobs", "logo": None},
            {"name": "Airbnb", "website": "https://airbnb.com", "career": "https://careers.airbnb.com", "logo": None},
            {"name": "Anthropic", "website": "https://anthropic.com", "career": "https://anthropic.com/careers", "logo": None},
            {"name": "Datadog", "website": "https://datadoghq.com", "career": "https://careers.datadoghq.com", "logo": None},
            {"name": "Scale AI", "website": "https://scale.com", "career": "https://scale.com/careers", "logo": None},
            {"name": "Palantir", "website": "https://palantir.com", "career": "https://jobs.lever.co/palantir", "logo": None},
            {"name": "Ramp", "website": "https://ramp.com", "career": "https://jobs.ashbyhq.com/ramp", "logo": None},
        ]

        company_map = {}
        for c in companies_data:
            comp = db.query(Company).filter(Company.canonical_name == c["name"]).first()
            if not comp:
                comp = Company(
                    canonical_name=c["name"],
                    website=c["website"],
                    career_page_url=c["career"],
                    logo_url=c["logo"],
                    identity_status="VERIFIED"
                )
                db.add(comp)
                db.flush()
            company_map[c["name"]] = comp

        # 3. Sources
        sources_data = [
            {
                "company": "Stripe",
                "name": "Stripe Greenhouse ATS",
                "type": "GREENHOUSE",
                "url": "https://boards.greenhouse.io/stripe",
                "board_id": "stripe",
                "classification": "PUBLIC_API",
                "cron": "0 */4 * * *",
                "config": {"board_token": "stripe"}
            },
            {
                "company": "Airbnb",
                "name": "Airbnb Greenhouse ATS",
                "type": "GREENHOUSE",
                "url": "https://boards.greenhouse.io/airbnb",
                "board_id": "airbnb",
                "classification": "PUBLIC_API",
                "cron": "0 */6 * * *",
                "config": {"board_token": "airbnb"}
            },
            {
                "company": "Anthropic",
                "name": "Anthropic Greenhouse ATS",
                "type": "GREENHOUSE",
                "url": "https://boards.greenhouse.io/anthropic",
                "board_id": "anthropic",
                "classification": "PUBLIC_API",
                "cron": "0 */6 * * *",
                "config": {"board_token": "anthropic"}
            },
            {
                "company": "Datadog",
                "name": "Datadog Greenhouse ATS",
                "type": "GREENHOUSE",
                "url": "https://boards.greenhouse.io/datadog",
                "board_id": "datadog",
                "classification": "PUBLIC_API",
                "cron": "0 */8 * * *",
                "config": {"board_token": "datadog"}
            },
            {
                "company": "Scale AI",
                "name": "Scale AI Greenhouse ATS",
                "type": "GREENHOUSE",
                "url": "https://boards.greenhouse.io/scaleai",
                "board_id": "scaleai",
                "classification": "PUBLIC_API",
                "cron": "0 */6 * * *",
                "config": {"board_token": "scaleai"}
            },
            {
                "company": "Palantir",
                "name": "Palantir Lever ATS",
                "type": "LEVER",
                "url": "https://jobs.lever.co/palantir",
                "board_id": "palantir",
                "classification": "PUBLIC_API",
                "cron": "0 */6 * * *",
                "config": {"company_slug": "palantir"}
            },
            {
                "company": "Ramp",
                "name": "Ramp Ashby Board",
                "type": "ASHBY",
                "url": "https://jobs.ashbyhq.com/ramp",
                "board_id": "ramp",
                "classification": "PUBLIC_API",
                "cron": "0 */6 * * *",
                "config": {"board_name": "ramp"}
            }
        ]

        source_map = {}
        for s in sources_data:
            comp = company_map[s["company"]]
            src = db.query(Source).filter(Source.company_id == comp.id).first()
            if not src:
                src = Source(
                    company_id=comp.id,
                    source_name=s["name"],
                    source_type=s["type"],
                    canonical_source_url=s["url"],
                    external_board_id=s["board_id"],
                    access_classification=s["classification"],
                    sync_schedule_cron=s["cron"],
                    configuration=s["config"],
                    health_status="HEALTHY",
                    last_successful_sync_at=datetime.datetime.now(datetime.timezone.utc),
                    last_complete_sync_at=datetime.datetime.now(datetime.timezone.utc),
                )
                db.add(src)
                db.flush()
            else:
                src.source_name = s["name"]
                src.source_type = s["type"]
                src.canonical_source_url = s["url"]
                src.external_board_id = s["board_id"]
                src.access_classification = s["classification"]
                src.sync_schedule_cron = s["cron"]
                src.configuration = s["config"]
                db.flush()
            source_map[s["company"]] = src

        # 4. Jobs
        sample_jobs = [
            {
                "company": "Stripe",
                "external_id": "str-001",
                "title": "Senior Backend Engineer - Financial Infrastructure",
                "desc": "Build highly scalable, reliable payment services handling trillions of dollars globally. Lead architecture for fault-tolerant microservices, high-throughput database interactions, and real-time ledger consistency. Requirements: 5+ years experience in Python, Go or Java, deep PostgreSQL expertise, and distributed systems fundamentals.",
                "dept": "Financial Services",
                "location": "San Francisco, CA",
                "city": "San Francisco",
                "region": "California",
                "country": "United States",
                "remote": "HYBRID",
                "emp_type": "FULL_TIME",
                "level": "SENIOR",
                "exp_years": 5.0,
                "skills": ["Python", "PostgreSQL", "Distributed Systems", "AWS", "Go"],
                "salary_min": 175000,
                "salary_max": 230000,
                "app_url": "https://stripe.com/jobs/str-001"
            },
            {
                "company": "Airbnb",
                "external_id": "abnb-102",
                "title": "Staff Full Stack Engineer - Host Platform",
                "desc": "Empower millions of hosts worldwide with intuitive, performant tools. Work across Next.js, React, TypeScript, GraphQL, and resilient backend services. Requirements: 7+ years of product development, strong frontend state management, and modern component design.",
                "dept": "Host Experience",
                "location": "Remote - US / Global",
                "city": "Remote",
                "region": "Worldwide",
                "country": "United States",
                "remote": "REMOTE",
                "emp_type": "FULL_TIME",
                "level": "LEAD",
                "exp_years": 7.0,
                "skills": ["React", "TypeScript", "Next.js", "GraphQL", "Node.js"],
                "salary_min": 190000,
                "salary_max": 255000,
                "app_url": "https://careers.airbnb.com/positions/abnb-102"
            },
            {
                "company": "Anthropic",
                "external_id": "ant-405",
                "title": "AI Systems & API Platform Engineer",
                "desc": "Build the developer-facing API platform that serves Claude to millions of users and enterprise developers. Focus on low-latency streaming endpoints, robust rate limiting, observability, and high-availability FastAPI / Python services.",
                "dept": "API Infrastructure",
                "location": "San Francisco, CA",
                "city": "San Francisco",
                "region": "California",
                "country": "United States",
                "remote": "HYBRID",
                "emp_type": "FULL_TIME",
                "level": "SENIOR",
                "exp_years": 5.0,
                "skills": ["Python", "FastAPI", "Docker", "Kubernetes", "AWS", "Redis"],
                "salary_min": 210000,
                "salary_max": 280000,
                "app_url": "https://jobs.lever.co/anthropic/ant-405"
            },
            {
                "company": "Datadog",
                "external_id": "dd-883",
                "title": "Cloud Monitoring Software Engineer",
                "desc": "Scale observability agents processing petabytes of telemetry data daily. Design efficient aggregation algorithms and time-series pipelines. We look for engineers with strong Go, Python, and Linux systems expertise.",
                "dept": "Core Metrics",
                "location": "London, UK",
                "city": "London",
                "region": "Greater London",
                "country": "United Kingdom",
                "remote": "HYBRID",
                "emp_type": "FULL_TIME",
                "level": "MID",
                "exp_years": 3.0,
                "skills": ["Go", "Python", "Linux", "Kubernetes", "Docker"],
                "salary_min": 85000,
                "salary_max": 120000,
                "salary_currency": "GBP",
                "app_url": "https://jobs.ashbyhq.com/datadog/dd-883"
            },
            {
                "company": "Scale AI",
                "external_id": "scale-301",
                "title": "Data Engineering Lead - Autonomous Systems",
                "desc": "Direct data pipelines and labeling workflows for premier autonomous vehicle and robotics foundations. Lead engineers building ETL clusters, data quality verification, and scalable ML training dataset delivery pipelines.",
                "dept": "Autonomous Platform",
                "location": "Berlin, Germany",
                "city": "Berlin",
                "region": "Berlin",
                "country": "Germany",
                "remote": "REMOTE",
                "emp_type": "FULL_TIME",
                "level": "LEAD",
                "exp_years": 6.0,
                "skills": ["Python", "PostgreSQL", "AWS", "Apache Spark", "Docker"],
                "salary_min": 110000,
                "salary_max": 150000,
                "salary_currency": "EUR",
                "app_url": "https://scale.com/careers/scale-301"
            },
            {
                "company": "Stripe",
                "external_id": "str-099",
                "title": "Frontend Engineer - Billing & Checkout",
                "desc": "Craft delightful, accessible checkout experiences used by hundreds of thousands of merchants. Work in TypeScript, React, and CSS architecture with obsession over milliseconds and conversion rates.",
                "dept": "Billing Product",
                "location": "New York, NY",
                "city": "New York",
                "region": "New York",
                "country": "United States",
                "remote": "ONSITE",
                "emp_type": "FULL_TIME",
                "level": "MID",
                "exp_years": 3.0,
                "skills": ["React", "TypeScript", "CSS", "Next.js"],
                "salary_min": 140000,
                "salary_max": 185000,
                "app_url": "https://stripe.com/jobs/str-099"
            },
            {
                "company": "Airbnb",
                "external_id": "abnb-204",
                "title": "Backend Infrastructure Engineer - Distributed Cache",
                "desc": "Maintain and scale Redis and Memcached clusters serving hundreds of millions of requests per second. Optimize connection pooling, memory topology, and disaster recovery.",
                "dept": "Core Storage",
                "location": "Remote - Worldwide",
                "city": "Remote",
                "region": "Global",
                "country": "Remote",
                "remote": "REMOTE",
                "emp_type": "CONTRACT",
                "level": "SENIOR",
                "exp_years": 5.0,
                "skills": ["Python", "Redis", "Distributed Systems", "C++", "Linux"],
                "salary_min": 160000,
                "salary_max": 210000,
                "app_url": "https://careers.airbnb.com/positions/abnb-204"
            }
        ]

        now = datetime.datetime.now(datetime.timezone.utc)
        for j in sample_jobs:
            comp = company_map[j["company"]]
            src = source_map[j["company"]]

            norm_job = NormalizedJob(
                external_job_id=j["external_id"],
                title=j["title"],
                description=j["desc"],
                department=j.get("dept"),
                location=j.get("location"),
                city=j.get("city"),
                region=j.get("region"),
                country=j.get("country"),
                remote_type=j.get("remote", "ONSITE"),
                employment_type=j.get("emp_type", "FULL_TIME"),
                experience_level=j.get("level"),
                min_experience_years=j.get("exp_years"),
                skills=j.get("skills", []),
                salary_min=j.get("salary_min"),
                salary_max=j.get("salary_max"),
                salary_currency=j.get("salary_currency", "USD"),
                application_url=j["app_url"]
            )
            fingerprint = compute_content_fingerprint(norm_job, comp.canonical_name)

            existing_job = db.query(Job).filter(Job.source_id == src.id, Job.external_job_id == j["external_id"]).first()
            if not existing_job:
                new_job = Job(
                    company_id=comp.id,
                    source_id=src.id,
                    external_job_id=j["external_id"],
                    title=j["title"],
                    description=j["desc"],
                    department=j.get("dept"),
                    location=j.get("location"),
                    city=j.get("city"),
                    region=j.get("region"),
                    country=j.get("country"),
                    remote_type=j.get("remote", "ONSITE"),
                    employment_type=j.get("emp_type", "FULL_TIME"),
                    experience_level=j.get("level"),
                    min_experience_years=j.get("exp_years"),
                    skills=j.get("skills", []),
                    salary_min=j.get("salary_min"),
                    salary_max=j.get("salary_max"),
                    salary_currency=j.get("salary_currency", "USD"),
                    salary_period="YEAR",
                    posting_date=now - datetime.timedelta(days=2),
                    first_seen_at=now - datetime.timedelta(days=2),
                    last_seen_at=now,
                    last_verified_at=now,
                    status="ACTIVE",
                    application_url=j["app_url"],
                    content_fingerprint=fingerprint,
                    raw_source_data={"seed": True}
                )
                db.add(new_job)

        # 5. Ingestion Runs History
        for comp_name, src in source_map.items():
            existing_run = db.query(IngestionRun).filter(IngestionRun.source_id == src.id).first()
            if not existing_run:
                run = IngestionRun(
                    source_id=src.id,
                    status="SUCCESS",
                    start_time=now - datetime.timedelta(hours=3),
                    end_time=now - datetime.timedelta(hours=3) + datetime.timedelta(seconds=4),
                    duration_seconds=4.2,
                    records_discovered=12,
                    records_inserted=4,
                    records_updated=0,
                    records_unchanged=8,
                    records_rejected=0,
                    anomaly_detected=False,
                    anomaly_details={"status": "clean_sync"}
                )
                db.add(run)

        # 6. Saved Job for candidate
        first_job = db.query(Job).first()
        if candidate_user and first_job:
            saved = db.query(SavedJob).filter(SavedJob.user_id == candidate_user.id, SavedJob.job_id == first_job.id).first()
            if not saved:
                db.add(SavedJob(user_id=candidate_user.id, job_id=first_job.id, notes="Excited about the infra scale!"))

        # 7. Alert for candidate
        if candidate_user:
            alert = db.query(Alert).filter(Alert.user_id == candidate_user.id).first()
            if not alert:
                db.add(Alert(
                    user_id=candidate_user.id,
                    title="Senior Python & Remote Roles",
                    criteria={"keywords": "Python", "remote_only": True, "skills": ["Python", "FastAPI"]},
                    frequency="DAILY",
                    is_active=True
                ))

        db.commit()
        print("Database seeded successfully with companies, sources, jobs, users, and ingestion logs!")

    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed()
