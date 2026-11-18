"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  Search,
  MapPin,
  Building2,
  Sparkles,
  ShieldCheck,
  CheckCircle2,
  ArrowRight,
  TrendingUp,
  Cpu,
  Globe2,
  Code,
  Palette,
  Scale,
  Users,
  Briefcase,
  Zap,
  Lock,
  Layers,
  Headphones,
  FileCheck,
  FileText,
  Clock,
  ExternalLink,
  ChevronRight,
  Loader2,
} from "lucide-react";
import { api } from "@/lib/api";
import { motion } from "motion/react";
import JobCard from "@/components/JobCard";
import CompanyAvatar from "@/components/CompanyAvatar";
import { Button, Card, Badge } from "@/components/ui";

const TRACK_ICON_MAP = {
  ENGINEERING: Code,
  SOFTWARE_IT: Code,
  DATA_AI: Cpu,
  PRODUCT_DESIGN: Palette,
  SALES_BIZDEV: TrendingUp,
  FINANCE_ACCOUNTING: Scale,
  FINANCE_LEGAL: Scale,
  HR_RECRUITMENT: Users,
  OPERATIONS_LOGISTICS: Layers,
  OPERATIONS_PEOPLE: Layers,
  CUSTOMER_SUPPORT: Headphones,
  MARKETING_GROWTH: Briefcase,
};

