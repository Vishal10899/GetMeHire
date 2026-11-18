import re
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.api.deps import get_db, get_current_user
from app.models import User, Profile, Job, Company, ResumeVersion
from app.schemas.resume_studio import (
    ResumeContentSchema,
    ResumeAnalysisResponse,
    TailorResumeRequest,
    TailorResumeResponse,
    ImproveBulletRequest,
    ImproveBulletResponse,
    ImproveSummaryRequest,
    ImproveSummaryResponse,
    SaveResumeVersionRequest,
    ResumeVersionResponse,
    JDMatchRequest,
    JDMatchResponse,
    RoleTemplateItem,
    RoleTemplatesResponse,
)
from app.services.profile_service import ProfileService
from app.services.resume_analyzer import ResumeAnalyzerService
from app.services.resume_improver import ResumeImproverService
from app.services.resume_tailor import ResumeTailorService
from app.services.resume_exporter import ResumeExporterService
from app.services.jd_matching_service import JDMatchingService
from app.services.resume_template_intelligence import (
    ROLE_TEMPLATE_REGISTRY,
    get_all_templates,
    get_template,
    detect_optimal_template_for_role,
)
from app.services.payment_service import PaymentService
from app.schemas.payment import (
    CheckoutRequest,
    CheckoutResponse,
    OrderResponse,
    EntitlementResponse,
    EntitlementCheckResponse,
)

router = APIRouter()


def _build_master_content(user: User, profile: Optional[Profile]) -> Dict[str, Any]:
    full_name = ""
    headline = ""
    phone = ""
    location = ""
    linkedin_url = ""
    portfolio_url = ""
    summary = ""
    skills = []
    work_experience = []
    education = []
    projects = []
    certifications = []

    if profile:
        full_name = profile.full_name or ""
        headline = profile.headline or ""
        phone = profile.phone_number or ""
        location = profile.current_location or ""
        linkedin_url = profile.linkedin_url or ""
        portfolio_url = profile.portfolio_url or ""
        skills = list(profile.skills or [])
        work_experience = list(profile.work_experience or [])
        education = list(profile.education or [])
        projects = list(profile.projects or [])
        cert_list = []
        for c in (profile.certifications or []):
            if isinstance(c, dict):
                name = c.get("name") or c.get("title") or ""
                org = c.get("issuing_organization") or c.get("organization") or ""
                if name and org:
                    cert_list.append(f"{name} ({org})")
                elif name:
                    cert_list.append(name)
                elif org:
                    cert_list.append(org)
                else:
                    cert_list.append(str(c))
            elif isinstance(c, str):
                cert_list.append(c)
            else:
                cert_list.append(str(c))
        certifications = cert_list

        # Check extracted_resume_data for fallback summary or details
        extracted = profile.extracted_resume_data or {}
        summary = extracted.get("summary") or headline or ""
        if not skills and extracted.get("skills"):
            skills = list(extracted.get("skills"))
        if not work_experience and extracted.get("work_experience"):
            work_experience = list(extracted.get("work_experience"))
        if not education and extracted.get("education"):
            education = list(extracted.get("education"))

    if not full_name and user.email:
        full_name = user.email.split("@")[0].replace(".", " ").title()

    return {
        "full_name": full_name,
        "headline": headline,
        "email": user.email,
        "phone": phone,
        "location": location,
        "linkedin_url": linkedin_url,
        "portfolio_url": portfolio_url,
        "summary": summary,
        "skills": skills,
        "technical_skills": skills,
        "tools_technologies": [],
        "work_experience": work_experience,
        "education": education,
        "projects": projects,
        "certifications": certifications,
    }


