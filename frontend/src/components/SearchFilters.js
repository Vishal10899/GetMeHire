"use client";

import {
  Filter,
  RotateCcw,
  MapPin,
  Building2,
  Globe,
  Calendar,
  Briefcase,
  Award,
  Layers,
} from "lucide-react";

const JOB_CATEGORIES = [
  { value: "", label: "All Categories & Industries" },
  { value: "ENGINEERING", label: "Software Engineering & IT" },
  { value: "SALES_BIZDEV", label: "Sales & Business Development" },
  { value: "OPERATIONS_LOGISTICS", label: "Operations, People & Logistics" },
  { value: "PRODUCT_DESIGN", label: "Product Management & UI/UX" },
  { value: "DATA_AI", label: "Data Science & AI" },
  { value: "MARKETING_GROWTH", label: "Marketing & Growth" },
  { value: "FINANCE_ACCOUNTING", label: "Finance & Accounting" },
  { value: "CUSTOMER_SUPPORT", label: "Customer Support & Services" },
  { value: "LEGAL_ADMIN", label: "Legal & Corporate Administration" },
  { value: "HR_RECRUITMENT", label: "HR & Talent Acquisition" },
  { value: "HEALTHCARE_MEDICAL", label: "Healthcare & Medical" },
  { value: "HOSPITALITY_RETAIL", label: "Hospitality, Food & Retail" },
  { value: "EDUCATION_TRAINING", label: "Education & EdTech" },
  { value: "MANUFACTURING_TRADES", label: "Manufacturing & Physical Trades" },
];

const POPULAR_COUNTRIES = [
  { code: "", label: "All Countries (Global)" },
  { code: "US", label: "United States (US)" },
  { code: "GB", label: "United Kingdom (GB)" },
  { code: "IN", label: "India (IN)" },
  { code: "IE", label: "Ireland (IE)" },
  { code: "SG", label: "Singapore (SG)" },
  { code: "CA", label: "Canada (CA)" },
  { code: "JP", label: "Japan (JP)" },
  { code: "FR", label: "France (FR)" },
  { code: "DE", label: "Germany (DE)" },
  { code: "AU", label: "Australia (AU)" },
  { code: "CH", label: "Switzerland (CH)" },
  { code: "NL", label: "Netherlands (NL)" },
];

const EXPERIENCE_RANGES = [
  { value: "", label: "All Experience Ranges" },
  { value: "internship", label: "Internship" },
  { value: "entry", label: "Entry Level" },
  { value: "0-1", label: "0–1 years" },
  { value: "1-3", label: "1–3 years" },
  { value: "3-5", label: "3–5 years" },
  { value: "5-8", label: "5–8 years" },
  { value: "8+", label: "8+ years" },
  { value: "unspecified", label: "Not Specified" },
];

const DATE_POSTED_OPTIONS = [
  { value: "", label: "Any Time" },
  { value: "24h", label: "Past 24 Hours" },
  { value: "3d", label: "Past 3 Days" },
  { value: "7d", label: "Past Week (7d)" },
  { value: "30d", label: "Past Month (30d)" },
];

const EMPLOYMENT_TYPES = [
  { value: "", label: "All Employment Types" },
  { value: "FULL_TIME", label: "Full-Time" },
  { value: "PART_TIME", label: "Part-Time" },
  { value: "CONTRACT", label: "Contract" },
  { value: "INTERNSHIP", label: "Internship" },
  { value: "FREELANCE", label: "Freelance" },
  { value: "FIXED_TERM", label: "Fixed-Term" },
  { value: "TEMPORARY", label: "Temporary" },
  { value: "SEASONAL", label: "Seasonal" },
  { value: "SHIFT_BASED", label: "Shift-Based" },
  { value: "APPRENTICESHIP", label: "Apprenticeship" },
  { value: "PERMANENT", label: "Permanent" },
  { value: "CASUAL", label: "Casual" },
  { value: "COMMISSION", label: "Commission-Based" },
];

