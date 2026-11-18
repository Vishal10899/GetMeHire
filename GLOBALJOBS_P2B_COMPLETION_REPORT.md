# GlobalJobs — P2B Personalized Job Matching Sprint Completion Report

**Sprint Date:** November 16, 2026  
**Status:** **COMPLETED & VERIFIED (100%)**  
**Lead Software Architect & Auditor:** DeepMind Antigravity Engine  
**Target Repository:** `D:\24JObs`  
**Frozen Architecture:** Next.js 14 (App Router, JavaScript Only), FastAPI, PostgreSQL 17, Zero Paid APIs

---

## 1. Executive Summary & Core Results

The **P2B Personalized Job Matching Sprint** successfully audited, redesigned, and verified GlobalJobs' recommendation and match-scoring architecture. We eliminated the legacy "neutral fallback" defect uncovered in P1—where unconfigured dimensions awarded 40%–65% default baseline points to completely blank profiles or completely unrelated professions (such as 40% for *Corporate Counsel* awarded to a *Python Backend Developer*).

In its place, we engineered **Matching Engine v2.0 (`v2.0-evidence-based-matching`)**: an evidence-backed, transparent scoring framework where:
1. Points are awarded **only upon explicit positive alignment** between candidate profile data and job listing criteria.
2. Missing or unstated criteria earn **0 positive points** without penalizing other valid dimensions.
3. Completely unrelated career tracks with zero skills overlap earn **0.0%** total score.
4. Candidate profiles lacking substantive signals trigger an explainable **Insufficient Data** state rather than fabricating misleading match scores.
5. Scores are strictly **suppressed for unauthenticated visitors**, ensuring privacy and preventing hallucinated personalization.
6. A dedicated **My Matches** interface (`/matches` & `/recommendations`) provides ranked jobs, multi-track pills, score thresholds (50%+, 70%+, 85%+), remote/location filters, 4-bar progress breakdowns, matched/missing skill badges, and direct ATS application links with provenance tracking.

---

## 2. Audit of Previous Scoring vs New Evidence-Based Engine

### The Root Cause of the P1 Neutral Fallback Defect
In the legacy `v1.0` implementation (`backend/app/services/matching_service.py`), each dimension was assigned a positive fallback when data was absent or partial:
- **Skills (40 max):** Awarded a 10.0 to 25.0 pt default baseline if skills were missing or if job descriptions lacked parsed skills.
- **Roles (25 max):** Awarded 10.0 to 15.0 pts if no preferred role was specified or for vague substring matches.
- **Location (20 max):** Awarded 15.0 pts if the job or candidate did not specify strict location constraints.
- **Experience (15 max):** Awarded 10.0 pts if minimum experience was unstated in the job.

**Consequence:** A candidate with zero profile information scored **50% to 65%** across arbitrary jobs. A Python backend engineer scored **40% for Corporate Counsel** solely because both had unstated/neutral fallbacks.

### Comparison Matrix: v1.0 vs v2.0

| Feature / Behavior | Legacy v1.0 Engine | Evidence-Based v2.0 Engine |
| :--- | :--- | :--- |
| **Blank Candidate Profile** | 50%–65% fabricated baseline score | **0.0%** score + `has_sufficient_data=False` |
| **Python Dev vs Corporate Counsel** | 40% (misleading neutral points) | **0.0%** (track mismatch + 0 skills + unrelated exp) |
| **Missing Candidate Information** | Earns default positive points | Earns **0 points**; marked as *Not Specified* |
| **Missing Job Skills Array** | Awarded default 10–25 pts | Regex token search in description (0 pts if not found) |
| **Remote Eligibility Handling** | Inferred loosely from word "Remote" | Distinguishes `WORLDWIDE_REMOTE` vs `INDIA_ONLY` vs restricted |
| **Unauthenticated Visitors** | Ambiguous or leaked profile scoring | **Strictly Suppressed** (`match_score=None`) |
| **Candidate Isolation** | Shared single default fallback | Multi-tenant user isolation with separate tokens |
| **Scoring Disclaimer** | None | Explicit: reflects qualification fit, not hiring probability |

