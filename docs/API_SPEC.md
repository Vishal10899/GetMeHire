# REST API Specification — Global Job Discovery Platform v2.0

All endpoints are versioned under prefix `/api/v1`.
Authentication is bearer-token based via `Authorization: Bearer <TOKEN>`.

---

## 1. Authentication Endpoints (`/api/v1/auth`)

### `POST /api/v1/auth/register`
- **Request Body**:
  ```json
  {
    "email": "candidate@example.com",
    "password": "SecurePassword@123"
  }
  ```
- **Response**: HTTP 201 Created
  ```json
  {
    "id": 2,
    "email": "candidate@example.com",
    "role": "USER",
    "account_status": "ACTIVE",
    "is_verified": true,
    "created_at": "2026-10-22T19:30:00Z"
  }
  ```

### `POST /api/v1/auth/login`
- **Request Body** (`application/json`):
  ```json
  {
    "email": "candidate@example.com",
    "password": "SecurePassword@123"
  }
  ```
- **Response**: HTTP 200 OK
  ```json
  {
    "access_token": "eyJhbGciOi...",
    "token_type": "bearer",
    "user": { "id": 2, "email": "candidate@example.com", "role": "USER" }
  }
  ```

### `POST /api/v1/auth/token` (OAuth2 Password Grant for Swagger UI)
- **Request Body** (`application/x-www-form-urlencoded`):
  ```text
  username=candidate@example.com&password=SecurePassword@123
  ```
- **Response**: HTTP 200 OK
  ```json
  {
    "access_token": "eyJhbGciOi...",
    "token_type": "bearer",
    "user": { "id": 2, "email": "candidate@example.com", "role": "USER" }
  }
  ```

### `POST /api/v1/auth/password-reset/request`
- **Request Body**: `{"email": "candidate@example.com"}`
- **Response**: `{"message": "Password reset token generated", "token": "..."}`

### `POST /api/v1/auth/password-reset/confirm`
- **Request Body**: `{"token": "...", "new_password": "NewSecurePassword@123"}`
- **Response**: `{"message": "Password reset successful"}`

### `DELETE /api/v1/auth/me`
- **Headers**: `Authorization: Bearer <TOKEN>`
- **Response**: `{"message": "Account successfully deleted"}`

---

## 2. Candidate Profile Endpoints (`/api/v1/profile`)

### `GET /api/v1/profile`
- **Headers**: `Authorization: Bearer <TOKEN>`
- **Response**:
  ```json
  {
    "id": 2,
    "user_id": 2,
    "full_name": "Alex Mercer",
    "headline": "Senior Full Stack & Python Engineer",
    "skills": ["Python", "FastAPI", "React", "PostgreSQL"],
    "preferred_roles": ["Senior Software Engineer"],
    "total_experience_years": 6.0,
    "relevant_experience_years": 5.0,
    "work_arrangements": ["REMOTE", "HYBRID"],
    "employment_types": ["FULL_TIME"],
    "salary_expectation_min": 140000.0,
    "salary_expectation_max": 190000.0,
    "salary_currency": "USD",
    "salary_period": "YEAR",
    "profile_completion_pct": 85,
    "resume_filename": "resume.pdf"
  }
  ```

### `PATCH /api/v1/profile`
- **Request Body**: Subset of profile fields.

### `POST /api/v1/profile/resume`
- **Content-Type**: `multipart/form-data`
- **Payload**: `file` (PDF, DOCX, or TXT up to 5MB).
- **Response**:
  ```json
  {
    "message": "Resume successfully uploaded",
    "filename": "Alex_Mercer_Resume.pdf",
    "profile_completion_pct": 95,
    "download_url": "/api/v1/profile/resume/download?token=..."
  }
  ```

### `DELETE /api/v1/profile/resume`
- Removes file from private disk storage and clears reference.

---

## 3. Job Discovery & Search Endpoints (`/api/v1/jobs`)

