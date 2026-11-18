"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  MapPin,
  DollarSign,
  Bookmark,
  ExternalLink,
  Clock,
  Sparkles,
} from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/authContext";
import { motion } from "motion/react";
import CompanyAvatar from "@/components/CompanyAvatar";

const PROFESSION_CONFIG = {
  CUSTOMER_SUPPORT: { label: "Customer Support", color: "bg-sky-50 text-sky-700 border-sky-200" },
  ENGINEERING: { label: "Software & IT", color: "bg-blue-50 text-blue-700 border-blue-200" },
  SOFTWARE_IT: { label: "Software & IT", color: "bg-blue-50 text-blue-700 border-blue-200" },
  HEALTHCARE_MEDICAL: { label: "Healthcare", color: "bg-rose-50 text-rose-700 border-rose-200" },
  SALES_BIZDEV: { label: "Sales & BD", color: "bg-emerald-50 text-emerald-700 border-emerald-200" },
  MARKETING_GROWTH: { label: "Marketing", color: "bg-orange-50 text-orange-700 border-orange-200" },
  FINANCE_ACCOUNTING: { label: "Finance & Banking", color: "bg-teal-50 text-teal-700 border-teal-200" },
  FINANCE_LEGAL: { label: "Finance & Legal", color: "bg-teal-50 text-teal-700 border-teal-200" },
  DATA_AI: { label: "Data & AI", color: "bg-indigo-50 text-indigo-700 border-indigo-200" },
  HR_RECRUITMENT: { label: "HR & Talent", color: "bg-violet-50 text-violet-700 border-violet-200" },
  OPERATIONS_LOGISTICS: { label: "Operations", color: "bg-amber-50 text-amber-700 border-amber-200" },
  OPERATIONS_PEOPLE: { label: "Operations & HR", color: "bg-amber-50 text-amber-700 border-amber-200" },
  EDUCATION_TRAINING: { label: "Education", color: "bg-yellow-50 text-yellow-800 border-yellow-200" },
  MANUFACTURING_TRADES: { label: "Trades & Mfg", color: "bg-stone-50 text-stone-700 border-stone-200" },
  HOSPITALITY_RETAIL: { label: "Hospitality & Retail", color: "bg-lime-50 text-lime-800 border-lime-200" },
  LEGAL_ADMIN: { label: "Legal & Admin", color: "bg-purple-50 text-purple-700 border-purple-200" },
  PRODUCT_DESIGN: { label: "Product & Design", color: "bg-fuchsia-50 text-fuchsia-700 border-fuchsia-200" },
};

/**
 * Format long or pipe-separated location lists cleanly.
 * e.g. "San Francisco, CA | New York, NY | London" -> "San Francisco, CA (+2 locations)"
 */
export function formatLocation(loc) {
  if (!loc || typeof loc !== "string") return "Location flexible";
  const trimmed = loc.trim();
  if (trimmed.includes("|")) {
    const parts = trimmed.split("|").map((p) => p.trim()).filter(Boolean);
    if (parts.length > 2) {
      return `${parts[0]} (+${parts.length - 1} locations)`;
    }
    return parts.join(", ");
  }
  if (trimmed.includes(";")) {
    const parts = trimmed.split(";").map((p) => p.trim()).filter(Boolean);
    if (parts.length > 2) {
      return `${parts[0]} (+${parts.length - 1} locations)`;
    }
    return parts.join(", ");
  }
  return trimmed;
}

function formatEmploymentType(emp) {
  if (!emp) return null;
  const clean = emp.replace(/_/g, " ").toLowerCase();
  return clean.charAt(0).toUpperCase() + clean.slice(1);
}

function formatWorkArrangement(arr) {
  if (!arr) return null;
  const upper = arr.toUpperCase();
  if (upper === "REMOTE") return "Remote";
  if (upper === "HYBRID") return "Hybrid";
  if (upper === "ONSITE" || upper === "ON_SITE") return "On-site";
  return arr;
}

function formatExperienceLevel(exp) {
  if (!exp) return null;
  const upper = exp.toUpperCase();
  if (upper === "ENTRY" || upper === "ENTRY_LEVEL") return "Entry Level";
  if (upper === "MID" || upper === "MID_LEVEL") return "Mid Level";
  if (upper === "SENIOR") return "Senior";
  if (upper === "LEAD") return "Lead";
  if (upper === "EXECUTIVE" || upper === "DIRECTOR") return "Executive";
  return exp;
}