---

## 3. Mathematical Scoring Architecture & Formula Verification

The total match score is bounded in $[0.0, 100.0]$ as the sum of four discrete dimensions:

$$\text{Total Score} = \min\left(100.0, \, \mathcal{S}_{\text{skills}} + \mathcal{R}_{\text{role}} + \mathcal{L}_{\text{location}} + \mathcal{E}_{\text{experience}}\right)$$

### Dimension 1: Skills & Tools ($\mathcal{S}_{\text{skills}}$, Max 40.0 pts)
Evaluates exact overlap between candidate skills and job-required skills:
- **Case A: Job defines explicit skills ($N_{\text{job}} > 0$):**
  $$\mathcal{S}_{\text{skills}} = \text{round}\left(\min\left(40.0, \, \frac{|S_{\text{candidate}} \cap S_{\text{job}}|}{|S_{\text{job}}|} \times 40.0\right), \, 1\right)$$
  - Unmatched skills are categorized into `missing_skills`.
  - Matched skills are categorized into `matched_skills`.
- **Case B: Job skills array is empty:**
  - Performs bounded whole-word regex token search across job description text:
  $$\mathcal{S}_{\text{skills}} = \text{round}\left(\min\left(40.0, \, |S_{\text{candidate}} \cap \text{Tokens}(\text{Description})| \times 10.0\right), \, 1\right)$$
- **Case C: Candidate has no skills:**
  - $\mathcal{S}_{\text{skills}} = 0.0$ pts.

### Dimension 2: Title & Career Track Alignment ($\mathcal{R}_{\text{role}}$, Max 25.0 pts)
Divided into two transparent sub-components:
- **Career Track Alignment (Max 10.0 pts):**
  $$\mathcal{R}_{\text{track}} = \begin{cases} 10.0 & \text{if } \text{Taxonomy}(\text{Profile}) = \text{Taxonomy}(\text{Job}) \\ 0.0 & \text{if tracks differ or unspecified} \end{cases}$$
- **Role / Title Alignment (Max 15.0 pts):**
  $$\mathcal{R}_{\text{title}} = \begin{cases} 15.0 & \text{if exact normalized role matches job title} \\ 8.0 & \text{if significant role stem/keyword matches} \\ 0.0 & \text{if no role match or unspecified} \end{cases}$$
  $$\mathcal{R}_{\text{role}} = \mathcal{R}_{\text{track}} + \mathcal{R}_{\text{title}}$$

### Dimension 3: Location & Remote Eligibility ($\mathcal{L}_{\text{location}}$, Max 20.0 pts)
Divided into two sub-components:
- **Work Arrangement Alignment (Max 10.0 pts):**
  - If job is `REMOTE` and candidate prefers `REMOTE`:
    - `WORLDWIDE_REMOTE`: $+10.0$ pts.
    - `INDIA_ONLY`: $+10.0$ pts if candidate is India-located; $+0.0$ pts if foreign.
    - Country-restricted (e.g. `US_ONLY` for Indian candidate): $+0.0$ pts (`Restricted`).
  - If job is `ONSITE` or `HYBRID` and matches candidate arrangement: $+10.0$ pts.
  - If arrangements conflict: $+0.0$ pts.
- **Geographic Match (Max 10.0 pts):**
  - If `WORLDWIDE_REMOTE`: $+10.0$ pts (100% geographic flexibility).
  - If candidate city or country matches job location: $+10.0$ pts.
  - Otherwise: $+0.0$ pts.
  $$\mathcal{L}_{\text{location}} = \mathcal{L}_{\text{arrangement}} + \mathcal{L}_{\text{geographic}}$$