### `GET /api/v1/jobs`
- **Query Parameters**:
  - `keyword` (string): Title, description, or department match
  - `company` (string): Company name match
  - `location` (string): Location match
  - `remote_type` (string): `REMOTE`, `HYBRID`, or `ONSITE`
  - `employment_type` (string): `FULL_TIME`, `PART_TIME`, `CONTRACT`, `INTERNSHIP`
  - `experience_level` (string): `ENTRY`, `MID`, `SENIOR`, `LEAD`, `EXECUTIVE`
  - `skills` (list): Array of technology tags
  - `min_salary` (float)
  - `max_salary` (float)
  - `currency` (string): `USD`, `EUR`, `GBP`
  - `sort_by` (string): `newest`, `oldest`, `salary_high`
  - `page` (int, default: 1)
  - `page_size` (int, default: 20, max: 100)
- **Response**:
  ```json
  {
    "items": [...],
    "total": 124,
    "page": 1,
    "page_size": 20,
    "total_pages": 7,
    "has_next": true,
    "has_prev": false
  }
  ```

### `GET /api/v1/jobs/{job_id}`
- Returns full job details, company verification, source attribution, and direct application URL.

### `GET /api/v1/jobs/{job_id}/similar`
- Returns related listings in similar engineering areas or companies.

---

## 4. Saved Jobs Endpoints (`/api/v1/saved-jobs`)

- `GET /api/v1/saved-jobs`: List user bookmarked positions.
- `PUT /api/v1/saved-jobs/{job_id}`: Idempotently save job with optional notes.
- `DELETE /api/v1/saved-jobs/{job_id}`: Unsave job.

---

## 5. Explainable Recommendations (`/api/v1/recommendations`)

### `GET /api/v1/recommendations`
- **Response**:
  ```json
  {
    "algorithm_version": "v1.0-explainable-rule-engine",
    "items": [
      {
        "job": { ... },
        "match_score": 92,
        "match_breakdown": {
          "skill_score": 38.0,
          "role_score": 25.0,
          "location_score": 15.0,
          "experience_score": 14.0,
          "total_score": 92.0,
          "matched_skills": ["Python", "FastAPI", "PostgreSQL"],
          "missing_skills": ["Redis"],
          "reasons": [
            "Matched 3 core skills: Python, FastAPI, PostgreSQL",
            "Title directly matches preferred role 'Senior Software Engineer'",
            "Offers full remote work flexibility",
            "Your experience (5 yrs) satisfies requirement (4 yrs)"
          ]
        }
      }
    ]
  }
  ```

---

## 6. Job Alerts Endpoints (`/api/v1/alerts`)

- `GET /api/v1/alerts`: List active alert subscriptions.
- `POST /api/v1/alerts`: Create alert with criteria (`keywords`, `remote_only`, `min_salary`, `frequency`).
- `PATCH /api/v1/alerts/{alert_id}`: Modify alert settings or pause.
- `DELETE /api/v1/alerts/{alert_id}`: Remove alert.
- `POST /api/v1/alerts/{alert_id}/evaluate`: Evaluate alert against newest records with deduplicated delivery log.

---

## 7. Administration Endpoints (`/api/v1/admin`)

- `GET /api/v1/admin/sources`: List registered sources with health status and active job counts.
- `POST /api/v1/admin/sources`: Register new source (Greenhouse, Lever, Ashby, JSON, Web Scraper).
- `PATCH /api/v1/admin/sources/{source_id}`: Update source schedule, concurrency, or pause.
- `POST /api/v1/admin/sources/{source_id}/sync`: Trigger immediate ingestion run.
- `GET /api/v1/admin/ingestion-runs`: View historical ingestion executions and anomaly records.
- `GET /api/v1/admin/health`: System health metrics.
- `POST /api/v1/admin/sources/probe`: Probe company handle across Greenhouse, Ashby, Lever (US & EU) ATS boards.
- `POST /api/v1/admin/sources/discover`: Probe and automatically register verified company and source.
- `POST /api/v1/admin/scheduler/run`: Evaluate and execute all due scheduled ingestion sources and maintenance.
- `POST /api/v1/admin/jobs/expire-stale`: Transition `POSSIBLY_STALE` jobs older than configured grace period (default 14 days) to `CLOSED`.
