const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  (typeof window !== "undefined" ? "/api/v1" : "http://127.0.0.1:8000/api/v1");

export function getStoredToken() {
  if (typeof window !== "undefined") {
    return localStorage.getItem("job_platform_token");
  }
  return null;
}

export function setStoredToken(token) {
  if (typeof window !== "undefined") {
    if (token) {
      localStorage.setItem("job_platform_token", token);
    } else {
      localStorage.removeItem("job_platform_token");
    }
  }
}

export async function apiRequest(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  const token = getStoredToken();

  const headers = {
    ...options.headers,
  };

  if (options.body && !(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (response.status === 204) {
    return null;
  }

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    const errorMsg = data.detail || data.message || `API error (${response.status})`;
    throw new Error(errorMsg);
  }

  return data;
}

export async function downloadBlob(endpoint, options = {}, defaultFilename = "Resume.pdf") {
  const url = `${API_BASE_URL}${endpoint}`;
  const token = getStoredToken();
  const headers = { ...options.headers };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (options.body && !(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(url, { ...options, headers });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    const error = new Error(err.detail || "Download failed");
    error.status = response.status;
    throw error;
  }

  const blob = await response.blob();
  const blobUrl = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = blobUrl;
  a.download = defaultFilename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  window.URL.revokeObjectURL(blobUrl);
}

export const api = {
  // Auth
  login: (email, password) =>
    apiRequest("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  register: (email, password) =>
    apiRequest("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  getMe: () => apiRequest("/auth/me"),

  // Profile
  getProfile: () => apiRequest("/profile"),
  updateProfile: (profileData) =>
    apiRequest("/profile", {
      method: "PATCH",
      body: JSON.stringify(profileData),
    }),
  uploadResume: (file) => {
    const formData = new FormData();
    formData.append("file", file);
    return apiRequest("/profile/resume", {
      method: "POST",
      body: formData,
    });
  },
  approveResumeProfile: (data) =>
    apiRequest("/profile/resume/apply", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  deleteResume: () =>
    apiRequest("/profile/resume", {
      method: "DELETE",
    }),

  // Jobs
  getProfessions: () => apiRequest("/jobs/professions"),
  getCategories: () => apiRequest("/jobs/categories"),
  getCompanies: (params = {}) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") {
        query.set(k, v);
      }
    });
    const qs = query.toString();
    return apiRequest(`/jobs/companies${qs ? `?${qs}` : ""}`);
  },
  searchJobs: (params = {}, options = {}) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") {
        if (Array.isArray(v)) {
          v.forEach((val) => query.append(k, val));
        } else {
          query.set(k, v);
        }
      }
    });
    return apiRequest(`/jobs?${query.toString()}`, options);
  },
  getRecentJobs: (limit = 4) =>
    apiRequest(`/jobs?page=1&page_size=${limit}&sort_by=newest`),
  getJob: (jobId) => apiRequest(`/jobs/${jobId}`),
  getSimilarJobs: (jobId) => apiRequest(`/jobs/${jobId}/similar`),

  // Saved Jobs
  getSavedJobs: () => apiRequest("/saved-jobs"),
  saveJob: (jobId, notes = "") =>
    apiRequest(`/saved-jobs/${jobId}`, {
      method: "PUT",
      body: JSON.stringify({ notes }),
    }),
  unsaveJob: (jobId) =>
    apiRequest(`/saved-jobs/${jobId}`, {
      method: "DELETE",
    }),

  // Visited Jobs Tracking (PRD §4.4)
  trackJobVisit: (jobId) =>
    apiRequest(`/jobs/${jobId}/visit`, {
      method: "POST",
    }),
  getVisitedJobs: () => apiRequest("/profile/visited-jobs"),

  // Application Redirection & Activity Telemetry (Target 3)
  applyToJob: (jobId, allowClosed = false) =>
    apiRequest(`/jobs/${jobId}/apply?allow_closed=${allowClosed}`, {
      method: "POST",
    }),
  recordJobView: (jobId) =>
    apiRequest(`/jobs/${jobId}/view`, {
      method: "POST",
    }),
  getUserActivitySummary: () => apiRequest("/profile/activity/summary"),
  getUserActivityTimeline: (params = {}) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") {
        query.set(k, v);
      }
    });
    return apiRequest(`/profile/activity?${query.toString()}`);
  },

  // Recommendations & Matches (P2B)
  getRecommendations: (limit = 20, profession = "") =>
    apiRequest(`/recommendations?limit=${limit}${profession ? `&profession=${encodeURIComponent(profession)}` : ""}`),
  getMatches: (params = {}) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") {
        query.set(k, v);
      }
    });
    return apiRequest(`/recommendations?${query.toString()}`);
  },

  // Alerts
  getAlerts: () => apiRequest("/alerts"),
  createAlert: (alertData) =>
    apiRequest("/alerts", {
      method: "POST",
      body: JSON.stringify(alertData),
    }),
  deleteAlert: (alertId) =>
    apiRequest(`/alerts/${alertId}`, {
      method: "DELETE",
    }),
  evaluateAlert: (alertId) =>
    apiRequest(`/alerts/${alertId}/evaluate`, {
      method: "POST",
    }),

  // Admin & Ingestion Operations
  getSources: () => apiRequest("/admin/sources"),
  createSource: (sourceData) =>
    apiRequest("/admin/sources", {
      method: "POST",
      body: JSON.stringify(sourceData),
    }),
  triggerSync: (sourceId) =>
    apiRequest(`/admin/sources/${sourceId}/sync`, {
      method: "POST",
    }),
  probeBoard: (query) =>
    apiRequest("/admin/sources/probe", {
      method: "POST",
      body: JSON.stringify({ query }),
    }),
  discoverSource: (data) =>
    apiRequest("/admin/sources/discover", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  runScheduler: (limit = 10) =>
    apiRequest(`/admin/scheduler/run?limit=${limit}`, {
      method: "POST",
    }),
  expireStaleJobs: (graceDays = 14) =>
    apiRequest(`/admin/jobs/expire-stale?grace_days=${graceDays}`, {
      method: "POST",
    }),
  getIngestionRuns: (limit = 50) => apiRequest(`/admin/ingestion-runs?limit=${limit}`),
  getHealth: () => apiRequest("/admin/health"),
  getQualityDashboard: () => apiRequest("/admin/quality-dashboard"),

  // Admin Global Company Discovery
  getDiscoverySummary: () => apiRequest("/admin/discovery/summary"),
  getDiscoveryCompanies: (params = {}) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, val]) => {
      if (val !== undefined && val !== null && val !== "") {
        query.append(key, val);
      }
    });
    return apiRequest(`/admin/discovery/companies?${query.toString()}`);
  },
  runDiscoveryPipeline: (payload = {}) =>
    apiRequest("/admin/discovery/run", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateCompanyStatus: (companyId, verification_status, verification_notes = "") =>
    apiRequest(`/admin/discovery/companies/${companyId}/status`, {
      method: "PATCH",
      body: JSON.stringify({ verification_status, verification_notes }),
    }),

  // P2C Resume Studio & Role Templates
  getRoleTemplates: () => apiRequest("/resume-studio/templates"),
  getRecommendedTemplate: (roleTitle) =>
    apiRequest(`/resume-studio/templates/recommended?role_title=${encodeURIComponent(roleTitle)}`),
  matchJobDescription: (data) =>
    apiRequest("/resume-studio/jd-match", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  getMasterResume: () => apiRequest("/resume-studio/master"),
  updateMasterResume: (content) =>
    apiRequest("/resume-studio/master", {
      method: "POST",
      body: JSON.stringify(content),
    }),
  analyzeResume: (content) =>
    apiRequest("/resume-studio/analyze", {
      method: "POST",
      body: JSON.stringify(content),
    }),
  improveBullet: (bullet_text, role_title = null, target_keywords = null) =>
    apiRequest("/resume-studio/improve/bullet", {
      method: "POST",
      body: JSON.stringify({ bullet_text, role_title, target_keywords }),
    }),
  improveSummary: (current_summary = "", target_role = "", years_of_experience = null, top_skills = []) =>
    apiRequest("/resume-studio/improve/summary", {
      method: "POST",
      body: JSON.stringify({ current_summary, target_role, years_of_experience, top_skills }),
    }),
  tailorResume: (job_id, base_version_id = null, custom_instructions = null) =>
    apiRequest("/resume-studio/tailor", {
      method: "POST",
      body: JSON.stringify({ job_id, base_version_id, custom_instructions }),
    }),
  getResumeVersions: () => apiRequest("/resume-studio/versions"),
  createResumeVersion: (data) =>
    apiRequest("/resume-studio/versions", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  getResumeVersion: (versionId) => apiRequest(`/resume-studio/versions/${versionId}`),
  updateResumeVersion: (versionId, data) =>
    apiRequest(`/resume-studio/versions/${versionId}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  duplicateResumeVersion: (versionId) =>
    apiRequest(`/resume-studio/versions/${versionId}/duplicate`, {
      method: "POST",
    }),
  deleteResumeVersion: (versionId) =>
    apiRequest(`/resume-studio/versions/${versionId}`, {
      method: "DELETE",
    }),
  downloadVersionPdf: async (versionId, filename = "Resume.pdf") => {
    return downloadBlob(`/resume-studio/versions/${versionId}/export/pdf`, { method: "GET" }, filename);
  },
  downloadVersionDocx: async (versionId, filename = "Resume.docx") => {
    return downloadBlob(`/resume-studio/versions/${versionId}/export/docx`, { method: "GET" }, filename);
  },
  downloadDirectPdf: async (data, filename = "Resume.pdf") => {
    return downloadBlob(
      "/resume-studio/export/pdf",
      { method: "POST", body: JSON.stringify(data) },
      filename
    );
  },
  downloadDirectDocx: async (data, filename = "Resume.docx") => {
    return downloadBlob(
      "/resume-studio/export/docx",
      { method: "POST", body: JSON.stringify(data) },
      filename
    );
  },

  // Premium Entitlements & Checkout
  getEntitlements: () => apiRequest("/resume-studio/entitlements"),
  checkEntitlement: (jobId) =>
    apiRequest(`/resume-studio/entitlements/check?job_id=${jobId}`),
  checkoutTailoredResume: (data) =>
    apiRequest("/resume-studio/checkout", {
      method: "POST",
      body: JSON.stringify(data),
    }),
};