### Dimension 4: Relevant Experience & Seniority ($\mathcal{E}_{\text{experience}}$, Max 15.0 pts)
- **Unrelated Field Guard:** If career tracks differ and $\mathcal{S}_{\text{skills}} = 0.0$, $\mathcal{E}_{\text{experience}} = 0.0$ pts (`Unrelated Field`). Software engineering experience does not count as legal experience.
- **Experience Requirement Alignment:**
  $$\mathcal{E}_{\text{experience}} = \begin{cases} 15.0 & \text{if } Y_{\text{candidate}} \ge Y_{\text{job\_min}} \quad \text{("Meets Requirement")} \\ 8.0 & \text{if } Y_{\text{candidate}} \ge 0.7 \times Y_{\text{job\_min}} \quad \text{("Within Reach")} \\ 0.0 & \text{if } Y_{\text{candidate}} < 0.7 \times Y_{\text{job\_min}} \quad \text{("Below Requirement")} \end{cases}$$
- **Seniority Level Fallback (when minimum years unstated):**
  - $+15.0$ pts if years align with level tier (e.g. Senior $\ge 3.5$ yrs).
  - $+5.0$ pts if different tier.
  - $+0.0$ pts if unknown.

---

## 4. Concrete Score Walkthroughs

### Candidate Profile: Alex Mercer
- **Profession:** `ENGINEERING`
- **Skills:** `["Python", "FastAPI", "Docker", "PostgreSQL"]`
- **Preferred Roles:** `["Senior Backend Engineer", "Python Developer"]`
- **Location & Arrangement:** Bangalore, India; `REMOTE`
- **Total Experience:** 5.0 years

---

### Case 1: Senior Backend Engineer (Python/FastAPI)
- **Company:** Razorpay / Stripe
- **Profession:** `ENGINEERING`
- **Skills Required:** `["Python", "FastAPI", "PostgreSQL"]`
- **Remote / Location:** `REMOTE`, `INDIA_ONLY`, Bengaluru, India
- **Experience Required:** 4.0 years

| Component | Calculation | Points | Explanation |
| :--- | :--- | :---: | :--- |
| **Skills** | $3 / 3 \times 40.0$ | **40.0** / 40 | Matched 3 of 3 core skills: Python, FastAPI, PostgreSQL |
| **Role & Track** | Track (10.0) + Title (15.0) | **25.0** / 25 | Direct match with 'Engineering' track & 'Senior Backend Engineer' title |
| **Location** | Arrangement (10.0) + Geo (10.0) | **20.0** / 20 | India-eligible remote position; Bengaluru location match |
| **Experience** | $5.0 \text{ yrs} \ge 4.0 \text{ yrs}$ | **15.0** / 15 | Experience (5 yrs) satisfies requirement (4 yrs) |
| **TOTAL SCORE** | Sum | **100.0%** | **Strong Exceptional Match** |

---

### Case 2: Engineering Manager, Billing Platform
- **Company:** Stripe
- **Profession:** `ENGINEERING`
- **Skills Required:** `["Distributed Systems", "Architecture", "People Management"]`
- **Remote / Location:** `HYBRID`, San Francisco, CA
- **Experience Required:** 7.0 years

| Component | Calculation | Points | Explanation |
| :--- | :--- | :---: | :--- |
| **Skills** | $0 / 3 \times 40.0$ | **0.0** / 40 | No required management skills matched |
| **Role & Track** | Track (10.0) + Title (8.0 stem) | **18.0** / 25 | Engineering track matched; role stem 'Engineer' aligns partially |
| **Location** | Arrangement (0.0) + Geo (0.0) | **0.0** / 20 | Hybrid differs from Remote preference; SF differs from Bangalore |
| **Experience** | $5.0 \text{ yrs} \ge 7.0 \times 0.7 = 4.9$ | **8.0** / 15 | Close experience alignment (5 yrs vs 7 yrs required — Within Reach) |
| **TOTAL SCORE** | Sum | **26.0%** | **Low Fit (Previously artificially inflated to 48%)** |

