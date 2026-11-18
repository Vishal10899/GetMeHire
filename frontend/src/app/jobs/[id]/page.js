"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  Building2,
  MapPin,
  DollarSign,
  Briefcase,
  Bookmark,
  ExternalLink,
  Clock,
  ArrowLeft,
  ShieldCheck,
  CheckCircle2,
  Share2,
  Loader2,
  AlertCircle,
  Sparkles,
  ChevronRight,
} from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/authContext";
import { sanitizeHtml } from "@/lib/sanitize";
import { motion } from "motion/react";
import JobCard, { formatLocation } from "@/components/JobCard";
import CompanyAvatar from "@/components/CompanyAvatar";
import AnimatedDialog from "@/components/animations/AnimatedDialog";

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

export default function JobDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { user } = useAuth();

  const [job, setJob] = useState(null);
  const [similar, setSimilar] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isSaved, setIsSaved] = useState(false);
  const [saving, setSaving] = useState(false);
  const [copied, setCopied] = useState(false);
  const [applying, setApplying] = useState(false);
  const [closedModalOpen, setClosedModalOpen] = useState(false);
  const [linkError, setLinkError] = useState(null);

  const handleApplyClick = async (allowClosed = false) => {
    if (!job) return;
    if (job.status === "CLOSED" && !allowClosed) {
      setClosedModalOpen(true);
      return;
    }
    setApplying(true);
    setLinkError(null);
    try {
      const resp = await api.applyToJob(job.id, allowClosed);
      if (resp?.application_url) {
        window.open(resp.application_url, "_blank", "noopener,noreferrer");
        setClosedModalOpen(false);
      }
    } catch (err) {
      const msg = err.message || "";
      if (msg.includes("closed") || msg.includes("410") || job.status === "CLOSED") {
        setClosedModalOpen(true);
      } else {
        setLinkError(msg || "Unable to proceed to employer application link safely.");
      }
    } finally {
      setApplying(false);
    }
  };

  const handleShare = () => {
    if (typeof window !== "undefined") {
      navigator.clipboard.writeText(window.location.href);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  useEffect(() => {
    if (!params?.id) return;
    setLoading(true);
    Promise.all([api.getJob(params.id), api.getSimilarJobs(params.id)])
      .then(([jobData, similarData]) => {
        setJob(jobData);
        setIsSaved(jobData.is_saved || false);
        setSimilar(similarData.jobs || []);
        if (typeof document !== "undefined" && jobData) {
          const comp = jobData.company?.canonical_name || jobData.company_name;
          const role = jobData.normalized_title || jobData.title;
          document.title = `${role} at ${comp} | GetMeHire`;
        }
      })
      .catch((err) => {
        setError(err.message || "Failed to load job listing");
      })
      .finally(() => {
        setLoading(false);
      });
  }, [params?.id]);

  const handleSaveToggle = async () => {
    if (!user) {
      router.push("/login");
      return;
    }
    setSaving(true);
    try {
      if (isSaved) {
        await api.unsaveJob(job.id);
        setIsSaved(false);
      } else {
        await api.saveJob(job.id);
        setIsSaved(true);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  const formatSalary = (min, max, currency, period) => {
    if (!min && !max) return null;
    const curr = currency === "USD" ? "$" : currency === "EUR" ? "€" : currency === "GBP" ? "£" : `${currency} `;
    if (min && max) return `${curr}${Number(min).toLocaleString()} - ${curr}${Number(max).toLocaleString()} / ${period.toLowerCase()}`;
    if (min) return `From ${curr}${Number(min).toLocaleString()} / ${period.toLowerCase()}`;
    return `Up to ${curr}${Number(max).toLocaleString()} / ${period.toLowerCase()}`;
  };

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-20 flex flex-col items-center justify-center">
        <Loader2 className="w-8 h-8 text-blue-600 animate-spin mb-3" />
        <p className="text-sm font-semibold text-slate-500">Loading position details...</p>
      </div>
    );
  }

  if (error || !job) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-16">
        <div className="p-6 bg-red-50 rounded-2xl border border-red-200 text-red-800 space-y-3">
          <AlertCircle className="w-6 h-6 text-red-600" />
          <h2 className="text-lg font-bold">Listing not found or closed</h2>
          <p className="text-xs text-red-700">{error || "This job may have been closed or filled by the employer."}</p>
          <Link
            href="/jobs"
            className="inline-flex items-center space-x-1.5 px-4 py-2 rounded-xl bg-red-600 text-white text-xs font-semibold hover:bg-red-700 cursor-pointer"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Return to Discover Jobs</span>
          </Link>
        </div>
      </div>
    );
  }

  const salaryStr = formatSalary(job.salary_min, job.salary_max, job.salary_currency, job.salary_period || "YEAR");
  const profInfo = PROFESSION_CONFIG[job.profession] || { label: "General", color: "bg-slate-50 text-slate-700 border-slate-200" };

  // Parse clean system summary without the raw prefix
  const cleanSummary = job.system_summary
    ? job.system_summary.replace(/^(System-generated summary:\s*|System-Generated Summary:\s*)/i, "").trim()
    : null;

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 pb-24 sm:pb-8">
      {/* Breadcrumb Navigation & Back Button */}
      <div className="flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center space-x-1.5 text-slate-500">
          <Link href="/jobs" className="hover:text-blue-600 transition-colors font-medium">
            Jobs
          </Link>
          <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
          {job.profession && (
            <>
              <Link
                href={`/jobs?profession=${job.profession}`}
                className="hover:text-blue-600 transition-colors font-medium"
              >
                {profInfo.label}
              </Link>
              <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
            </>
          )}
          <span className="text-slate-800 font-bold truncate max-w-[200px] sm:max-w-sm">
            {job.company?.canonical_name || job.company_name}
          </span>
        </div>

        <button
          onClick={() => router.back()}
          className="inline-flex items-center space-x-1.5 font-bold text-slate-500 hover:text-slate-900 transition-colors cursor-pointer"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to results</span>
        </button>
      </div>

      {/* Main Header Card */}
      <div className="bg-white rounded-2xl border border-slate-200/90 p-6 sm:p-8 shadow-sm space-y-6">
        <div className="flex flex-col sm:flex-row items-start justify-between gap-6 pb-6 border-b border-slate-100">
          <div className="flex items-start space-x-4">
            <CompanyAvatar
              name={job.company?.canonical_name || job.company_name}
              logoUrl={job.company?.logo_url || job.company_logo}
              size="lg"
            />

            <div className="space-y-1">
              <div className="flex flex-wrap items-center gap-1.5 mb-1">
                <span className="text-sm font-bold text-slate-900">
                  {job.company?.canonical_name || job.company_name}
                </span>

                {job.profession && (
                  <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-bold border ${profInfo.color}`}>
                    {profInfo.label}
                  </span>
                )}

                <span className="text-[11px] text-slate-400 font-medium">
                  • {job.source_name ? `via ${job.source_name.replace(/_/g, " ")}` : "Direct employer post"}
                </span>

                {/* Truthful Application Link Status Badge */}
                {job.status === "CLOSED" ? (
                  <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-md text-[10px] font-bold bg-amber-50 text-amber-800 border border-amber-300">
                    <AlertCircle className="w-3 h-3 text-amber-600" />
                    <span>Position Closed</span>
                  </span>
                ) : job.application_link_status === "VERIFIED_ACCESSIBLE" ? (
                  <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-md text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                    <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                    <span>Verified Application Link</span>
                  </span>
                ) : job.application_link_status === "INACCESSIBLE" ? (
                  <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-md text-[10px] font-bold bg-rose-50 text-rose-700 border border-rose-200">
                    <AlertCircle className="w-3 h-3 text-rose-600" />
                    <span>Link Inaccessible</span>
                  </span>
                ) : job.application_link_status === "UNAVAILABLE" ? (
                  <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-md text-[10px] font-bold bg-slate-100 text-slate-700 border border-slate-300">
                    <AlertCircle className="w-3 h-3 text-slate-500" />
                    <span>Link Unavailable</span>
                  </span>
                ) : (
                  <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-md text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-200">
                    <ShieldCheck className="w-3 h-3 text-blue-600" />
                    <span>Official Employer Link</span>
                  </span>
                )}
              </div>

              <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight leading-snug">
                {job.normalized_title || job.title}
              </h1>
              {job.normalized_title && job.normalized_title !== job.title && (
                <p className="text-xs text-slate-400 font-medium">
                  Original Title: {job.title}
                </p>
              )}

              <div className="flex flex-wrap items-center gap-y-1 gap-x-3 text-xs text-slate-500 pt-1">
                <span className="flex items-center space-x-1">
                  <MapPin className="w-3.5 h-3.5 text-slate-400" />
                  <span title={job.location}>{formatLocation(job.location)}</span>
                </span>
                <span className="flex items-center space-x-1">
                  <Clock className="w-3.5 h-3.5 text-slate-400" />
                  <span>
                    {job.posting_date
                      ? `Posted ${new Date(job.posting_date).toLocaleDateString()}`
                      : `Discovered ${new Date(job.first_seen_at).toLocaleDateString()}`}
                  </span>
                </span>
              </div>
            </div>
          </div>

          {/* Action buttons (Desktop) */}
          <div className="flex flex-col items-stretch sm:items-end gap-2.5 w-full sm:w-auto shrink-0">
            <motion.button
              type="button"
              disabled={applying}
              onClick={() => handleApplyClick(false)}
              whileHover={{ scale: 1.015 }}
              whileTap={{ scale: 0.98 }}
              transition={{ duration: 0.12 }}
              className="w-full sm:w-auto px-6 py-3 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs sm:text-sm shadow-sm shadow-blue-500/20 flex items-center justify-center space-x-1.5 cursor-pointer disabled:opacity-75"
            >
              {applying ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Redirecting...</span>
                </>
              ) : (
                <>
                  <span>Apply on Employer Site</span>
                  <ExternalLink className="w-4 h-4" />
                </>
              )}
            </motion.button>

            {linkError && (
              <div className="w-full sm:max-w-xs p-2 bg-rose-50 border border-rose-200 rounded-xl text-[11px] text-rose-700 flex items-center justify-between">
                <span>{linkError}</span>
                <button type="button" onClick={() => setLinkError(null)} className="text-rose-500 font-bold ml-1 hover:text-rose-800">×</button>
              </div>
            )}

            <div className="flex items-center gap-2 w-full sm:w-auto">
              <Link
                href={`/resume-studio?jobId=${job.id}`}
                className="flex-1 sm:flex-none px-4 py-2.5 rounded-xl border border-sky-200 bg-sky-50 hover:bg-sky-100 text-sky-800 text-xs font-bold flex items-center justify-center space-x-1.5 transition-colors"
                title="Create tailored resume for this vacancy"
              >
                <Sparkles className="w-3.5 h-3.5 text-sky-600" />
                <span>Tailor Resume</span>
              </Link>

              <motion.button
                onClick={handleSaveToggle}
                disabled={saving}
                whileTap={{ scale: 0.96 }}
                transition={{ duration: 0.1 }}
                className={`flex-1 sm:flex-none px-4 py-2.5 rounded-xl border text-xs font-bold flex items-center justify-center space-x-1.5 transition-colors cursor-pointer ${
                  isSaved
                    ? "bg-amber-50 border-amber-300 text-amber-700 shadow-2xs"
                    : "border-slate-200 text-slate-700 hover:bg-slate-50 hover:border-slate-300"
                }`}
              >
                <Bookmark className={`w-3.5 h-3.5 ${isSaved ? "fill-current" : ""}`} />
                <span>{isSaved ? "Saved" : "Save Job"}</span>
              </motion.button>

              <motion.button
                onClick={handleShare}
                whileTap={{ scale: 0.96 }}
                transition={{ duration: 0.1 }}
                className="p-2.5 rounded-xl border border-slate-200 text-slate-500 hover:text-slate-800 hover:bg-slate-50 hover:border-slate-300 transition-colors cursor-pointer"
                title="Copy job listing URL"
                aria-label="Copy job listing URL"
              >
                <Share2 className="w-4 h-4" />
              </motion.button>
            </div>

            {copied && (
              <p className="text-[11px] text-emerald-600 font-semibold self-center sm:self-end animate-fade-in">
                Listing URL copied to clipboard!
              </p>
            )}
          </div>
        </div>

        {/* Badges strip: Work Arrangement, Compensation, Employment Type, Source */}
        <div className="grid grid-cols-2 sm:grid-cols-2 md:grid-cols-4 gap-3 sm:gap-4">
          <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-100">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-1">
              Work Arrangement
            </span>
            <span className="text-sm font-bold text-slate-800">
              {job.remote_type}
            </span>
          </div>

          <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-100">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-1">
              Compensation
            </span>
            <span className="text-sm font-bold text-emerald-700">
              {salaryStr || "Competitive / Unspecified"}
            </span>
          </div>

          <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-100">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-1">
              Employment Type
            </span>
            <span className="text-sm font-bold text-slate-800">
              {job.employment_type?.replace("_", " ")}
            </span>
          </div>

          <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-100">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-1">
              Source Attribution
            </span>
            <span className="text-sm font-bold text-slate-800 truncate block">
              {job.source_name || "Official Feed"}
            </span>
          </div>
        </div>
      </div>

      {/* Full Available Description (Logical Reading Order Item 4) */}
      <div className="bg-white rounded-2xl border border-slate-200/90 p-6 sm:p-8 shadow-xs space-y-4">
        <h2 className="text-base font-bold text-slate-900 pb-3 border-b border-slate-100">
          Job Description
        </h2>
        <div
          className="job-prose text-xs sm:text-sm text-slate-700 leading-relaxed"
          dangerouslySetInnerHTML={{ __html: sanitizeHtml(job.description) }}
        />
      </div>

      {/* Role Snapshot & Key Details (Logical Reading Order Item 5) */}
      {cleanSummary && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.22, ease: "easeOut" }}
          className="bg-blue-50/70 rounded-2xl border border-blue-200/80 p-5 sm:p-6 shadow-2xs flex items-start space-x-3.5"
        >
          <div className="w-9 h-9 rounded-xl bg-blue-100/90 text-blue-700 flex items-center justify-center shrink-0">
            <Sparkles className="w-5 h-5 text-blue-600" />
          </div>
          <div className="space-y-1.5 flex-1">
            <div className="flex items-center space-x-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-blue-900">
                Role Snapshot
              </h3>
              <span className="text-[10px] font-bold text-blue-700 bg-blue-100 px-2 py-0.5 rounded-full">
                System-Generated Summary
              </span>
            </div>
            <p className="text-xs sm:text-sm text-slate-700 leading-relaxed font-normal">
              {cleanSummary}
            </p>
          </div>
        </motion.div>
      )}

      {/* Skills & Available Details (Logical Reading Order Item 6) */}
      {job.skills && job.skills.length > 0 && (
        <div className="bg-white rounded-2xl border border-slate-200/90 p-6 shadow-xs space-y-3">
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400">
            Required Skills &amp; Technologies
          </h2>
          <div className="flex flex-wrap gap-2">
            {job.skills.map((skill, idx) => (
              <Link
                key={idx}
                href={`/jobs?keyword=${encodeURIComponent(skill)}`}
                className="px-3 py-1.5 rounded-xl text-xs font-semibold bg-slate-50 hover:bg-blue-50 text-slate-700 hover:text-blue-700 border border-slate-200 hover:border-blue-200 transition-colors cursor-pointer"
              >
                {skill}
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* Original Employer / Source Notice (Logical Reading Order Item 7) */}
      <div className="bg-slate-50 rounded-2xl border border-slate-200/80 p-5 flex items-start space-x-3 text-xs text-slate-600">
        <ShieldCheck className="w-5 h-5 text-blue-600 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <h4 className="font-bold text-slate-900">Official Direct Application Notice</h4>
          <p className="leading-relaxed">
            Clicking apply redirects directly to <strong>{job.company?.canonical_name || job.company_name}</strong>&apos;s verified career board at{" "}
            <code className="bg-white border border-slate-200 px-1 py-0.5 rounded text-[11px] text-slate-700 font-mono">
              {(() => {
                try {
                  return new URL(job.application_url).hostname;
                } catch (e) {
                  return "employer career portal";
                }
              })()}
            </code>
            . GetMeHire maintains direct provenance and does not submit applications on your behalf.
          </p>
        </div>
      </div>

      {/* Similar Opportunities */}
      {similar.length > 0 && (
        <div className="space-y-4 pt-4">
          <h2 className="text-base font-bold text-slate-900">
            Similar Open Positions
          </h2>
          <div className="space-y-3">
            {similar.map((sJob) => (
              <JobCard key={sJob.id} job={sJob} />
            ))}
          </div>
        </div>
      )}

      {/* Floating Bottom Apply Bar on Mobile */}
      <div className="sm:hidden fixed bottom-0 left-0 right-0 p-3 bg-white/95 backdrop-blur-md border-t border-slate-200 z-40 flex items-center gap-2 shadow-lg">
        <motion.button
          type="button"
          disabled={applying}
          onClick={() => handleApplyClick(false)}
          whileTap={{ scale: 0.98 }}
          className="flex-1 py-3 px-4 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs flex items-center justify-center space-x-1.5 shadow-sm shadow-blue-500/20 disabled:opacity-75"
        >
          {applying ? (
            <>
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
              <span>Redirecting...</span>
            </>
          ) : (
            <>
              <span>Apply on Employer Site</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </>
          )}
        </motion.button>

        <button
          onClick={handleSaveToggle}
          disabled={saving}
          className={`p-3 rounded-xl border text-xs font-bold flex items-center justify-center transition-colors ${
            isSaved
              ? "bg-amber-50 border-amber-300 text-amber-700"
              : "border-slate-200 text-slate-700 bg-white"
          }`}
          aria-label={isSaved ? "Saved job" : "Save job"}
        >
          <Bookmark className={`w-4 h-4 ${isSaved ? "fill-current" : ""}`} />
        </button>
      </div>

      {/* Closed Job Confirmation Dialog */}
      <AnimatedDialog
        isOpen={closedModalOpen}
        onClose={() => setClosedModalOpen(false)}
      >
        <div className="space-y-4">
          <div className="flex items-start space-x-3">
            <div className="w-10 h-10 rounded-xl bg-amber-100 text-amber-700 flex items-center justify-center shrink-0">
              <AlertCircle className="w-5 h-5 text-amber-600" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900">Position Marked Closed</h3>
              <p className="text-xs text-slate-500 mt-1">
                This position at <strong>{job.company?.canonical_name || job.company_name}</strong> was marked as closed or filled by the employer.
              </p>
            </div>
          </div>

          <div className="p-3 bg-amber-50 rounded-xl border border-amber-200 text-xs text-amber-800 leading-relaxed">
            Employer application links for closed positions may lead to expired listings, corporate career portals, or 404 pages. You can still inspect this historical posting or proceed to the archived employer link.
          </div>

          <div className="flex items-center justify-end space-x-2.5 pt-2">
            <button
              type="button"
              onClick={() => setClosedModalOpen(false)}
              className="px-4 py-2 rounded-xl border border-slate-200 text-xs font-semibold text-slate-700 hover:bg-slate-50 cursor-pointer"
            >
              Stay on Page
            </button>
            <button
              type="button"
              disabled={applying}
              onClick={() => handleApplyClick(true)}
              className="px-4 py-2 rounded-xl bg-blue-600 text-xs font-bold text-white hover:bg-blue-700 flex items-center space-x-1.5 cursor-pointer shadow-xs disabled:opacity-75"
            >
              {applying ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Redirecting...</span>
                </>
              ) : (
                <>
                  <span>Proceed to Employer Archive</span>
                  <ExternalLink className="w-3.5 h-3.5" />
                </>
              )}
            </button>
          </div>
        </div>
      </AnimatedDialog>
    </div>
  );
}
