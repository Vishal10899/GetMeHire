# Operational Runbooks — Global Job Discovery Platform v2.0

## Table of Contents
1. [Overview & Severity Classifications](#1-overview--severity-classifications)
2. [Source Management Runbooks](#2-source-management-runbooks)
   - [Pausing a Failing Source](#pausing-a-failing-source)
   - [Retrying a Failed Synchronization Run](#retrying-a-failed-synchronization-run)
   - [Investigating Parsing & Extraction Errors](#investigating-parsing--extraction-errors)
   - [Resolving Ingestion Anomaly Quarantines](#resolving-ingestion-anomaly-quarantines)
3. [Database & Search Operations](#3-database--search-operations)
   - [Database Backup and Restoration](#database-backup-and-restoration)
   - [Reconstructing PostgreSQL Full-Text Indexes](#reconstructing-postgresql-full-text-indexes)
4. [Security Incident Runbooks](#4-security-incident-runbooks)
   - [Revoking Compromised Credentials](#revoking-compromised-credentials)
   - [Candidate Data Deletion & Privacy Compliance](#candidate-data-deletion--privacy-compliance)
5. [Incident Escalation Contacts](#5-incident-escalation-contacts)

---

## 1. Overview & Severity Classifications

| Severity | Definition | Response Target | Example |
|---|---|---|---|
| **SEV-1** | Critical user journey down (search outage, DB unreachable) | < 15 minutes | PostgreSQL connection exhaustion; 500 errors on `/api/v1/jobs` |
| **SEV-2** | Ingestion pipeline failure or anomaly quarantine for multiple tier-1 sources | < 1 hour | Greenhouse/Lever rate limit exceeded; Mass deactivation guard triggered |
| **SEV-3** | Minor integration parsing failure or non-critical alert delivery retry | < 4 hours | Individual job markdown formatting issue |

---

## 2. Source Management Runbooks

### Pausing a Failing Source
**Trigger**: Source enters `FAILING` or `DEGRADED` health status due to repeated HTTP 429/401 or upstream schema changes.

**Procedure**:
1. Open Admin Dashboard at `http://localhost:3000/admin` or execute API PATCH:
   ```bash
   curl -X PATCH http://localhost:8000/api/v1/admin/sources/{SOURCE_ID} \
     -H "Authorization: Bearer <ADMIN_TOKEN>" \
     -H "Content-Type: application/json" \
     -d '{"is_active": false}'
   ```
2. Verify existing active jobs for the paused source are preserved in `POSSIBLY_STALE` or `ACTIVE` state. Per PRD Section 5.8: *Source failure is never proof of job closure.*

---

### Retrying a Failed Synchronization Run
**Trigger**: A transient network timeout or rate limit error caused an IngestionRun to fail.

**Procedure**:
1. Check failure category in ingestion runs:
   ```bash
   curl -s http://localhost:8000/api/v1/admin/ingestion-runs?limit=5 \
     -H "Authorization: Bearer <ADMIN_TOKEN>"
   ```
2. If `error_category` is `TRANSIENT` or `RATE_LIMIT` and cooldown has elapsed:
   ```bash
   curl -X POST http://localhost:8000/api/v1/admin/sources/{SOURCE_ID}/sync \
     -H "Authorization: Bearer <ADMIN_TOKEN>"
   ```
3. Monitor log output for completion status `SUCCESS`.

---

### Resolving Ingestion Anomaly Quarantines
**Trigger**: IngestionRun status is `ANOMALY_QUARANTINE`.
Causes:
- Sudden drop in discovered listing count (>60% reduction).
- Rejection rate of malformed records exceeds 25%.

**Procedure**:
1. Inspect run anomaly details:
   ```json
   {
     "status": "ANOMALY_QUARANTINE",
     "anomaly_details": {
       "reasons": ["Sudden sharp drop in discovered job listings: from 120 to 14 (-88.3%)"]
     }
   }
   ```
2. Check upstream career portal URL to determine if the employer migrated ATS boards or altered URL routing.
3. If valid restructuring, update source `canonical_source_url` and re-run.
4. If upstream outage, keep source quarantined to prevent invalid bulk closure of active listings.

---

## 3. Database & Search Operations

### Database Backup and Restoration
Authoritative Database: **PostgreSQL 17** (`job_discovery`)

**Automated Backup**:
```powershell
pg_dump -U postgres -h 127.0.0.1 -Fc -f "D:\24JObs\backups\job_discovery_$(Get-Date -Format 'yyyyMMdd_HHmm').dump" job_discovery
```

**Restoration Procedure**:
1. Terminate active backend workers to release locks.
2. Restore database:
```powershell
pg_restore -U postgres -h 127.0.0.1 -d job_discovery --clean --if-exists "D:\24JObs\backups\target.dump"
```
3. Restart FastAPI backend instances and verify `/api/v1/admin/health`.

---

### Reconstructing PostgreSQL Full-Text Indexes
If text search queries degrade or search vector index requires rebuilding:
```sql
REINDEX TABLE jobs;
VACUUM ANALYZE jobs;
```

---

## 4. Security Incident Runbooks

### Revoking Compromised Credentials
1. Rotate `SECRET_KEY` in environment file (`.env`).
2. Immediate effect: All issued JWT access tokens and password reset tokens will be invalidated across all user sessions.
3. Restart API workers:
   ```powershell
   & "D:\24JObs\backend\venv\Scripts\uvicorn.exe" app.main:app --reload
   ```

### Candidate Data Deletion & Privacy Compliance
When a user requests personal data deletion (PRD Section 4.1):
1. Send deletion request:
   ```bash
   curl -X DELETE http://localhost:8000/api/v1/auth/me \
     -H "Authorization: Bearer <USER_TOKEN>"
   ```
2. Cascade deletes:
   - Account record in `users`
   - Candidate `profiles` record
   - Physical resume file on private disk / object storage
   - Bookmarked entries in `saved_jobs`
   - Active alert subscriptions in `alerts`
   - Audit trail recorded with anonymized metadata.