---

### Case 3: Corporate Counsel, Commercial (The P1 Verification Defect)
- **Company:** Brex / Swiggy
- **Profession:** `LEGAL_ADMIN`
- **Skills Required:** `["Commercial Contracts", "Compliance", "Contract Negotiation", "Bar License"]`
- **Remote / Location:** `ONSITE`, New York, NY
- **Experience Required:** 6.0 years

| Component | Calculation | Points | Explanation |
| :--- | :--- | :---: | :---: |
| **Skills** | $0 / 4 \times 40.0$ | **0.0** / 40 | Missing all 4 required legal skills |
| **Role & Track** | Track (0.0) + Title (0.0) | **0.0** / 25 | Different career track (Legal Admin vs Engineering) |
| **Location** | Arrangement (0.0) + Geo (0.0) | **0.0** / 20 | Onsite in New York differs from Remote in Bangalore |
| **Experience** | Unrelated field guard | **0.0** / 15 | Software experience does not satisfy legal role requirement |
| **TOTAL SCORE** | Sum | **0.0%** | **Zero Alignment (Previously 40.0%!)** |

*The Corporate Counsel defect is 100% resolved.*

---

## 5. My Matches UI/UX Architecture & Components

The **My Matches** interface is implemented at `/matches` (with `/recommendations` acting as a synchronized alias) adhering strictly to the `GlobalJobs` design tokens and `motion/react` animation guidelines:

### Page Highlights (`frontend/src/app/matches/page.js`)
1. **Interactive Filter Toolbar:**
   - **Score Threshold Filter:** Dropdown with `All Matches`, `50%+ Fit`, `70%+ Strong`, `85%+ Exceptional`.
   - **Career Track Switcher:** Multi-track filter pills dynamically populated from candidate's `career_interests` or profile profession.
   - **Remote Arrangement Filter:** `All`, `Remote Only`, `Hybrid`, `On-site`.
   - **Location Query Filter:** Freeform text input with instant reset button.
2. **Explainable Scoring Drawer (`Why this match?`):**
   - 4-bar progress indicator showing exact fractional points:
     - `Skills Overlap`: `[score]/40` (blue)
     - `Role Alignment`: `[score]/25` (indigo)
     - `Location & Remote`: `[score]/20` (emerald)
     - `Experience Level`: `[score]/15` (purple)
   - Evidence statements detailing exactly why points were awarded or omitted.
   - Tag badges for `Matched Skills` (green) and `Missing Skills` (slate).
   - Location eligibility summary (e.g. `Eligible (India-Only Remote)`).
   - Experience alignment summary (e.g. `Meets Requirement`).
3. **Candidate Experience Guard:**
   - When a profile lacks data, a clean informational alert provides direct deep-links to `/profile` to complete skills, years of experience, or upload a resume.
4. **ATS Provenance & Actions:**
   - Bookmark toggle calling `PUT /api/v1/saved-jobs/{job_id}`.
   - Direct ATS application button tracking visited job telemetry (`/api/v1/jobs/{id}/visit`).

---

## 6. Test Execution & Coverage Report

The dedicated P2B test suite `backend/tests/test_p2b_personalized_matching.py` was executed alongside the complete backend test suite.

### P2B Test Results (`test_p2b_personalized_matching.py`)