function getEarlyCareerBadge(category, metadata) {
  if (!category) return null;
  const upper = category.toUpperCase();
  if (upper === "TRUE_FRESHER") {
    return {
      label: "🎓 True Fresher Friendly",
      className: "bg-emerald-50 text-emerald-800 border-emerald-300 font-bold",
      title: "Zero professional experience required. Explicitly open to freshers and first-time job seekers."
    };
  }
  if (upper === "GRADUATE") {
    const batches = (metadata && metadata.eligible_graduation_years && metadata.eligible_graduation_years.length > 0)
      ? ` (${metadata.eligible_graduation_years.join("/")} Batch)`
      : "";
    return {
      label: `🎓 Graduate Program${batches}`,
      className: "bg-teal-50 text-teal-800 border-teal-300 font-bold",
      title: "Structured university graduate entry-level program with professional training."
    };
  }
  if (upper === "INTERNSHIP") {
    return {
      label: "💼 Internship",
      className: "bg-indigo-50 text-indigo-700 border-indigo-200 font-bold",
      title: "Internship or university co-op opportunity."
    };
  }
  if (upper === "APPRENTICESHIP") {
    return {
      label: "🛠 Apprenticeship",
      className: "bg-violet-50 text-violet-700 border-violet-200 font-bold",
      title: "Earn-while-you-learn structured apprenticeship."
    };
  }
  if (upper === "TRAINEE") {
    return {
      label: "🌟 Management / Graduate Trainee",
      className: "bg-amber-50 text-amber-800 border-amber-300 font-bold",
      title: "Trainee program with structured on-the-job mentorship."
    };
  }
  if (upper === "ENTRY_LEVEL" || upper === "EARLY_CAREER") {
    return {
      label: "🌱 0-1 Yrs Entry Level",
      className: "bg-blue-50 text-blue-700 border-blue-200 font-medium",
      title: "Early-career role suitable for candidates with 0 to 1 years experience."
    };
  }
  if (upper === "MISLABELLED_ENTRY_LEVEL") {
    return {
      label: "⚠️ Requires 3+ Yrs Exp",
      className: "bg-rose-50 text-rose-700 border-rose-200 font-medium",
      title: metadata?.mislabelled_warning || "Job title suggests entry-level but description requires 3+ years experience."
    };
  }
  return null;
}

