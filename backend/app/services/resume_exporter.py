import io
import re
from typing import Dict, Any, List, Optional
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

from app.services.resume_template_intelligence import ROLE_TEMPLATE_REGISTRY


class ResumeExporterService:
    """
    Exports structured resume documents to ATS-compliant PDF and DOCX.
    Supports all 16+ role-specific architectures and legacy ATS templates.
    Guarantees:
      - Proper text layer extraction without canvas fragmentation
      - Standard headings & readable ATS fonts
      - Single-column flow avoiding multi-column ATS parser clipping
      - Role-specific section ordering and custom professional titles
    """

    @classmethod
    def _hex_to_rgb_tuple(cls, hex_str: str) -> RGBColor:
        clean = hex_str.lstrip("#")
        if len(clean) == 6:
            r = int(clean[0:2], 16)
            g = int(clean[2:4], 16)
            b = int(clean[4:6], 16)
            return RGBColor(r, g, b)
        return RGBColor(15, 23, 42)

    @classmethod
    def generate_pdf(cls, content: Dict[str, Any], template_id: str = "classic_single") -> bytes:
        buffer = io.BytesIO()
        template_key = (template_id or "classic_single").lower()

        # Check if role-specific template is requested
        role_meta = ROLE_TEMPLATE_REGISTRY.get(template_key)

        is_compact = (template_key == "compact_technical")
        top_margin = bottom_margin = left_margin = right_margin = 36 if is_compact else 46

        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            leftMargin=left_margin,
            rightMargin=right_margin,
            topMargin=top_margin,
            bottomMargin=bottom_margin,
        )

        base_styles = getSampleStyleSheet()

        # Resolve typography & palette
        if role_meta:
            palette = role_meta.get("color_palette", {})
            font_family = palette.get("font_family", "Helvetica")
            font_bold = f"{font_family}-Bold" if font_family != "Times-Roman" else "Times-Bold"
            font_italic = f"{font_family}-Oblique" if font_family != "Times-Roman" else "Times-Italic"
            header_color = colors.HexColor(palette.get("primary", "#0f172a"))
            accent_color = colors.HexColor(palette.get("accent", "#2563eb"))
            divider_color = colors.HexColor(palette.get("divider", "#3b82f6"))
            section_order = role_meta.get("recommended_sections_order", [])
            custom_titles = role_meta.get("section_titles", {})
        elif template_key == "classic_single":
            font_family = "Times-Roman"
            font_bold = "Times-Bold"
            font_italic = "Times-Italic"
            header_color = colors.black
            accent_color = colors.HexColor("#333333")
            divider_color = colors.HexColor("#666666")
            section_order = ["summary", "technical_skills", "work_experience", "projects", "education", "certifications"]
            custom_titles = {}
        elif template_key == "modern_professional":
            font_family = "Helvetica"
            font_bold = "Helvetica-Bold"
            font_italic = "Helvetica-Oblique"
            header_color = colors.HexColor("#1e3a8a")
            accent_color = colors.HexColor("#1e293b")
            divider_color = colors.HexColor("#3b82f6")
            section_order = ["summary", "technical_skills", "work_experience", "projects", "education", "certifications"]
            custom_titles = {}
        elif template_key == "compact_technical":
            font_family = "Helvetica"
            font_bold = "Helvetica-Bold"
            font_italic = "Helvetica-Oblique"
            header_color = colors.HexColor("#0f172a")
            accent_color = colors.HexColor("#334155")
            divider_color = colors.HexColor("#94a3b8")
            section_order = ["technical_skills", "work_experience", "projects", "education", "certifications"]
            custom_titles = {}
        elif template_key == "data_analytics":
            font_family = "Helvetica"
            font_bold = "Helvetica-Bold"
            font_italic = "Helvetica-Oblique"
            header_color = colors.HexColor("#0f766e")
            accent_color = colors.HexColor("#1e293b")
            divider_color = colors.HexColor("#14b8a6")
            section_order = ["summary", "technical_skills", "work_experience", "projects", "education", "certifications"]
            custom_titles = {}
        else:  # executive_leadership or default
            font_family = "Helvetica"
            font_bold = "Helvetica-Bold"
            font_italic = "Helvetica-Oblique"
            header_color = colors.HexColor("#09090b")
            accent_color = colors.HexColor("#27272a")
            divider_color = colors.HexColor("#71717a")
            section_order = ["summary", "work_experience", "technical_skills", "projects", "education", "certifications"]
            custom_titles = {}

        # Fallback section order if empty
        if not section_order:
            section_order = ["summary", "technical_skills", "work_experience", "projects", "education", "certifications"]

        # Define custom styles
        name_style = ParagraphStyle(
            "ResumeName",
            parent=base_styles["Normal"],
            fontName=font_bold,
            fontSize=20 if not is_compact else 17,
            leading=24 if not is_compact else 20,
            textColor=header_color,
            alignment=1 if not is_compact else 0,
            spaceAfter=4,
        )

        title_style = ParagraphStyle(
            "ResumeTitle",
            parent=base_styles["Normal"],
            fontName=font_family,
            fontSize=11,
            leading=14,
            textColor=accent_color,
            alignment=1 if not is_compact else 0,
            spaceAfter=4,
        )

        contact_style = ParagraphStyle(
            "ResumeContact",
            parent=base_styles["Normal"],
            fontName=font_family,
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#475569"),
            alignment=1 if not is_compact else 0,
            spaceAfter=12 if not is_compact else 8,
        )

        section_heading_style = ParagraphStyle(
            "ResumeSectionHeading",
            parent=base_styles["Normal"],
            fontName=font_bold,
            fontSize=12,
            leading=15,
            textColor=header_color,
            spaceBefore=10 if not is_compact else 6,
            spaceAfter=3,
            keepWithNext=True,
        )

        body_style = ParagraphStyle(
            "ResumeBody",
            parent=base_styles["Normal"],
            fontName=font_family,
            fontSize=9.5 if not is_compact else 8.5,
            leading=13 if not is_compact else 11,
            textColor=colors.HexColor("#1e293b"),
            spaceAfter=4,
        )

        bold_item_style = ParagraphStyle(
            "ResumeBoldItem",
            parent=base_styles["Normal"],
            fontName=font_bold,
            fontSize=10 if not is_compact else 9,
            leading=13 if not is_compact else 11,
            textColor=colors.HexColor("#0f172a"),
            spaceAfter=2,
        )

        date_style = ParagraphStyle(
            "ResumeDate",
            parent=base_styles["Normal"],
            fontName=font_italic,
            fontSize=9 if not is_compact else 8,
            leading=12 if not is_compact else 10,
            textColor=colors.HexColor("#64748b"),
            alignment=2,
        )

        bullet_style = ParagraphStyle(
            "ResumeBullet",
            parent=base_styles["Normal"],
            fontName=font_family,
            fontSize=9 if not is_compact else 8.5,
            leading=12.5 if not is_compact else 11,
            textColor=colors.HexColor("#1e293b"),
            leftIndent=14,
            firstLineIndent=-10,
            spaceAfter=2,
        )

        story = []

        # ----------------------------------------------------------------------
        # Header: Name, Target Role, Contact
        # ----------------------------------------------------------------------
        full_name = content.get("full_name") or "Candidate Name"
        story.append(Paragraph(full_name, name_style))

        target_role = content.get("target_role") or content.get("headline")
        if target_role:
            story.append(Paragraph(target_role, title_style))

        contact_parts = []
        if content.get("email"):
            contact_parts.append(content["email"])
        if content.get("phone"):
            contact_parts.append(content["phone"])
        if content.get("location"):
            contact_parts.append(content["location"])
        if content.get("linkedin_url"):
            clean_li = content["linkedin_url"].replace("https://", "").replace("http://", "").rstrip("/")
            contact_parts.append(clean_li)
        if content.get("portfolio_url"):
            clean_pf = content["portfolio_url"].replace("https://", "").replace("http://", "").rstrip("/")
            contact_parts.append(clean_pf)

        if contact_parts:
            story.append(Paragraph(" | ".join(contact_parts), contact_style))

        def add_section_divider(title: str):
            story.append(Paragraph(title.upper(), section_heading_style))
            story.append(HRFlowable(width="100%", thickness=1, color=divider_color, spaceAfter=6, spaceBefore=1))

        # ----------------------------------------------------------------------
        # Section Renderers
        # ----------------------------------------------------------------------
        def render_summary():
            summary = content.get("summary")
            if summary and summary.strip():
                title = custom_titles.get("summary", "Professional Summary")
                add_section_divider(title)
                story.append(Paragraph(summary.strip(), body_style))
                story.append(Spacer(1, 4))

        def render_skills():
            skills = content.get("skills") or []
            tech_skills = content.get("technical_skills") or []
            tools = content.get("tools_technologies") or []
            all_skills = list(dict.fromkeys(skills + tech_skills + tools))
            if all_skills:
                title = custom_titles.get("technical_skills", custom_titles.get("skills", "Core Skills & Competencies"))
                add_section_divider(title)
                skills_text = ", ".join(all_skills)
                story.append(Paragraph(f"<b>Key Competencies:</b> {skills_text}", body_style))
                story.append(Spacer(1, 4))

        def render_experience():
            experiences = content.get("work_experience") or []
            if experiences:
                title = custom_titles.get("work_experience", "Professional Experience")
                add_section_divider(title)
                for exp in experiences:
                    company = exp.get("company") or "Employer"
                    exp_title = exp.get("title") or exp.get("role") or "Position"
                    start = exp.get("start_date") or ""
                    end = exp.get("end_date") or "Present"
                    date_str = f"{start} – {end}" if start else end

                    col_w = [380 if not is_compact else 400, 140 if not is_compact else 140]
                    header_data = [
                        [
                            Paragraph(f"<b>{exp_title}</b> — {company}", bold_item_style),
                            Paragraph(date_str, date_style),
                        ]
                    ]
                    t = Table(header_data, colWidths=col_w)
                    t.setStyle(TableStyle([
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                        ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ]))
                    story.append(t)

                    bullets = []
                    if isinstance(exp.get("bullets"), list):
                        bullets.extend([str(b).strip() for b in exp.get("bullets") if str(b).strip()])
                    if exp.get("description"):
                        bullets.extend([b.strip() for b in re.split(r"[\n•\-\*]", str(exp.get("description"))) if b.strip() and len(b.strip()) > 8])

                    for b in bullets:
                        story.append(Paragraph(f"• {b}", bullet_style))

                    story.append(Spacer(1, 5 if not is_compact else 3))

        def render_projects():
            projects = content.get("projects") or []
            if projects:
                title = custom_titles.get("projects", "Key Projects & Initiatives")
                add_section_divider(title)
                for proj in projects:
                    p_title = proj.get("title") or proj.get("name") or "Project"
                    p_desc = proj.get("description") or ""
                    techs = proj.get("technologies") or []
                    tech_str = f" [<i>{', '.join(techs)}</i>]" if techs else ""

                    story.append(Paragraph(f"<b>{p_title}</b>{tech_str}", bold_item_style))
                    if p_desc:
                        story.append(Paragraph(p_desc, bullet_style))
                    for b in proj.get("bullets") or []:
                        story.append(Paragraph(f"• {b}", bullet_style))
                    story.append(Spacer(1, 4))

        def render_education():
            education = content.get("education") or []
            if education:
                title = custom_titles.get("education", "Education")
                add_section_divider(title)
                for edu in education:
                    degree = edu.get("degree") or "Degree"
                    inst = edu.get("institution") or "Institution"
                    grad_year = edu.get("graduation_year")
                    year_str = str(grad_year) if grad_year else ""

                    edu_data = [
                        [
                            Paragraph(f"<b>{degree}</b>, {inst}", bold_item_style),
                            Paragraph(year_str, date_style),
                        ]
                    ]
                    col_widths = [400, 120]
                    t = Table(edu_data, colWidths=col_widths)
                    t.setStyle(TableStyle([
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                        ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ]))
                    story.append(t)
                    story.append(Spacer(1, 3))

        def render_certifications():
            certs = content.get("certifications") or []
            if certs:
                title = custom_titles.get("certifications", "Certifications & Credentials")
                add_section_divider(title)
                for cert in certs:
                    cert_name = cert if isinstance(cert, str) else (cert.get("name") if isinstance(cert, dict) else str(cert))
                    story.append(Paragraph(f"• {cert_name}", bullet_style))
                story.append(Spacer(1, 4))

        dispatch = {
            "summary": render_summary,
            "skills": render_skills,
            "technical_skills": render_skills,
            "work_experience": render_experience,
            "projects": render_projects,
            "education": render_education,
            "certifications": render_certifications,
        }

        # Render sections in specified template order
        rendered_keys = set()
        for sec in section_order:
            sec_clean = sec.lower().strip()
            if sec_clean in ("contact", "header"):
                continue
            if sec_clean in dispatch and sec_clean not in rendered_keys:
                dispatch[sec_clean]()
                rendered_keys.add(sec_clean)
                if sec_clean in ("skills", "technical_skills"):
                    rendered_keys.add("skills")
                    rendered_keys.add("technical_skills")

        # Fallback render any remaining non-empty sections not in order
        for sec_clean, fn in dispatch.items():
            if sec_clean not in rendered_keys:
                fn()
                rendered_keys.add(sec_clean)

        doc.build(story)
        return buffer.getvalue()

    @classmethod
    def generate_docx(cls, content: Dict[str, Any], template_id: str = "classic_single") -> bytes:
        doc = docx.Document()
        template_key = (template_id or "classic_single").lower()

        role_meta = ROLE_TEMPLATE_REGISTRY.get(template_key)
        custom_titles = role_meta.get("section_titles", {}) if role_meta else {}
        section_order = role_meta.get("recommended_sections_order", []) if role_meta else []

        if not section_order:
            section_order = ["summary", "technical_skills", "work_experience", "projects", "education", "certifications"]

        palette = role_meta.get("color_palette", {}) if role_meta else {}
        primary_rgb = cls._hex_to_rgb_tuple(palette.get("primary", "#0f172a"))
        accent_rgb = cls._hex_to_rgb_tuple(palette.get("accent", "#2563eb"))

        # Set 0.75 in margins
        for section in doc.sections:
            section.top_margin = Inches(0.75)
            section.bottom_margin = Inches(0.75)
            section.left_margin = Inches(0.75)
            section.right_margin = Inches(0.75)

        full_name = content.get("full_name") or "Candidate Name"
        title_p = doc.add_paragraph()
        title_p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        title_p.paragraph_format.space_after = Pt(2)
        run_name = title_p.add_run(full_name)
        run_name.bold = True
        run_name.font.size = Pt(20)
        run_name.font.color.rgb = primary_rgb
        run_name.font.name = "Calibri"

        target_role = content.get("target_role") or content.get("headline")
        if target_role:
            sub_p = doc.add_paragraph()
            sub_p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
            sub_p.paragraph_format.space_after = Pt(4)
            r_sub = sub_p.add_run(target_role)
            r_sub.font.size = Pt(11)
            r_sub.font.color.rgb = accent_rgb
            r_sub.font.name = "Calibri"

        contact_parts = []
        if content.get("email"):
            contact_parts.append(content["email"])
        if content.get("phone"):
            contact_parts.append(content["phone"])
        if content.get("location"):
            contact_parts.append(content["location"])
        if content.get("linkedin_url"):
            contact_parts.append(content["linkedin_url"].replace("https://", ""))
        if content.get("portfolio_url"):
            contact_parts.append(content["portfolio_url"].replace("https://", ""))

        if contact_parts:
            cnt_p = doc.add_paragraph()
            cnt_p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
            cnt_p.paragraph_format.space_after = Pt(14)
            r_cnt = cnt_p.add_run(" | ".join(contact_parts))
            r_cnt.font.size = Pt(9.5)
            r_cnt.font.color.rgb = RGBColor(100, 116, 139)
            r_cnt.font.name = "Calibri"

        def add_heading(title: str):
            h = doc.add_heading(title, level=1)
            h.paragraph_format.space_before = Pt(10)
            h.paragraph_format.space_after = Pt(4)
            for r in h.runs:
                r.font.name = "Calibri"
                r.font.size = Pt(12)
                r.bold = True
                r.font.color.rgb = primary_rgb

        # Renderers for DOCX
        def docx_render_summary():
            summary = content.get("summary")
            if summary and summary.strip():
                title = custom_titles.get("summary", "Professional Summary")
                add_heading(title)
                p = doc.add_paragraph(summary.strip())
                p.paragraph_format.space_after = Pt(6)
                for r in p.runs:
                    r.font.name = "Calibri"
                    r.font.size = Pt(10)

        def docx_render_skills():
            skills = content.get("skills") or []
            tech_skills = content.get("technical_skills") or []
            all_skills = list(dict.fromkeys(skills + tech_skills))
            if all_skills:
                title = custom_titles.get("technical_skills", custom_titles.get("skills", "Core Skills & Competencies"))
                add_heading(title)
                p = doc.add_paragraph()
                p.paragraph_format.space_after = Pt(6)
                r_lbl = p.add_run("Key Competencies: ")
                r_lbl.bold = True
                r_lbl.font.name = "Calibri"
                r_lbl.font.size = Pt(10)
                r_val = p.add_run(", ".join(all_skills))
                r_val.font.name = "Calibri"
                r_val.font.size = Pt(10)

        def docx_render_experience():
            experiences = content.get("work_experience") or []
            if experiences:
                title = custom_titles.get("work_experience", "Professional Experience")
                add_heading(title)
                for exp in experiences:
                    comp = exp.get("company") or "Employer"
                    exp_title = exp.get("title") or exp.get("role") or "Position"
                    start = exp.get("start_date") or ""
                    end = exp.get("end_date") or "Present"
                    date_str = f"{start} – {end}" if start else end

                    p_job = doc.add_paragraph()
                    p_job.paragraph_format.space_before = Pt(4)
                    p_job.paragraph_format.space_after = Pt(2)
                    r1 = p_job.add_run(exp_title)
                    r1.bold = True
                    r1.font.size = Pt(10.5)
                    r1.font.name = "Calibri"

                    r2 = p_job.add_run(f" | {comp} ({date_str})")
                    r2.font.italic = True
                    r2.font.size = Pt(9.5)
                    r2.font.color.rgb = RGBColor(71, 85, 105)
                    r2.font.name = "Calibri"

                    bullets = []
                    if isinstance(exp.get("bullets"), list):
                        bullets.extend([str(b).strip() for b in exp.get("bullets") if str(b).strip()])
                    if exp.get("description"):
                        bullets.extend([b.strip() for b in re.split(r"[\n•\-\*]", str(exp.get("description"))) if b.strip() and len(b.strip()) > 8])

                    for b in bullets:
                        bp = doc.add_paragraph(style="List Bullet")
                        bp.paragraph_format.space_after = Pt(2)
                        r_b = bp.add_run(b)
                        r_b.font.size = Pt(9.5)
                        r_b.font.name = "Calibri"

        def docx_render_projects():
            projects = content.get("projects") or []
            if projects:
                title = custom_titles.get("projects", "Key Projects & Initiatives")
                add_heading(title)
                for proj in projects:
                    p_title = proj.get("title") or proj.get("name") or "Project"
                    p_desc = proj.get("description") or ""
                    pp = doc.add_paragraph()
                    pp.paragraph_format.space_after = Pt(2)
                    r_pt = pp.add_run(p_title)
                    r_pt.bold = True
                    r_pt.font.size = Pt(10)
                    r_pt.font.name = "Calibri"

                    if p_desc:
                        bp = doc.add_paragraph(style="List Bullet")
                        bp.paragraph_format.space_after = Pt(2)
                        r_pd = bp.add_run(p_desc)
                        r_pd.font.size = Pt(9.5)
                        r_pd.font.name = "Calibri"

        def docx_render_education():
            education = content.get("education") or []
            if education:
                title = custom_titles.get("education", "Education")
                add_heading(title)
                for edu in education:
                    degree = edu.get("degree") or "Degree"
                    inst = edu.get("institution") or "Institution"
                    yr = str(edu.get("graduation_year") or "")
                    p_edu = doc.add_paragraph()
                    p_edu.paragraph_format.space_after = Pt(2)
                    r_deg = p_edu.add_run(f"{degree}, {inst}")
                    r_deg.bold = True
                    r_deg.font.size = Pt(10)
                    r_deg.font.name = "Calibri"
                    if yr:
                        r_yr = p_edu.add_run(f" ({yr})")
                        r_yr.font.italic = True
                        r_yr.font.size = Pt(9.5)
                        r_yr.font.name = "Calibri"

        def docx_render_certifications():
            certs = content.get("certifications") or []
            if certs:
                title = custom_titles.get("certifications", "Certifications & Credentials")
                add_heading(title)
                for cert in certs:
                    cert_name = cert if isinstance(cert, str) else (cert.get("name") if isinstance(cert, dict) else str(cert))
                    p_cert = doc.add_paragraph(style="List Bullet")
                    p_cert.paragraph_format.space_after = Pt(2)
                    rc = p_cert.add_run(cert_name)
                    rc.font.size = Pt(9.5)
                    rc.font.name = "Calibri"

        docx_dispatch = {
            "summary": docx_render_summary,
            "skills": docx_render_skills,
            "technical_skills": docx_render_skills,
            "work_experience": docx_render_experience,
            "projects": docx_render_projects,
            "education": docx_render_education,
            "certifications": docx_render_certifications,
        }

        rendered = set()
        for sec in section_order:
            sec_clean = sec.lower().strip()
            if sec_clean in ("contact", "header"):
                continue
            if sec_clean in docx_dispatch and sec_clean not in rendered:
                docx_dispatch[sec_clean]()
                rendered.add(sec_clean)
                if sec_clean in ("skills", "technical_skills"):
                    rendered.add("skills")
                    rendered.add("technical_skills")

        for sec_clean, fn in docx_dispatch.items():
            if sec_clean not in rendered:
                fn()
                rendered.add(sec_clean)

        buffer = io.BytesIO()
        doc.save(buffer)
        return buffer.getvalue()