| Test Name | Focus Area | Status |
| :--- | :--- | :---: |
| `test_blank_profile_zero_score_and_insufficient_data` | Blank candidate yields 0.0% and insufficient data state | **PASSED** |
| `test_unrelated_job_zero_score_corporate_counsel_for_python_dev` | Unrelated job yields 0.0% with zero artificial baselines | **PASSED** |
| `test_strong_match_python_fastapi_backend` | Perfect fit earns $\ge 85\%$ with all 4 dimensions satisfied | **PASSED** |
| `test_partial_match_half_skills` | Proportional skills scoring ($2/4 = 20.0$ pts) | **PASSED** |
| `test_location_mismatch_onsite_different_countries` | Onsite in different country awards 0 geo pts | **PASSED** |
| `test_remote_eligibility_worldwide_vs_india_only` | Worldwide vs India-only vs US-restricted remote | **PASSED** |
| `test_experience_alignment_thresholds` | Meets (15 pts), Within Reach (8 pts), Below (0 pts) | **PASSED** |
| `test_unauthenticated_user_suppression_on_jobs_search` | Unauthenticated requests receive `match_score=None` | **PASSED** |
| `test_authenticated_candidate_isolation` | Candidate B never sees or leaks Candidate A's matches | **PASSED** |
| `test_recommendations_filtering_and_pagination` | `min_score`, `profession`, `remote_type`, `limit`, `offset` | **PASSED** |
| `test_saved_job_state_reflected_in_recommendations` | Saved jobs mark `is_saved=True` on recommendation items | **PASSED** |

**P2B Test Suite Duration:** 0.93 seconds (11 passed, 0 failed).

### Full Backend Test Suite Execution
```
============================= test session starts =============================
platform win32 -- Python 3.10.11, pytest-9.1.1, pluggy-1.7.0
118 passed, 1 warning in 18.98s
```
**Overall Backend Suite:** **118 passed, 0 failed.**

### Frontend Linting
```bash
npm --prefix frontend run lint
# Exit code: 0 (0 errors)
```

---

## 7. Security & Candidate Privacy Audit

1. **Authentication Enforcement:** Unauthenticated users accessing `/matches` or `/recommendations` are redirected to `/login?redirect=/matches`.
2. **Candidate Isolation:** The recommendations query directly isolates the authenticated candidate via `current_user.id`. SQL queries join `SavedJob.user_id == current_user.id` and `Profile.user_id == current_user.id`. There is zero cross-tenant contamination.
3. **Public Search Shielding:** Calling `JobService.search_jobs` without an authenticated session (`current_user=None`) strictly suppresses match calculations, preventing inadvertent profile leaking or unauthorized compute usage.
4. **Cryptographic Protection:** JWT tokens, bcrypt hashed passwords, and environment security remain protected.

---

## 8. Database & Production Health Status

Inspection executed against the live PostgreSQL database:
- **Total Ingested Jobs:** **3,691**
- **Active Jobs:** **2,999**
- **Active ATS Sources:** **15** (Stripe, Airbnb, Coinbase, Figma, GitHub, Databricks, Cloudflare, Razorpay, Swiggy, Zomato, CRED, Groww, Zerodha, etc.)
- **Source Health:** **15 / 15 HEALTHY (100%)**
- **Database Deletions / Overwrites:** **0** (strictly non-destructive)
- **Data Integrity:** All ATS provenance links, company associations, and candidate records preserved.

---

## 9. Verification Checklist & Conformance

- [x] **Frozen Architecture Maintained:** Next.js 14 App Router, JavaScript only (`.js`, `.jsx`), FastAPI, PostgreSQL. No TypeScript introduced.
- [x] **No Paid Dependencies:** Local Python matching algorithm, no OpenAI/Claude/external LLM calls.
- [x] **P1 Neutral Fallback Fixed:** Corporate Counsel scores 0.0% for Python developers. Blank profiles score 0.0%.
- [x] **Explainable Matching Implemented:** 4 dimensions (Skills 40, Role 25, Location 20, Experience 15) with itemized reasons list and matched/missing skills badges.
- [x] **Dedicated My Matches Experience:** `/matches` and `/recommendations` updated with score filters, track pills, and drawer breakdowns.
- [x] **Search Consistency:** Unauthenticated requests have scores suppressed; authenticated job cards display uniform semantic badges.
- [x] **Comprehensive Testing:** 11 new tests in `test_p2b_personalized_matching.py`; all 118 backend tests passing; frontend linting passing.

---
*Report generated and validated autonomously by Antigravity on November 16, 2026.*
