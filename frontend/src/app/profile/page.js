"use client";

import { useState, useEffect, useRef, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import CompanyAvatar from "@/components/CompanyAvatar";
import {
  User,
  Mail,
  Phone,
  MapPin,
  Briefcase,
  Globe,
  FileText,
  Upload,
  Trash2,
  Plus,
  X,
  CheckCircle2,
  AlertCircle,
  AlertTriangle,
  Sparkles,
  Loader2,
  DollarSign,
  Layers,
  ExternalLink,
  Clock,
  Bookmark,
  ChevronRight,
  ShieldCheck,
  History,
  Eye,
  ArrowUpRight,
  Building2,
  Search,
  Calendar,
  Filter,
  Save,
  GraduationCap,
  Award,
  Code,
  Check,
} from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/authContext";
import { motion, AnimatePresence } from "motion/react";
import AnimatedDialog from "@/components/animations/AnimatedDialog";
import { Button, Input, Card, Badge, Tabs } from "@/components/ui";

const AVAILABLE_CATEGORIES = [
  { key: "CUSTOMER_SUPPORT", label: "Customer Support & Success" },
  { key: "SOFTWARE_IT", label: "Software & IT" },
  { key: "ENGINEERING", label: "Software Engineering" },
  { key: "SALES_BIZDEV", label: "Sales & Business Development" },
  { key: "OPERATIONS_LOGISTICS", label: "Operations & Logistics" },
  { key: "PRODUCT_DESIGN", label: "Product & Design" },
  { key: "DATA_AI", label: "Data Science & AI" },
  { key: "FINANCE_ACCOUNTING", label: "Finance & Accounting" },
  { key: "HR_RECRUITMENT", label: "Human Resources & Talent" },
  { key: "HEALTHCARE_MEDICAL", label: "Healthcare & Clinical Ops" },
  { key: "MARKETING_GROWTH", label: "Marketing & Growth" },
  { key: "EDUCATION_TRAINING", label: "Education & Learning" },
  { key: "LEGAL_ADMIN", label: "Legal & Administration" },
];

const SUGGESTED_SKILLS = [
  "Python", "SQL", "Excel", "Power BI", "Pandas", "React", "TypeScript",
  "JavaScript", "Node.js", "AWS", "Docker", "Kubernetes", "Salesforce CRM",
  "Zendesk", "Customer Support", "Project Management", "Figma"
];

const CURRENCIES = [
  { code: "USD", symbol: "$", label: "USD ($) - US Dollar" },
  { code: "EUR", symbol: "€", label: "EUR (€) - Euro" },
  { code: "GBP", symbol: "£", label: "GBP (£) - British Pound" },
  { code: "CAD", symbol: "$", label: "CAD ($) - Canadian Dollar" },
  { code: "AUD", symbol: "$", label: "AUD ($) - Australian Dollar" },
  { code: "INR", symbol: "₹", label: "INR (₹) - Indian Rupee" },
];

const SALARY_PERIODS = [
  { value: "YEAR", label: "Annual (per year)" },
  { value: "MONTH", label: "Monthly (per month)" },
];

function ProfileContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, refreshUser, loading: authLoading } = useAuth();
  const fileInputRef = useRef(null);

  // Active Tab state: "personal" | "skills" | "experience" | "activity"
  const initialTab = searchParams.get("tab") === "history" ? "activity" : "personal";
  const [activeTab, setActiveTab] = useState(initialTab);

  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [saveError, setSaveError] = useState(null);
  const [isDirty, setIsDirty] = useState(false);

  // Resume state
  const [uploadingResume, setUploadingResume] = useState(false);
  const [deletingResume, setDeletingResume] = useState(false);
  const [showDeleteResumeModal, setShowDeleteResumeModal] = useState(false);
  const [resumeNotice, setResumeNotice] = useState(null);

  // Resume Review / Approval Modal
  const [showReviewModal, setShowReviewModal] = useState(false);
  const [reviewData, setReviewData] = useState(null);
  const [reviewConflicts, setReviewConflicts] = useState([]);
  const [applyingReview, setApplyingReview] = useState(false);

  // Quick inputs
  const [newSkill, setNewSkill] = useState("");
  const [skillError, setSkillError] = useState("");
  const [newRole, setNewRole] = useState("");
  const [newLocation, setNewLocation] = useState("");
  const [newCountry, setNewCountry] = useState("");

  // Modals for Experience, Education, Project, Cert
  const [showAddExp, setShowAddExp] = useState(false);
  const [expForm, setExpForm] = useState({ company: "", title: "", location: "", start_date: "", end_date: "", description: "" });

  const [showAddEdu, setShowAddEdu] = useState(false);
  const [eduForm, setEduForm] = useState({ institution: "", degree: "", field_of_study: "", graduation_year: "" });

  const [showAddProj, setShowAddProj] = useState(false);
  const [projForm, setProjForm] = useState({ title: "", description: "", technologies: "", url: "" });

  const [showAddCert, setShowAddCert] = useState(false);
  const [certForm, setCertForm] = useState({ name: "", issuing_organization: "", issue_date: "", url: "" });

  // Activity telemetry state
  const [activitySummary, setActivitySummary] = useState(null);
  const [activityTimeline, setActivityTimeline] = useState([]);
  const [activityTotal, setActivityTotal] = useState(0);
  const [activityLoading, setActivityLoading] = useState(false);
  const [activityFilterType, setActivityFilterType] = useState("ALL");
  const [savedCount, setSavedCount] = useState(0);

  useEffect(() => {
    if (!authLoading && !user) {
      router.push("/login?redirect=/profile");
      return;
    }
    if (user) {
      loadProfileData();
    }
  }, [user, authLoading]);

  const loadProfileData = async () => {
    setLoading(true);
    try {
      const [pData, summaryData, timelineData, savedData] = await Promise.allSettled([
        api.getProfile(),
        api.getUserActivitySummary(),
        api.getUserActivityTimeline({ limit: 50 }),
        api.getSavedJobs(),
      ]);

      if (pData.status === "fulfilled" && pData.value) {
        setProfile(pData.value);
      }
      if (summaryData.status === "fulfilled" && summaryData.value) {
        setActivitySummary(summaryData.value);
      }
      if (timelineData.status === "fulfilled" && timelineData.value) {
        setActivityTimeline(timelineData.value.items || []);
        setActivityTotal(timelineData.value.total_count || 0);
      }
      if (savedData.status === "fulfilled" && savedData.value) {
        setSavedCount(savedData.value.items?.length || 0);
      }
      setIsDirty(false);
    } catch (err) {
      setSaveError(err.message || "Failed to load candidate profile");
    } finally {
      setLoading(false);
    }
  };

  const updateField = (field, value) => {
    setProfile((prev) => ({ ...prev, [field]: value }));
    setIsDirty(true);
    setSaveSuccess(false);
  };

  // --- Skills Handlers ---
  const handleAddSkill = (candidate) => {
    const val = (candidate || newSkill).trim();
    if (!val) return;
    const current = profile.skills || [];
    if (current.some((s) => s.toLowerCase() === val.toLowerCase())) {
      setSkillError(`"${val}" is already in your skills.`);
      setTimeout(() => setSkillError(""), 3000);
      return;
    }
    setSkillError("");
    setProfile((prev) => ({ ...prev, skills: [...current, val] }));
    setIsDirty(true);
    setNewSkill("");
  };

  const handleRemoveSkill = (skill) => {
    setProfile((prev) => ({
      ...prev,
      skills: (prev.skills || []).filter((s) => s !== skill),
    }));
    setIsDirty(true);
  };

  // --- Preferred Roles Handlers ---
  const handleAddRole = () => {
    const candidate = newRole.trim();
    if (!candidate) return;
    const current = profile.preferred_roles || [];
    if (!current.some((r) => r.toLowerCase() === candidate.toLowerCase())) {
      setProfile((prev) => ({ ...prev, preferred_roles: [...current, candidate] }));
      setIsDirty(true);
    }
    setNewRole("");
  };

  const handleRemoveRole = (role) => {
    setProfile((prev) => ({
      ...prev,
      preferred_roles: (prev.preferred_roles || []).filter((r) => r !== role),
    }));
    setIsDirty(true);
  };

  // --- Locations & Countries ---
  const handleAddLocation = () => {
    const val = newLocation.trim();
    if (!val) return;
    const current = profile.preferred_locations || [];
    if (!current.some((l) => l.toLowerCase() === val.toLowerCase())) {
      setProfile((prev) => ({ ...prev, preferred_locations: [...current, val] }));
      setIsDirty(true);
    }
    setNewLocation("");
  };

  const handleRemoveLocation = (loc) => {
    setProfile((prev) => ({
      ...prev,
      preferred_locations: (prev.preferred_locations || []).filter((l) => l !== loc),
    }));
    setIsDirty(true);
  };

  const handleAddCountry = () => {
    const val = newCountry.trim();
    if (!val) return;
    const current = profile.preferred_countries || [];
    if (!current.some((c) => c.toLowerCase() === val.toLowerCase())) {
      setProfile((prev) => ({ ...prev, preferred_countries: [...current, val] }));
      setIsDirty(true);
    }
    setNewCountry("");
  };

  const handleRemoveCountry = (c) => {
    setProfile((prev) => ({
      ...prev,
      preferred_countries: (prev.preferred_countries || []).filter((x) => x !== c),
    }));
    setIsDirty(true);
  };

  // --- Toggles ---
  const toggleWorkArrangement = (arrKey) => {
    const current = profile.work_arrangements || [];
    const updated = current.includes(arrKey)
      ? current.filter((x) => x !== arrKey)
      : [...current, arrKey];
    setProfile((prev) => ({ ...prev, work_arrangements: updated }));
    setIsDirty(true);
  };

  const toggleEmploymentType = (empKey) => {
    const current = profile.employment_types || [];
    const updated = current.includes(empKey)
      ? current.filter((x) => x !== empKey)
      : [...current, empKey];
    setProfile((prev) => ({ ...prev, employment_types: updated }));
    setIsDirty(true);
  };

  const toggleCategory = (catKey) => {
    const currentInterests = profile.career_interests || [];
    const isSelected = currentInterests.some((ci) => ci.profession === catKey);

    let updatedInterests;
    let newPrimaryProfession = profile.profession;

    if (isSelected) {
      updatedInterests = currentInterests.filter((ci) => ci.profession !== catKey);
      if (newPrimaryProfession === catKey) {
        newPrimaryProfession = updatedInterests[0]?.profession || null;
      }
    } else {
      updatedInterests = [
        ...currentInterests,
        {
          profession: catKey,
          preferred_roles: [],
          skills: [],
          experience_years: profile.relevant_experience_years || 2.0,
        },
      ];
      if (!newPrimaryProfession) {
        newPrimaryProfession = catKey;
      }
    }

    setProfile((prev) => ({
      ...prev,
      career_interests: updatedInterests,
      profession: newPrimaryProfession,
    }));
    setIsDirty(true);
  };

  // --- Work Experience Handlers ---
  const handleAddExperience = () => {
    if (!expForm.title?.trim() || !expForm.company?.trim()) return;
    const current = profile.work_experience || [];
    const updated = [...current, { ...expForm, title: expForm.title.trim(), company: expForm.company.trim() }];
    setProfile((prev) => ({ ...prev, work_experience: updated }));
    setIsDirty(true);
    setExpForm({ company: "", title: "", location: "", start_date: "", end_date: "", description: "" });
    setShowAddExp(false);
  };

  const handleRemoveExperience = (idx) => {
    const updated = (profile.work_experience || []).filter((_, i) => i !== idx);
    setProfile((prev) => ({ ...prev, work_experience: updated }));
    setIsDirty(true);
  };

  // --- Education Handlers ---
  const handleAddEducation = () => {
    if (!eduForm.institution?.trim()) return;
    const current = profile.education || [];
    const updated = [...current, { ...eduForm, institution: eduForm.institution.trim() }];
    setProfile((prev) => ({ ...prev, education: updated }));
    setIsDirty(true);
    setEduForm({ institution: "", degree: "", field_of_study: "", graduation_year: "" });
    setShowAddEdu(false);
  };

  const handleRemoveEducation = (idx) => {
    const updated = (profile.education || []).filter((_, i) => i !== idx);
    setProfile((prev) => ({ ...prev, education: updated }));
    setIsDirty(true);
  };

  // --- Projects Handlers ---
  const handleAddProject = () => {
    if (!projForm.title?.trim()) return;
    const current = profile.projects || [];
    const techs = projForm.technologies ? projForm.technologies.split(",").map((t) => t.trim()).filter(Boolean) : [];
    const updated = [...current, { ...projForm, title: projForm.title.trim(), technologies: techs }];
    setProfile((prev) => ({ ...prev, projects: updated }));
    setIsDirty(true);
    setProjForm({ title: "", description: "", technologies: "", url: "" });
    setShowAddProj(false);
  };

  const handleRemoveProject = (idx) => {
    const updated = (profile.projects || []).filter((_, i) => i !== idx);
    setProfile((prev) => ({ ...prev, projects: updated }));
    setIsDirty(true);
  };

  // --- Certifications Handlers ---
  const handleAddCert = () => {
    if (!certForm.name?.trim()) return;
    const current = profile.certifications || [];
    const updated = [...current, { ...certForm, name: certForm.name.trim() }];
    setProfile((prev) => ({ ...prev, certifications: updated }));
    setIsDirty(true);
    setCertForm({ name: "", issuing_organization: "", issue_date: "", url: "" });
    setShowAddCert(false);
  };

  const handleRemoveCert = (idx) => {
    const updated = (profile.certifications || []).filter((_, i) => i !== idx);
    setProfile((prev) => ({ ...prev, certifications: updated }));
    setIsDirty(true);
  };

  // --- Resume Upload / Delete ---
  const handleResumeFileSelect = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const extension = file.name.split(".").pop().toLowerCase();
    const validExtensions = ["pdf", "docx", "doc"];
    if (!validExtensions.includes(extension)) {
      setResumeNotice({ type: "error", message: "Invalid file format. Please upload a PDF or DOCX file." });
      if (fileInputRef.current) fileInputRef.current.value = "";
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      setResumeNotice({ type: "error", message: "File exceeds 5MB limit. Please upload a smaller file." });
      if (fileInputRef.current) fileInputRef.current.value = "";
      return;
    }

    setUploadingResume(true);
    setResumeNotice(null);
    try {
      const res = await api.uploadResume(file);
      setProfile((prev) => ({
        ...prev,
        resume_filename: res.filename,
        resume_uploaded_at: new Date().toISOString(),
        profile_completion_pct: res.profile_completion_pct || prev.profile_completion_pct,
        extracted_resume_data: res.extracted_data || prev?.extracted_resume_data || {},
      }));

      if (res.extracted_data) {
        setReviewData({
          full_name: res.extracted_data.full_name || profile?.full_name || "",
          headline: res.extracted_data.headline || profile?.headline || "",
          phone_number: res.extracted_data.phone || profile?.phone_number || "",
          current_location: res.extracted_data.location || profile?.current_location || "",
          profession: res.extracted_data.profession || profile?.profession || "",
          total_experience_years:
            res.extracted_data.total_experience_years !== null && res.extracted_data.total_experience_years !== undefined
              ? res.extracted_data.total_experience_years
              : (profile?.total_experience_years ?? ""),
          skills: res.extracted_data.skills || profile?.skills || [],
          preferred_roles: res.extracted_data.preferred_roles || profile?.preferred_roles || [],
          work_experience: res.extracted_data.work_experience || profile?.work_experience || [],
          education: res.extracted_data.education || profile?.education || [],
          projects: res.extracted_data.projects || profile?.projects || [],
          certifications: res.extracted_data.certifications || profile?.certifications || [],
        });
        setReviewConflicts(res.conflicts || []);
        setShowReviewModal(true);
        setResumeNotice({
          type: "success",
          message: `Resume "${res.filename}" parsed! Review extracted details to approve and apply.`,
        });
      } else {
        setResumeNotice({ type: "success", message: `Resume "${res.filename}" uploaded successfully.` });
      }
    } catch (err) {
      setResumeNotice({ type: "error", message: err.message || "Failed to upload resume file." });
    } finally {
      setUploadingResume(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleApplyReviewedExtraction = async () => {
    if (!reviewData) return;
    setApplyingReview(true);
    try {
      const payload = {
        full_name: reviewData.full_name?.trim() || null,
        headline: reviewData.headline?.trim() || null,
        phone_number: reviewData.phone_number?.trim() || null,
        current_location: reviewData.current_location?.trim() || null,
        profession: reviewData.profession || null,
        skills: reviewData.skills || [],
        preferred_roles: reviewData.preferred_roles || [],
        total_experience_years:
          reviewData.total_experience_years !== "" && reviewData.total_experience_years !== null
            ? parseFloat(reviewData.total_experience_years)
            : null,
        work_experience: reviewData.work_experience || [],
        education: reviewData.education || [],
        projects: reviewData.projects || [],
        certifications: reviewData.certifications || [],
      };
      const updatedProfile = await api.approveResumeProfile(payload);
      setProfile(updatedProfile);
      setShowReviewModal(false);
      setResumeNotice({
        type: "success",
        message: "Extracted resume details successfully approved and saved to your profile!",
      });
      setIsDirty(false);
    } catch (err) {
      setResumeNotice({
        type: "error",
        message: err.message || "Failed to apply extracted details.",
      });
    } finally {
      setApplyingReview(false);
    }
  };

  const confirmDeleteResume = async () => {
    setDeletingResume(true);
    try {
      await api.deleteResume();
      setProfile((prev) => ({
        ...prev,
        resume_filename: null,
        resume_uploaded_at: null,
      }));
      setShowDeleteResumeModal(false);
      setResumeNotice({ type: "success", message: "Resume successfully removed." });
    } catch (err) {
      setResumeNotice({ type: "error", message: err.message || "Failed to remove resume." });
    } finally {
      setDeletingResume(false);
    }
  };

  // --- Save Profile Changes ---
  const handleSaveProfile = async (e) => {
    if (e) e.preventDefault();
    setSaving(true);
    setSaveSuccess(false);
    setSaveError(null);

    const minSal = profile.salary_expectation_min ? parseFloat(profile.salary_expectation_min) : null;
    const maxSal = profile.salary_expectation_max ? parseFloat(profile.salary_expectation_max) : null;
    if (minSal !== null && maxSal !== null && maxSal < minSal) {
      setSaveError("Target salary cannot be lower than minimum expected salary.");
      setSaving(false);
      return;
    }

    try {
      const payload = {
        full_name: profile.full_name?.trim() || null,
        headline: profile.headline?.trim() || null,
        phone_number: profile.phone_number?.trim() || null,
        current_location: profile.current_location?.trim() || null,
        linkedin_url: profile.linkedin_url?.trim() || null,
        portfolio_url: profile.portfolio_url?.trim() || null,
        profession: profile.profession || null,
        career_interests: profile.career_interests || [],
        skills: profile.skills || [],
        preferred_roles: profile.preferred_roles || [],
        preferred_locations: profile.preferred_locations || [],
        preferred_countries: profile.preferred_countries || [],
        work_arrangements: profile.work_arrangements || [],
        employment_types: profile.employment_types || [],
        experience_level: profile.experience_level || null,
        total_experience_years:
          profile.total_experience_years !== null && profile.total_experience_years !== ""
            ? parseFloat(profile.total_experience_years)
            : null,
        salary_currency: profile.salary_currency || "USD",
        salary_expectation_min: minSal,
        salary_expectation_max: maxSal,
        salary_period: profile.salary_period || "YEAR",
        work_experience: profile.work_experience || [],
        education: profile.education || [],
        projects: profile.projects || [],
        certifications: profile.certifications || [],
      };

      const updated = await api.updateProfile(payload);
      setProfile(updated);
      setIsDirty(false);
      setSaveSuccess(true);
      await refreshUser();
      setTimeout(() => setSaveSuccess(false), 4000);
    } catch (err) {
      setSaveError(err.message || "Failed to save profile changes.");
    } finally {
      setSaving(false);
    }
  };

  const handleFilterTimeline = async (type) => {
    setActivityFilterType(type);
    setActivityLoading(true);
    try {
      const res = await api.getUserActivityTimeline({
        activity_type: type === "ALL" ? undefined : type,
        limit: 50,
      });
      setActivityTimeline(res.items || []);
      setActivityTotal(res.total_count || 0);
    } catch (err) {
      console.error("Filter timeline error:", err);
    } finally {
      setActivityLoading(false);
    }
  };

  if (loading || authLoading) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-20 flex flex-col items-center justify-center">
        <Loader2 className="w-8 h-8 text-blue-600 animate-spin mb-3" />
        <p className="text-sm font-semibold text-slate-500">Loading candidate workspace...</p>
      </div>
    );
  }

  if (!profile) return null;

  const candidateInitials = profile.full_name
    ? profile.full_name
        .split(" ")
        .map((p) => p[0])
        .slice(0, 2)
        .join("")
        .toUpperCase()
    : "CA";

  const completionPct = profile.profile_completion_pct || 40;

  const tabsConfig = [
    { id: "personal", label: "Personal Details & Resume", icon: User },
    { id: "skills", label: "Skills & Preferences", icon: Sparkles },
    { id: "experience", label: "Experience & Education", icon: Briefcase },
    { id: "activity", label: "Application Activity", icon: History, count: activityTotal || undefined },
  ];

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* 1. PROFESSIONAL PROFILE HEADER */}
      <div className="bg-white rounded-3xl border border-slate-200/90 p-6 sm:p-8 shadow-xs flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="flex items-start sm:items-center space-x-4 sm:space-x-5 min-w-0">
          <div className="w-16 h-16 sm:w-20 sm:h-20 rounded-2xl bg-gradient-to-br from-blue-600 to-blue-700 text-white font-extrabold text-xl sm:text-2xl flex items-center justify-center shadow-xs shrink-0 uppercase">
            {candidateInitials}
          </div>

          <div className="min-w-0 space-y-1">
            <div className="flex items-center space-x-2.5">
              <h1 className="text-xl sm:text-2xl font-extrabold text-slate-900 tracking-tight truncate">
                {profile.full_name || "Candidate Profile"}
              </h1>
              <Badge variant="blue">Candidate Account</Badge>
            </div>

            <p className="text-xs sm:text-sm text-slate-600 font-medium truncate max-w-lg">
              {profile.headline || "Add your professional headline (e.g. Senior Backend Engineer)"}
            </p>

            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500 pt-0.5">
              {profile.current_location && (
                <span className="flex items-center space-x-1">
                  <MapPin className="w-3.5 h-3.5 text-slate-400" />
                  <span>{profile.current_location}</span>
                </span>
              )}
              {profile.email && (
                <span className="flex items-center space-x-1">
                  <Mail className="w-3.5 h-3.5 text-slate-400" />
                  <span>{profile.email}</span>
                </span>
              )}
              {profile.phone_number && (
                <span className="flex items-center space-x-1">
                  <Phone className="w-3.5 h-3.5 text-slate-400" />
                  <span>{profile.phone_number}</span>
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Profile Completion & Quick Save Action */}
        <div className="w-full md:w-auto shrink-0 flex flex-col sm:flex-row md:flex-col items-stretch sm:items-center md:items-end gap-3 pt-2 md:pt-0 border-t md:border-t-0 border-slate-100">
          <div className="text-left md:text-right space-y-1.5 min-w-[160px]">
            <div className="flex justify-between md:justify-end items-center gap-2 text-xs">
              <span className="text-slate-500 font-medium">Profile Strength:</span>
              <span className="font-extrabold text-blue-600">{completionPct}%</span>
            </div>
            <div className="w-full md:w-40 bg-slate-100 h-2 rounded-full overflow-hidden">
              <div
                className="bg-blue-600 h-full rounded-full transition-all duration-300"
                style={{ width: `${Math.min(100, Math.max(10, completionPct))}%` }}
              />
            </div>
          </div>

          <div className="flex items-center gap-2">
            {saveSuccess && (
              <span className="inline-flex items-center space-x-1 text-xs font-semibold text-emerald-600">
                <Check className="w-4 h-4" />
                <span>Saved</span>
              </span>
            )}
            <Button
              variant="primary"
              size="sm"
              icon={Save}
              loading={saving}
              onClick={handleSaveProfile}
              disabled={!isDirty && !saveSuccess}
            >
              {isDirty ? "Save Changes" : "Saved"}
            </Button>
          </div>
        </div>
      </div>

      {/* Global Alerts / Feedback */}
      {saveError && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-2xl text-xs text-red-800 flex items-start space-x-2.5">
          <AlertCircle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
          <span>{saveError}</span>
        </div>
      )}
      {resumeNotice && (
        <div
          className={`p-4 rounded-2xl text-xs flex items-start space-x-2.5 ${
            resumeNotice.type === "error"
              ? "bg-red-50 border border-red-200 text-red-800"
              : "bg-emerald-50 border border-emerald-200 text-emerald-800"
          }`}
        >
          {resumeNotice.type === "error" ? (
            <AlertCircle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
          ) : (
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
          )}
          <span>{resumeNotice.message}</span>
        </div>
      )}

      {/* 2. TABBED NAVIGATION */}
      <Tabs
        tabs={tabsConfig}
        activeTab={activeTab}
        onChange={(id) => setActiveTab(id)}
      />

      {/* 3. TAB A: PERSONAL DETAILS & RESUME */}
      {activeTab === "personal" && (
        <div className="space-y-6 animate-fade-in">
          {/* Card: Basic Details */}
          <Card padding="lg" className="space-y-6">
            <div className="border-b border-slate-100 pb-3">
              <h2 className="text-base font-bold text-slate-900">Personal &amp; Contact Information</h2>
              <p className="text-xs text-slate-500">
                Manage your candidate contact details and professional headline visible to hiring teams.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Input
                label="Full Name"
                placeholder="Alex Morgan"
                value={profile.full_name || ""}
                onChange={(e) => updateField("full_name", e.target.value)}
                icon={User}
              />
              <Input
                label="Email Address"
                placeholder="alex@example.com"
                value={profile.email || ""}
                disabled
                helper="Account login email address (read-only)"
                icon={Mail}
              />
              <Input
                label="Phone Number"
                placeholder="+1 (555) 000-0000"
                value={profile.phone_number || ""}
                onChange={(e) => updateField("phone_number", e.target.value)}
                icon={Phone}
              />
              <Input
                label="Current Location"
                placeholder="City, Country (e.g. San Francisco, US)"
                value={profile.current_location || ""}
                onChange={(e) => updateField("current_location", e.target.value)}
                icon={MapPin}
              />
              <div className="sm:col-span-2">
                <Input
                  label="Professional Headline"
                  placeholder="e.g. Senior Full Stack Engineer • Python, React & Distributed Systems"
                  value={profile.headline || ""}
                  onChange={(e) => updateField("headline", e.target.value)}
                  icon={Briefcase}
                />
              </div>
              <Input
                label="LinkedIn Profile"
                placeholder="https://linkedin.com/in/alexmorgan"
                value={profile.linkedin_url || ""}
                onChange={(e) => updateField("linkedin_url", e.target.value)}
                icon={Globe}
              />
              <Input
                label="Portfolio / GitHub URL"
                placeholder="https://github.com/alexmorgan"
                value={profile.portfolio_url || ""}
                onChange={(e) => updateField("portfolio_url", e.target.value)}
                icon={ExternalLink}
              />
            </div>
          </Card>

          {/* Card: Resume Management */}
          <Card padding="lg" className="space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-3">
              <div>
                <h2 className="text-base font-bold text-slate-900">Encrypted Resume Storage</h2>
                <p className="text-xs text-slate-500">
                  Upload your master resume (PDF or DOCX). Used for intelligent ATS benchmark scoring.
                </p>
              </div>

              {profile.resume_filename && (
                <span className="inline-flex items-center space-x-1 text-xs font-semibold text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-lg border border-emerald-200">
                  <ShieldCheck className="w-3.5 h-3.5" />
                  <span>Resume Stored Safely</span>
                </span>
              )}
            </div>

            {profile.resume_filename ? (
              <div className="p-4 bg-slate-50 rounded-2xl border border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div className="flex items-center space-x-3.5 min-w-0">
                  <div className="w-10 h-10 rounded-xl bg-blue-100 text-blue-700 flex items-center justify-center shrink-0">
                    <FileText className="w-5 h-5" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-xs sm:text-sm font-bold text-slate-900 truncate">
                      {profile.resume_filename}
                    </p>
                    <p className="text-[11px] text-slate-500">
                      Uploaded on{" "}
                      {profile.resume_uploaded_at
                        ? new Date(profile.resume_uploaded_at).toLocaleDateString()
                        : "recently"}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <input
                    type="file"
                    ref={fileInputRef}
                    onChange={handleResumeFileSelect}
                    accept=".pdf,.docx,.doc"
                    className="hidden"
                  />
                  <Button
                    variant="outline"
                    size="sm"
                    icon={Upload}
                    loading={uploadingResume}
                    onClick={() => fileInputRef.current?.click()}
                  >
                    Replace
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-red-600 hover:bg-red-50"
                    icon={Trash2}
                    onClick={() => setShowDeleteResumeModal(true)}
                  >
                    Remove
                  </Button>
                </div>
              </div>
            ) : (
              <div className="border-2 border-dashed border-slate-200 hover:border-blue-400 rounded-2xl p-8 text-center space-y-3 transition-colors bg-slate-50/50">
                <div className="w-12 h-12 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center mx-auto">
                  <Upload className="w-6 h-6" />
                </div>
                <div className="space-y-1">
                  <p className="text-sm font-bold text-slate-800">
                    Upload your candidate resume
                  </p>
                  <p className="text-xs text-slate-500 max-w-sm mx-auto">
                    Supported formats: PDF, DOCX (up to 5MB). Automatically extracts skills, titles, and achievements.
                  </p>
                </div>

                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleResumeFileSelect}
                  accept=".pdf,.docx,.doc"
                  className="hidden"
                />

                <Button
                  variant="primary"
                  size="md"
                  icon={Upload}
                  loading={uploadingResume}
                  onClick={() => fileInputRef.current?.click()}
                >
                  Select Resume File
                </Button>
              </div>
            )}
          </Card>
        </div>
      )}

      {/* 4. TAB B: SKILLS & PREFERENCES */}
      {activeTab === "skills" && (
        <div className="space-y-6 animate-fade-in">
          {/* Skills Management */}
          <Card padding="lg" className="space-y-6">
            <div className="border-b border-slate-100 pb-3">
              <h2 className="text-base font-bold text-slate-900">Verified Technical Skills</h2>
              <p className="text-xs text-slate-500">
                Add skills you possess. Used by the explainable matching algorithm to compute your job match scores.
              </p>
            </div>

            {skillError && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-xs text-red-700">
                {skillError}
              </div>
            )}

            {/* Current Skills Pill Rail */}
            <div className="space-y-2">
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-400">
                My Skills ({(profile.skills || []).length})
              </label>

              {(profile.skills || []).length > 0 ? (
                <div className="flex flex-wrap gap-1.5 p-3 bg-slate-50 rounded-2xl border border-slate-200/80 min-h-[50px]">
                  {profile.skills.map((skill) => (
                    <span
                      key={skill}
                      className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-xl bg-white border border-slate-200 text-xs font-semibold text-slate-800 shadow-2xs"
                    >
                      <span>{skill}</span>
                      <button
                        type="button"
                        onClick={() => handleRemoveSkill(skill)}
                        className="text-slate-400 hover:text-red-500 p-0.5 cursor-pointer"
                        aria-label={`Remove ${skill}`}
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </span>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-slate-400 italic p-3 bg-slate-50 rounded-2xl border border-slate-200/80">
                  No skills added yet. Type below or pick from recommended skills.
                </p>
              )}
            </div>

            {/* Add Skill Input */}
            <div className="flex gap-2 max-w-md">
              <input
                type="text"
                placeholder="Add skill (e.g. PostgreSQL, FastAPI)..."
                value={newSkill}
                onChange={(e) => setNewSkill(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    handleAddSkill();
                  }
                }}
                className="flex-1 text-xs rounded-xl border border-slate-200 px-3.5 py-2.5 bg-white text-slate-900 focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-500/15"
              />
              <Button variant="secondary" size="sm" icon={Plus} onClick={() => handleAddSkill()}>
                Add
              </Button>
            </div>

            {/* Suggested Skills */}
            <div className="space-y-2 pt-2 border-t border-slate-100">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                Suggested Industry Skills:
              </span>
              <div className="flex flex-wrap gap-1.5">
                {SUGGESTED_SKILLS.filter(
                  (s) => !(profile.skills || []).some((ex) => ex.toLowerCase() === s.toLowerCase())
                ).map((skill) => (
                  <button
                    key={skill}
                    type="button"
                    onClick={() => handleAddSkill(skill)}
                    className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-blue-50 hover:text-blue-700 hover:border-blue-200 border border-transparent text-xs text-slate-600 font-medium transition-colors cursor-pointer"
                  >
                    <Plus className="w-3 h-3 text-slate-400" />
                    <span>{skill}</span>
                  </button>
                ))}
              </div>
            </div>
          </Card>

          {/* Career Tracks & Preferred Roles */}
          <Card padding="lg" className="space-y-6">
            <div className="border-b border-slate-100 pb-3">
              <h2 className="text-base font-bold text-slate-900">Career Tracks &amp; Target Roles</h2>
              <p className="text-xs text-slate-500">
                Choose the industry disciplines and job titles you want to receive recommendations for.
              </p>
            </div>

            {/* Category checkboxes */}
            <div className="space-y-2">
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-400">
                Active Career Tracks
              </label>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
                {AVAILABLE_CATEGORIES.map((cat) => {
                  const active = (profile.career_interests || []).some((ci) => ci.profession === cat.key);
                  return (
                    <button
                      key={cat.key}
                      type="button"
                      onClick={() => toggleCategory(cat.key)}
                      className={`flex items-center space-x-2.5 p-3 rounded-xl border text-left text-xs font-semibold transition-all cursor-pointer ${
                        active
                          ? "bg-blue-50 border-blue-300 text-blue-800 shadow-2xs font-bold"
                          : "bg-slate-50/70 border-slate-200 text-slate-700 hover:bg-slate-100 hover:border-slate-300"
                      }`}
                    >
                      <div
                        className={`w-4 h-4 rounded-md border flex items-center justify-center shrink-0 ${
                          active ? "bg-blue-600 border-blue-600 text-white" : "border-slate-300 bg-white"
                        }`}
                      >
                        {active && <Check className="w-3 h-3" />}
                      </div>
                      <span className="truncate">{cat.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Target Job Roles */}
            <div className="space-y-3 pt-2 border-t border-slate-100">
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-400">
                Target Job Titles
              </label>

              {(profile.preferred_roles || []).length > 0 && (
                <div className="flex flex-wrap gap-1.5 p-3 bg-slate-50 rounded-2xl border border-slate-200/80">
                  {profile.preferred_roles.map((r) => (
                    <span
                      key={r}
                      className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-xl bg-white border border-slate-200 text-xs font-semibold text-slate-800 shadow-2xs"
                    >
                      <span>{r}</span>
                      <button
                        type="button"
                        onClick={() => handleRemoveRole(r)}
                        className="text-slate-400 hover:text-red-500 p-0.5 cursor-pointer"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </span>
                  ))}
                </div>
              )}

              <div className="flex gap-2 max-w-md">
                <input
                  type="text"
                  placeholder="e.g. Senior Frontend Engineer, DevOps Lead..."
                  value={newRole}
                  onChange={(e) => setNewRole(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      handleAddRole();
                    }
                  }}
                  className="flex-1 text-xs rounded-xl border border-slate-200 px-3.5 py-2.5 bg-white text-slate-900 focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-500/15"
                />
                <Button variant="secondary" size="sm" icon={Plus} onClick={handleAddRole}>
                  Add Role
                </Button>
              </div>
            </div>
          </Card>

          {/* Work Arrangement & Employment Types */}
          <Card padding="lg" className="space-y-6">
            <div className="border-b border-slate-100 pb-3">
              <h2 className="text-base font-bold text-slate-900">Work Mode &amp; Arrangements</h2>
              <p className="text-xs text-slate-500">
                Filter and personalize jobs based on your preferred remote setup and contract type.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
              {/* Work Arrangement */}
              <div className="space-y-2">
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-400">
                  Work Arrangement
                </label>
                <div className="grid grid-cols-3 gap-2">
                  {[
                    { key: "REMOTE", label: "Remote" },
                    { key: "HYBRID", label: "Hybrid" },
                    { key: "ONSITE", label: "On-site" },
                  ].map((item) => {
                    const active = (profile.work_arrangements || []).includes(item.key);
                    return (
                      <button
                        key={item.key}
                        type="button"
                        onClick={() => toggleWorkArrangement(item.key)}
                        className={`py-2 px-3 rounded-xl text-xs font-bold border text-center transition-all cursor-pointer ${
                          active
                            ? "bg-blue-600 border-blue-600 text-white shadow-2xs"
                            : "bg-slate-50 border-slate-200 text-slate-700 hover:bg-slate-100 hover:border-slate-300"
                        }`}
                      >
                        {item.label}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Employment Types */}
              <div className="space-y-2">
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-400">
                  Employment Types
                </label>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  {[
                    { key: "FULL_TIME", label: "Full Time" },
                    { key: "CONTRACT", label: "Contract" },
                    { key: "PART_TIME", label: "Part Time" },
                    { key: "INTERN", label: "Intern" },
                  ].map((item) => {
                    const active = (profile.employment_types || []).includes(item.key);
                    return (
                      <button
                        key={item.key}
                        type="button"
                        onClick={() => toggleEmploymentType(item.key)}
                        className={`py-2 px-2 rounded-xl text-xs font-bold border text-center transition-all cursor-pointer ${
                          active
                            ? "bg-blue-600 border-blue-600 text-white shadow-2xs"
                            : "bg-slate-50 border-slate-200 text-slate-700 hover:bg-slate-100 hover:border-slate-300"
                        }`}
                      >
                        {item.label}
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* Salary Expectations */}
            <div className="space-y-3 pt-4 border-t border-slate-100">
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-400">
                Salary Expectations
              </label>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="block text-[11px] font-semibold text-slate-600 mb-1">
                    Currency
                  </label>
                  <select
                    value={profile.salary_currency || "USD"}
                    onChange={(e) => updateField("salary_currency", e.target.value)}
                    className="w-full text-xs rounded-xl border border-slate-200 bg-white py-2.5 px-3 focus:outline-none focus:border-blue-600"
                  >
                    {CURRENCIES.map((c) => (
                      <option key={c.code} value={c.code}>
                        {c.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-[11px] font-semibold text-slate-600 mb-1">
                    Minimum Target Salary
                  </label>
                  <input
                    type="number"
                    placeholder="e.g. 120000"
                    value={profile.salary_expectation_min || ""}
                    onChange={(e) => updateField("salary_expectation_min", e.target.value)}
                    className="w-full text-xs rounded-xl border border-slate-200 bg-white py-2.5 px-3 focus:outline-none focus:border-blue-600"
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-semibold text-slate-600 mb-1">
                    Payment Period
                  </label>
                  <select
                    value={profile.salary_period || "YEAR"}
                    onChange={(e) => updateField("salary_period", e.target.value)}
                    className="w-full text-xs rounded-xl border border-slate-200 bg-white py-2.5 px-3 focus:outline-none focus:border-blue-600"
                  >
                    {SALARY_PERIODS.map((p) => (
                      <option key={p.value} value={p.value}>
                        {p.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* 5. TAB C: EXPERIENCE & EDUCATION */}
      {activeTab === "experience" && (
        <div className="space-y-6 animate-fade-in">
          {/* Work Experience */}
          <Card padding="lg" className="space-y-6">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <h2 className="text-base font-bold text-slate-900">Work Experience</h2>
                <p className="text-xs text-slate-500">
                  Chronological employment history used by ATS parser to calculate domain seniority.
                </p>
              </div>
              <Button variant="outline" size="sm" icon={Plus} onClick={() => setShowAddExp(true)}>
                Add Position
              </Button>
            </div>

            {(profile.work_experience || []).length > 0 ? (
              <div className="space-y-4">
                {profile.work_experience.map((exp, idx) => (
                  <div
                    key={idx}
                    className="p-4 bg-slate-50 rounded-2xl border border-slate-200/80 space-y-2 relative group"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <h3 className="text-sm font-bold text-slate-900">{exp.title}</h3>
                        <p className="text-xs font-semibold text-blue-700">{exp.company}</p>
                        <p className="text-[11px] text-slate-400">
                          {exp.start_date || "Start"} — {exp.end_date || "Present"} {exp.location ? `• ${exp.location}` : ""}
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={() => handleRemoveExperience(idx)}
                        className="text-slate-400 hover:text-red-500 p-1 cursor-pointer"
                        aria-label="Remove experience"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>

                    {exp.description && (
                      <p className="text-xs text-slate-600 leading-relaxed whitespace-pre-line">
                        {exp.description}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-xs text-slate-400 italic bg-slate-50 rounded-2xl border border-slate-200/80">
                No work experience recorded yet. Click &quot;Add Position&quot; to build your history.
              </div>
            )}
          </Card>

          {/* Education */}
          <Card padding="lg" className="space-y-6">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <h2 className="text-base font-bold text-slate-900">Education &amp; Academic Background</h2>
                <p className="text-xs text-slate-500">Degrees, colleges, and certifications obtained.</p>
              </div>
              <Button variant="outline" size="sm" icon={Plus} onClick={() => setShowAddEdu(true)}>
                Add Education
              </Button>
            </div>

            {(profile.education || []).length > 0 ? (
              <div className="space-y-3">
                {profile.education.map((edu, idx) => (
                  <div
                    key={idx}
                    className="p-4 bg-slate-50 rounded-2xl border border-slate-200/80 flex items-start justify-between gap-3"
                  >
                    <div>
                      <h3 className="text-sm font-bold text-slate-900">{edu.institution}</h3>
                      <p className="text-xs text-slate-600">
                        {edu.degree} {edu.field_of_study ? `in ${edu.field_of_study}` : ""}
                      </p>
                      {edu.graduation_year && (
                        <p className="text-[11px] text-slate-400">Class of {edu.graduation_year}</p>
                      )}
                    </div>
                    <button
                      type="button"
                      onClick={() => handleRemoveEducation(idx)}
                      className="text-slate-400 hover:text-red-500 p-1 cursor-pointer"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-xs text-slate-400 italic bg-slate-50 rounded-2xl border border-slate-200/80">
                No education details recorded yet.
              </div>
            )}
          </Card>

          {/* Projects */}
          <Card padding="lg" className="space-y-6">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <h2 className="text-base font-bold text-slate-900">Notable Projects</h2>
                <p className="text-xs text-slate-500">Software, research, open-source or creative portfolios.</p>
              </div>
              <Button variant="outline" size="sm" icon={Plus} onClick={() => setShowAddProj(true)}>
                Add Project
              </Button>
            </div>

            {(profile.projects || []).length > 0 ? (
              <div className="space-y-3">
                {profile.projects.map((proj, idx) => (
                  <div key={idx} className="p-4 bg-slate-50 rounded-2xl border border-slate-200/80 space-y-1.5">
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-center space-x-2">
                        <h3 className="text-sm font-bold text-slate-900">{proj.title}</h3>
                        {proj.url && (
                          <a
                            href={proj.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-blue-600 hover:underline"
                          >
                            <ExternalLink className="w-3.5 h-3.5" />
                          </a>
                        )}
                      </div>
                      <button
                        type="button"
                        onClick={() => handleRemoveProject(idx)}
                        className="text-slate-400 hover:text-red-500 p-1 cursor-pointer"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                    {proj.description && <p className="text-xs text-slate-600">{proj.description}</p>}
                    {proj.technologies && proj.technologies.length > 0 && (
                      <div className="flex flex-wrap gap-1 pt-1">
                        {proj.technologies.map((t) => (
                          <span key={t} className="px-2 py-0.5 rounded-md bg-white border border-slate-200 text-[10px] text-slate-700 font-semibold">
                            {t}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-xs text-slate-400 italic bg-slate-50 rounded-2xl border border-slate-200/80">
                No projects added yet.
              </div>
            )}
          </Card>
        </div>
      )}

      {/* 6. TAB D: APPLICATION ACTIVITY */}
      {activeTab === "activity" && (
        <div className="space-y-6 animate-fade-in">
          {/* Real Metrics Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <Card padding="md" className="text-center space-y-1">
              <p className="text-2xl sm:text-3xl font-extrabold text-blue-600">
                {activitySummary?.total_views || 0}
              </p>
              <p className="text-xs font-semibold text-slate-600">Jobs Viewed</p>
            </Card>

            <Card padding="md" className="text-center space-y-1">
              <p className="text-2xl sm:text-3xl font-extrabold text-emerald-600">
                {activitySummary?.total_apply_clicks || 0}
              </p>
              <p className="text-xs font-semibold text-slate-600">Apply Clicks</p>
            </Card>

            <Card padding="md" className="text-center space-y-1">
              <p className="text-2xl sm:text-3xl font-extrabold text-slate-900">
                {activitySummary?.unique_companies_visited || 0}
              </p>
              <p className="text-xs font-semibold text-slate-600">Hiring Companies</p>
            </Card>

            <Card padding="md" className="text-center space-y-1">
              <p className="text-2xl sm:text-3xl font-extrabold text-amber-600">
                {savedCount}
              </p>
              <p className="text-xs font-semibold text-slate-600">Saved Positions</p>
            </Card>
          </div>

          {/* Activity Timeline */}
          <Card padding="lg" className="space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-3">
              <div>
                <h2 className="text-base font-bold text-slate-900">Application Activity Timeline</h2>
                <p className="text-xs text-slate-500">
                  Every job view and external application redirect tracked in real time.
                </p>
              </div>

              {/* Activity Type Filters */}
              <div className="flex items-center gap-1.5 p-1 bg-slate-100 rounded-xl">
                {[
                  { key: "ALL", label: "All Events" },
                  { key: "APPLY_CLICK", label: "Apply Clicks" },
                  { key: "VIEW", label: "Views" },
                ].map((item) => (
                  <button
                    key={item.key}
                    type="button"
                    onClick={() => handleFilterTimeline(item.key)}
                    className={`px-3 py-1 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                      activityFilterType === item.key
                        ? "bg-white text-blue-700 shadow-2xs"
                        : "text-slate-600 hover:text-slate-900"
                    }`}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            </div>

            {activityLoading ? (
              <div className="py-12 flex justify-center">
                <Loader2 className="w-6 h-6 text-blue-600 animate-spin" />
              </div>
            ) : activityTimeline.length > 0 ? (
              <div className="space-y-3">
                {activityTimeline.map((item, idx) => (
                  <div
                    key={idx}
                    className="p-3.5 bg-slate-50 rounded-2xl border border-slate-200/80 flex items-center justify-between gap-4"
                  >
                    <div className="flex items-center space-x-3 min-w-0">
                      <CompanyAvatar name={item.company_name || "Company"} size="sm" />
                      <div className="min-w-0">
                        <Link
                          href={`/jobs/${item.job_id}`}
                          className="text-xs sm:text-sm font-bold text-slate-900 hover:text-blue-600 hover:underline truncate block"
                        >
                          {item.job_title}
                        </Link>
                        <p className="text-[11px] text-slate-500">
                          {item.company_name} • {item.created_at ? new Date(item.created_at).toLocaleString() : ""}
                        </p>
                      </div>
                    </div>

                    <div className="shrink-0 flex items-center space-x-2">
                      <Badge variant={item.activity_type === "APPLY_CLICK" ? "emerald" : "blue"}>
                        {item.activity_type === "APPLY_CLICK" ? "Apply Redirect" : "Job View"}
                      </Badge>
                      <Link
                        href={`/jobs/${item.job_id}`}
                        className="p-1 text-slate-400 hover:text-blue-600"
                        title="View Position"
                      >
                        <ArrowUpRight className="w-4 h-4" />
                      </Link>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-12 text-xs text-slate-400 italic bg-slate-50 rounded-2xl border border-slate-200/80">
                No activity records found matching this filter.
              </div>
            )}
          </Card>
        </div>
      )}

      {/* MODAL: ADD WORK EXPERIENCE */}
      <AnimatedDialog
        isOpen={showAddExp}
        onClose={() => setShowAddExp(false)}
        title="Add Work Experience"
      >
        <div className="space-y-4">
          <Input
            label="Job Title"
            required
            placeholder="e.g. Senior Software Engineer"
            value={expForm.title}
            onChange={(e) => setExpForm({ ...expForm, title: e.target.value })}
          />
          <Input
            label="Company Name"
            required
            placeholder="e.g. Acme Corp"
            value={expForm.company}
            onChange={(e) => setExpForm({ ...expForm, company: e.target.value })}
          />
          <Input
            label="Location"
            placeholder="City, Country (e.g. New York, US)"
            value={expForm.location}
            onChange={(e) => setExpForm({ ...expForm, location: e.target.value })}
          />
          <div className="grid grid-cols-2 gap-3">
            <Input
              label="Start Date"
              placeholder="e.g. Jan 2022"
              value={expForm.start_date}
              onChange={(e) => setExpForm({ ...expForm, start_date: e.target.value })}
            />
            <Input
              label="End Date"
              placeholder="e.g. Present"
              value={expForm.end_date}
              onChange={(e) => setExpForm({ ...expForm, end_date: e.target.value })}
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Key Achievements &amp; Description
            </label>
            <textarea
              rows={3}
              placeholder="Describe core impact, technologies used, metrics achieved..."
              value={expForm.description}
              onChange={(e) => setExpForm({ ...expForm, description: e.target.value })}
              className="w-full text-xs rounded-xl border border-slate-200 p-3 focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-500/15"
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" size="sm" onClick={() => setShowAddExp(false)}>
              Cancel
            </Button>
            <Button variant="primary" size="sm" onClick={handleAddExperience}>
              Add Position
            </Button>
          </div>
        </div>
      </AnimatedDialog>

      {/* MODAL: ADD EDUCATION */}
      <AnimatedDialog
        isOpen={showAddEdu}
        onClose={() => setShowAddEdu(false)}
        title="Add Education"
      >
        <div className="space-y-4">
          <Input
            label="Institution / University"
            required
            placeholder="e.g. University of California, Berkeley"
            value={eduForm.institution}
            onChange={(e) => setEduForm({ ...eduForm, institution: e.target.value })}
          />
          <Input
            label="Degree"
            placeholder="e.g. Bachelor of Science"
            value={eduForm.degree}
            onChange={(e) => setEduForm({ ...eduForm, degree: e.target.value })}
          />
          <Input
            label="Field of Study"
            placeholder="e.g. Computer Science"
            value={eduForm.field_of_study}
            onChange={(e) => setEduForm({ ...eduForm, field_of_study: e.target.value })}
          />
          <Input
            label="Graduation Year"
            placeholder="e.g. 2021"
            value={eduForm.graduation_year}
            onChange={(e) => setEduForm({ ...eduForm, graduation_year: e.target.value })}
          />
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" size="sm" onClick={() => setShowAddEdu(false)}>
              Cancel
            </Button>
            <Button variant="primary" size="sm" onClick={handleAddEducation}>
              Save Education
            </Button>
          </div>
        </div>
      </AnimatedDialog>

      {/* MODAL: ADD PROJECT */}
      <AnimatedDialog
        isOpen={showAddProj}
        onClose={() => setShowAddProj(false)}
        title="Add Notable Project"
      >
        <div className="space-y-4">
          <Input
            label="Project Title"
            required
            placeholder="e.g. Distributed Task Queue"
            value={projForm.title}
            onChange={(e) => setProjForm({ ...projForm, title: e.target.value })}
          />
          <Input
            label="Project URL"
            placeholder="https://github.com/..."
            value={projForm.url}
            onChange={(e) => setProjForm({ ...projForm, url: e.target.value })}
          />
          <Input
            label="Technologies Used"
            placeholder="Comma-separated (e.g. Python, Redis, Docker)"
            value={projForm.technologies}
            onChange={(e) => setProjForm({ ...projForm, technologies: e.target.value })}
          />
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Description
            </label>
            <textarea
              rows={3}
              placeholder="Brief overview of project architecture and results..."
              value={projForm.description}
              onChange={(e) => setProjForm({ ...projForm, description: e.target.value })}
              className="w-full text-xs rounded-xl border border-slate-200 p-3 focus:outline-none focus:border-blue-600"
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" size="sm" onClick={() => setShowAddProj(false)}>
              Cancel
            </Button>
            <Button variant="primary" size="sm" onClick={handleAddProject}>
              Save Project
            </Button>
          </div>
        </div>
      </AnimatedDialog>

      {/* MODAL: DELETE RESUME CONFIRMATION */}
      <AnimatedDialog
        isOpen={showDeleteResumeModal}
        onClose={() => setShowDeleteResumeModal(false)}
        title="Remove Resume"
      >
        <div className="space-y-4">
          <p className="text-xs text-slate-600 leading-relaxed">
            Are you sure you want to remove your encrypted resume? Your parsed technical skills and profile information will remain intact.
          </p>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" size="sm" onClick={() => setShowDeleteResumeModal(false)}>
              Cancel
            </Button>
            <Button
              variant="danger"
              size="sm"
              loading={deletingResume}
              onClick={confirmDeleteResume}
            >
              Confirm Remove
            </Button>
          </div>
        </div>
      </AnimatedDialog>

      {/* MODAL: RESUME REVIEW & APPROVAL */}
      <AnimatedDialog
        isOpen={showReviewModal}
        onClose={() => setShowReviewModal(false)}
        title="Review & Approve Resume Details"
      >
        <div className="space-y-4 max-h-[70vh] overflow-y-auto pr-1">
          <p className="text-xs text-slate-600 leading-relaxed">
            We extracted the following career details from your resume. Review and edit before applying them to your candidate profile.
          </p>

          {reviewData && (
            <div className="space-y-3">
              <Input
                label="Full Name"
                value={reviewData.full_name || ""}
                onChange={(e) => setReviewData({ ...reviewData, full_name: e.target.value })}
              />
              <Input
                label="Professional Headline"
                value={reviewData.headline || ""}
                onChange={(e) => setReviewData({ ...reviewData, headline: e.target.value })}
              />
              <Input
                label="Current Location"
                value={reviewData.current_location || ""}
                onChange={(e) => setReviewData({ ...reviewData, current_location: e.target.value })}
              />

              <div className="space-y-1">
                <label className="block text-xs font-semibold text-slate-700">
                  Extracted Skills ({(reviewData.skills || []).length})
                </label>
                <div className="flex flex-wrap gap-1 p-2 bg-slate-50 rounded-xl border border-slate-200">
                  {(reviewData.skills || []).map((sk) => (
                    <span
                      key={sk}
                      className="px-2 py-0.5 rounded-lg bg-white border border-slate-200 text-xs font-semibold text-slate-800"
                    >
                      {sk}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          )}

          <div className="flex justify-end gap-2 pt-4 border-t border-slate-100">
            <Button variant="outline" size="sm" onClick={() => setShowReviewModal(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              size="sm"
              loading={applyingReview}
              onClick={handleApplyReviewedExtraction}
            >
              Approve &amp; Update Profile
            </Button>
          </div>
        </div>
      </AnimatedDialog>
    </div>
  );
}

export default function ProfilePage() {
  return (
    <Suspense
      fallback={
        <div className="max-w-4xl mx-auto px-4 py-20 flex flex-col items-center justify-center">
          <Loader2 className="w-8 h-8 text-blue-600 animate-spin mb-3" />
          <p className="text-sm font-semibold text-slate-500">Loading candidate profile...</p>
        </div>
      }
    >
      <ProfileContent />
    </Suspense>
  );
}