export default function JobCard({
  job,
  isSelected = false,
  onSelect = null,
  onSaveToggle = null,
  showMatchScore = false,
  matchScore,
}) {
  const router = useRouter();
  const { user } = useAuth();
  const [isSaved, setIsSaved] = useState(job.is_saved || false);
  const [saving, setSaving] = useState(false);

  const handleSaveToggle = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (!user) {
      router.push("/login");
      return;
    }
    setSaving(true);
    try {
      if (isSaved) {
        await api.unsaveJob(job.id);
        setIsSaved(false);
        if (onSaveToggle) onSaveToggle(job.id, false);
      } else {
        await api.saveJob(job.id);
        setIsSaved(true);
        if (onSaveToggle) onSaveToggle(job.id, true);
      }
    } catch (err) {
      console.error("Save error:", err);
    } finally {
      setSaving(false);
    }
  };

  const handleApplyClick = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    try {
      const res = await api.applyToJob(job.id, false);
      if (res?.application_url) {
        window.open(res.application_url, "_blank", "noopener,noreferrer");
      }
    } catch (err) {
      if (job.application_url) {
        window.open(job.application_url, "_blank", "noopener,noreferrer");
      }
    }
  };

  const handleCardClick = (e) => {
    // Prevent triggering navigation when clicking on action links or buttons
    if (e.target.closest("button") || e.target.closest("a")) {
      return;
    }
    if (onSelect) {
      onSelect(job);
    } else {
      router.push(`/jobs/${job.id}`);
    }
  };

  const formatSalary = (min, max, currency, period) => {
    if (!min && !max) return null;
    const curr = currency === "USD" ? "$" : currency === "EUR" ? "€" : currency === "GBP" ? "£" : `${currency} `;
    const fmt = (val) => {
      if (val >= 1000) return `${Math.round(val / 1000)}k`;
      return Number(val).toLocaleString();
    };

    if (min && max) return `${curr}${fmt(min)} - ${curr}${fmt(max)} / ${period.toLowerCase()}`;
    if (min) return `From ${curr}${fmt(min)} / ${period.toLowerCase()}`;
    return `Up to ${curr}${fmt(max)} / ${period.toLowerCase()}`;
  };

  const salaryStr = formatSalary(job.salary_min, job.salary_max, job.salary_currency, job.salary_period || "YEAR");
  const profInfo = PROFESSION_CONFIG[job.profession] || { label: "General", color: "bg-slate-50 text-slate-700 border-slate-200" };
  const formattedLoc = formatLocation(job.location);
  const workArrangement = formatWorkArrangement(job.remote_type);
  const employmentType = formatEmploymentType(job.employment_type);
  const experienceLevel = formatExperienceLevel(job.experience_level);

  const sourceAttribution = job.source_name
    ? `via ${job.source_name.replace(/_/g, " ")}`
    : "Direct employer post";

  const earlyCareerBadge = getEarlyCareerBadge(job.early_career_category, job.early_career_metadata);

  return (
    <motion.div
      onClick={handleCardClick}
      whileHover={{ y: -2 }}
      transition={{ duration: 0.15, ease: "easeOut" }}
      className={`group relative bg-white rounded-2xl border p-4 sm:p-5 transition-shadow duration-150 cursor-pointer ${
        isSelected
          ? "border-blue-600 ring-2 ring-blue-500/15 bg-blue-50/10 shadow-xs"
          : "border-slate-200/90 hover:border-slate-300 hover:shadow-xs"
      }`}
    >
      <div className="flex items-start justify-between gap-3.5 sm:gap-4">
        {/* Company Avatar */}
        <CompanyAvatar
          name={job.company_name}
          logoUrl={job.company_logo}
          size="md"
        />

        {/* Core Job Details */}
        <div className="min-w-0 flex-1 space-y-1.5">
          {/* Company & Provenance Row */}
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <Link
              href={`/jobs?company=${encodeURIComponent(job.company_name)}`}
              onClick={(e) => {
                e.stopPropagation();
              }}
              className="text-xs font-bold text-slate-900 hover:text-blue-600 hover:underline transition-colors cursor-pointer"
              title={`View all open positions at ${job.company_name}`}
            >
              {job.company_name}
            </Link>

            {/* Profession pill */}
            <span className={`inline-flex items-center px-2 py-0.2 rounded-md text-[10px] font-bold border ${profInfo.color}`}>
              {profInfo.label}
            </span>

            {/* Early Career & Fresher Badge */}
            {earlyCareerBadge && (
              <span
                title={earlyCareerBadge.title}
                className={`inline-flex items-center px-2 py-0.5 rounded-md text-[10px] border shadow-2xs ${earlyCareerBadge.className}`}
              >
                {earlyCareerBadge.label}
              </span>
            )}

            {/* Source attribution */}
            <span className="text-[11px] text-slate-400 font-medium">
              • {sourceAttribution}
            </span>
          </div>

          {/* Job Title */}
          <Link
            href={`/jobs/${job.id}`}
            onClick={(e) => {
              if (onSelect && !e.metaKey && !e.ctrlKey) {
                e.preventDefault();
                onSelect(job);
              }
            }}
            className="block"
          >
            <h3 className="text-base sm:text-lg font-bold text-slate-900 group-hover:text-blue-600 transition-colors line-clamp-1 leading-snug">
              {job.normalized_title || job.title}
            </h3>
          </Link>

          {/* Metadata Row: Location, Arrangement, Employment, Experience, Salary */}
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5 text-xs text-slate-500 pt-0.5">
            <span className="inline-flex items-center space-x-1 shrink-0">
              <MapPin className="w-3.5 h-3.5 text-slate-400 shrink-0" />
              <span className="truncate max-w-[200px]" title={job.location}>
                {formattedLoc}
              </span>
            </span>

            {workArrangement && (
              <span
                className={`px-2 py-0.5 rounded-md text-[10px] font-bold border shrink-0 ${
                  workArrangement === "Remote"
                    ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                    : workArrangement === "Hybrid"
                    ? "bg-purple-50 text-purple-700 border-purple-200"
                    : "bg-slate-50 text-slate-700 border-slate-200"
                }`}
              >
                {workArrangement}
              </span>
            )}

            {employmentType && (
              <span className="px-2 py-0.5 rounded-md bg-slate-50 text-slate-700 border border-slate-200 text-[10px] font-semibold shrink-0">
                {employmentType}
              </span>
            )}

            {experienceLevel && (
              <span className="px-2 py-0.5 rounded-md bg-slate-50 text-slate-600 border border-slate-200 text-[10px] font-medium shrink-0">
                {experienceLevel}
              </span>
            )}

            {salaryStr && (
              <span className="inline-flex items-center space-x-0.5 font-bold text-emerald-700 text-xs shrink-0">
                <DollarSign className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                <span>{salaryStr}</span>
              </span>
            )}
          </div>
        </div>

        {/* Action Column: Save & Match Score */}
        <div className="flex flex-col items-end space-y-2 shrink-0">
          <motion.button
            onClick={handleSaveToggle}
            disabled={saving}
            whileTap={{ scale: 0.88 }}
            transition={{ duration: 0.1 }}
            className={`p-2 rounded-xl border transition-all duration-150 cursor-pointer ${
              isSaved
                ? "bg-amber-50 border-amber-300 text-amber-600 shadow-2xs"
                : "border-slate-200 text-slate-400 hover:text-slate-700 hover:bg-slate-50 hover:border-slate-300"
            }`}
            title={isSaved ? "Saved to bookmarks" : "Save job"}
            aria-label={isSaved ? "Saved job" : "Save job"}
          >
            <Bookmark className={`w-4 h-4 ${isSaved ? "fill-current" : ""}`} />
          </motion.button>

          {showMatchScore && matchScore !== undefined && matchScore !== null && (
            <div
              className={`flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold shadow-2xs ${
                matchScore >= 80
                  ? "bg-emerald-50 border border-emerald-300 text-emerald-800"
                  : matchScore >= 60
                  ? "bg-blue-50 border border-blue-200 text-blue-800"
                  : matchScore >= 40
                  ? "bg-amber-50 border border-amber-200 text-amber-800"
                  : "bg-slate-100 border border-slate-200 text-slate-700"
              }`}
            >
              <Sparkles
                className={`w-3 h-3 ${
                  matchScore >= 80
                    ? "text-emerald-600"
                    : matchScore >= 60
                    ? "text-blue-600"
                    : matchScore >= 40
                    ? "text-amber-600"
                    : "text-slate-500"
                }`}
              />
              <span>{matchScore}% Match</span>
            </div>
          )}
        </div>
      </div>

      {/* Relevant Skills Preview */}
      {job.skills && job.skills.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5 mt-3 pt-2.5 border-t border-slate-100">
          {job.skills.slice(0, 3).map((skill, idx) => (
            <span
              key={idx}
              className="px-2 py-0.5 rounded-md text-[11px] font-medium bg-slate-50 text-slate-600 border border-slate-200/80"
            >
              {skill}
            </span>
          ))}
          {job.skills.length > 3 && (
            <span className="text-[10px] text-slate-400 font-semibold">
              +{job.skills.length - 3} more
            </span>
          )}
        </div>
      )}

      {/* Footer Info: Freshness timestamp and Direct application link */}
      <div className="flex items-center justify-between mt-3 pt-2 text-[11px] text-slate-400 border-t border-slate-100">
        <span className="flex items-center space-x-1">
          <Clock className="w-3 h-3 text-slate-400" />
          <span>
            {job.posting_date
              ? `Posted ${new Date(job.posting_date).toLocaleDateString()}`
              : `Discovered ${new Date(job.first_seen_at).toLocaleDateString()}`}
          </span>
        </span>

        <a
          href={job.application_url}
          target="_blank"
          rel="noopener noreferrer"
          onClick={handleApplyClick}
          className="inline-flex items-center space-x-1 font-bold text-blue-600 hover:text-blue-800 transition-colors cursor-pointer"
        >
          <span className="truncate max-w-[150px] sm:max-w-none">
            {job.company_name ? `Apply on ${job.company_name}` : "Apply on Employer Site"}
          </span>
          <ExternalLink className="w-3 h-3 shrink-0" />
        </a>
      </div>
    </motion.div>
  );
}