def _version_to_response(v: ResumeVersion, db: Session) -> ResumeVersionResponse:
    job_title = None
    company_name = None
    if v.target_job_id:
        job = db.query(Job).filter(Job.id == v.target_job_id).first()
        if job:
            job_title = job.title
            if job.company_id:
                comp = db.query(Company).filter(Company.id == job.company_id).first()
                if comp:
                    company_name = comp.canonical_name

    return ResumeVersionResponse(
        id=v.id,
        version_title=v.version_title,
        version_number=v.version_number,
        target_job_id=v.target_job_id,
        target_job_title=job_title,
        target_company_name=company_name,
        template_id=v.template_id,
        content=v.content or {},
        analysis=v.analysis,
        is_master=v.is_master,
        created_at=v.created_at,
        updated_at=v.updated_at,
    )


# ------------------------------------------------------------------------------
# 1. Master Profile Endpoints
# ------------------------------------------------------------------------------

@router.get("/master", response_model=ResumeContentSchema)
def get_master_resume(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns the user's master resume data derived from their profile.
    """
    profile = ProfileService.get_or_create_profile(db, current_user)
    data = _build_master_content(current_user, profile)
    return ResumeContentSchema(**data)


@router.post("/master", response_model=ResumeContentSchema)
def update_master_resume(
    content: ResumeContentSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Saves edited resume details back to the candidate's master profile with explicit approval.
    """
    profile = ProfileService.get_or_create_profile(db, current_user)

    if content.full_name:
        profile.full_name = content.full_name
    if content.headline:
        profile.headline = content.headline
    if content.phone:
        profile.phone_number = content.phone
    if content.location:
        profile.current_location = content.location
    if content.linkedin_url:
        profile.linkedin_url = content.linkedin_url
    if content.portfolio_url:
        profile.portfolio_url = content.portfolio_url

    if content.skills:
        profile.skills = content.skills
    if content.work_experience:
        profile.work_experience = content.work_experience
    if content.education:
        profile.education = content.education
    if content.projects:
        profile.projects = content.projects
    if content.certifications:
        profile.certifications = content.certifications

    extracted = dict(profile.extracted_resume_data or {})
    if content.summary:
        extracted["summary"] = content.summary
    extracted["skills"] = profile.skills
    extracted["work_experience"] = profile.work_experience
    extracted["education"] = profile.education
    profile.extracted_resume_data = extracted

    # Recalculate profile completion percentage
    profile.profile_completion_pct = ProfileService.calculate_completion(profile)

    db.add(profile)
    db.commit()
    db.refresh(profile)

    data = _build_master_content(current_user, profile)
    return ResumeContentSchema(**data)


# ------------------------------------------------------------------------------
# 2. Smart Resume Analysis & Improvement
# ------------------------------------------------------------------------------

@router.post("/analyze", response_model=ResumeAnalysisResponse)
def analyze_resume(
    content: Dict[str, Any],
    current_user: User = Depends(get_current_user),
):
    """
    Evaluates resume against deterministic ATS criteria across 6 categories.
    """
    return ResumeAnalyzerService.analyze_resume(content)


@router.post("/improve/bullet", response_model=ImproveBulletResponse)
def improve_bullet(
    req: ImproveBulletRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Rewrites a weak bullet point into high-impact ATS options and coaching questions.
    """
    result = ResumeImproverService.improve_bullet(
        bullet_text=req.bullet_text,
        role_title=req.role_title,
        target_keywords=req.target_keywords,
    )
    return ImproveBulletResponse(**result)


@router.post("/improve/summary", response_model=ImproveSummaryResponse)
def improve_summary(
    req: ImproveSummaryRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Generates 3 ATS summary options (executive, impact-driven, concise technical).
    """
    options = ResumeImproverService.improve_summary(
        current_summary=req.current_summary,
        target_role=req.target_role,
        years_of_experience=req.years_of_experience,
        top_skills=req.top_skills,
    )
    return ImproveSummaryResponse(options=options)


# ------------------------------------------------------------------------------
# 3. Vacancy-Specific Tailoring & Bidirectional JD Matching
# ------------------------------------------------------------------------------

@router.get("/templates", response_model=RoleTemplatesResponse)
def list_role_templates():
    """
    Returns all 16+ role-specific resume template specifications, color palettes,
    and ATS section hierarchies.
    """
    templates = get_all_templates()
    items = [RoleTemplateItem(**t) for t in templates]
    return RoleTemplatesResponse(templates=items, total=len(items))


@router.get("/templates/recommended")
def get_recommended_template(role_title: str = Query(..., description="Target job title or profession")):
    """
    Determines and returns the optimal ATS resume template for a given role title.
    """
    rec = detect_optimal_template_for_role(role_title)
    return rec


@router.post("/jd-match", response_model=JDMatchResponse)
def match_job_description(
    req: JDMatchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Performs comprehensive bidirectional matching between a Job Description
    (from GetMeHire database or custom input) and candidate resume.
    Computes skills compatibility, experience alignment, degree fit, keyword density,
    and detailed ATS parsing friction points.
    """
    return JDMatchingService.match(db=db, user=current_user, request=req)


@router.post("/tailor", response_model=TailorResumeResponse)
def tailor_resume(
    req: TailorResumeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generates a tailored resume for any vacancy in GetMeHire.
    Categorizes skills (matched, adjacent, missing) and re-ranks bullet points.
    """
    base_data = None
    if req.base_version_id:
        v = db.query(ResumeVersion).filter(
            ResumeVersion.id == req.base_version_id,
            ResumeVersion.user_id == current_user.id
        ).first()
        if not v:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Base resume version not found")
        base_data = v.content

    return ResumeTailorService.tailor_resume_for_job(
        db=db,
        user=current_user,
        job_id=req.job_id,
        base_resume_data=base_data,
        custom_instructions=req.custom_instructions,
    )


# ------------------------------------------------------------------------------
# 4. Resume Version Management (Candidate Isolation Protected)
# ------------------------------------------------------------------------------

@router.get("/versions", response_model=List[ResumeVersionResponse])
def list_resume_versions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Lists all saved resume versions for the authenticated candidate.
    """
    versions = (
        db.query(ResumeVersion)
        .filter(ResumeVersion.user_id == current_user.id)
        .order_by(desc(ResumeVersion.updated_at))
        .all()
    )
    return [_version_to_response(v, db) for v in versions]


@router.post("/versions", response_model=ResumeVersionResponse, status_code=status.HTTP_201_CREATED)
def create_resume_version(
    req: SaveResumeVersionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Saves a new tailored or custom resume version.
    """
    # Validate target_job_id if supplied
    if req.target_job_id is not None:
        job_exists = db.query(Job.id).filter(Job.id == req.target_job_id).first()
        if not job_exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Target job with ID {req.target_job_id} does not exist"
            )

    # Determine next version number
    max_ver = (
        db.query(ResumeVersion.version_number)
        .filter(ResumeVersion.user_id == current_user.id)
        .order_by(desc(ResumeVersion.version_number))
        .first()
    )
    next_ver = (max_ver[0] + 1) if max_ver and max_ver[0] else 1

    # Run analysis
    analysis_res = ResumeAnalyzerService.analyze_resume(req.content)
    analysis_dict = analysis_res.model_dump()

    new_version = ResumeVersion(
        user_id=current_user.id,
        target_job_id=req.target_job_id,
        version_title=req.version_title.strip() or f"Tailored Resume v{next_ver}",
        version_number=next_ver,
        template_id=req.template_id or "classic_single",
        content=req.content,
        analysis=analysis_dict,
        is_master=req.is_master or False,
    )

    db.add(new_version)
    db.commit()
    db.refresh(new_version)

    return _version_to_response(new_version, db)


@router.get("/versions/{version_id}", response_model=ResumeVersionResponse)
def get_resume_version(
    version_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieves a single resume version. Strictly verifies candidate ownership.
    """
    v = (
        db.query(ResumeVersion)
        .filter(ResumeVersion.id == version_id, ResumeVersion.user_id == current_user.id)
        .first()
    )
    if not v:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resume version {version_id} not found"
        )
    return _version_to_response(v, db)


@router.put("/versions/{version_id}", response_model=ResumeVersionResponse)
def update_resume_version(
    version_id: int,
    req: SaveResumeVersionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Updates an existing resume version's title, template, target job, or content.
    """
    v = (
        db.query(ResumeVersion)
        .filter(ResumeVersion.id == version_id, ResumeVersion.user_id == current_user.id)
        .first()
    )
    if not v:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resume version {version_id} not found"
        )

    v.version_title = req.version_title.strip() or v.version_title
    v.template_id = req.template_id or v.template_id
    if req.target_job_id is not None:
        job_exists = db.query(Job.id).filter(Job.id == req.target_job_id).first()
        if not job_exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Target job with ID {req.target_job_id} does not exist"
            )
        v.target_job_id = req.target_job_id
    v.content = req.content

    # Recalculate analysis
    analysis_res = ResumeAnalyzerService.analyze_resume(req.content)
    v.analysis = analysis_res.model_dump()

    db.add(v)
    db.commit()
    db.refresh(v)

    return _version_to_response(v, db)


@router.post("/versions/{version_id}/duplicate", response_model=ResumeVersionResponse, status_code=status.HTTP_201_CREATED)
def duplicate_resume_version(
    version_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Duplicates an existing resume version with an incremented version number.
    """
    orig = (
        db.query(ResumeVersion)
        .filter(ResumeVersion.id == version_id, ResumeVersion.user_id == current_user.id)
        .first()
    )
    if not orig:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resume version {version_id} not found"
        )

    max_ver = (
        db.query(ResumeVersion.version_number)
        .filter(ResumeVersion.user_id == current_user.id)
        .order_by(desc(ResumeVersion.version_number))
        .first()
    )
    next_ver = (max_ver[0] + 1) if max_ver and max_ver[0] else 1

    dup = ResumeVersion(
        user_id=current_user.id,
        target_job_id=orig.target_job_id,
        version_title=f"{orig.version_title} (Copy)",
        version_number=next_ver,
        template_id=orig.template_id,
        content=dict(orig.content or {}),
        analysis=dict(orig.analysis or {}),
        is_master=False,
    )

    db.add(dup)
    db.commit()
    db.refresh(dup)

    return _version_to_response(dup, db)


@router.delete("/versions/{version_id}")
def delete_resume_version(
    version_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Deletes a saved resume version. Never deletes the candidate's master profile.
    """
    v = (
        db.query(ResumeVersion)
        .filter(ResumeVersion.id == version_id, ResumeVersion.user_id == current_user.id)
        .first()
    )
    if not v:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resume version {version_id} not found"
        )

    db.delete(v)
    db.commit()

    return {"message": f"Resume version {version_id} deleted successfully", "id": version_id}


# ------------------------------------------------------------------------------
# 5. Premium Entitlement & Checkout Endpoints
# ------------------------------------------------------------------------------

@router.get("/entitlements", response_model=List[EntitlementResponse])
def get_user_entitlements(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns all active premium entitlements belonging to the authenticated candidate.
    """
    return PaymentService.list_user_entitlements(db, current_user.id)


@router.get("/entitlements/check", response_model=EntitlementCheckResponse)
def check_job_entitlement(
    job_id: int = Query(..., description="Target job vacancy ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Checks if the candidate is entitled to download the tailored resume for this job.
    """
    ent = PaymentService.check_user_entitlement(db, user_id=current_user.id, target_job_id=job_id)
    if ent:
        return EntitlementCheckResponse(
            is_entitled=True,
            has_entitlement=True,
            entitlement=ent,
            target_job_id=job_id,
            message="Active premium entitlement found."
        )
    return EntitlementCheckResponse(
        is_entitled=False,
        has_entitlement=False,
        entitlement=None,
        target_job_id=job_id,
        message="No active entitlement for this vacancy. Unlock required to download tailored resume."
    )


@router.post("/checkout", response_model=CheckoutResponse)
def checkout_tailored_resume(
    req: CheckoutRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Initiates and completes checkout for a job-specific tailored resume entitlement.
    Guarantees idempotency and candidate data isolation.
    """
    order, entitlement = PaymentService.complete_test_checkout(
        db=db,
        user=current_user,
        target_job_id=req.target_job_id,
        resume_version_id=req.resume_version_id,
        idempotency_key=req.idempotency_key,
    )

    return CheckoutResponse(
        order=order,
        entitlement=entitlement,
        message="Premium job-specific resume unlocked successfully.",
        is_unlocked=True
    )


# ------------------------------------------------------------------------------
# 6. Export to ATS-Friendly PDF and DOCX (Free vs Premium Entitlement Protected)
# ------------------------------------------------------------------------------

def _sanitize_filename(name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_\- ]", "", name).strip()
    return cleaned.replace(" ", "_") or "Resume"


def _verify_export_entitlement(db: Session, user_id: int, version: ResumeVersion):
    """
    Enforces Free vs Premium boundary:
    - Master resumes and generic versions (no target_job_id): 100% FREE.
    - Vacancy-specific tailored resumes: require valid server-verified entitlement.
    """
    if version.target_job_id is not None and not version.is_master:
        ent = PaymentService.check_user_entitlement(
            db, user_id=user_id, target_job_id=version.target_job_id, resume_version_id=version.id
        )
        if not ent:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Premium entitlement required to download tailored resume for this vacancy. Please unlock this job-specific resume."
            )


@router.get("/versions/{version_id}/export/pdf")
def export_version_pdf(
    version_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generates and downloads ATS-compliant PDF for a saved version.
    Free for master/generic; requires entitlement for job-tailored versions.
    """
    v = (
        db.query(ResumeVersion)
        .filter(ResumeVersion.id == version_id, ResumeVersion.user_id == current_user.id)
        .first()
    )
    if not v:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume version not found")

    _verify_export_entitlement(db, current_user.id, v)

    pdf_bytes = ResumeExporterService.generate_pdf(v.content, template_id=v.template_id)
    safe_name = _sanitize_filename(v.version_title)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}.pdf"'}
    )


@router.get("/versions/{version_id}/export/docx")
def export_version_docx(
    version_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generates and downloads ATS-compliant DOCX for a saved version.
    Free for master/generic; requires entitlement for job-tailored versions.
    """
    v = (
        db.query(ResumeVersion)
        .filter(ResumeVersion.id == version_id, ResumeVersion.user_id == current_user.id)
        .first()
    )
    if not v:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume version not found")

    _verify_export_entitlement(db, current_user.id, v)

    docx_bytes = ResumeExporterService.generate_docx(v.content, template_id=v.template_id)
    safe_name = _sanitize_filename(v.version_title)

    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}.docx"'}
    )


class DirectExportRequest(SaveResumeVersionRequest):
    pass


@router.post("/export/pdf")
def export_direct_pdf(
    req: DirectExportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generates and streams ATS-compliant PDF directly from memory without saving first.
    Free for master/generic; requires entitlement if target_job_id is specified.
    """
    if req.target_job_id is not None and not req.is_master:
        ent = PaymentService.check_user_entitlement(
            db, user_id=current_user.id, target_job_id=req.target_job_id
        )
        if not ent:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Premium entitlement required to download tailored resume for this vacancy. Please unlock this job-specific resume."
            )

    pdf_bytes = ResumeExporterService.generate_pdf(req.content, template_id=req.template_id)
    safe_name = _sanitize_filename(req.version_title)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}.pdf"'}
    )


@router.post("/export/docx")
def export_direct_docx(
    req: DirectExportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generates and streams ATS-compliant DOCX directly from memory without saving first.
    Free for master/generic; requires entitlement if target_job_id is specified.
    """
    if req.target_job_id is not None and not req.is_master:
        ent = PaymentService.check_user_entitlement(
            db, user_id=current_user.id, target_job_id=req.target_job_id
        )
        if not ent:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Premium entitlement required to download tailored resume for this vacancy. Please unlock this job-specific resume."
            )

    docx_bytes = ResumeExporterService.generate_docx(req.content, template_id=req.template_id)
    safe_name = _sanitize_filename(req.version_title)
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}.docx"'}
    )
