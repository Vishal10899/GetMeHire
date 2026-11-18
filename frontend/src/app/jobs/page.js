"use client";

import { useState, useEffect, useRef, Suspense, useCallback } from "react";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/authContext";
import JobCard from "@/components/JobCard";
import ProfessionPills from "@/components/ProfessionPills";
import SearchFilters from "@/components/SearchFilters";
import { motion, AnimatePresence } from "motion/react";
import {
  backdropVariants,
  slideOverDrawerVariants,
  staggerListVariants,
  staggerItemVariants,
} from "@/components/animations/variants";
import {
  Search,
  MapPin,
  ArrowUpDown,
  ChevronLeft,
  ChevronRight,
  Loader2,
  AlertCircle,
  SlidersHorizontal,
  X,
  Sparkles,
  RotateCcw,
  Globe,
  Calendar,
  Building2,
  Award,
  Layers,
} from "lucide-react";

/**
 * Builds a deterministic, normalized signature for a filter set.
 * Used for strict request deduplication to prevent redundant network calls.
 */
function buildFilterSignature(f) {
  if (!f) return "";
  const skillsStr = Array.isArray(f.skills)
    ? f.skills.slice().sort().join(",")
    : String(f.skills || "");
  return [
    (f.keyword || "").trim().toLowerCase(),
    (f.location || "").trim().toLowerCase(),
    (f.company || "").trim().toLowerCase(),
    f.company_id || "",
    f.country_code || "",
    f.profession || "",
    f.category || "",
    f.remote_type || "",
    f.work_arrangement || "",
    f.remote_eligibility || "",
    f.employment_type || "",
    f.experience_level || "",
    f.experience_range || "",
    f.early_career_category || "",
    f.is_fresher_friendly || "",
    f.date_posted || "",
    f.min_salary || "",
    skillsStr,
    f.sort_by || "newest",
    Number(f.page || 1),
  ].join("|");
}

function parseFiltersFromSearchParams(sp) {
  return {
    keyword: sp.get("keyword") || "",
    location: sp.get("location") || "",
    company: sp.get("company") || "",
    company_id: sp.get("company_id") || "",
    country_code: sp.get("country_code") || "",
    profession: sp.get("profession") || "",
    category: sp.get("category") || "",
    remote_type: sp.get("remote_type") || "",
    work_arrangement: sp.get("work_arrangement") || "",
    remote_eligibility: sp.get("remote_eligibility") || "",
    employment_type: sp.get("employment_type") || "",
    experience_level: sp.get("experience_level") || "",
    experience_range: sp.get("experience_range") || "",
    early_career_category: sp.get("early_career_category") || "",
    is_fresher_friendly: sp.get("is_fresher_friendly") || "",
    date_posted: sp.get("date_posted") || "",
    min_salary: sp.get("min_salary") || "",
    skills: sp.getAll("skills") || [],
    sort_by: sp.get("sort_by") || "newest",
    page: parseInt(sp.get("page") || "1", 10),
  };
}

function JobsContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const { user } = useAuth();

  // Initial filters parsed once from current URL query
  const [filters, setFilters] = useState(() => parseFiltersFromSearchParams(searchParams));

  // Immediate input states decoupled from debounced network requests
  const [keywordInput, setKeywordInput] = useState(() => searchParams.get("keyword") || "");
  const [locationInput, setLocationInput] = useState(() => searchParams.get("location") || "");

  // Results & Request State Machine: "idle" | "loading" | "success" | "empty" | "error"
  const [searchStatus, setSearchStatus] = useState("loading");
  const [jobs, setJobs] = useState([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showFilterDrawer, setShowFilterDrawer] = useState(false);
  const [searchMeta, setSearchMeta] = useState({
    did_you_mean: null,
    is_corrected: false,
    suggested_roles: [],
    detected_profession: null,
    query_latency_ms: null,
  });

  // Lifecycle control refs
  const debounceTimerRef = useRef(null);
  const activeAbortControllerRef = useRef(null);
  const latestRequestIdRef = useRef(0);
  const lastExecutedSignatureRef = useRef("");
  const isInternalUrlUpdateRef = useRef(false);

  // Synchronize browser URL query string without creating feedback loops
  const syncUrlParams = useCallback(
    (currentFilters) => {
      const params = new URLSearchParams();
      Object.entries(currentFilters).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== "") {
          if (Array.isArray(v)) {
            v.forEach((item) => params.append(k, item));
          } else if (k === "page" && Number(v) === 1) {
            // omit default page 1 for cleaner URLs
          } else if (k === "sort_by" && v === "newest") {
            // omit default sort for cleaner URLs
          } else {
            params.set(k, String(v));
          }
        }
      });
      const qs = params.toString();
      const targetUrl = qs ? `${pathname}?${qs}` : pathname;
      if (typeof window !== "undefined" && window.location.search !== (qs ? `?${qs}` : "")) {
        isInternalUrlUpdateRef.current = true;
        window.history.replaceState(null, "", targetUrl);
      }
    },
    [pathname]
  );

  /**
   * Executes an atomic job search with:
   * 1. Query deduplication (prevents redundant identical requests).
   * 2. In-flight cancellation via AbortController.
   * 3. Monotonic request ID guarding against stale response overwrites.
   * 4. Reliable state machine transitions ("loading" -> "success" | "empty" | "error").
   */
  const executeSearch = useCallback(
    async (targetFilters, { force = false } = {}) => {
      const sig = buildFilterSignature(targetFilters);
      if (!force && sig === lastExecutedSignatureRef.current) {
        return;
      }

      // Abort any prior in-flight request
      if (activeAbortControllerRef.current) {
        activeAbortControllerRef.current.abort();
      }
      const controller = new AbortController();
      activeAbortControllerRef.current = controller;

      const thisRequestId = ++latestRequestIdRef.current;
      lastExecutedSignatureRef.current = sig;

      setLoading(true);
      setSearchStatus("loading");
      setError(null);

      try {
        const data = await api.searchJobs(
          {
            keyword: targetFilters.keyword,
            location: targetFilters.location,
            company: targetFilters.company,
            company_id: targetFilters.company_id,
            country_code: targetFilters.country_code,
            profession: targetFilters.profession,
            category: targetFilters.category,
            remote_type: targetFilters.remote_type,
            work_arrangement: targetFilters.work_arrangement,
            remote_eligibility: targetFilters.remote_eligibility,
            employment_type: targetFilters.employment_type,
            experience_level: targetFilters.experience_level,
            experience_range: targetFilters.experience_range,
            date_posted: targetFilters.date_posted,
            min_salary: targetFilters.min_salary,
            skills: targetFilters.skills,
            sort_by: targetFilters.sort_by || "newest",
            page: targetFilters.page || 1,
            page_size: 15,
          },
          { signal: controller.signal }
        );

        // Stale response guard: ignore if a newer search was initiated
        if (thisRequestId !== latestRequestIdRef.current) {
          return;
        }

        const items = data.items || [];
        setJobs(items);
        setTotal(data.total || 0);
        setTotalPages(data.total_pages || 1);
        setSearchMeta({
          did_you_mean: data.did_you_mean || null,
          is_corrected: Boolean(data.is_corrected),
          suggested_roles: data.suggested_roles || [],
          detected_profession: data.detected_profession || null,
          query_latency_ms: data.query_latency_ms || null,
        });

        setSearchStatus(items.length === 0 ? "empty" : "success");
        setLoading(false);
        syncUrlParams(targetFilters);
      } catch (err) {
        // Silently ignore aborted requests
        if (controller.signal.aborted || err.name === "AbortError") {
          return;
        }
        // Stale request guard
        if (thisRequestId !== latestRequestIdRef.current) {
          return;
        }

        console.error("Job search error:", err);
        setError(err.message || "Failed to load job listings");
        setSearchStatus("error");
        setLoading(false);
      }
    },
    [syncUrlParams]
  );

  /**
   * Applies filter updates, synchronizing inputs and executing a single request.
   */
  const applyFilters = useCallback(
    (patch, { immediate = true } = {}) => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
        debounceTimerRef.current = null;
      }

      setFilters((prev) => {
        const next = { ...prev, ...patch };
        if (patch.keyword !== undefined) setKeywordInput(patch.keyword);
        if (patch.location !== undefined) setLocationInput(patch.location);

        if (immediate) {
          executeSearch(next);
        }
        return next;
      });
    },
    [executeSearch]
  );

  // Debounced typing handlers (350ms delay for smooth typing without request flood)
  const handleKeywordChange = (val) => {
    setKeywordInput(val);
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }
    debounceTimerRef.current = setTimeout(() => {
      applyFilters({ keyword: val, page: 1 }, { immediate: true });
    }, 350);
  };

  const handleKeywordKeyDown = (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
        debounceTimerRef.current = null;
      }
      applyFilters({ keyword: keywordInput, page: 1 }, { immediate: true });
    }
  };

  const handleClearKeyword = () => {
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
      debounceTimerRef.current = null;
    }
    setKeywordInput("");
    applyFilters({ keyword: "", page: 1 }, { immediate: true });
  };

  const handleLocationChange = (val) => {
    setLocationInput(val);
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }
    debounceTimerRef.current = setTimeout(() => {
      applyFilters({ location: val, page: 1 }, { immediate: true });
    }, 350);
  };

  const handleLocationKeyDown = (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
        debounceTimerRef.current = null;
      }
      applyFilters({ location: locationInput, page: 1 }, { immediate: true });
    }
  };

  const handleClearLocation = () => {
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
      debounceTimerRef.current = null;
    }
    setLocationInput("");
    applyFilters({ location: "", page: 1 }, { immediate: true });
  };

  // Run initial search exactly once on mount
  useEffect(() => {
    executeSearch(filters, { force: true });

    return () => {
      if (debounceTimerRef.current) clearTimeout(debounceTimerRef.current);
      if (activeAbortControllerRef.current) activeAbortControllerRef.current.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Handle browser back/forward or external navigation safely
  useEffect(() => {
    if (isInternalUrlUpdateRef.current) {
      isInternalUrlUpdateRef.current = false;
      return;
    }

    const nextFromUrl = parseFiltersFromSearchParams(searchParams);
    const urlSig = buildFilterSignature(nextFromUrl);

    if (urlSig !== lastExecutedSignatureRef.current) {
      setKeywordInput(nextFromUrl.keyword);
      setLocationInput(nextFromUrl.location);
      setFilters(nextFromUrl);
      executeSearch(nextFromUrl);
    }
  }, [searchParams, executeSearch]);

  const handleReset = () => {
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
      debounceTimerRef.current = null;
    }
    setKeywordInput("");
    setLocationInput("");
    const resetState = {
      keyword: "",
      location: "",
      company: "",
      company_id: "",
      country_code: "",
      profession: "",
      category: "",
      remote_type: "",
      employment_type: "",
      experience_level: "",
      experience_range: "",
      early_career_category: "",
      is_fresher_friendly: "",
      date_posted: "",
      min_salary: "",
      skills: [],
      sort_by: "newest",
      page: 1,
    };
    setFilters(resetState);
    executeSearch(resetState, { force: true });
  };

  const handleSelectProfession = (profKey) => {
    applyFilters({ profession: profKey, page: 1 });
  };

  const handleSelectRole = (role) => {
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
      debounceTimerRef.current = null;
    }
    setKeywordInput(role);
    applyFilters({ keyword: role, page: 1 });
  };

  const handleSelectDidYouMean = (correction) => {
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
      debounceTimerRef.current = null;
    }
    setKeywordInput(correction);
    applyFilters({ keyword: correction, page: 1 });
  };

  const handleCardClick = (job) => {
    router.push(`/jobs/${job.id}`);
  };

  const activeFilterCount = [
    filters.profession,
    filters.category,
    filters.remote_type,
    filters.employment_type,
    filters.experience_level,
    filters.experience_range,
    filters.early_career_category,
    filters.country_code,
    filters.date_posted,
    filters.min_salary,
    filters.company,
    filters.company_id,
    ...(filters.skills || []),
  ].filter(Boolean).length;

  const removeFilter = (key, value) => {
    if (key === "skills") {
      applyFilters({
        skills: (filters.skills || []).filter((s) => s !== value),
        page: 1,
      });
    } else {
      applyFilters({
        [key]: "",
        page: 1,
      });
    }
  };

  const handlePageChange = (newPage) => {
    if (newPage < 1 || newPage > totalPages || newPage === filters.page) return;
    applyFilters({ page: newPage });
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Search Header Banner */}
      <div className="bg-white p-4 sm:p-6 rounded-2xl border border-slate-200/90 shadow-sm space-y-4">
        {/* Main Search Inputs Row */}
        <div className="flex flex-col md:flex-row gap-3 items-stretch md:items-center">
          {/* Keyword Search */}
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-3.5" />
            <input
              type="text"
              placeholder="Search by job title, skill, or keyword..."
              value={keywordInput}
              onChange={(e) => handleKeywordChange(e.target.value)}
              onKeyDown={handleKeywordKeyDown}
              className="w-full pl-10 pr-8 py-2.5 text-xs sm:text-sm rounded-xl border border-slate-200 bg-slate-50/70 focus:bg-white focus:border-blue-500 focus:outline-none transition-colors"
            />
            {keywordInput && (
              <button
                onClick={handleClearKeyword}
                className="absolute right-3 top-3 text-slate-400 hover:text-slate-600 cursor-pointer"
                aria-label="Clear keyword search"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>

          {/* Location input */}
          <div className="relative w-full md:w-64">
            <MapPin className="w-4 h-4 text-slate-400 absolute left-3.5 top-3.5" />
            <input
              type="text"
              placeholder="City, state, or country..."
              value={locationInput}
              onChange={(e) => handleLocationChange(e.target.value)}
              onKeyDown={handleLocationKeyDown}
              className="w-full pl-10 pr-8 py-2.5 text-xs sm:text-sm rounded-xl border border-slate-200 bg-slate-50/70 focus:bg-white focus:border-blue-500 focus:outline-none transition-colors"
            />
            {locationInput && (
              <button
                onClick={handleClearLocation}
                className="absolute right-3 top-3 text-slate-400 hover:text-slate-600 cursor-pointer"
                aria-label="Clear location filter"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>

          {/* Controls: Filter Drawer Toggle + Sort */}
          <div className="flex items-center justify-between sm:justify-start gap-2 w-full md:w-auto">
            {/* Filter Drawer Button */}
            <motion.button
              onClick={() => setShowFilterDrawer(true)}
              whileTap={{ scale: 0.97 }}
              transition={{ duration: 0.1 }}
              className={`flex-1 sm:flex-none flex items-center justify-center space-x-1.5 px-3.5 py-2.5 rounded-xl border text-xs font-bold transition-all cursor-pointer ${
                activeFilterCount > 0
                  ? "bg-blue-50 border-blue-300 text-blue-700 shadow-2xs"
                  : "bg-white border-slate-200 text-slate-700 hover:bg-slate-50 hover:border-slate-300"
              }`}
            >
              <SlidersHorizontal className="w-3.5 h-3.5 text-blue-600" />
              <span>Filters</span>
              {activeFilterCount > 0 && (
                <span className="w-4 h-4 rounded-full bg-blue-600 text-white text-[10px] flex items-center justify-center font-bold">
                  {activeFilterCount}
                </span>
              )}
            </motion.button>

            {/* Sort Dropdown */}
            <div className="flex-1 sm:flex-none flex items-center justify-center space-x-1 border border-slate-200 rounded-xl px-2.5 py-2 bg-slate-50 text-xs font-medium text-slate-700">
              <ArrowUpDown className="w-3.5 h-3.5 text-slate-400 shrink-0" />
              <select
                value={filters.sort_by}
                onChange={(e) => applyFilters({ sort_by: e.target.value, page: 1 })}
                className="bg-transparent border-none text-xs font-semibold focus:outline-none text-slate-800 cursor-pointer"
              >
                <option value="newest">Newest First</option>
                <option value="relevant">Most Relevant</option>
                <option value="company">Company (A–Z)</option>
                <option value="salary_high">Highest Salary</option>
                <option value="oldest">Oldest First</option>
              </select>
            </div>
          </div>
        </div>

        {/* Early Career & Freshers Quick Filter Tabs */}
        <div className="pt-2 border-t border-slate-100 flex items-center gap-1.5 overflow-x-auto scrollbar-none pb-1">
          <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider shrink-0 mr-1 flex items-center space-x-1">
            <span>Career Stage:</span>
          </span>
          {[
            { id: "", label: "All Careers" },
            { id: "TRUE_FRESHER", label: "🎓 Freshers (0 Yrs)" },
            { id: "GRADUATE", label: "🎓 Graduate Programs" },
            { id: "INTERNSHIP", label: "💼 Internships" },
            { id: "ENTRY_LEVEL", label: "🌱 0-1 Yrs Entry Level" },
            { id: "TRAINEE", label: "🌟 Trainees" },
            { id: "APPRENTICESHIP", label: "🛠 Apprenticeships" },
          ].map((tab) => {
            const isSelected = (filters.early_career_category || "") === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => applyFilters({ early_career_category: tab.id, page: 1 })}
                className={`px-3 py-1.5 rounded-xl text-xs font-bold shrink-0 transition-all cursor-pointer ${
                  isSelected
                    ? "bg-slate-900 text-white shadow-2xs"
                    : "bg-slate-50 text-slate-600 hover:bg-slate-100 border border-slate-200/80 hover:border-slate-300"
                }`}
              >
                {tab.label}
              </button>
            );
          })}
        </div>

        {/* Horizontal Multi-Profession Pills */}
        <div className="pt-2 border-t border-slate-100">
          <ProfessionPills
            selectedProfession={filters.profession}
            onSelectProfession={handleSelectProfession}
          />
        </div>

        {/* Removable Active Filter Badges */}
        {activeFilterCount > 0 && (
          <div className="pt-2 border-t border-slate-100 flex flex-wrap items-center gap-1.5 text-xs animate-fade-in">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mr-1">
              Active Filters:
            </span>

            {filters.country_code && (
              <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-blue-50 text-blue-700 border border-blue-200 text-xs font-semibold">
                <Globe className="w-3 h-3 text-blue-600" />
                <span>Country: {filters.country_code}</span>
                <button
                  onClick={() => removeFilter("country_code")}
                  className="hover:text-blue-900 cursor-pointer"
                  aria-label="Remove country filter"
                >
                  <X className="w-3 h-3" />
                </button>
              </span>
            )}

            {filters.category && (
              <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-blue-50 text-blue-700 border border-blue-200 text-xs font-semibold">
                <Layers className="w-3 h-3 text-blue-600" />
                <span>Category: {filters.category.replace(/_/g, " ")}</span>
                <button
                  onClick={() => removeFilter("category")}
                  className="hover:text-blue-900 cursor-pointer"
                  aria-label="Remove category filter"
                >
                  <X className="w-3 h-3" />
                </button>
              </span>
            )}

            {filters.profession && (
              <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-blue-50 text-blue-700 border border-blue-200 text-xs font-semibold">
                <span>Profession: {filters.profession.replace(/_/g, " ")}</span>
                <button
                  onClick={() => removeFilter("profession")}
                  className="hover:text-blue-900 cursor-pointer"
                  aria-label="Remove profession filter"
                >
                  <X className="w-3 h-3" />
                </button>
              </span>
            )}

            {filters.early_career_category && (
              <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-teal-50 text-teal-800 border border-teal-200 text-xs font-semibold">
                <span>Career Stage: {filters.early_career_category.replace(/_/g, " ")}</span>
                <button
                  onClick={() => removeFilter("early_career_category")}
                  className="hover:text-teal-950 cursor-pointer"
                  aria-label="Remove career stage filter"
                >
                  <X className="w-3 h-3" />
                </button>
              </span>
            )}

            {filters.remote_type && (
              <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-blue-50 text-blue-700 border border-blue-200 text-xs font-semibold">
                <span>Work: {filters.remote_type}</span>
                <button
                  onClick={() => removeFilter("remote_type")}
                  className="hover:text-blue-900 cursor-pointer"
                  aria-label="Remove work arrangement filter"
                >
                  <X className="w-3 h-3" />
                </button>
              </span>
            )}

            {filters.experience_range && (
              <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-blue-50 text-blue-700 border border-blue-200 text-xs font-semibold">
                <Award className="w-3 h-3 text-blue-600" />
                <span>Exp: {filters.experience_range}</span>
                <button
                  onClick={() => removeFilter("experience_range")}
                  className="hover:text-blue-900 cursor-pointer"
                  aria-label="Remove experience range filter"
                >
                  <X className="w-3 h-3" />
                </button>
              </span>
            )}

            {filters.date_posted && (
              <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-blue-50 text-blue-700 border border-blue-200 text-xs font-semibold">
                <Calendar className="w-3 h-3 text-blue-600" />
                <span>Posted: {filters.date_posted}</span>
                <button
                  onClick={() => removeFilter("date_posted")}
                  className="hover:text-blue-900 cursor-pointer"
                  aria-label="Remove date posted filter"
                >
                  <X className="w-3 h-3" />
                </button>
              </span>
            )}

            {filters.employment_type && (
              <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-blue-50 text-blue-700 border border-blue-200 text-xs font-semibold">
                <span>Type: {filters.employment_type}</span>
                <button
                  onClick={() => removeFilter("employment_type")}
                  className="hover:text-blue-900 cursor-pointer"
                  aria-label="Remove employment type filter"
                >
                  <X className="w-3 h-3" />
                </button>
              </span>
            )}

            {filters.min_salary && (
              <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-emerald-50 text-emerald-800 border border-emerald-200 text-xs font-semibold">
                <span>Min: ${Number(filters.min_salary).toLocaleString()}</span>
                <button
                  onClick={() => removeFilter("min_salary")}
                  className="hover:text-emerald-950 cursor-pointer"
                  aria-label="Remove salary filter"
                >
                  <X className="w-3 h-3" />
                </button>
              </span>
            )}

            {filters.company && (
              <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-blue-50 text-blue-700 border border-blue-200 text-xs font-semibold">
                <Building2 className="w-3 h-3 text-blue-600" />
                <span>Company: {filters.company}</span>
                <button
                  onClick={() => removeFilter("company")}
                  className="hover:text-blue-900 cursor-pointer"
                  aria-label="Remove company filter"
                >
                  <X className="w-3 h-3" />
                </button>
              </span>
            )}

            {(filters.skills || []).map((skill) => (
              <span
                key={skill}
                className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-slate-100 text-slate-800 border border-slate-200 text-xs font-semibold"
              >
                <span>{skill}</span>
                <button
                  onClick={() => removeFilter("skills", skill)}
                  className="hover:text-slate-900 cursor-pointer"
                  aria-label={`Remove skill ${skill}`}
                >
                  <X className="w-3 h-3" />
                </button>
              </span>
            ))}

            <button
              onClick={handleReset}
              className="text-xs font-bold text-slate-500 hover:text-blue-600 transition-colors ml-1 cursor-pointer"
            >
              Reset all
            </button>
          </div>
        )}
      </div>

      {/* Results Header: Count & Typo Correction */}
      <div className="space-y-4">
        <div className="flex items-center justify-between px-1">
          <span className="text-sm font-bold text-slate-800">
            {loading ? (
              <span className="flex items-center space-x-1.5 text-blue-600">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Searching verified opportunities...</span>
              </span>
            ) : (
              <div className="flex items-center space-x-2">
                <span>{total.toLocaleString()} opportunities</span>
                {searchMeta.query_latency_ms && (
                  <span className="text-[11px] text-slate-400 font-normal">
                    ({searchMeta.query_latency_ms.toFixed(0)}ms)
                  </span>
                )}
              </div>
            )}
          </span>

          {activeFilterCount > 0 && (
            <button
              onClick={handleReset}
              className="text-xs font-bold text-blue-600 hover:text-blue-800 transition-colors flex items-center space-x-1 cursor-pointer"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Clear filters</span>
            </button>
          )}
        </div>

        {/* Typo Correction Banner */}
        {searchMeta.is_corrected && searchMeta.did_you_mean && (
          <div className="p-3 bg-blue-50/80 rounded-xl border border-blue-200 text-xs text-blue-950 flex items-center justify-between">
            <div className="flex items-center space-x-2 min-w-0">
              <Sparkles className="w-4 h-4 text-blue-600 shrink-0" />
              <span className="truncate">
                Showing results for{" "}
                <button
                  onClick={() => handleSelectDidYouMean(searchMeta.did_you_mean)}
                  className="font-bold underline hover:text-blue-700 cursor-pointer"
                >
                  {searchMeta.did_you_mean}
                </button>
              </span>
            </div>
          </div>
        )}

        {/* Related Roles Chips */}
        {searchMeta.suggested_roles && searchMeta.suggested_roles.length > 0 && (
          <div className="flex items-center space-x-1.5 overflow-x-auto pb-1 text-xs no-scrollbar">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 shrink-0">
              Related Roles:
            </span>
            {searchMeta.suggested_roles.map((role) => (
              <button
                key={role}
                onClick={() => handleSelectRole(role)}
                className="px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-blue-50 hover:text-blue-700 text-slate-700 text-xs font-semibold whitespace-nowrap transition-colors cursor-pointer"
              >
                {role}
              </button>
            ))}
          </div>
        )}

        {/* Job Listings List - Governed by Search State Machine */}
        {searchStatus === "loading" && jobs.length === 0 ? (
          <div className="space-y-3">
            {[1, 2, 3, 4, 5].map((i) => (
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
                <div className="flex gap-2 pt-1 border-t border-slate-100">
                  <div className="h-4 w-16 bg-slate-100 rounded" />
                  <div className="h-4 w-20 bg-slate-100 rounded" />
                </div>
              </div>
            ))}
          </div>
        ) : searchStatus === "error" ? (
          <div className="p-6 bg-red-50 rounded-2xl border border-red-200 text-red-800 flex items-start space-x-3">
            <AlertCircle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
            <div>
              <h4 className="font-bold text-sm">Unable to load job listings</h4>
              <p className="text-xs mt-1">{error}</p>
              <button
                onClick={() => executeSearch(filters, { force: true })}
                className="mt-3 text-xs font-semibold underline hover:no-underline cursor-pointer"
              >
                Retry request
              </button>
            </div>
          </div>
        ) : searchStatus === "empty" || (searchStatus === "success" && jobs.length === 0) ? (
          <div className="text-center py-16 bg-white rounded-2xl border border-slate-200 p-8 space-y-3">
            <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center mx-auto text-slate-400">
              <Search className="w-6 h-6" />
            </div>
            <h3 className="font-bold text-slate-900 text-base">No matching job listings found</h3>
            <p className="text-xs text-slate-500 max-w-sm mx-auto">
              Try widening your search terms, clearing specific filters, or selecting another profession pill above.
            </p>
            <button
              onClick={handleReset}
              className="px-4 py-2 rounded-xl bg-blue-50 text-blue-700 text-xs font-semibold hover:bg-blue-100 transition-colors cursor-pointer"
            >
              Clear all filters
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            <motion.div
              variants={staggerListVariants}
              initial="hidden"
              animate="visible"
              className="space-y-3"
            >
              {jobs.map((job) => (
                <motion.div key={job.id} variants={staggerItemVariants}>
                  <JobCard
                    job={job}
                    onSelect={handleCardClick}
                    onSaveToggle={(id, saved) => {
                      setJobs((prev) =>
                        prev.map((j) => (j.id === id ? { ...j, is_saved: saved } : j))
                      );
                    }}
                    showMatchScore={Boolean(user && job.match_score !== null && job.match_score !== undefined)}
                    matchScore={job.match_score}
                  />
                </motion.div>
              ))}
            </motion.div>

            {/* Bounded Pagination Controls */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between pt-6 border-t border-slate-200 px-1 text-xs">
                <button
                  onClick={() => handlePageChange(Math.max(1, filters.page - 1))}
                  disabled={filters.page <= 1}
                  className="flex items-center space-x-1 px-3.5 py-2 rounded-xl border border-slate-200 bg-white font-semibold text-slate-700 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-50 transition-colors shadow-2xs cursor-pointer"
                >
                  <ChevronLeft className="w-4 h-4" />
                  <span>Previous</span>
                </button>

                <span className="font-bold text-slate-600">
                  Page {filters.page} of {totalPages}
                </span>

                <button
                  onClick={() => handlePageChange(Math.min(totalPages, filters.page + 1))}
                  disabled={filters.page >= totalPages}
                  className="flex items-center space-x-1 px-3.5 py-2 rounded-xl border border-slate-200 bg-white font-semibold text-slate-700 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-50 transition-colors shadow-2xs cursor-pointer"
                >
                  <span>Next</span>
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Slide-over Filter Drawer on Mobile/Tablet/Desktop */}
      <AnimatePresence>
        {showFilterDrawer && (
          <div className="fixed inset-0 z-50 overflow-hidden flex justify-end">
            <motion.div
              variants={backdropVariants}
              initial="hidden"
              animate="visible"
              exit="exit"
              className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs"
              onClick={() => setShowFilterDrawer(false)}
            />
            <motion.div
              variants={slideOverDrawerVariants}
              initial="hidden"
              animate="visible"
              exit="exit"
              className="relative w-full max-w-md bg-white h-full shadow-2xl flex flex-col p-6 z-10 overflow-y-auto"
            >
              {/* Filter Opportunities header */}
              <div className="flex items-center justify-between pb-4 border-b border-slate-200">
                <div className="flex items-center space-x-2">
                  <SlidersHorizontal className="w-5 h-5 text-blue-600" />
                  <h3 className="font-extrabold text-slate-900 text-base">Filter Opportunities</h3>
                </div>
                <button
                  onClick={() => setShowFilterDrawer(false)}
                  className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 cursor-pointer"
                  aria-label="Close filters"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="py-4 flex-1">
                <SearchFilters
                  filters={filters}
                  onChange={(newFilters) => {
                    applyFilters({
                      ...newFilters,
                      page: 1,
                    });
                  }}
                  onReset={() => {
                    handleReset();
                    setShowFilterDrawer(false);
                  }}
                />
              </div>

              <div className="pt-4 border-t border-slate-200 flex items-center space-x-3">
                <button
                  onClick={() => setShowFilterDrawer(false)}
                  className="flex-1 py-3 rounded-xl bg-blue-600 text-white font-bold text-xs hover:bg-blue-700 transition-colors shadow-xs cursor-pointer"
                >
                  Show {total.toLocaleString()} opportunities
                </button>
                <button
                  onClick={() => {
                    handleReset();
                    setShowFilterDrawer(false);
                  }}
                  className="px-4 py-3 rounded-xl border border-slate-200 text-slate-700 font-bold text-xs hover:bg-slate-50 transition-colors cursor-pointer"
                >
                  Reset
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default function JobsPage() {
  return (
    <Suspense
      fallback={
        <div className="max-w-4xl mx-auto px-4 py-20 flex flex-col items-center justify-center">
          <Loader2 className="w-8 h-8 text-blue-600 animate-spin mb-3" />
          <p className="text-sm font-semibold text-slate-500">Loading opportunities...</p>
        </div>
      }
    >
      <JobsContent />
    </Suspense>
  );
}
