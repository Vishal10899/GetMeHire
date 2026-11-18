"use client";

import { useState, useEffect, useCallback, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  FileText,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  Download,
  Save,
  Search,
  Building2,
  MapPin,
  ArrowRight,
  ArrowLeft,
  Check,
  Edit3,
  Eye,
  Sliders,
  Briefcase,
  User,
  Plus,
  X,
  Loader2,
  ShieldCheck,
  Lock,
  ChevronRight,
  RotateCcw,
  Zap,
  GraduationCap,
  Clock,
  Target,
  Layers,
  Award,
  Palette,
} from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/authContext";
import { motion, AnimatePresence } from "motion/react";
import CompanyAvatar from "@/components/CompanyAvatar";
import AnimatedDialog from "@/components/animations/AnimatedDialog";
import { Button, Input, Card, Badge } from "@/components/ui";

const DEFAULT_TEMPLATES = [
  {
    id: "classic_single",
    name: "Classic Single-Column",
    profession: "GENERAL",
    description: "100% linear ATS text flow, serif typography, guaranteed ATS parsing compatibility.",
    tag: "Highest Compatibility",
    color_palette: { primary: "#000000", accent: "#333333", divider: "#666666" },
  },
  {
    id: "modern_professional",
    name: "Modern Professional",
    profession: "GENERAL",
    description: "Clean sans-serif typography with corporate deep blue accents and section dividers.",
    tag: "Recommended",
    color_palette: { primary: "#1e3a8a", accent: "#1e293b", divider: "#3b82f6" },
  },
  {
    id: "software_engineering",
    name: "Software & DevOps Engineering",
    profession: "ENGINEERING",
    description: "Engineered for Software Developers, Systems Architects, and DevOps. Prioritizes tech stack, scale, and repositories.",
    tag: "Tech Stack Priority",
    color_palette: { primary: "#0f172a", accent: "#2563eb", divider: "#3b82f6" },
  },
  {
    id: "ai_ml_engineer",
    name: "AI, Machine Learning & LLM Specialist",
    profession: "DATA_AI",
    description: "Optimized for AI Researchers, ML Engineers, and LLM Specialists. Focuses on model architectures, fine-tuning, and inference latency.",
    tag: "AI Architecture",
    color_palette: { primary: "#1e1b4b", accent: "#4f46e5", divider: "#6366f1" },
  },
  {
    id: "data_analyst",
    name: "Data Analyst & Analytics Engineer",
    profession: "DATA_AI",
    description: "Emphasizes SQL, business intelligence, data pipelining, and commercial impact.",
    tag: "Quant Focused",
    color_palette: { primary: "#0f766e", accent: "#0d9488", divider: "#14b8a6" },
  },
  {
    id: "executive_leadership",
    name: "Executive Leadership & C-Suite",
    profession: "LEADERSHIP",
    description: "Structured for VPs, Directors, and C-Suite. Focuses on P&L ownership, organizational growth, and board governance.",
    tag: "Executive Impact",
    color_palette: { primary: "#09090b", accent: "#27272a", divider: "#71717a" },
  },
];

const STEPS = [
  { step: 1, id: "select_job", label: "1. Target Opportunity", icon: Briefcase },
  { step: 2, id: "analyze", label: "2. Deep ATS Match", icon: Sparkles },
  { step: 3, id: "improve", label: "3. Tailor & Architecture", icon: Edit3 },
  { step: 4, id: "export", label: "4. Preview & Export", icon: Download },
];

function ResumeStudioContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, loading: authLoading } = useAuth();

  // Workflow Step State (1: Select, 2: Analyze, 3: Improve, 4: Preview/Export)
  const [currentStep, setCurrentStep] = useState(1);

  // Job selection mode in Step 1: 'database' vs 'custom_jd'
  const [jobMode, setJobMode] = useState("database");
  const [customJobTitle, setCustomJobTitle] = useState("");
  const [customCompanyName, setCustomCompanyName] = useState("");
  const [customJDText, setCustomJDText] = useState("");

  // Core Resume Data
  const [resumeData, setResumeData] = useState({
    full_name: "",
    email: "",
    phone: "",
    location: "",
    headline: "",
    summary: "",
    skills: [],
    work_experience: [],
    education: [],
    projects: [],
    certifications: [],
  });

  const [targetJobId, setTargetJobId] = useState(null);
  const [targetJob, setTargetJob] = useState(null);
  const [availableTemplates, setAvailableTemplates] = useState(DEFAULT_TEMPLATES);
  const [templateFilter, setTemplateFilter] = useState("ALL");
  const [selectedTemplate, setSelectedTemplate] = useState("software_engineering");
  const [recommendedTemplateMeta, setRecommendedTemplateMeta] = useState(null);
  const [versionTitle, setVersionTitle] = useState("My Resume");
  const [activeVersionId, setActiveVersionId] = useState(null);
  const [isEntitled, setIsEntitled] = useState(true);

  // Search & Async State
  const [jobSearchQuery, setJobSearchQuery] = useState("");
  const [jobSearchResults, setJobSearchResults] = useState([]);
  const [searchingJobs, setSearchingJobs] = useState(false);
  const [loadingMaster, setLoadingMaster] = useState(true);

  // ATS Deep Match State
  const [jdMatchResult, setJdMatchResult] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [tailoring, setTailoring] = useState(false);

  // Export State
  const [exportingPdf, setExportingPdf] = useState(false);
  const [exportingDocx, setExportingDocx] = useState(false);
  const [savingVersion, setSavingVersion] = useState(false);
  const [showUnlockModal, setShowUnlockModal] = useState(false);
  const [pendingExportType, setPendingExportType] = useState(null);
  const [unlocking, setUnlocking] = useState(false);
  const [feedbackMsg, setFeedbackMsg] = useState(null);

  useEffect(() => {
    if (!authLoading && !user) {
      router.push("/login?redirect=/resume-studio");
      return;
    }
    if (user) {
      loadInitialData();
    }
  }, [user, authLoading]);

  const loadInitialData = async () => {
    setLoadingMaster(true);
    try {
      // 1. Load Master Resume
      const data = await api.getMasterResume();
      if (data) {
        setResumeData({
          full_name: data.full_name || "",
          email: data.email || user.email || "",
          phone: data.phone_number || "",
          location: data.current_location || "",
          headline: data.headline || "",
          summary: data.summary || "",
          skills: data.skills || [],
          work_experience: data.work_experience || [],
          education: data.education || [],
          projects: data.projects || [],
          certifications: data.certifications || [],
        });
      }

      // 2. Load Role Templates Catalog
      try {
        const tplRes = await api.getRoleTemplates();
        if (tplRes && tplRes.templates && tplRes.templates.length > 0) {
          setAvailableTemplates(tplRes.templates);
        }
      } catch (e) {
        console.warn("Could not fetch full role templates catalog, using default:", e);
      }

      // 3. Check for job_id in URL params
      const paramJobId = searchParams.get("job_id");
      if (paramJobId) {
        const jobIdNum = parseInt(paramJobId, 10);
        if (!isNaN(jobIdNum)) {
          loadTargetJob(jobIdNum);
        }
      }
    } catch (err) {
      console.error("Failed to load initial resume data:", err);
    } finally {
      setLoadingMaster(false);
    }
  };

  const loadTargetJob = async (id) => {
    try {
      const job = await api.getJob(id);
      if (job) {
        setTargetJobId(job.id);
        setTargetJob(job);
        setVersionTitle(`Resume - ${job.company_name} (${job.normalized_title || job.title})`);
        checkJobEntitlement(job.id);
        setCurrentStep(2);
      }
    } catch (err) {
      console.error("Failed to load target job:", err);
    }
  };

  const checkJobEntitlement = async (jobId) => {
    try {
      const res = await api.checkEntitlement(jobId);
      setIsEntitled(res.is_entitled || false);
    } catch {
      setIsEntitled(true);
    }
  };

  const handleSearchJobs = async (q) => {
    setJobSearchQuery(q);
    if (!q || q.trim().length < 2) {
      setJobSearchResults([]);
      return;
    }
    setSearchingJobs(true);
    try {
      const res = await api.getJobs({ keyword: q.trim(), page_size: 6 });
      setJobSearchResults(res.items || []);
    } catch (err) {
      console.error("Job search error:", err);
    } finally {
      setSearchingJobs(false);
    }
  };

  const handleSelectJob = (job) => {
    setTargetJobId(job.id);
    setTargetJob(job);
    setJobSearchResults([]);
    setJobSearchQuery("");
    setVersionTitle(`Resume - ${job.company_name} (${job.normalized_title || job.title})`);
    checkJobEntitlement(job.id);
    setCurrentStep(2);
  };

  const handleApplyCustomJD = () => {
    if (!customJobTitle.trim()) {
      setFeedbackMsg({ type: "error", text: "Please enter a target job title." });
      return;
    }
    if (!customJDText.trim() || customJDText.trim().length < 30) {
      setFeedbackMsg({ type: "error", text: "Please paste a descriptive job requirements text." });
      return;
    }

    const synthesizedJob = {
      id: null,
      title: customJobTitle.trim(),
      normalized_title: customJobTitle.trim(),
      company_name: customCompanyName.trim() || "Target Employer",
      description: customJDText.trim(),
      location: "Worldwide / Direct Opportunity",
      skills: [],
    };

    setTargetJobId(null);
    setTargetJob(synthesizedJob);
    setVersionTitle(`Resume - ${synthesizedJob.company_name} (${synthesizedJob.title})`);
    setIsEntitled(true); // Custom JDs are 100% free
    setCurrentStep(2);
  };

  // Run Bidirectional ATS Match Analysis
  const runDeepMatchAnalysis = async (content = resumeData) => {
    setAnalyzing(true);
    try {
      const payload = {
        job_id: targetJobId || undefined,
        job_title: targetJob?.normalized_title || targetJob?.title || customJobTitle || "Target Role",
        job_description_text: targetJob?.description || customJDText || undefined,
        company_name: targetJob?.company_name || customCompanyName || "Target Employer",
        resume_content: content,
      };

      const matchData = await api.matchJobDescription(payload);
      setJdMatchResult(matchData);

      if (matchData.recommended_template) {
        setRecommendedTemplateMeta(matchData.recommended_template);
        if (matchData.recommended_template.id) {
          setSelectedTemplate(matchData.recommended_template.id);
        }
      }
    } catch (err) {
      console.error("Deep match analysis failed:", err);
      setFeedbackMsg({ type: "error", text: "Match analysis failed: " + err.message });
    } finally {
      setAnalyzing(false);
    }
  };

  useEffect(() => {
    if (currentStep === 2 && !analyzing && targetJob) {
      runDeepMatchAnalysis();
    }
  }, [currentStep, targetJob]);

  const handleAddMissingSkill = (skillName) => {
    if (!resumeData.skills.includes(skillName)) {
      const updatedSkills = [...resumeData.skills, skillName];
      const updatedContent = { ...resumeData, skills: updatedSkills };
      setResumeData(updatedContent);
      runDeepMatchAnalysis(updatedContent);
      setFeedbackMsg({
        type: "success",
        text: `Added '${skillName}' to your resume competencies. Re-evaluated ATS score!`,
      });
    }
  };

  const handleRunTailoring = async () => {
    if (!targetJobId) {
      // For custom JD, advance to step 3 directly
      setCurrentStep(3);
      return;
    }
    setTailoring(true);
    try {
      const res = await api.tailorResume(targetJobId, activeVersionId);
      if (res.tailored_content) {
        setResumeData((prev) => ({
          ...prev,
          ...res.tailored_content,
        }));
        runDeepMatchAnalysis(res.tailored_content);
      }
      setFeedbackMsg({
        type: "success",
        text: `Tailored successfully! Match fit improved from ${res.match_score_before}% to ${res.match_score_after}%.`,
      });
      setCurrentStep(3);
    } catch (err) {
      setFeedbackMsg({ type: "error", text: err.message || "Failed to tailor resume" });
    } finally {
      setTailoring(false);
    }
  };

  const handleExportPdf = async () => {
    setExportingPdf(true);
    try {
      const fname = `${(versionTitle || "Resume").replace(/\s+/g, "_")}.pdf`;
      if (activeVersionId) {
        await api.downloadVersionPdf(activeVersionId, fname);
      } else {
        await api.downloadDirectPdf(
          {
            version_title: versionTitle,
            target_job_id: targetJobId || null,
            template_id: selectedTemplate,
            content: resumeData,
            is_master: false,
          },
          fname
        );
      }
    } catch (err) {
      if (err.status === 402) {
        setPendingExportType("pdf");
        setShowUnlockModal(true);
      } else {
        setFeedbackMsg({ type: "error", text: err.message || "PDF export failed" });
      }
    } finally {
      setExportingPdf(false);
    }
  };

  const handleExportDocx = async () => {
    setExportingDocx(true);
    try {
      const fname = `${(versionTitle || "Resume").replace(/\s+/g, "_")}.docx`;
      if (activeVersionId) {
        await api.downloadVersionDocx(activeVersionId, fname);
      } else {
        await api.downloadDirectDocx(
          {
            version_title: versionTitle,
            target_job_id: targetJobId || null,
            template_id: selectedTemplate,
            content: resumeData,
            is_master: false,
          },
          fname
        );
      }
    } catch (err) {
      if (err.status === 402) {
        setPendingExportType("docx");
        setShowUnlockModal(true);
      } else {
        setFeedbackMsg({ type: "error", text: err.message || "Word export failed" });
      }
    } finally {
      setExportingDocx(false);
    }
  };

  const handleSaveVersion = async () => {
    setSavingVersion(true);
    try {
      const saved = await api.createResumeVersion({
        version_title: versionTitle,
        target_job_id: targetJobId || null,
        template_id: selectedTemplate,
        content: resumeData,
        is_master: false,
      });
      setActiveVersionId(saved.id);
      setFeedbackMsg({
        type: "success",
        text: `Saved resume version: "${saved.version_title}" (Version #${saved.version_number})`,
      });
    } catch (err) {
      setFeedbackMsg({ type: "error", text: err.message || "Failed to save version" });
    } finally {
      setSavingVersion(false);
    }
  };

  const handleSimulatedCheckout = async () => {
    if (!targetJobId) return;
    setUnlocking(true);
    try {
      await api.checkoutTailoredResume({
        target_job_id: targetJobId,
        resume_version_id: activeVersionId || undefined,
        idempotency_key: `client_checkout_${targetJobId}_${Date.now()}`,
      });
      setIsEntitled(true);
      setShowUnlockModal(false);
      setFeedbackMsg({
        type: "success",
        text: `Unlocked tailored resume for ${targetJob?.company_name || "this vacancy"}!`,
      });
      const pendingType = pendingExportType;
      setPendingExportType(null);
      if (pendingType === "docx") {
        setTimeout(() => handleExportDocx(), 100);
      } else {
        setTimeout(() => handleExportPdf(), 100);
      }
    } catch (err) {
      setFeedbackMsg({ type: "error", text: "Checkout failed: " + err.message });
    } finally {
      setUnlocking(false);
    }
  };

  const filteredTemplates = availableTemplates.filter((t) => {
    if (templateFilter === "ALL") return true;
    return t.profession === templateFilter;
  });

  if (loadingMaster || authLoading) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-20 flex flex-col items-center justify-center">
        <Loader2 className="w-8 h-8 text-blue-600 animate-spin mb-3" />
        <p className="text-sm font-semibold text-slate-500">Loading Resume Studio &amp; AI Intelligence Engine...</p>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-6 sm:p-8 rounded-3xl border border-slate-200/90 shadow-xs">
        <div className="space-y-1">
          <div className="flex items-center space-x-2">
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
              Resume Studio
            </h1>
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-blue-100 text-blue-800">
              AI Career Intelligence
            </span>
          </div>
          <p className="text-xs sm:text-sm text-slate-600">
            Bidirectional ATS job matching, 16+ profession architectures, and verified single-column exports.
          </p>
        </div>

        {targetJob && (
          <div className="flex items-center space-x-3 p-3 bg-slate-50 rounded-2xl border border-slate-200/80">
            <CompanyAvatar name={targetJob.company_name} size="sm" />
            <div className="min-w-0">
              <p className="text-xs font-bold text-slate-900 truncate max-w-[180px]">
                {targetJob.normalized_title || targetJob.title}
              </p>
              <p className="text-[11px] text-slate-500 truncate">
                {targetJob.company_name}
              </p>
            </div>
            <button
              onClick={() => {
                setTargetJob(null);
                setTargetJobId(null);
                setJdMatchResult(null);
                setCurrentStep(1);
              }}
              className="text-xs font-semibold text-blue-600 hover:underline shrink-0 ml-1 cursor-pointer"
            >
              Change
            </button>
          </div>
        )}
      </div>

      {/* Global Feedback Banner */}
      {feedbackMsg && (
        <div
          className={`p-4 rounded-2xl text-xs flex items-center justify-between ${
            feedbackMsg.type === "error"
              ? "bg-red-50 border border-red-200 text-red-800"
              : "bg-emerald-50 border border-emerald-200 text-emerald-800"
          }`}
        >
          <div className="flex items-center space-x-2">
            {feedbackMsg.type === "error" ? (
              <AlertTriangle className="w-4 h-4 shrink-0 text-red-600" />
            ) : (
              <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600" />
            )}
            <span>{feedbackMsg.text}</span>
          </div>
          <button
            onClick={() => setFeedbackMsg(null)}
            className="text-slate-400 hover:text-slate-600 p-1 cursor-pointer"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* 4-STEP PROGRESS BREADCRUMB */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 p-1.5 bg-slate-100 rounded-2xl border border-slate-200/80">
        {STEPS.map((s) => {
          const isActive = currentStep === s.step;
          const isDone = currentStep > s.step;
          const Icon = s.icon;

          return (
            <button
              key={s.step}
              type="button"
              onClick={() => {
                if (s.step === 1 || targetJob) {
                  setCurrentStep(s.step);
                }
              }}
              className={`flex items-center space-x-2 px-3 py-2.5 rounded-xl text-xs font-bold transition-all text-left cursor-pointer ${
                isActive
                  ? "bg-white text-blue-700 shadow-2xs font-extrabold"
                  : isDone
                  ? "text-slate-700 hover:bg-slate-200/70"
                  : "text-slate-400 cursor-not-allowed"
              }`}
            >
              <div
                className={`w-5 h-5 rounded-lg flex items-center justify-center shrink-0 text-[10px] ${
                  isDone
                    ? "bg-emerald-100 text-emerald-700 font-extrabold"
                    : isActive
                    ? "bg-blue-600 text-white"
                    : "bg-slate-200 text-slate-500"
                }`}
              >
                {isDone ? <Check className="w-3 h-3" /> : s.step}
              </div>
              <span className="truncate">{s.label.split(". ")[1]}</span>
            </button>
          );
        })}
      </div>

      {/* STEP 1: SELECT OR PASTE TARGET OPPORTUNITY */}
      {currentStep === 1 && (
        <Card padding="lg" className="space-y-6 animate-fade-in">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 pb-3">
            <div>
              <h2 className="text-base font-bold text-slate-900">Step 1: Choose Your Target Opportunity</h2>
              <p className="text-xs text-slate-500">
                Benchmark against genuine live employer vacancies or paste any custom job description.
              </p>
            </div>

            {/* Mode Toggle */}
            <div className="flex items-center p-1 bg-slate-100 rounded-xl border border-slate-200 self-start sm:self-auto">
              <button
                type="button"
                onClick={() => setJobMode("database")}
                className={`px-3 py-1.5 text-xs font-bold rounded-lg transition-all ${
                  jobMode === "database"
                    ? "bg-white text-blue-700 shadow-xs"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                GetMeHire Vacancies
              </button>
              <button
                type="button"
                onClick={() => setJobMode("custom_jd")}
                className={`px-3 py-1.5 text-xs font-bold rounded-lg transition-all ${
                  jobMode === "custom_jd"
                    ? "bg-white text-blue-700 shadow-xs"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                Paste Any Job Description
              </button>
            </div>
          </div>

          {/* Mode A: Database Search */}
          {jobMode === "database" && (
            <div className="space-y-4">
              <div className="relative max-w-xl">
                <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-3.5" />
                <input
                  type="text"
                  placeholder="Search open positions by title or company (e.g. Stripe, AI Engineer, Cardiac Surgeon)..."
                  value={jobSearchQuery}
                  onChange={(e) => handleSearchJobs(e.target.value)}
                  className="w-full pl-10 pr-4 py-2.5 text-xs sm:text-sm rounded-xl border border-slate-200 bg-slate-50 focus:bg-white focus:border-blue-600 focus:outline-none"
                />
                {searchingJobs && (
                  <Loader2 className="w-4 h-4 text-slate-400 animate-spin absolute right-3.5 top-3.5" />
                )}
              </div>

              {jobSearchResults.length > 0 && (
                <div className="bg-white rounded-2xl border border-slate-200/90 shadow-sm divide-y divide-slate-100 max-h-80 overflow-y-auto">
                  {jobSearchResults.map((j) => (
                    <div
                      key={j.id}
                      onClick={() => handleSelectJob(j)}
                      className="p-3.5 hover:bg-blue-50/50 transition-colors cursor-pointer flex items-center justify-between gap-3"
                    >
                      <div className="flex items-center space-x-3 min-w-0">
                        <CompanyAvatar name={j.company_name} size="sm" />
                        <div className="min-w-0">
                          <p className="text-xs sm:text-sm font-bold text-slate-900 truncate">
                            {j.normalized_title || j.title}
                          </p>
                          <p className="text-[11px] text-slate-500">
                            {j.company_name} • {j.location || "Remote"}
                          </p>
                        </div>
                      </div>
                      <Button variant="secondary" size="sm" iconRight={ChevronRight}>
                        Select
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Mode B: Custom JD Paste */}
          {jobMode === "custom_jd" && (
            <div className="space-y-4 bg-slate-50/70 p-5 rounded-2xl border border-slate-200">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-xs font-bold text-slate-700">Target Role Title *</label>
                  <input
                    type="text"
                    placeholder="e.g. Senior Machine Learning Engineer"
                    value={customJobTitle}
                    onChange={(e) => setCustomJobTitle(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-xl border border-slate-200 bg-white focus:outline-none focus:border-blue-600"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-bold text-slate-700">Company / Employer (Optional)</label>
                  <input
                    type="text"
                    placeholder="e.g. DeepMind, Microsoft, NHS"
                    value={customCompanyName}
                    onChange={(e) => setCustomCompanyName(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-xl border border-slate-200 bg-white focus:outline-none focus:border-blue-600"
                  />
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-xs font-bold text-slate-700">
                  Job Description / Requirements Text *
                </label>
                <textarea
                  rows={6}
                  placeholder="Paste the job description, required qualifications, experience expectations, and responsibilities..."
                  value={customJDText}
                  onChange={(e) => setCustomJDText(e.target.value)}
                  className="w-full p-3 text-xs rounded-xl border border-slate-200 bg-white focus:outline-none focus:border-blue-600 leading-relaxed"
                />
              </div>

              <div className="flex justify-end pt-2">
                <Button
                  variant="primary"
                  size="md"
                  iconRight={ArrowRight}
                  onClick={handleApplyCustomJD}
                >
                  Analyze Custom Job Description
                </Button>
              </div>
            </div>
          )}

          {/* Current Selection summary if selected */}
          {targetJob && (
            <div className="p-4 bg-blue-50/60 rounded-2xl border border-blue-200 flex items-center justify-between gap-4">
              <div className="flex items-center space-x-3.5">
                <CompanyAvatar name={targetJob.company_name} size="md" />
                <div>
                  <h3 className="text-sm font-bold text-slate-900">
                    {targetJob.normalized_title || targetJob.title}
                  </h3>
                  <p className="text-xs text-slate-600">
                    {targetJob.company_name} • {targetJob.location || "Direct Requirements"}
                  </p>
                </div>
              </div>
              <Button
                variant="primary"
                size="md"
                iconRight={ArrowRight}
                onClick={() => setCurrentStep(2)}
              >
                Proceed to Deep Match
              </Button>
            </div>
          )}
        </Card>
      )}

      {/* STEP 2: BIDIRECTIONAL DEEP ATS MATCH */}
      {currentStep === 2 && (
        <Card padding="lg" className="space-y-6 animate-fade-in">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-3">
            <div>
              <h2 className="text-base font-bold text-slate-900">Step 2: Bidirectional Job-Description Match</h2>
              <p className="text-xs text-slate-500">
                Evaluating candidate experience against{" "}
                <span className="font-semibold text-slate-800">
                  {targetJob?.normalized_title || targetJob?.title || "Target Role"}
                </span>{" "}
                at {targetJob?.company_name || "Employer"}.
              </p>
            </div>

            <Button
              variant="outline"
              size="sm"
              icon={RotateCcw}
              loading={analyzing}
              onClick={() => runDeepMatchAnalysis()}
            >
              Re-evaluate
            </Button>
          </div>

          {analyzing ? (
            <div className="py-16 text-center space-y-3">
              <Loader2 className="w-8 h-8 text-blue-600 animate-spin mx-auto" />
              <p className="text-xs font-semibold text-slate-600">
                Evaluating hard skills, experience duration, degree alignment, and ATS parsing friction...
              </p>
            </div>
          ) : jdMatchResult ? (
            <div className="space-y-6">
              {/* Overall Score Header */}
              <div className="p-6 bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900 rounded-3xl text-white space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div className="space-y-1">
                    <span className="text-xs font-bold uppercase tracking-wider text-indigo-300">
                      Overall ATS Compatibility
                    </span>
                    <div className="flex items-baseline space-x-3">
                      <span className="text-4xl font-black text-white">
                        {jdMatchResult.overall_match_score}%
                      </span>
                      <Badge
                        variant={
                          jdMatchResult.overall_match_score >= 80
                            ? "success"
                            : jdMatchResult.overall_match_score >= 60
                            ? "blue"
                            : "amber"
                        }
                      >
                        {jdMatchResult.overall_match_score >= 80
                          ? "High ATS Probability"
                          : jdMatchResult.overall_match_score >= 60
                          ? "Competitive Match"
                          : "Tailoring Recommended"}
                      </Badge>
                    </div>
                  </div>

                  {jdMatchResult.recommended_template && (
                    <div className="p-3 bg-white/10 rounded-2xl border border-white/15 max-w-sm">
                      <span className="text-[10px] font-extrabold uppercase text-indigo-200 block">
                        Recommended Architecture
                      </span>
                      <p className="text-xs font-bold text-white">
                        {jdMatchResult.recommended_template.name}
                      </p>
                      <button
                        onClick={() => {
                          setSelectedTemplate(jdMatchResult.recommended_template.id);
                          setCurrentStep(3);
                        }}
                        className="text-[11px] text-blue-300 hover:text-white font-semibold underline mt-1 cursor-pointer block"
                      >
                        Adopt Recommended Architecture &rarr;
                      </button>
                    </div>
                  )}
                </div>

                {/* 5-Dimension Score Progress Grid */}
                <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 pt-3 border-t border-white/10 text-xs">
                  <div>
                    <span className="text-[10px] text-indigo-200">Skills Fit</span>
                    <p className="text-base font-bold text-white">
                      {jdMatchResult.score_breakdown.skills}%
                    </p>
                  </div>
                  <div>
                    <span className="text-[10px] text-indigo-200">Experience Alignment</span>
                    <p className="text-base font-bold text-white">
                      {jdMatchResult.score_breakdown.experience}%
                    </p>
                  </div>
                  <div>
                    <span className="text-[10px] text-indigo-200">Education Match</span>
                    <p className="text-base font-bold text-white">
                      {jdMatchResult.score_breakdown.education}%
                    </p>
                  </div>
                  <div>
                    <span className="text-[10px] text-indigo-200">Keyword Density</span>
                    <p className="text-base font-bold text-white">
                      {jdMatchResult.score_breakdown.keyword_density}%
                    </p>
                  </div>
                  <div>
                    <span className="text-[10px] text-indigo-200">ATS Formatting</span>
                    <p className="text-base font-bold text-white">
                      {jdMatchResult.score_breakdown.formatting}%
                    </p>
                  </div>
                </div>
              </div>

              {/* Skills Analysis: Matched vs Missing with 1-Click Injection */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* Matched Skills */}
                <div className="p-4 bg-emerald-50/50 rounded-2xl border border-emerald-200 space-y-2">
                  <span className="text-xs font-bold text-emerald-800 flex items-center space-x-1.5">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                    <span>Matched Requirements ({jdMatchResult.matched_skills.length})</span>
                  </span>
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {jdMatchResult.matched_skills.map((s, idx) => (
                      <span
                        key={idx}
                        title={s.resume_evidence || "Verified in resume"}
                        className="px-2.5 py-1 rounded-lg bg-white text-emerald-900 border border-emerald-300 text-xs font-semibold shadow-2xs"
                      >
                        {s.skill}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Missing Skills */}
                <div className="p-4 bg-amber-50/50 rounded-2xl border border-amber-200 space-y-2">
                  <span className="text-xs font-bold text-amber-900 flex items-center space-x-1.5">
                    <AlertTriangle className="w-4 h-4 text-amber-600" />
                    <span>Missing Skills ({jdMatchResult.missing_skills.length}) — Click to add</span>
                  </span>
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {jdMatchResult.missing_skills.map((s, idx) => (
                      <button
                        key={idx}
                        type="button"
                        onClick={() => handleAddMissingSkill(s.skill)}
                        className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-white hover:bg-amber-100 text-amber-900 border border-amber-300 text-xs font-semibold transition-colors cursor-pointer shadow-2xs"
                        title={s.suggestion}
                      >
                        <Plus className="w-3 h-3 text-amber-600" />
                        <span>{s.skill}</span>
                        {s.importance === "CRITICAL" && (
                          <span className="ml-1 text-[9px] px-1 bg-red-100 text-red-700 rounded">
                            REQ
                          </span>
                        )}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              {/* Experience & Education Alignment Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="p-4 bg-slate-50 rounded-2xl border border-slate-200 space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-800 flex items-center space-x-1.5">
                      <Clock className="w-4 h-4 text-blue-600" />
                      <span>Experience Alignment</span>
                    </span>
                    <Badge variant={jdMatchResult.experience_analysis.status === "BELOW_REQUIREMENT" ? "amber" : "success"}>
                      {jdMatchResult.experience_analysis.status}
                    </Badge>
                  </div>
                  <p className="text-xs text-slate-600 pt-1 leading-relaxed">
                    {jdMatchResult.experience_analysis.explanation}
                  </p>
                </div>

                <div className="p-4 bg-slate-50 rounded-2xl border border-slate-200 space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-800 flex items-center space-x-1.5">
                      <GraduationCap className="w-4 h-4 text-indigo-600" />
                      <span>Education Fit</span>
                    </span>
                    <Badge variant={jdMatchResult.education_analysis.status === "BELOW_REQUIREMENT" ? "amber" : "success"}>
                      {jdMatchResult.education_analysis.status}
                    </Badge>
                  </div>
                  <p className="text-xs text-slate-600 pt-1 leading-relaxed">
                    {jdMatchResult.education_analysis.explanation}
                  </p>
                </div>
              </div>

              {/* ATS Friction Points & Prioritized Actions */}
              {jdMatchResult.ats_friction_points && jdMatchResult.ats_friction_points.length > 0 && (
                <div className="p-4 bg-slate-50 rounded-2xl border border-slate-200 space-y-3">
                  <h3 className="text-xs font-bold text-slate-800 flex items-center space-x-1.5">
                    <ShieldCheck className="w-4 h-4 text-slate-600" />
                    <span>ATS Parsing Friction &amp; Formatting Checks</span>
                  </h3>
                  <div className="space-y-2">
                    {jdMatchResult.ats_friction_points.map((f, idx) => (
                      <div
                        key={idx}
                        className="p-3 bg-white rounded-xl border border-slate-200 text-xs space-y-0.5"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-slate-900">{f.rule}</span>
                          <span
                            className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                              f.severity === "CRITICAL"
                                ? "bg-red-100 text-red-700"
                                : f.severity === "WARNING"
                                ? "bg-amber-100 text-amber-800"
                                : "bg-blue-100 text-blue-800"
                            }`}
                          >
                            {f.severity}
                          </span>
                        </div>
                        <p className="text-slate-600">{f.explanation}</p>
                        <p className="text-blue-700 font-semibold pt-0.5">Tip: {f.recommendation}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-4 border-t border-slate-100">
                <Button
                  variant="outline"
                  size="md"
                  icon={ArrowLeft}
                  onClick={() => setCurrentStep(1)}
                >
                  Back to Target Job
                </Button>

                <div className="flex items-center gap-2 w-full sm:w-auto">
                  {targetJobId && (
                    <Button
                      variant="primary"
                      size="md"
                      icon={Sparkles}
                      loading={tailoring}
                      onClick={handleRunTailoring}
                    >
                      Tailor Automatically
                    </Button>
                  )}
                  <Button
                    variant="secondary"
                    size="md"
                    iconRight={ArrowRight}
                    onClick={() => setCurrentStep(3)}
                  >
                    Proceed to Architecture &amp; Review
                  </Button>
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-8">
              <Button variant="primary" size="md" onClick={() => runDeepMatchAnalysis()}>
                Run Deep ATS Match Analysis
              </Button>
            </div>
          )}
        </Card>
      )}

      {/* STEP 3: ROLE TEMPLATE ARCHITECTURE & EDITING */}
      {currentStep === 3 && (
        <Card padding="lg" className="space-y-6 animate-fade-in">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-3">
            <div>
              <h2 className="text-base font-bold text-slate-900">Step 3: Role-Specific Template Architecture</h2>
              <p className="text-xs text-slate-500">
                Select from 16+ professional recruitment structures tailored to your target discipline.
              </p>
            </div>

            <Button
              variant="primary"
              size="sm"
              icon={Save}
              loading={savingVersion}
              onClick={handleSaveVersion}
            >
              Save Version
            </Button>
          </div>

          {/* Profession Category Filter */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-xs font-bold uppercase tracking-wider text-slate-400">
                Select Architecture ({availableTemplates.length} Available)
              </label>
              {recommendedTemplateMeta && (
                <span className="text-[11px] font-bold text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded-md border border-indigo-200">
                  Recommended: {recommendedTemplateMeta.name}
                </span>
              )}
            </div>

            <div className="flex flex-wrap gap-1.5 pb-2">
              {[
                { label: "All Professions", val: "ALL" },
                { label: "Engineering", val: "ENGINEERING" },
                { label: "Data & AI", val: "DATA_AI" },
                { label: "Healthcare & Clinical", val: "HEALTHCARE_MEDICAL" },
                { label: "Finance & Accounting", val: "FINANCE_ACCOUNTING" },
                { label: "Sales & Marketing", val: "SALES_BIZDEV" },
                { label: "Executive Leadership", val: "LEADERSHIP" },
              ].map((pill) => (
                <button
                  key={pill.val}
                  type="button"
                  onClick={() => setTemplateFilter(pill.val)}
                  className={`px-2.5 py-1 text-xs font-semibold rounded-lg transition-all cursor-pointer ${
                    templateFilter === pill.val
                      ? "bg-slate-900 text-white"
                      : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                  }`}
                >
                  {pill.label}
                </button>
              ))}
            </div>

            {/* Template Card Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 max-h-96 overflow-y-auto p-1">
              {filteredTemplates.map((tmpl) => {
                const isSelected = selectedTemplate === tmpl.id;
                const isRec = recommendedTemplateMeta?.id === tmpl.id;
                const palette = tmpl.color_palette || {};

                return (
                  <button
                    key={tmpl.id}
                    type="button"
                    onClick={() => setSelectedTemplate(tmpl.id)}
                    className={`p-3.5 rounded-2xl border text-left transition-all cursor-pointer space-y-2 relative ${
                      isSelected
                        ? "bg-blue-50/70 border-blue-600 shadow-xs ring-2 ring-blue-500/15"
                        : "bg-white border-slate-200 hover:border-slate-300"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-slate-900">{tmpl.name}</span>
                      {isRec ? (
                        <Badge variant="blue">Optimal Fit</Badge>
                      ) : (
                        <div className="flex items-center space-x-1">
                          <span
                            className="w-2.5 h-2.5 rounded-full inline-block"
                            style={{ backgroundColor: palette.primary || "#0f172a" }}
                          />
                          <span
                            className="w-2.5 h-2.5 rounded-full inline-block"
                            style={{ backgroundColor: palette.accent || "#2563eb" }}
                          />
                        </div>
                      )}
                    </div>
                    <p className="text-[11px] text-slate-500 leading-snug line-clamp-2">
                      {tmpl.description}
                    </p>
                    {tmpl.recommended_sections_order && (
                      <div className="text-[10px] text-slate-400 truncate">
                        Sections: {tmpl.recommended_sections_order.slice(0, 4).join(" &rarr; ")}
                      </div>
                    )}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Executive Summary Editor */}
          <div className="space-y-2 pt-2 border-t border-slate-100">
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-400">
              Professional Summary
            </label>
            <textarea
              rows={4}
              value={resumeData.summary || ""}
              onChange={(e) => setResumeData({ ...resumeData, summary: e.target.value })}
              className="w-full text-xs rounded-xl border border-slate-200 p-3.5 focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-500/15 leading-relaxed bg-white"
            />
          </div>

          {/* Work Experience Section */}
          <div className="space-y-3 pt-2 border-t border-slate-100">
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-400">
              Work Experience ({(resumeData.work_experience || []).length} Roles)
            </label>
            <div className="space-y-3">
              {(resumeData.work_experience || []).map((exp, idx) => (
                <div key={idx} className="p-4 bg-slate-50 rounded-2xl border border-slate-200/80 space-y-2">
                  <div className="flex justify-between items-start">
                    <div>
                      <p className="text-xs font-bold text-slate-900">{exp.title}</p>
                      <p className="text-[11px] font-semibold text-blue-700">{exp.company}</p>
                    </div>
                    <span className="text-[11px] text-slate-400">
                      {exp.start_date || "Start"} — {exp.end_date || "Present"}
                    </span>
                  </div>
                  <textarea
                    rows={3}
                    value={exp.description || (exp.bullets ? exp.bullets.join("\n") : "")}
                    onChange={(e) => {
                      const updated = [...resumeData.work_experience];
                      updated[idx].description = e.target.value;
                      setResumeData({ ...resumeData, work_experience: updated });
                    }}
                    className="w-full text-xs rounded-xl border border-slate-200 p-2.5 bg-white focus:outline-none focus:border-blue-600"
                  />
                </div>
              ))}
            </div>
          </div>

          {/* Navigation Buttons */}
          <div className="flex items-center justify-between pt-4 border-t border-slate-100">
            <Button
              variant="outline"
              size="md"
              icon={ArrowLeft}
              onClick={() => setCurrentStep(2)}
            >
              Back to Deep Match
            </Button>
            <Button
              variant="primary"
              size="md"
              iconRight={ArrowRight}
              onClick={() => setCurrentStep(4)}
            >
              Proceed to Export
            </Button>
          </div>
        </Card>
      )}

      {/* STEP 4: PREVIEW & EXPORT */}
      {currentStep === 4 && (
        <Card padding="lg" className="space-y-6 animate-fade-in">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 pb-4">
            <div>
              <div className="flex items-center space-x-2">
                <h2 className="text-base font-bold text-slate-900">Step 4: Preview &amp; Export</h2>
                <Badge variant="blue">
                  {availableTemplates.find((t) => t.id === selectedTemplate)?.name || "Role Architecture"}
                </Badge>
              </div>
              <p className="text-xs text-slate-500">
                Verified ATS-compliant resume prepared for submission to {targetJob?.company_name || "the employer"}.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <Button
                variant="primary"
                size="md"
                icon={Download}
                loading={exportingPdf}
                onClick={handleExportPdf}
              >
                Download PDF
              </Button>
              <Button
                variant="secondary"
                size="md"
                icon={Download}
                loading={exportingDocx}
                onClick={handleExportDocx}
              >
                Download DOCX
              </Button>
            </div>
          </div>

          {/* Document Preview Frame */}
          <div className="bg-white rounded-2xl border border-slate-300 p-8 sm:p-12 shadow-sm space-y-6 max-w-3xl mx-auto font-sans text-slate-900">
            {/* Header info */}
            <div className="border-b border-slate-200 pb-4 text-center space-y-1">
              <h3 className="text-2xl font-extrabold tracking-tight text-slate-900">
                {resumeData.full_name || "Candidate Name"}
              </h3>
              <p className="text-xs font-semibold text-blue-700">
                {resumeData.headline || targetJob?.normalized_title || "Professional Specialist"}
              </p>
              <div className="text-[11px] text-slate-500 flex flex-wrap justify-center gap-x-3 pt-1">
                {resumeData.email && <span>{resumeData.email}</span>}
                {resumeData.phone && <span>• {resumeData.phone}</span>}
                {resumeData.location && <span>• {resumeData.location}</span>}
              </div>
            </div>

            {/* Summary */}
            {resumeData.summary && (
              <div className="space-y-1.5">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-800 border-b border-slate-200 pb-0.5">
                  Professional Summary
                </h4>
                <p className="text-xs text-slate-700 leading-relaxed">
                  {resumeData.summary}
                </p>
              </div>
            )}

            {/* Core Competencies / Skills */}
            {(resumeData.skills || []).length > 0 && (
              <div className="space-y-1.5">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-800 border-b border-slate-200 pb-0.5">
                  Core Competencies
                </h4>
                <p className="text-xs text-slate-700 leading-relaxed font-medium">
                  {resumeData.skills.join(" • ")}
                </p>
              </div>
            )}

            {/* Work History */}
            {(resumeData.work_experience || []).length > 0 && (
              <div className="space-y-3">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-800 border-b border-slate-200 pb-0.5">
                  Professional Experience
                </h4>
                {resumeData.work_experience.map((exp, idx) => (
                  <div key={idx} className="space-y-1 text-xs">
                    <div className="flex justify-between items-baseline font-bold text-slate-900">
                      <span>{exp.title} — <span className="font-semibold text-blue-800">{exp.company}</span></span>
                      <span className="text-[11px] text-slate-500 font-normal">
                        {exp.start_date || "Start"} – {exp.end_date || "Present"}
                      </span>
                    </div>
                    {exp.description && (
                      <p className="text-slate-600 leading-relaxed whitespace-pre-line">
                        {exp.description}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Education */}
            {(resumeData.education || []).length > 0 && (
              <div className="space-y-2">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-800 border-b border-slate-200 pb-0.5">
                  Education
                </h4>
                {resumeData.education.map((edu, idx) => (
                  <div key={idx} className="flex justify-between text-xs">
                    <span className="font-semibold text-slate-800">{edu.institution}</span>
                    <span className="text-slate-600">{edu.degree} {edu.field_of_study ? `in ${edu.field_of_study}` : ""}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Footer Navigation */}
          <div className="flex items-center justify-between pt-4 border-t border-slate-100">
            <Button
              variant="outline"
              size="md"
              icon={ArrowLeft}
              onClick={() => setCurrentStep(3)}
            >
              Back to Architecture &amp; Review
            </Button>

            {targetJob?.application_url && (
              <a
                href={targetJob.application_url}
                target="_blank"
                rel="noopener noreferrer"
              >
                <Button variant="primary" size="md" iconRight={ChevronRight}>
                  Apply to {targetJob.company_name}
                </Button>
              </a>
            )}
          </div>
        </Card>
      )}

      {/* MODAL: PREMIUM UNLOCK CHECKOUT */}
      <AnimatedDialog
        isOpen={showUnlockModal}
        onClose={() => setShowUnlockModal(false)}
        title="Unlock Tailored Resume"
      >
        <div className="space-y-4">
          <p className="text-xs text-slate-600 leading-relaxed">
            Exporting tailored ATS-optimized resumes for specific employer vacancies requires an active entitlement.
          </p>
          <div className="p-3 bg-blue-50 border border-blue-200 rounded-xl text-xs text-blue-800 space-y-1">
            <p className="font-bold">ATS Tailoring Package</p>
            <p className="text-[11px] text-blue-700">
              Unlimited PDF and DOCX downloads for {targetJob?.company_name || "this vacancy"}.
            </p>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" size="sm" onClick={() => setShowUnlockModal(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              size="sm"
              loading={unlocking}
              onClick={handleSimulatedCheckout}
            >
              Confirm Entitlement
            </Button>
          </div>
        </div>
      </AnimatedDialog>
    </div>
  );
}

export default function ResumeStudioPage() {
  return (
    <Suspense
      fallback={
        <div className="max-w-4xl mx-auto px-4 py-20 flex flex-col items-center justify-center">
          <Loader2 className="w-8 h-8 text-blue-600 animate-spin mb-3" />
          <p className="text-sm font-semibold text-slate-500">Loading Resume Studio...</p>
        </div>
      }
    >
      <ResumeStudioContent />
    </Suspense>
  );
}
