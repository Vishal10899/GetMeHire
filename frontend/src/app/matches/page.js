"use client";

import { useState, useEffect, useCallback, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  Sparkles,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  Loader2,
  User,
  Layers,
  ArrowRight,
  Filter,
  MapPin,
  RotateCcw,
  ShieldCheck,
  Bookmark,
  Search,
  Briefcase,
  Globe,
  Info,
} from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/authContext";
import JobCard from "@/components/JobCard";
import { motion, AnimatePresence } from "motion/react";
import {
  accordionVariants,
  staggerListVariants,
  staggerItemVariants,
} from "@/components/animations/variants";

const SCORE_THRESHOLDS = [
  { label: "All Matches", value: "" },
  { label: "50%+ Fit", value: "50" },
  { label: "70%+ Strong", value: "70" },
  { label: "85%+ Exceptional", value: "85" },
];

const REMOTE_OPTIONS = [
  { label: "All Arrangements", value: "" },
  { label: "Remote Only", value: "REMOTE" },
  { label: "Hybrid", value: "HYBRID" },
  { label: "On-site", value: "ONSITE" },
];

function MyMatchesContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, loading: authLoading } = useAuth();

  const [matches, setMatches] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [hasSufficientData, setHasSufficientData] = useState(true);
  const [insufficientReasons, setInsufficientReasons] = useState([]);
  const [expandedBreakdown, setExpandedBreakdown] = useState({});

  // Filter states
  const [minScore, setMinScore] = useState(searchParams.get("min_score") || "");
  const [activeTrack, setActiveTrack] = useState(searchParams.get("profession") || "");
  const [remoteType, setRemoteType] = useState(searchParams.get("remote_type") || "");
  const [locationQuery, setLocationQuery] = useState(searchParams.get("location") || "");

  // Candidate Profile state
  const [profile, setProfile] = useState(null);
  const [careerTracks, setCareerTracks] = useState([]);

  useEffect(() => {
    if (!authLoading && !user) {
      router.push("/login?redirect=/matches");
    }
  }, [user, authLoading, router]);

  const loadMatches = useCallback(async () => {
    if (!user) return;
    setLoading(true);
    setError(null);
    try {
      const p = await api.getProfile().catch(() => null);
      if (p) {
        setProfile(p);
        if (p.career_interests && p.career_interests.length > 0) {
          setCareerTracks(p.career_interests);
        } else if (p.profession) {
          setCareerTracks([{ profession: p.profession }]);
        }
      }

      const params = {};
      if (minScore) params.min_score = minScore;
      if (activeTrack) params.profession = activeTrack;
      if (remoteType) params.remote_type = remoteType;
      if (locationQuery) params.location = locationQuery;
      params.limit = 30;

      const data = await api.getMatches(params);
      setMatches(data.items || []);
      setTotal(data.total || 0);
      setHasSufficientData(data.has_sufficient_data ?? true);
      setInsufficientReasons(data.insufficient_data_reasons || []);
    } catch (err) {
      console.error("Failed to load matches:", err);
      setError(err.message || "Failed to load matching jobs.");
    } finally {
      setLoading(false);
    }
  }, [user, minScore, activeTrack, remoteType, locationQuery]);

  useEffect(() => {
    if (user) {
      loadMatches();
    }
  }, [user, loadMatches]);

  const toggleBreakdown = (jobId) => {
    setExpandedBreakdown((prev) => ({
      ...prev,
      [jobId]: !prev[jobId],
    }));
  };

  const handleResetFilters = () => {
    setMinScore("");
    setActiveTrack("");
    setRemoteType("");
    setLocationQuery("");
  };

  const activeFilterCount = [
    minScore !== "",
    activeTrack !== "",
    remoteType !== "",
    locationQuery.trim() !== "",
  ].filter(Boolean).length;

  if (authLoading) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-24 flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-blue-600 animate-spin" />
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Header with Title and Profile Link */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <div className="space-y-1">
          <div className="flex items-center space-x-2.5">
            <div className="w-9 h-9 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center shrink-0">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
                My Matches
              </h1>
            </div>
          </div>
          <p className="text-xs text-slate-500">
            Ranked job opportunities evaluated against your resume skills, career track, and preferences.
          </p>
        </div>

        <div className="flex items-center space-x-2 shrink-0">
          <Link
            href="/profile"
            className="inline-flex items-center space-x-1.5 px-3.5 py-2 rounded-xl border border-slate-200 text-slate-700 text-xs font-bold hover:bg-slate-50 hover:border-slate-300 transition-colors"
          >
            <User className="w-3.5 h-3.5 text-slate-400" />
            <span>Edit My Profile</span>
          </Link>
        </div>
      </div>

      {/* Insufficient Profile Data Banner */}
      {!hasSufficientData && (
        <div className="p-6 bg-blue-50/80 rounded-2xl border border-blue-200 space-y-3">
          <div className="flex items-center space-x-2 text-blue-900 font-bold text-sm">
            <Info className="w-4 h-4 text-blue-600 shrink-0" />
            <span>Profile Information Required for Personalized Matching</span>
          </div>
          <p className="text-xs text-blue-800 leading-relaxed max-w-2xl">
            {insufficientReasons.length > 0
              ? insufficientReasons[0]
              : "Your profile contains insufficient skills or career track preferences. Upload a PDF/DOCX resume or add your core skills to view ranked job matches."}
          </p>
          <div className="pt-1">
            <Link
              href="/profile#section-resume"
              className="inline-flex items-center space-x-1.5 px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold shadow-sm shadow-blue-500/20 transition-all"
            >
              <span>Upload Resume or Add Skills</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      )}

      {/* Filter Controls Bar */}
      {hasSufficientData && (
        <div className="bg-white rounded-2xl border border-slate-200/90 shadow-2xs p-4 space-y-3">
          {/* Top row: Track pills */}
          {careerTracks.length > 0 && (
            <div className="flex items-center space-x-2 overflow-x-auto pb-1 no-scrollbar">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 shrink-0 mr-1">
                Track:
              </span>
              <button
                type="button"
                onClick={() => setActiveTrack("")}
                className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all shrink-0 cursor-pointer ${
                  activeTrack === ""
                    ? "bg-slate-900 text-white shadow-2xs"
                    : "bg-slate-100 hover:bg-slate-200 text-slate-700"
                }`}
              >
                All Tracks
              </button>
              {careerTracks.map((item) => (
                <button
                  type="button"
                  key={item.profession}
                  onClick={() => setActiveTrack(item.profession)}
                  className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all shrink-0 cursor-pointer ${
                    activeTrack === item.profession
                      ? "bg-blue-600 text-white shadow-2xs"
                      : "bg-slate-100 hover:bg-slate-200 text-slate-700"
                  }`}
                >
                  {item.profession.replace(/_/g, " ")}
                </button>
              ))}
            </div>
          )}

          {/* Secondary filter inputs: Score threshold, remote type, location search */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-1">
            {/* Score filter */}
            <div>
              <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-500 mb-1">
                Match Threshold
              </label>
              <select
                value={minScore}
                onChange={(e) => setMinScore(e.target.value)}
                className="w-full px-3 py-2 text-xs rounded-xl border border-slate-200 bg-white font-medium text-slate-700 focus:outline-none focus:border-blue-500 cursor-pointer"
              >
                {SCORE_THRESHOLDS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Remote type */}
            <div>
              <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-500 mb-1">
                Work Arrangement
              </label>
              <select
                value={remoteType}
                onChange={(e) => setRemoteType(e.target.value)}
                className="w-full px-3 py-2 text-xs rounded-xl border border-slate-200 bg-white font-medium text-slate-700 focus:outline-none focus:border-blue-500 cursor-pointer"
              >
                {REMOTE_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Location filter */}
            <div>
              <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-500 mb-1">
                Filter by Location
              </label>
              <div className="relative">
                <input
                  type="text"
                  value={locationQuery}
                  onChange={(e) => setLocationQuery(e.target.value)}
                  placeholder="e.g. Bengaluru, Remote"
                  className="w-full pl-8 pr-3 py-2 text-xs rounded-xl border border-slate-200 focus:outline-none focus:border-blue-500 font-medium text-slate-700"
                />
                <MapPin className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
              </div>
            </div>
          </div>

          {/* Active filter counter and reset button */}
          {activeFilterCount > 0 && (
            <div className="flex items-center justify-between pt-2 border-t border-slate-100 text-xs">
              <span className="text-slate-500">
                {activeFilterCount} active filter{activeFilterCount > 1 ? "s" : ""} applied
              </span>
              <button
                type="button"
                onClick={handleResetFilters}
                className="inline-flex items-center space-x-1 text-blue-600 hover:text-blue-800 font-bold cursor-pointer"
              >
                <RotateCcw className="w-3 h-3" />
                <span>Reset filters</span>
              </button>
            </div>
          )}
        </div>
      )}

      {/* Main Results Listing */}
      {loading ? (
        <div className="space-y-4">
          {[1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className="p-5 rounded-2xl bg-white border border-slate-200/90 shadow-2xs space-y-3 animate-pulse"
            >
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 rounded-xl bg-slate-200 shrink-0" />
                <div className="space-y-1.5 flex-1">
                  <div className="h-3 w-28 bg-slate-200 rounded" />
                  <div className="h-4 w-56 bg-slate-200 rounded" />
                </div>
              </div>
              <div className="h-3 w-40 bg-slate-100 rounded" />
            </div>
          ))}
        </div>
      ) : error ? (
        <div className="p-6 bg-red-50 rounded-2xl border border-red-200 text-red-800 space-y-2">
          <div className="flex items-center space-x-2 font-bold text-sm">
            <AlertCircle className="w-5 h-5 text-red-600 shrink-0" />
            <span>Unable to load matching jobs</span>
          </div>
          <p className="text-xs">{error}</p>
          <button
            type="button"
            onClick={loadMatches}
            className="mt-2 px-3 py-1.5 rounded-lg bg-red-100 hover:bg-red-200 text-red-800 text-xs font-bold transition-colors cursor-pointer"
          >
            Retry
          </button>
        </div>
      ) : matches.length === 0 ? (
        <div className="text-center py-20 bg-white rounded-2xl border border-slate-200 p-8 space-y-4 shadow-xs">
          <div className="w-12 h-12 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center mx-auto">
            <Sparkles className="w-6 h-6" />
          </div>
          <h3 className="font-bold text-slate-900 text-base">No matching jobs found</h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto leading-relaxed">
            {activeFilterCount > 0
              ? "No jobs meet your current filter criteria. Try lowering the match threshold or clearing filters."
              : "No eligible jobs currently match your profile. Update your skills, experience, or target roles to discover more opportunities."}
          </p>
          <div className="flex items-center justify-center gap-3 pt-2">
            {activeFilterCount > 0 && (
              <button
                type="button"
                onClick={handleResetFilters}
                className="px-4 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold transition-colors cursor-pointer"
              >
                Clear Filters
              </button>
            )}
            <Link
              href="/profile"
              className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold shadow-sm shadow-blue-500/20 transition-all cursor-pointer"
            >
              Update Profile
            </Link>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="flex items-center justify-between text-xs text-slate-500 px-1">
            <span>
              Showing <strong className="text-slate-800">{matches.length}</strong> matching opportunity
              {matches.length > 1 ? "ies" : "y"}
            </span>
            <span className="text-[11px] text-slate-400">
              Ranked by evidence alignment
            </span>
          </div>

          <motion.div
            variants={staggerListVariants}
            initial="hidden"
            animate="visible"
            className="space-y-4"
          >
            {matches.map((item) => {
              const bd = item.match_breakdown;
              const isExpanded = !!expandedBreakdown[item.job.id];

              return (
                <motion.div
                  key={item.job.id}
                  variants={staggerItemVariants}
                  className="bg-white rounded-2xl border border-slate-200/90 shadow-2xs overflow-hidden"
                >
                  {/* Job Card with score badge */}
                  <JobCard
                    job={item.job}
                    showMatchScore={true}
                    matchScore={item.match_score}
                  />

                  {/* Explainable Drawer Bar */}
                  <div className="px-5 py-2.5 bg-slate-50/80 border-t border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-bold text-slate-700">
                        Score Breakdown:
                      </span>
                      <span className="inline-flex items-center px-2 py-0.5 rounded-md bg-blue-50 text-blue-700 border border-blue-200 text-[11px] font-semibold">
                        Skills: {bd.skill_score}/40
                      </span>
                      <span className="inline-flex items-center px-2 py-0.5 rounded-md bg-indigo-50 text-indigo-700 border border-indigo-200 text-[11px] font-semibold">
                        Role: {bd.role_score}/25
                      </span>
                      <span className="inline-flex items-center px-2 py-0.5 rounded-md bg-emerald-50 text-emerald-700 border border-emerald-200 text-[11px] font-semibold">
                        Location: {bd.location_score}/20
                      </span>
                      <span className="inline-flex items-center px-2 py-0.5 rounded-md bg-purple-50 text-purple-700 border border-purple-200 text-[11px] font-semibold">
                        Experience: {bd.experience_score}/15
                      </span>
                    </div>

                    <div className="flex items-center space-x-3 shrink-0">
                      <Link
                        href={`/resume-studio?job_id=${item.job.id}`}
                        className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-sky-50 text-sky-800 border border-sky-200 text-xs font-bold hover:bg-sky-100 transition-colors"
                        title="Tailor resume specifically for this position"
                      >
                        <Sparkles className="w-3 h-3 text-sky-600" />
                        <span>Tailor Resume</span>
                      </Link>

                      <a
                        href={item.job.application_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={() => api.trackJobVisit(item.job.id).catch(() => {})}
                        className="inline-flex items-center space-x-1 text-blue-600 hover:text-blue-800 font-bold cursor-pointer"
                      >
                        <span>Apply on ATS</span>
                        <ExternalLink className="w-3 h-3" />
                      </a>

                      <button
                        type="button"
                        onClick={() => toggleBreakdown(item.job.id)}
                        className="inline-flex items-center space-x-1 font-bold text-slate-600 hover:text-slate-900 transition-colors cursor-pointer"
                      >
                        <span>{isExpanded ? "Hide Details" : "View Breakdown"}</span>
                        {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                      </button>
                    </div>
                  </div>

                  {/* Expandable Evidence Drawer */}
                  <AnimatePresence>
                    {isExpanded && (
                      <motion.div
                        variants={accordionVariants}
                        initial="collapsed"
                        animate="open"
                        exit="collapsed"
                        className="p-5 border-t border-slate-100 bg-white space-y-4 text-xs overflow-hidden"
                      >
                        {/* Matched vs Missing Skills */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          <div className="space-y-1.5">
                            <span className="font-bold text-slate-900 flex items-center space-x-1.5">
                              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                              <span>Matched Skills ({bd.matched_skills?.length || 0})</span>
                            </span>
                            <div className="flex flex-wrap gap-1.5 pt-0.5">
                              {bd.matched_skills && bd.matched_skills.length > 0 ? (
                                bd.matched_skills.map((s, idx) => (
                                  <span
                                    key={idx}
                                    className="px-2.5 py-0.5 rounded-lg bg-emerald-50 text-emerald-800 border border-emerald-200 text-[11px] font-semibold"
                                  >
                                    {s}
                                  </span>
                                ))
                              ) : (
                                <span className="text-slate-400 italic text-[11px]">
                                  No direct skill overlap with stated requirements.
                                </span>
                              )}
                            </div>
                          </div>

                          <div className="space-y-1.5">
                            <span className="font-bold text-slate-900 flex items-center space-x-1.5">
                              <AlertCircle className="w-3.5 h-3.5 text-amber-500" />
                              <span>Missing Required Skills ({bd.missing_skills?.length || 0})</span>
                            </span>
                            <div className="flex flex-wrap gap-1.5 pt-0.5">
                              {bd.missing_skills && bd.missing_skills.length > 0 ? (
                                bd.missing_skills.map((s, idx) => (
                                  <span
                                    key={idx}
                                    className="px-2.5 py-0.5 rounded-lg bg-amber-50 text-amber-800 border border-amber-200 text-[11px] font-semibold"
                                  >
                                    {s}
                                  </span>
                                ))
                              ) : (
                                <span className="text-slate-400 italic text-[11px]">
                                  None missing — you possess all stated core skills.
                                </span>
                              )}
                            </div>
                          </div>
                        </div>

                        {/* Alignment Badges */}
                        <div className="flex flex-wrap items-center gap-3 pt-2 border-t border-slate-100">
                          {bd.location_eligibility && (
                            <span className="inline-flex items-center space-x-1 text-slate-600">
                              <strong className="text-slate-800">Location Status:</strong>
                              <span className="px-2 py-0.5 rounded-md bg-slate-100 font-semibold text-slate-700">
                                {bd.location_eligibility}
                              </span>
                            </span>
                          )}

                          {bd.experience_alignment && (
                            <span className="inline-flex items-center space-x-1 text-slate-600">
                              <strong className="text-slate-800">Experience Alignment:</strong>
                              <span className="px-2 py-0.5 rounded-md bg-slate-100 font-semibold text-slate-700">
                                {bd.experience_alignment}
                              </span>
                            </span>
                          )}
                        </div>

                        {/* Explainability Reasons List */}
                        {bd.reasons && bd.reasons.length > 0 && (
                          <div className="space-y-1.5 pt-2 border-t border-slate-100">
                            <span className="font-bold text-slate-900">
                              Detailed Scoring Reasons:
                            </span>
                            <ul className="space-y-1 list-disc pl-5 text-slate-600">
                              {bd.reasons.map((r, i) => (
                                <li key={i}>{r}</li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {/* Disclaimer */}
                        <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80 text-[11px] text-slate-500 leading-relaxed">
                          <strong>Note:</strong> {bd.score_disclaimer || "Match score reflects profile alignment against stated job requirements and does not predict employer hiring decisions."}
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </motion.div>
              );
            })}
          </motion.div>
        </div>
      )}
    </div>
  );
}

export default function MyMatchesPage() {
  return (
    <Suspense
      fallback={
        <div className="max-w-5xl mx-auto px-4 py-24 flex items-center justify-center">
          <Loader2 className="w-8 h-8 text-blue-600 animate-spin" />
        </div>
      }
    >
      <MyMatchesContent />
    </Suspense>
  );
}
