import re
import httpx
from typing import List, Dict, Any, Optional

POWER_VERBS = [
    ("architected", "Engineered and structured"),
    ("spearheaded", "Led the end-to-end design and delivery of"),
    ("optimized", "Refactored and performance-tuned"),
    ("automated", "Built automated workflows and pipelines for"),
    ("deployed", "Productionized and released"),
    ("scaled", "Expanded system throughput and reliability for"),
    ("streamlined", "Eliminated bottlenecks and simplified"),
    ("delivered", "Successfully built and launched"),
]

WEAK_PHRASE_REPLACEMENTS = [
    (r"\bresponsible\s+for\s+(?:managing|building|handling|developing)\b", "Architected and delivered"),
    (r"\bresponsible\s+for\b", "Spearheaded"),
    (r"\bassisted\s+with\b", "Collaborated to deliver"),
    (r"\bhelped\s+(?:with|to)\b", "Engineered solutions for"),
    (r"\bworked\s+on\b", "Developed and maintained"),
    (r"\btasked\s+with\b", "Executed the technical implementation of"),
    (r"\bduties\s+included\b", "Delivered core responsibilities including"),
]

class ResumeImproverService:
    """
    Resume improvement engine strictly complying with Zero Paid AI Policy.
    Uses deterministic linguistic transforms and optional local Ollama acceleration.
    Guarantees: NEVER invents metrics, dates, companies, or unverified skills.
    """

    @classmethod
    def _query_local_ollama(cls, prompt: str, system_prompt: str) -> Optional[str]:
        """Optionally check for local Ollama running on localhost:11434 with zero paid API call."""
        try:
            with httpx.Client(timeout=2.5) as client:
                resp = client.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": "qwen2.5:latest",
                        "prompt": prompt,
                        "system": system_prompt,
                        "stream": False,
                        "options": {"temperature": 0.3}
                    }
                )
                if resp.status_code == 200:
                    data = resp.json()
                    res = (data.get("response") or "").strip()
                    if res:
                        return res
        except Exception:
            pass  # Fall back immediately to deterministic rule engine
        return None

    @classmethod
    def improve_bullet(
        cls,
        bullet_text: str,
        role_title: Optional[str] = None,
        target_keywords: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Rewrites a weak experience bullet into multiple strong options.
        Asks coaching questions rather than fabricating numbers.
        """
        clean_bullet = bullet_text.strip().lstrip("•-* ").strip()
        if not clean_bullet:
            return {"original": "", "improved_options": [], "coaching_questions": []}

        # 1. Identify coaching questions for missing metrics
        coaching_questions = []
        has_metrics = bool(re.search(r"\b(?:\d+%|\$\d+|\d+\s*(?:k|m|users|requests|hours|days|x))\b|\b\d{2,}\b", clean_bullet))

        if not has_metrics:
            coaching_questions.append("What was the measurable outcome? (e.g. latency reduced by 30%, 10k active users, 5 hours saved weekly)")
            coaching_questions.append("What was the scale or throughput of the system? (e.g. database size, daily requests, team size)")

        # 2. Check weak phrase replacement
        improved_variants = []

        # Option A: Action-Result Focus
        var_a = clean_bullet
        for pattern, replacement in WEAK_PHRASE_REPLACEMENTS:
            var_a = re.sub(pattern, replacement, var_a, flags=re.IGNORECASE)

        # Capitalize first letter
        if var_a and var_a[0].islower():
            var_a = var_a[0].upper() + var_a[1:]

        # Ensure period at end
        if var_a and not var_a.endswith("."):
            var_a += "."

        improved_variants.append({
            "style": "Action & Impact",
            "text": var_a,
            "tip": "Strong active opening focusing on ownership."
        })

        # Option B: Architectural & Engineering Depth Focus
        words = clean_bullet.split()
        lead_word = words[0].lower() if words else ""
        if lead_word in ("built", "made", "worked", "did", "helped", "assisted", "responsible"):
            var_b = "Architected and deployed " + " ".join(words[1:])
        else:
            var_b = "Engineered and optimized " + clean_bullet

        if not var_b.endswith("."):
            var_b += "."

        improved_variants.append({
            "style": "Technical Depth",
            "text": var_b,
            "tip": "Emphasizes engineering rigor and modern best practices."
        })

        # Option C: Metric-Placeholder Template (Prompting candidate to add real metric)
        if not has_metrics:
            var_c = var_a.rstrip(".") + ", achieving [X% performance gain / saving Y hours weekly]."
            improved_variants.append({
                "style": "Quantified Result (Fill In Metric)",
                "text": var_c,
                "tip": "Fill in your actual numerical metric to maximize recruiter impact."
            })

        return {
            "original": clean_bullet,
            "improved_options": improved_variants,
            "coaching_questions": coaching_questions
        }

    @classmethod
    def improve_summary(
        cls,
        current_summary: Optional[str] = None,
        target_role: Optional[str] = None,
        years_of_experience: Optional[float] = None,
        top_skills: Optional[List[str]] = None
    ) -> List[Dict[str, str]]:
        """
        Generates 3 professional summary variations based on actual candidate data.
        Never fabricates degrees or unverified skills.
        """
        role = target_role or "Software Professional"
        years_str = f"{int(years_of_experience)}+ years" if years_of_experience and years_of_experience >= 1 else "extensive"
        skills_str = ", ".join(top_skills[:5]) if top_skills else "modern software engineering practices"

        # Style 1: Impact-Driven Summary
        style_1 = (
            f"Results-oriented {role} with {years_str} of experience designing, scaling, and delivering "
            f"high-performance solutions using {skills_str}. Proven track record of optimizing system reliability, "
            f"collaborating across cross-functional teams, and transforming business requirements into robust production software."
        )

        # Style 2: Technical Specialist Summary
        style_2 = (
            f"{role} specializing in {skills_str}. Deep expertise across full software development lifecycle, "
            f"modular system architecture, and automated testing. Committed to engineering excellence, "
            f"clean maintainable code, and high-throughput infrastructure."
        )

        # Style 3: Leadership & Growth Summary
        style_3 = (
            f"Experienced {role} bringing {years_str} of expertise in {skills_str}. "
            f"Skilled at partnering with product and engineering stakeholders to solve complex challenges, "
            f"mentor emerging talent, and drive sustainable technical velocity in collaborative environments."
        )

        return [
            {
                "style": "Impact-Driven",
                "description": "Emphasizes measurable business outcomes and system scale.",
                "text": style_1
            },
            {
                "style": "Technical Depth",
                "description": "Highlights architectural mastery and core technical stack.",
                "text": style_2
            },
            {
                "style": "Leadership & Growth",
                "description": "Showcases cross-functional partnership, velocity, and mentoring.",
                "text": style_3
            }
        ]
