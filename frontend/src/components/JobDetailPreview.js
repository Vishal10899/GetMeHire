"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Building2,
  MapPin,
  Clock,
  DollarSign,
  Bookmark,
  ExternalLink,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  Briefcase,
  Share2,
  Sparkles,
  Maximize2,
  Loader2,
  Lock,
} from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/authContext";
import { sanitizeHtml } from "@/lib/sanitize";
import CompanyAvatar from "@/components/CompanyAvatar";
import { formatLocation } from "@/components/JobCard";

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

export default function JobDetailPreview({ jobSummary, onSaveChange = null }) {
  const router = useRouter();
  const { user } = useAuth();
  const [jobDetail, setJobDetail] = useState(null);
  const [loading, setLoading] = useState(false);
  const [isSaved, setIsSaved] = useState(false);
  const [saving, setSaving] = useState(false);
  const [copied, setCopied] = useState(false);
  const [saveNotice, setSaveNotice] = useState(null);

  useEffect(() => {
    if (!jobSummary?.id) return;
    setIsSaved(jobSummary.is_saved || false);
    loadFullDetail(jobSummary.id);
  }, [jobSummary?.id]);

  const loadFullDetail = async (id) => {
    setLoading(true);
    try {
      const data = await api.getJob(id);
      setJobDetail(data);
      if (data.is_saved !== undefined) {
        setIsSaved(data.is_saved);
      }
    } catch (err) {
      console.error("Failed to load detail preview:", err);
      setJobDetail(jobSummary);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveToggle = async () => {
    if (!user) {
      router.push("/login");
      return;
    }
    const targetId = jobDetail?.id || jobSummary?.id;
    if (!targetId) return;

    setSaving(true);
    setSaveNotice(null);
    try {
      if (isSaved) {
        await api.unsaveJob(targetId);
        setIsSaved(false);
        setSaveNotice("Job removed from saved listings");
        if (onSaveChange) onSaveChange(targetId, false);
      } else {
        await api.saveJob(targetId);
        setIsSaved(true);
        setSaveNotice("Job saved to your profile");
        if (onSaveChange) onSaveChange(targetId, true);
      }
      setTimeout(() => setSaveNotice(null), 3000);
    } catch (err) {
      console.error(err);
      setSaveNotice("Failed to update saved job");
    } finally {
      setSaving(false);
    }
  };

  const handleShare = () => {
    if (typeof window !== "undefined") {
      const url = `${window.location.origin}/jobs/${jobSummary.id}`;
      navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleApplyClick = async (e) => {
    e.preventDefault();
    const targetJob = jobDetail || jobSummary;
    if (!targetJob) return;
    try {
      const res = await api.applyToJob(targetJob.id, false);
      if (res?.application_url) {
        window.open(res.application_url, "_blank", "noopener,noreferrer");
      }
    } catch (err) {
      if (targetJob.application_url) {
        window.open(targetJob.application_url, "_blank", "noopener,noreferrer");
      }
    }
  };

  const activeJob = jobDetail || jobSummary;
  if (!activeJob) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-8 text-center text-slate-400 bg-white rounded-2xl border border-slate-200/90 shadow-xs">
        <Briefcase className="w-10 h-10 mb-2 text-slate-300" />
        <p className="text-sm font-bold text-slate-700">Select a job listing to view details</p>
        <p className="text-xs text-slate-400 mt-1 max-w-xs">
          Explore verified positions aggregated directly from official employer career boards.
        </p>
      </div>
    );
  }

  const formatSalary = (min, max, currency, period) => {
    if (!min && !max) return null;
    const curr = currency === "USD" ? "$" : currency === "EUR" ? "€" : currency === "GBP" ? "£" : `${currency} `;
    const fmt = (val) => {
      if (val >= 1000) return `${Math.round(val / 1000)}k`;
      return val.toLocaleString();
    };

    if (min && max) return `${curr}${fmt(min)} - ${curr}${fmt(max)} / ${period?.toLowerCase() || 'year'}`;
    if (min) return `From ${curr}${fmt(min)} / ${period?.toLowerCase() || 'year'}`;
    return `Up to ${curr}${fmt(max)} / ${period?.toLowerCase() || 'year'}`;
  };

  const salaryStr = formatSalary(activeJob.salary_min, activeJob.salary_max, activeJob.salary_currency, activeJob.salary_period);
  const profInfo = PROFESSION_CONFIG[activeJob.profession] || { label: "General", color: "bg-slate-50 text-slate-700 border-slate-200" };

  return (
    <div className="bg-white rounded-2xl border border-slate-200/90 shadow-sm overflow-hidden flex flex-col h-[calc(100vh-6.5rem)] sticky top-20">
      {/* Header bar */}
      <div className="p-5 sm:p-6 border-b border-slate-200/80 bg-white">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start space-x-3.5 min-w-0">
            <CompanyAvatar
              name={activeJob.company_name || activeJob.company?.canonical_name}
              logoUrl={activeJob.company_logo || activeJob.company?.logo_url}
              size="md"
            />

            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-1.5 mb-1">
                <span className="text-xs font-bold text-slate-900">
                  {activeJob.company_name || activeJob.company?.canonical_name}
                </span>

                <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-bold border ${profInfo.color}`}>
                  {profInfo.label}
                </span>

                <span className="text-[11px] text-slate-400 font-medium">
                  • {activeJob.source_name ? `via ${activeJob.source_name.replace(/_/g, " ")}` : "Direct employer post"}
                </span>
              </div>

              <h2 className="text-lg sm:text-xl font-extrabold text-slate-900 tracking-tight leading-snug">
                {activeJob.normalized_title || activeJob.title}
              </h2>
              {activeJob.normalized_title && activeJob.normalized_title !== activeJob.title && (
                <p className="text-[11px] text-slate-400 mt-0.5 font-medium truncate">
                  Original Title: {activeJob.title}
                </p>
              )}

              <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-500 mt-1.5">
                <span className="flex items-center space-x-1">
                  <MapPin className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                  <span title={activeJob.location}>{formatLocation(activeJob.location)}</span>
                </span>

                <span className="flex items-center space-x-1">
                  <Clock className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                  <span>
                    {activeJob.posting_date
                      ? `Posted ${new Date(activeJob.posting_date).toLocaleDateString()}`
                      : `Discovered ${new Date(activeJob.first_seen_at).toLocaleDateString()}`}
                  </span>
                </span>
              </div>
            </div>
          </div>

          {/* Quick link to full dedicated view */}
          <Link
            href={`/jobs/${activeJob.id}`}
            title="Open dedicated job page"
            className="p-2 rounded-xl text-slate-400 hover:text-blue-600 hover:bg-blue-50 transition-colors border border-slate-200"
          >
            <Maximize2 className="w-4 h-4" />
          </Link>
        </div>

        {/* Action Row */}
        <div className="flex flex-wrap items-center gap-2.5 mt-4 pt-4 border-t border-slate-100">
          <a
            href={activeJob.application_url}
            target="_blank"
            rel="noopener noreferrer"
            onClick={handleApplyClick}
            className="flex-1 py-2.5 px-4 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs shadow-sm shadow-blue-500/20 transition-all flex items-center justify-center space-x-1.5 cursor-pointer"
          >
            <span>Apply on Employer Site</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </a>

          <Link
            href={`/resume-studio?jobId=${activeJob.id}`}
            className="py-2.5 px-3.5 rounded-xl border border-sky-200 bg-sky-50 hover:bg-sky-100 text-sky-800 text-xs font-bold flex items-center space-x-1.5 transition-colors"
            title="Create tailored resume for this vacancy"
          >
            <Sparkles className="w-3.5 h-3.5 text-sky-600" />
            <span>Tailor Resume</span>
          </Link>

          <button
            onClick={handleSaveToggle}
            disabled={saving}
            className={`py-2.5 px-4 rounded-xl border text-xs font-bold flex items-center space-x-1.5 transition-colors ${
              isSaved
                ? "bg-amber-50 border-amber-300 text-amber-700"
                : "border-slate-200 text-slate-700 hover:bg-slate-50"
            }`}
          >
            <Bookmark className={`w-3.5 h-3.5 ${isSaved ? "fill-current" : ""}`} />
            <span>{isSaved ? "Saved" : "Save Job"}</span>
          </button>

          <button
            onClick={handleShare}
            className="p-2.5 rounded-xl border border-slate-200 text-slate-500 hover:text-slate-800 hover:bg-slate-50 transition-colors"
            title="Share job URL"
          >
            <Share2 className="w-3.5 h-3.5" />
          </button>
        </div>

        {copied && (
          <p className="text-[11px] text-emerald-600 text-center mt-1.5 font-semibold">
            Listing URL copied to clipboard!
          </p>
        )}
      </div>

      {/* Scrollable content body with smooth scrolling */}
      <div className="flex-1 overflow-y-auto p-5 sm:p-6 space-y-6">
        {/* Role Snapshot (Senior Recruiter Style) */}
        {activeJob.system_summary && (
          <div className="p-4 bg-blue-50/70 rounded-xl border border-blue-200/80 space-y-1.5 shadow-2xs">
            <div className="flex items-center space-x-2">
              <Sparkles className="w-4 h-4 text-blue-600 shrink-0" />
              <h4 className="font-bold text-xs uppercase tracking-wider text-blue-900">
                Role Snapshot
              </h4>
            </div>
            <p className="text-xs text-slate-700 leading-relaxed font-normal">
              {activeJob.system_summary.replace(/^(System-generated summary:\s*|System-Generated Summary:\s*)/i, "").trim()}
            </p>
          </div>
        )}

        {/* Meta badges strip */}
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
          <div className="p-3 bg-slate-50/80 rounded-xl border border-slate-200/80">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-0.5">
              Arrangement
            </span>
            <span className="text-xs font-bold text-slate-800">
              {activeJob.remote_type || "ONSITE"}
            </span>
          </div>

          <div className="p-3 bg-slate-50/80 rounded-xl border border-slate-200/80">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-0.5">
              Employment
            </span>
            <span className="text-xs font-bold text-slate-800">
              {activeJob.employment_type?.replace('_', ' ') || "FULL TIME"}
            </span>
          </div>

          {salaryStr ? (
            <div className="p-3 bg-emerald-50/60 rounded-xl border border-emerald-200/80 col-span-2 sm:col-span-1">
              <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-700 block mb-0.5">
                Compensation
              </span>
              <span className="text-xs font-bold text-emerald-900">
                {salaryStr}
              </span>
            </div>
          ) : (
            <div className="p-3 bg-slate-50/80 rounded-xl border border-slate-200/80">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-0.5">
                Experience
              </span>
              <span className="text-xs font-bold text-slate-800">
                {activeJob.experience_level || "Not Specified"}
              </span>
            </div>
          )}
        </div>

        {/* Required Skills */}
        {activeJob.skills && activeJob.skills.length > 0 && (
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
              Key Skills & Requirements
            </h4>
            <div className="flex flex-wrap gap-1.5">
              {activeJob.skills.map((s, i) => (
                <span
                  key={i}
                  className="px-2.5 py-1 rounded-lg text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-200/80"
                >
                  {s}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Job Description (Sanitized HTML) */}
        <div>
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
            Role Overview & Responsibilities
          </h4>
          {loading ? (
            <div className="py-8 flex justify-center text-slate-400">
              <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
            </div>
          ) : activeJob.description ? (
            <div
              className="prose prose-xs sm:prose-sm max-w-none text-slate-600 leading-relaxed space-y-3"
              dangerouslySetInnerHTML={{ __html: sanitizeHtml(activeJob.description) }}
            />
          ) : (
            <p className="text-xs text-slate-400 italic">
              Detailed employer description available on the official ATS board.
            </p>
          )}
        </div>

        {/* Application notice footer */}
        <div className="p-4 bg-slate-50 rounded-xl border border-slate-200/80 flex items-start space-x-2.5 text-xs text-slate-500">
          <ShieldCheck className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
          <p className="leading-relaxed">
            All applications are completed directly on the employer&apos;s verified careers site. Visiting the application page records an entry in your Application History for tracking purposes.
          </p>
        </div>
      </div>
    </div>
  );
}