const REMOTE_ELIGIBILITY_OPTIONS = [
  { value: "", label: "All Remote Eligibilities" },
  { value: "WORLDWIDE", label: "Worldwide Remote" },
  { value: "COUNTRY_RESTRICTED", label: "Country-Restricted" },
  { value: "REGION_RESTRICTED", label: "Region-Restricted" },
  { value: "TIMEZONE_RESTRICTED", label: "Timezone-Restricted" },
  { value: "EMPLOYER_DEFINED", label: "Employer-Defined" },
];

const POPULAR_SKILLS = [
  "Python",
  "FastAPI",
  "React",
  "TypeScript",
  "PostgreSQL",
  "Docker",
  "AWS",
  "Kubernetes",
  "Go",
  "Next.js",
  "SQL",
  "Linux",
];

export default function SearchFilters({
  filters = {},
  setFilters,
  onChange,
  onFilterChange,
  onReset,
}) {
  const updateFilters = (updater) => {
    const notify = onChange || onFilterChange;
    if (typeof updater === "function") {
      if (setFilters) {
        setFilters(updater);
      } else if (notify) {
        const next = updater(filters);
        notify(next);
      }
    } else {
      if (setFilters) setFilters((prev) => ({ ...prev, ...updater }));
      if (notify) notify(updater);
    }
  };

  const handleRemoteToggle = (val) => {
    updateFilters((prev) => {
      const active = (prev.remote_type === val || prev.work_arrangement === val);
      return {
        ...prev,
        remote_type: active ? "" : val,
        work_arrangement: active ? "" : val,
        page: 1,
      };
    });
  };

  const handleSkillToggle = (skill) => {
    updateFilters((prev) => {
      const current = prev.skills || [];
      const updated = current.includes(skill)
        ? current.filter((s) => s !== skill)
        : [...current, skill];
      return { ...prev, skills: updated, page: 1 };
    });
  };

  return (
    <aside className="bg-white rounded-2xl border border-slate-200/90 p-5 shadow-xs space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b border-slate-100">
        <div className="flex items-center space-x-2">
          <Filter className="w-4 h-4 text-blue-600" />
          <h2 className="font-bold text-slate-900 text-sm">Filter Criteria</h2>
        </div>
        <button
          onClick={onReset}
          className="flex items-center space-x-1 text-xs font-semibold text-slate-500 hover:text-blue-600 transition-colors cursor-pointer"
        >
          <RotateCcw className="w-3 h-3" />
          <span>Reset all</span>
        </button>
      </div>

      <div className="space-y-5">
        {/* Country Selector */}
        <div>
          <label className="flex items-center space-x-1.5 text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
            <Globe className="w-3.5 h-3.5 text-slate-400" />
            <span>Country</span>
          </label>
          <select
            value={filters.country_code || ""}
            onChange={(e) =>
              updateFilters((prev) => ({
                ...prev,
                country_code: e.target.value,
                page: 1,
              }))
            }
            className="w-full text-xs rounded-xl border border-slate-200 bg-slate-50 py-2.5 px-3 focus:border-blue-500 focus:bg-white font-medium text-slate-800 transition-colors"
          >
            {POPULAR_COUNTRIES.map((c) => (
              <option key={c.code} value={c.code}>
                {c.label}
              </option>
            ))}
          </select>
        </div>

        {/* Job Category / Industry Filter */}
        <div>
          <label className="flex items-center space-x-1.5 text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
            <Layers className="w-3.5 h-3.5 text-slate-400" />
            <span>Job Category / Industry</span>
          </label>
          <select
            value={filters.category || ""}
            onChange={(e) =>
              updateFilters((prev) => ({
                ...prev,
                category: e.target.value,
                page: 1,
              }))
            }
            className="w-full text-xs rounded-xl border border-slate-200 bg-slate-50 py-2.5 px-3 focus:border-blue-500 focus:bg-white font-medium text-slate-800 transition-colors cursor-pointer"
          >
            {JOB_CATEGORIES.map((cat) => (
              <option key={cat.value} value={cat.value}>
                {cat.label}
              </option>
            ))}
          </select>
        </div>

        {/* Work Arrangement & Remote Eligibility */}
        <div>
          <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-2.5">
            Work Arrangement
          </label>
          <div className="grid grid-cols-3 gap-1.5 mb-2.5">
            {[
              { key: "REMOTE", label: "Remote" },
              { key: "HYBRID", label: "Hybrid" },
              { key: "ONSITE", label: "On-site" },
              { key: "FIELD_BASED", label: "Field" },
              { key: "FLEXIBLE", label: "Flexible" },
            ].map((item) => {
              const selected = (filters.work_arrangement || filters.remote_type) === item.key;
              return (
                <button
                  key={item.key}
                  type="button"
                  onClick={() => handleRemoteToggle(item.key)}
                  className={`py-2 px-2 rounded-xl text-xs font-bold border transition-all cursor-pointer ${
                    selected
                      ? "bg-blue-600 border-blue-600 text-white shadow-2xs"
                      : "bg-slate-50 border-slate-200 text-slate-700 hover:bg-slate-100 hover:border-slate-300"
                  }`}
                >
                  {item.label}
                </button>
              );
            })}
          </div>

          <div>
            <label className="text-[11px] font-semibold text-slate-500 mb-1 block">
              Remote Eligibility
            </label>
            <select
              value={filters.remote_eligibility || ""}
              onChange={(e) =>
                updateFilters((prev) => ({
                  ...prev,
                  remote_eligibility: e.target.value,
                  page: 1,
                }))
              }
              className="w-full text-xs rounded-xl border border-slate-200 bg-slate-50 py-2 px-2.5 focus:border-blue-500 focus:bg-white font-medium text-slate-800 transition-colors"
            >
              {REMOTE_ELIGIBILITY_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Early Career & Freshers */}
        <div>
          <label className="flex items-center space-x-1.5 text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
            <Award className="w-3.5 h-3.5 text-teal-600" />
            <span>Early Career & Freshers</span>
          </label>
          <select
            value={filters.early_career_category || ""}
            onChange={(e) =>
              updateFilters((prev) => ({
                ...prev,
                early_career_category: e.target.value,
                page: 1,
              }))
            }
            className="w-full text-xs rounded-xl border border-slate-200 bg-slate-50 py-2.5 px-3 focus:border-blue-500 focus:bg-white font-medium text-slate-800 transition-colors"
          >
            <option value="">All Career Stages</option>
            <option value="TRUE_FRESHER">🎓 True Fresher (0 Years Required)</option>
            <option value="GRADUATE">🎓 Graduate Programs & Batches</option>
            <option value="ENTRY_LEVEL">🌱 Entry-Level (0–1 Years)</option>
            <option value="INTERNSHIP">💼 Internships & Co-ops</option>
            <option value="TRAINEE">🌟 Management & Graduate Trainees</option>
            <option value="APPRENTICESHIP">🛠 Apprenticeships</option>
            <option value="EXPERIENCE_FLEXIBLE">⚡ Experience Flexible</option>
          </select>
        </div>

        {/* Experience Range */}
        <div>
          <label className="flex items-center space-x-1.5 text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
            <Award className="w-3.5 h-3.5 text-slate-400" />
            <span>Experience Range</span>
          </label>
          <select
            value={filters.experience_range || ""}
            onChange={(e) =>
              updateFilters((prev) => ({
                ...prev,
                experience_range: e.target.value,
                page: 1,
              }))
            }
            className="w-full text-xs rounded-xl border border-slate-200 bg-slate-50 py-2.5 px-3 focus:border-blue-500 focus:bg-white font-medium text-slate-800 transition-colors"
          >
            {EXPERIENCE_RANGES.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        {/* Date Posted */}
        <div>
          <label className="flex items-center space-x-1.5 text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
            <Calendar className="w-3.5 h-3.5 text-slate-400" />
            <span>Date Posted</span>
          </label>
          <select
            value={filters.date_posted || ""}
            onChange={(e) =>
              updateFilters((prev) => ({
                ...prev,
                date_posted: e.target.value,
                page: 1,
              }))
            }
            className="w-full text-xs rounded-xl border border-slate-200 bg-slate-50 py-2.5 px-3 focus:border-blue-500 focus:bg-white font-medium text-slate-800 transition-colors"
          >
            {DATE_POSTED_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        {/* Employment Type */}
        <div>
          <label className="flex items-center space-x-1.5 text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
            <Briefcase className="w-3.5 h-3.5 text-slate-400" />
            <span>Employment Type</span>
          </label>
          <select
            value={filters.employment_type || ""}
            onChange={(e) =>
              updateFilters((prev) => ({
                ...prev,
                employment_type: e.target.value,
                page: 1,
              }))
            }
            className="w-full text-xs rounded-xl border border-slate-200 bg-slate-50 py-2.5 px-3 focus:border-blue-500 focus:bg-white font-medium text-slate-800 transition-colors"
          >
            {EMPLOYMENT_TYPES.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        {/* Minimum Salary Slider */}
        <div>
          <div className="flex justify-between items-center mb-2">
            <label className="text-xs font-bold uppercase tracking-wider text-slate-400">
              Minimum Salary
            </label>
            <span className="text-xs font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-md border border-emerald-200/80">
              {filters.min_salary
                ? `$${Number(filters.min_salary).toLocaleString()} / yr`
                : "Any"}
            </span>
          </div>
          <div className="space-y-2">
            <input
              type="range"
              min="0"
              max="250000"
              step="10000"
              value={filters.min_salary || 0}
              onChange={(e) =>
                updateFilters((prev) => ({
                  ...prev,
                  min_salary: e.target.value > 0 ? Number(e.target.value) : "",
                  page: 1,
                }))
              }
              className="w-full accent-blue-600 cursor-pointer"
            />
            <div className="flex justify-between text-[11px] text-slate-400 font-medium">
              <span>$0</span>
              <span>$125k</span>
              <span>$250k+</span>
            </div>
          </div>
        </div>

        {/* Location or City Filter */}
        <div>
          <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
            City or Region
          </label>
          <div className="relative">
            <input
              type="text"
              placeholder="e.g. San Francisco, London, Bengaluru..."
              value={filters.location || ""}
              onChange={(e) =>
                updateFilters((prev) => ({
                  ...prev,
                  location: e.target.value,
                  page: 1,
                }))
              }
              className="w-full text-xs rounded-xl border border-slate-200 bg-slate-50 py-2.5 pl-8 pr-3 focus:border-blue-500 focus:bg-white text-slate-800 font-medium transition-colors"
            />
            <MapPin className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-3" />
          </div>
        </div>

        {/* Company Filter */}
        <div>
          <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
            Hiring Company
          </label>
          <div className="relative">
            <input
              type="text"
              placeholder="e.g. Stripe, Canonical, Bunq..."
              value={filters.company || ""}
              onChange={(e) =>
                updateFilters((prev) => ({
                  ...prev,
                  company: e.target.value,
                  page: 1,
                }))
              }
              className="w-full text-xs rounded-xl border border-slate-200 bg-slate-50 py-2.5 pl-8 pr-3 focus:border-blue-500 focus:bg-white text-slate-800 font-medium transition-colors"
            />
            <Building2 className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-3" />
          </div>
        </div>

        {/* Popular Key Technologies & Skills */}
        <div>
          <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
            Key Technologies &amp; Skills
          </label>
          <div className="flex flex-wrap gap-1.5">
            {POPULAR_SKILLS.map((skill) => {
              const active = (filters.skills || []).includes(skill);
              return (
                <button
                  key={skill}
                  type="button"
                  onClick={() => handleSkillToggle(skill)}
                  className={`px-2.5 py-1 rounded-lg text-xs font-semibold border transition-all cursor-pointer ${
                    active
                      ? "bg-blue-600 border-blue-600 text-white shadow-2xs"
                      : "bg-slate-50 border-slate-200 text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                  }`}
                >
                  {skill}
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </aside>
  );
}