export default function HomePage() {
  const router = useRouter();

  const [keyword, setKeyword] = useState("");
  const [location, setLocation] = useState("");
  const [recentJobs, setRecentJobs] = useState([]);
  const [professions, setProfessions] = useState([]);
  const [companies, setCompanies] = useState([]);
  const [stats, setStats] = useState({
    totalJobs: 0,
    totalCompanies: 0,
    totalTracks: 0,
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    async function loadHomeData() {
      try {
        const [jobsRes, profRes, compRes] = await Promise.allSettled([
          api.getRecentJobs(6),
          api.getProfessions(),
          api.getCompanies({ page_size: 6 }),
        ]);

        if (!isMounted) return;

        let totalJobsCount = 0;
        if (jobsRes.status === "fulfilled" && jobsRes.value) {
          setRecentJobs(jobsRes.value.items || []);
          totalJobsCount = jobsRes.value.total || 0;
        }

        let tracksList = [];
        if (profRes.status === "fulfilled" && profRes.value) {
          tracksList = profRes.value.professions || [];
          setProfessions(tracksList);
          if (profRes.value.total_jobs) {
            totalJobsCount = Math.max(totalJobsCount, profRes.value.total_jobs);
          }
        }

        let companiesList = [];
        let companiesTotal = 0;
        if (compRes.status === "fulfilled" && compRes.value) {
          companiesList = compRes.value.companies || [];
          companiesTotal = compRes.value.total || companiesList.length;
          setCompanies(companiesList);
        }

        setStats({
          totalJobs: totalJobsCount,
          totalCompanies: companiesTotal,
          totalTracks: tracksList.length || 12,
        });
      } catch (err) {
        console.error("Home page data load error:", err);
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    loadHomeData();

    return () => {
      isMounted = false;
    };
  }, []);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    const params = new URLSearchParams();
    if (keyword.trim()) params.set("keyword", keyword.trim());
    if (location.trim()) params.set("location", location.trim());
    router.push(`/jobs?${params.toString()}`);
  };

  const handleQuickTagClick = (query) => {
    router.push(`/jobs?keyword=${encodeURIComponent(query)}`);
  };

  return (
    <div className="space-y-16 sm:space-y-20 pb-16">
      {/* 1. HERO SECTION */}
      <section className="relative pt-12 sm:pt-16 lg:pt-20 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
        <div className="text-center max-w-3xl mx-auto space-y-6">
          {/* Heading */}
          <h1 className="text-3xl sm:text-5xl lg:text-6xl font-extrabold text-slate-900 tracking-tight leading-[1.12]">
            Discover genuine roles at{" "}
            <span className="text-blue-600">leading employers</span>
          </h1>

          {/* Value proposition */}
          <p className="text-sm sm:text-base text-slate-600 max-w-2xl mx-auto leading-relaxed">
            Search verified positions synced directly from official company applicant tracking systems. Direct employer application links, transparent job requirements, and zero ghost listings.
          </p>

          {/* Search Box */}
          <form
            onSubmit={handleSearchSubmit}
            className="pt-2 max-w-2xl mx-auto"
          >
            <div className="bg-white p-2 rounded-2xl border border-slate-200 shadow-sm flex flex-col sm:flex-row items-stretch gap-2">
              <div className="relative flex-1 flex items-center">
                <Search className="w-4 h-4 text-slate-400 absolute left-3.5" />
                <input
                  type="text"
                  placeholder="Job title, skills, or company"
                  value={keyword}
                  onChange={(e) => setKeyword(e.target.value)}
                  className="w-full pl-10 pr-3 py-2.5 text-xs sm:text-sm text-slate-900 placeholder:text-slate-400 bg-transparent focus:outline-none"
                />
              </div>

              <div className="hidden sm:block w-px bg-slate-200 my-1" />

              <div className="relative flex-1 flex items-center">
                <MapPin className="w-4 h-4 text-slate-400 absolute left-3.5" />
                <input
                  type="text"
                  placeholder="Location or 'Remote'"
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
                  className="w-full pl-10 pr-3 py-2.5 text-xs sm:text-sm text-slate-900 placeholder:text-slate-400 bg-transparent focus:outline-none"
                />
              </div>

              <Button
                type="submit"
                variant="primary"
                size="md"
                className="shrink-0"
                icon={Search}
              >
                Search Jobs
              </Button>
            </div>

            {/* Quick search suggestions */}
            <div className="pt-3 flex flex-wrap items-center justify-center gap-1.5 text-xs text-slate-500">
              <span className="text-[11px] font-medium text-slate-400">Popular:</span>
              {["Software Engineer", "Product Manager", "Data Analyst", "Remote", "DevOps"].map(
                (term) => (
                  <button
                    key={term}
                    type="button"
                    onClick={() => handleQuickTagClick(term)}
                    className="px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-[11px] font-medium transition-colors cursor-pointer"
                  >
                    {term}
                  </button>
                )
              )}
            </div>
          </form>

          {/* Real platform data summary */}
          {stats.totalJobs > 0 && (
            <div className="pt-4 flex flex-wrap items-center justify-center gap-4 sm:gap-8 text-xs text-slate-500 font-medium">
              <div>
                <span className="font-bold text-slate-900">{stats.totalJobs.toLocaleString()}</span> active vacancies
              </div>
              <div className="hidden sm:inline text-slate-300">•</div>
              <div>
                <span className="font-bold text-slate-900">{stats.totalCompanies.toLocaleString()}</span> hiring employers
              </div>
              <div className="hidden sm:inline text-slate-300">•</div>
              <div>
                Direct applications to official career portals
              </div>
            </div>
          )}
        </div>
      </section>

      {/* 3. RECENTLY INDEXED LIVE JOBS */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
          <div className="space-y-1">
            <div className="inline-flex items-center space-x-1.5 text-xs font-bold text-blue-600 uppercase tracking-wider">
              <Clock className="w-3.5 h-3.5" />
              <span>Real-Time Index</span>
            </div>
            <h2 className="text-xl sm:text-2xl font-extrabold text-slate-900 tracking-tight">
              Recently published opportunities
            </h2>
            <p className="text-xs text-slate-500">
              Verified job openings synced from employer career portals within the last 24 hours.
            </p>
          </div>

          <Link
            href="/jobs?sort_by=newest"
            className="inline-flex items-center space-x-1 text-xs font-bold text-blue-600 hover:text-blue-700 hover:underline shrink-0"
          >
            <span>View all verified jobs</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[1, 2, 3, 4].map((i) => (
              <div
                key={i}
                className="h-32 bg-white rounded-2xl border border-slate-200 animate-pulse p-4"
              />
            ))}
          </div>
        ) : recentJobs.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {recentJobs.slice(0, 6).map((job) => (
              <JobCard key={job.id} job={job} />
            ))}
          </div>
        ) : (
          <div className="text-center py-12 bg-white rounded-2xl border border-slate-200 p-6 space-y-2">
            <Briefcase className="w-8 h-8 text-slate-400 mx-auto" />
            <p className="text-sm font-semibold text-slate-700">No recent jobs indexed right now</p>
            <Link href="/jobs" className="text-xs font-bold text-blue-600 hover:underline">
              Browse full discovery directory
            </Link>
          </div>
        )}
      </section>

      {/* 4. CAREER TRACKS / DISCIPLINES */}
      <section id="tracks" className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-6">
        <div className="space-y-1">
          <div className="inline-flex items-center space-x-1.5 text-xs font-bold text-blue-600 uppercase tracking-wider">
            <Layers className="w-3.5 h-3.5" />
            <span>Taxonomy</span>
          </div>
          <h2 className="text-xl sm:text-2xl font-extrabold text-slate-900 tracking-tight">
            Explore positions by career track
          </h2>
          <p className="text-xs text-slate-500">
            Navigate canonical industry disciplines structured with verified technical skills and roles.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {professions.slice(0, 12).map((prof) => {
            const Icon = TRACK_ICON_MAP[prof.key] || Briefcase;

            return (
              <Link
                key={prof.key}
                href={`/jobs?profession=${encodeURIComponent(prof.key)}`}
                className="group bg-white rounded-2xl border border-slate-200/90 p-5 hover:border-blue-500 hover:shadow-xs transition-all duration-150 flex flex-col justify-between space-y-4"
              >
                <div className="space-y-3">
                  <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-700 flex items-center justify-center font-bold group-hover:bg-blue-600 group-hover:text-white transition-colors shrink-0">
                    <Icon className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-slate-900 group-hover:text-blue-600 transition-colors">
                      {prof.label}
                    </h3>
                    <p className="text-xs text-slate-500 line-clamp-2 mt-1 leading-relaxed">
                      {prof.description}
                    </p>
                  </div>
                </div>

                <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-xs">
                  <span className="font-semibold text-slate-600">
                    {prof.count.toLocaleString()} open position{prof.count === 1 ? "" : "s"}
                  </span>
                  <span className="text-blue-600 font-bold group-hover:translate-x-0.5 transition-transform flex items-center">
                    Browse <ChevronRight className="w-3.5 h-3.5" />
                  </span>
                </div>
              </Link>
            );
          })}
        </div>
      </section>

      {/* 5. HOW GETMEHIRE WORKS */}
      <section className="bg-white border-y border-slate-200/90 py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-12">
          <div className="text-center max-w-2xl mx-auto space-y-2">
            <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
              A direct path from discovery to application
            </h2>
            <p className="text-xs sm:text-sm text-slate-600">
              Designed to help you discover real positions and apply directly on employer systems.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {/* Step 1 */}
            <div className="bg-slate-50 rounded-2xl border border-slate-200/80 p-6 space-y-3">
              <div className="w-9 h-9 rounded-xl bg-blue-600 text-white font-extrabold text-xs flex items-center justify-center shadow-2xs">
                1
              </div>
              <h3 className="text-sm font-bold text-slate-900">
                Discover Verified Positions
              </h3>
              <p className="text-xs text-slate-600 leading-relaxed">
                Vacancies are synchronized directly with official enterprise applicant tracking systems including Greenhouse, Lever, Ashby, and Workday.
              </p>
            </div>

            {/* Step 2 */}
            <div className="bg-slate-50 rounded-2xl border border-slate-200/80 p-6 space-y-3">
              <div className="w-9 h-9 rounded-xl bg-blue-600 text-white font-extrabold text-xs flex items-center justify-center shadow-2xs">
                2
              </div>
              <h3 className="text-sm font-bold text-slate-900">
                Benchmark &amp; Tailor
              </h3>
              <p className="text-xs text-slate-600 leading-relaxed">
                Benchmark your experience against specific role requirements in Resume Studio. Identify matched skills and missing criteria before applying.
              </p>
            </div>

            {/* Step 3 */}
            <div className="bg-slate-50 rounded-2xl border border-slate-200/80 p-6 space-y-3">
              <div className="w-9 h-9 rounded-xl bg-blue-600 text-white font-extrabold text-xs flex items-center justify-center shadow-2xs">
                3
              </div>
              <h3 className="text-sm font-bold text-slate-900">
                Apply Directly to Employers
              </h3>
              <p className="text-xs text-slate-600 leading-relaxed">
                Follow direct provenance links to apply on the employer&apos;s authentic application portal. We never submit applications on your behalf.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* 6. RESUME STUDIO & APPLICANT TOOLS */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="bg-white rounded-2xl border border-slate-200/90 p-8 sm:p-12 grid grid-cols-1 lg:grid-cols-12 gap-8 items-center shadow-xs">
          <div className="lg:col-span-7 space-y-5">
            <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
              Prepare your resume for employer ATS requirements
            </h2>

            <p className="text-xs sm:text-sm text-slate-600 leading-relaxed max-w-xl">
              Compare your experience directly against authentic job descriptions. Identify required keywords, improve bullet points with action-oriented phrasing, and export clean, ATS-readable single-column resumes.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
              <div className="flex items-center space-x-2 text-xs text-slate-700">
                <CheckCircle2 className="w-4 h-4 text-blue-600 shrink-0" />
                <span>Deterministic keyword fit comparison</span>
              </div>
              <div className="flex items-center space-x-2 text-xs text-slate-700">
                <CheckCircle2 className="w-4 h-4 text-blue-600 shrink-0" />
                <span>Action-oriented bullet phrasing</span>
              </div>
              <div className="flex items-center space-x-2 text-xs text-slate-700">
                <CheckCircle2 className="w-4 h-4 text-blue-600 shrink-0" />
                <span>ATS-compatible single column export</span>
              </div>
              <div className="flex items-center space-x-2 text-xs text-slate-700">
                <CheckCircle2 className="w-4 h-4 text-blue-600 shrink-0" />
                <span>Private candidate profile storage</span>
              </div>
            </div>

            <div className="pt-4 flex flex-wrap items-center gap-3">
              <Link href="/resume-studio">
                <Button variant="primary" size="md">
                  Open Resume Studio
                </Button>
              </Link>
              <Link href="/profile">
                <Button variant="secondary" size="md">
                  Candidate Profile &amp; Resumes
                </Button>
              </Link>
            </div>
          </div>

          <div className="lg:col-span-5 bg-slate-50 rounded-2xl border border-slate-200 p-6 space-y-4">
            <div className="space-y-1">
              <span className="text-xs font-bold text-slate-900 block">Requirement Benchmarking</span>
              <p className="text-[11px] text-slate-500">How Resume Studio evaluates your resume against target roles:</p>
            </div>

            <div className="space-y-3 pt-1 text-xs">
              <div className="p-3 bg-white rounded-xl border border-slate-200/80 space-y-1">
                <div className="flex items-center justify-between text-slate-800 font-semibold text-[11px]">
                  <span>Matched Skills</span>
                  <span className="text-emerald-700 font-bold">Identified in your resume</span>
                </div>
                <p className="text-[11px] text-slate-500">Technologies and qualifications found in both your profile and the job description.</p>
              </div>

              <div className="p-3 bg-white rounded-xl border border-slate-200/80 space-y-1">
                <div className="flex items-center justify-between text-slate-800 font-semibold text-[11px]">
                  <span>Missing Criteria</span>
                  <span className="text-amber-700 font-bold">Areas to address</span>
                </div>
                <p className="text-[11px] text-slate-500">Skills or certifications listed by the employer that can be added if applicable.</p>
              </div>

              <div className="p-3 bg-white rounded-xl border border-slate-200/80 space-y-1">
                <div className="flex items-center justify-between text-slate-800 font-semibold text-[11px]">
                  <span>Clean Export</span>
                  <span className="text-blue-700 font-bold">PDF &amp; DOCX</span>
                </div>
                <p className="text-[11px] text-slate-500">Formatted to parse cleanly in standard employer ATS screeners.</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 7. VERIFIED ENTERPRISE HIRING ORGANIZATIONS */}
      {companies.length > 0 && (
        <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
            <div className="space-y-1">
              <div className="inline-flex items-center space-x-1.5 text-xs font-bold text-blue-600 uppercase tracking-wider">
                <Building2 className="w-3.5 h-3.5" />
                <span>Verified Employers</span>
              </div>
              <h2 className="text-xl sm:text-2xl font-extrabold text-slate-900 tracking-tight">
                Top companies actively hiring
              </h2>
              <p className="text-xs text-slate-500">
                Direct hiring pipelines verified through enterprise career platforms.
              </p>
            </div>

            <Link
              href="/jobs"
              className="inline-flex items-center space-x-1 text-xs font-bold text-blue-600 hover:text-blue-700 hover:underline shrink-0"
            >
              <span>Explore all hiring companies</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {companies.map((comp) => (
              <Link
                key={comp.id}
                href={`/jobs?company=${encodeURIComponent(comp.canonical_name)}`}
                className="group bg-white rounded-2xl border border-slate-200/90 p-5 hover:border-blue-500 hover:shadow-xs transition-all duration-150 flex items-center justify-between"
              >
                <div className="flex items-center space-x-3.5 min-w-0">
                  <CompanyAvatar name={comp.canonical_name} logoUrl={comp.logo_url} size="md" />
                  <div className="min-w-0">
                    <h3 className="text-sm font-bold text-slate-900 group-hover:text-blue-600 truncate transition-colors">
                      {comp.canonical_name}
                    </h3>
                    <p className="text-xs text-slate-500">
                      {comp.active_jobs_count} open position{comp.active_jobs_count === 1 ? "" : "s"}
                    </p>
                  </div>
                </div>
                <ChevronRight className="w-4 h-4 text-slate-400 group-hover:text-blue-600 group-hover:translate-x-0.5 transition-all shrink-0 ml-2" />
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* 8. CALL TO ACTION */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="bg-slate-900 rounded-2xl p-8 sm:p-12 text-center text-white space-y-6">
          <div className="max-w-2xl mx-auto space-y-3">
            <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
              Start your job search on GetMeHire
            </h2>
            <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
              Explore open positions from verified employer feeds or create an account to save jobs, track applications, and tailor resumes.
            </p>
          </div>

          <div className="flex flex-wrap items-center justify-center gap-3">
            <Link href="/jobs">
              <Button
                variant="primary"
                size="md"
                className="bg-blue-600 hover:bg-blue-500 text-white font-bold"
              >
                Search Open Jobs
              </Button>
            </Link>
            <Link href="/register">
              <Button
                variant="outline"
                size="md"
                className="bg-transparent hover:bg-slate-800 text-slate-200 border-slate-700 font-semibold"
              >
                Create Candidate Account
              </Button>
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
