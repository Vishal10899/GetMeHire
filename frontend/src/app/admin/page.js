"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  ShieldCheck,
  Server,
  Database,
  Activity,
  RefreshCw,
  Plus,
  Play,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Clock,
  Layers,
  Loader2,
  X,
  Search,
  Sparkles,
  CalendarClock,
  Archive,
  Globe,
  ExternalLink,
  Building2,
  Check,
  ChevronLeft,
  ChevronRight,
  Filter,
  Briefcase,
} from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/authContext";

export default function AdminPage() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();

  const [sources, setSources] = useState([]);
  const [runs, setRuns] = useState([]);
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [syncingId, setSyncingId] = useState(null);
  const [syncMessage, setSyncMessage] = useState(null);
  const [showAddSourceModal, setShowAddSourceModal] = useState(false);

  // Tab State: "sources" | "discovery"
  const [activeTab, setActiveTab] = useState("sources");

  // Global Employer Discovery State
  const [discoverySummary, setDiscoverySummary] = useState(null);
  const [discoveryCompanies, setDiscoveryCompanies] = useState([]);
  const [discoveryTotal, setDiscoveryTotal] = useState(0);
  const [discoveryPage, setDiscoveryPage] = useState(1);
  const [discoveryTier, setDiscoveryTier] = useState("");
  const [discoveryQuery, setDiscoveryQuery] = useState("");
  const [discoveryLoading, setDiscoveryLoading] = useState(false);
  const [updatingCompanyId, setUpdatingCompanyId] = useState(null);
  const [triggeringDiscovery, setTriggeringDiscovery] = useState(false);

  // Global Search Quality Dashboard State
  const [qualityDashboard, setQualityDashboard] = useState(null);
  const [qualityLoading, setQualityLoading] = useState(false);

  // Automated Operations & Discovery State
  const [runningScheduler, setRunningScheduler] = useState(false);
  const [expiringStale, setExpiringStale] = useState(false);
  const [showProbeModal, setShowProbeModal] = useState(false);
  const [probeQuery, setProbeQuery] = useState("");
  const [probeLoading, setProbeLoading] = useState(false);
  const [probeResult, setProbeResult] = useState(null);
  const [discoverCompanyName, setDiscoverCompanyName] = useState("");
  const [discoverWebsite, setDiscoverWebsite] = useState("");
  const [discovering, setDiscovering] = useState(false);

  // New Source Form
  const [newSource, setNewSource] = useState({
    company_name: "",
    source_name: "",
    source_type: "GREENHOUSE",
    canonical_source_url: "",
    external_board_id: "",
    access_classification: "PUBLIC_API",
  });

  useEffect(() => {
    if (!authLoading && !user) {
      router.push("/login");
      return;
    }
    if (user && user.role !== "ADMIN") {
      router.push("/jobs");
      return;
    }
    if (user) {
      loadAdminData();
    }
  }, [user, authLoading]);

  const loadAdminData = async () => {
    setLoading(true);
    try {
      const [sourcesData, runsData, healthData, discoverySum, qualityData] = await Promise.all([
        api.getSources(),
        api.getIngestionRuns(),
        api.getHealth(),
        api.getDiscoverySummary().catch(() => null),
        api.getQualityDashboard().catch(() => null),
      ]);
      setSources(sourcesData || []);
      setRuns(runsData || []);
      setHealth(healthData);
      setDiscoverySummary(discoverySum);
      setQualityDashboard(qualityData);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const loadQualityDashboard = async () => {
    setQualityLoading(true);
    try {
      const data = await api.getQualityDashboard();
      setQualityDashboard(data);
    } catch (err) {
      console.error("Failed to load quality dashboard:", err);
    } finally {
      setQualityLoading(false);
    }
  };

  const loadDiscoveryCompanies = async (page = 1, tier = discoveryTier, q = discoveryQuery) => {
    setDiscoveryLoading(true);
    try {
      const res = await api.getDiscoveryCompanies({
        page,
        page_size: 20,
        tier: tier || undefined,
        query: q || undefined,
      });
      setDiscoveryCompanies(res?.items || []);
      setDiscoveryTotal(res?.total || 0);
      setDiscoveryPage(page);
    } catch (err) {
      console.error("Failed to load discovery companies:", err);
    } finally {
      setDiscoveryLoading(false);
    }
  };

  const handleUpdateCompanyTier = async (companyId, newTier) => {
    setUpdatingCompanyId(companyId);
    try {
      await api.updateCompanyStatus(companyId, newTier);
      const sum = await api.getDiscoverySummary();
      setDiscoverySummary(sum);
      loadDiscoveryCompanies(discoveryPage, discoveryTier, discoveryQuery);
    } catch (err) {
      alert(err.message || "Failed to update company verification tier");
    } finally {
      setUpdatingCompanyId(null);
    }
  };

  const handleTriggerDiscoveryRun = async () => {
    setTriggeringDiscovery(true);
    try {
      const res = await api.runDiscoveryPipeline({ limit_per_source: 200, verify_online: false });
      setSyncMessage({
        status: "SUCCESS",
        text: `Discovery batch completed: ${res?.result?.discovered_new || 0} new companies registered, ${res?.result?.duplicates_skipped || 0} duplicates skipped. Total companies: ${res?.result?.total_companies || 0}.`,
      });
      const sum = await api.getDiscoverySummary();
      setDiscoverySummary(sum);
      loadDiscoveryCompanies(1, discoveryTier, discoveryQuery);
    } catch (err) {
      alert(err.message || "Failed to execute discovery batch");
    } finally {
      setTriggeringDiscovery(false);
    }
  };

  const handleTriggerSync = async (sourceId) => {
    setSyncingId(sourceId);
    setSyncMessage(null);
    try {
      const run = await api.triggerSync(sourceId);
      setSyncMessage({
        sourceId,
        text: `Sync complete: Status ${run.status}. Discovered: ${run.records_discovered}, Inserted: ${run.records_inserted}, Updated: ${run.records_updated}, Unchanged: ${run.records_unchanged}.`,
        status: run.status,
      });
      loadAdminData();
    } catch (err) {
      setSyncMessage({
        sourceId,
        text: err.message || "Sync execution failed",
        status: "FAILED",
      });
    } finally {
      setSyncingId(null);
    }
  };

  const handleRunScheduler = async () => {
    setRunningScheduler(true);
    setSyncMessage(null);
    try {
      const res = await api.runScheduler(10);
      setSyncMessage({
        status: "SUCCESS",
        text: `Ingestion scheduler executed successfully: ${res.sources_evaluated} sources evaluated, ${res.stale_jobs_expired} stale jobs expired across active feeds.`,
      });
      loadAdminData();
    } catch (err) {
      setSyncMessage({
        status: "FAILED",
        text: err.message || "Failed to execute scheduler run",
      });
    } finally {
      setRunningScheduler(false);
    }
  };

  const handleExpireStaleJobs = async () => {
    if (!window.confirm("Run stale job expiration (14-day threshold)? Jobs unrefreshed for >14 days will be marked CLOSED.")) {
      return;
    }
    setExpiringStale(true);
    setSyncMessage(null);
    try {
      const res = await api.expireStaleJobs(14);
      setSyncMessage({
        status: "SUCCESS",
        text: res.message || `Expired ${res.expired_count} stale listings.`,
      });
      loadAdminData();
    } catch (err) {
      setSyncMessage({
        status: "FAILED",
        text: err.message || "Failed to expire stale listings",
      });
    } finally {
      setExpiringStale(false);
    }
  };

  const handleProbeBoard = async (e) => {
    if (e) e.preventDefault();
    if (!probeQuery.trim()) return;
    setProbeLoading(true);
    setProbeResult(null);
    try {
      const res = await api.probeBoard(probeQuery.trim());
      setProbeResult(res);
      if (res.found && !discoverCompanyName) {
        setDiscoverCompanyName(
          res.board_id ? res.board_id.charAt(0).toUpperCase() + res.board_id.slice(1) : ""
        );
      }
    } catch (err) {
      setProbeResult({ found: false, details: err.message || "Probe request failed" });
    } finally {
      setProbeLoading(false);
    }
  };

  const handleAutoDiscoverAndRegister = async () => {
    if (!discoverCompanyName.trim() || !probeQuery.trim()) {
      alert("Please enter a company name and board slug/query");
      return;
    }
    setDiscovering(true);
    try {
      const res = await api.discoverSource({
        company_name: discoverCompanyName.trim(),
        query: probeQuery.trim(),
        website: discoverWebsite.trim() || null,
        sync_now: true,
      });
      setShowProbeModal(false);
      setProbeQuery("");
      setProbeResult(null);
      setDiscoverCompanyName("");
      setDiscoverWebsite("");
      setSyncMessage({
        status: "SUCCESS",
        text: `Source "${res.company_name}" (${res.source_type}) registered & ingested successfully! Found ${res.sample_jobs_count} live listings.`,
      });
      loadAdminData();
    } catch (err) {
      alert(err.message || "Failed to auto-discover and register source");
    } finally {
      setDiscovering(false);
    }
  };

  const handleCreateSource = async (e) => {
    e.preventDefault();
    try {
      await api.createSource({
        company_name: newSource.company_name.trim(),
        source_name: newSource.source_name.trim(),
        source_type: newSource.source_type,
        canonical_source_url: newSource.canonical_source_url.trim(),
        external_board_id: newSource.external_board_id || null,
        access_classification: newSource.access_classification,
        configuration: {
          board_token: newSource.external_board_id,
          company_slug: newSource.external_board_id,
        },
      });
      setShowAddSourceModal(false);
      setNewSource({
        company_name: "",
        source_name: "",
        source_type: "GREENHOUSE",
        canonical_source_url: "",
        external_board_id: "",
        access_classification: "PUBLIC_API",
      });
      loadAdminData();
    } catch (err) {
      alert(err.message || "Failed to create source");
    }
  };

  if (loading || authLoading) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-20 flex flex-col items-center justify-center">
        <Loader2 className="w-8 h-8 text-blue-600 animate-spin mb-3" />
        <p className="text-sm font-semibold text-slate-500">
          Loading platform administration telemetry...
        </p>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <div className="space-y-1">
          <div className="flex items-center space-x-2">
            <ShieldCheck className="w-6 h-6 text-blue-600" />
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
              Ingestion Telemetry & Administration
            </h1>
          </div>
          <p className="text-xs text-slate-500">
            Real-time ATS source registries, sync operations, health telemetry, and anomaly monitoring.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => setShowProbeModal(true)}
            className="px-3.5 py-2 rounded-xl bg-indigo-50 border border-indigo-200 text-indigo-700 hover:bg-indigo-100 text-xs font-bold flex items-center space-x-1.5 transition-colors shadow-2xs"
          >
            <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
            <span>Auto-Discover ATS</span>
          </button>

          <button
            onClick={handleRunScheduler}
            disabled={runningScheduler}
            className="px-3.5 py-2 rounded-xl border border-slate-200 bg-white text-slate-700 hover:bg-slate-50 text-xs font-bold flex items-center space-x-1.5 transition-colors shadow-2xs disabled:opacity-50"
            title="Evaluate and run scheduled ingestion for due sources"
          >
            {runningScheduler ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <CalendarClock className="w-3.5 h-3.5 text-slate-500" />
            )}
            <span>Run Scheduler</span>
          </button>

          <button
            onClick={handleExpireStaleJobs}
            disabled={expiringStale}
            className="px-3.5 py-2 rounded-xl border border-slate-200 bg-white text-slate-700 hover:bg-amber-50 hover:border-amber-200 hover:text-amber-700 text-xs font-bold flex items-center space-x-1.5 transition-colors shadow-2xs disabled:opacity-50"
            title="Expire listings not refreshed within 14 days"
          >
            {expiringStale ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Archive className="w-3.5 h-3.5 text-slate-500" />
            )}
            <span>Expire Stale (14d)</span>
          </button>

          <button
            onClick={loadAdminData}
            className="p-2 rounded-xl border border-slate-200 bg-white text-slate-700 hover:bg-slate-50 text-xs font-bold flex items-center space-x-1 transition-colors shadow-2xs"
            title="Refresh tables"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={() => setShowAddSourceModal(true)}
            className="px-3.5 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold shadow-sm shadow-blue-500/20 flex items-center space-x-1.5 transition-all"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Manual Register</span>
          </button>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex items-center space-x-2 border-b border-slate-200 pb-3">
        <button
          onClick={() => setActiveTab("sources")}
          className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center space-x-2 ${
            activeTab === "sources"
              ? "bg-blue-600 text-white shadow-xs"
              : "bg-white text-slate-600 border border-slate-200 hover:bg-slate-50"
          }`}
        >
          <Server className="w-3.5 h-3.5" />
          <span>Ingestion & Source Telemetry</span>
        </button>

        <button
          onClick={() => {
            setActiveTab("discovery");
            loadDiscoveryCompanies(1);
          }}
          className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center space-x-2 ${
            activeTab === "discovery"
              ? "bg-blue-600 text-white shadow-xs"
              : "bg-white text-slate-600 border border-slate-200 hover:bg-slate-50"
          }`}
        >
          <Globe className="w-3.5 h-3.5" />
          <span>Global Employer Discovery & Tiers</span>
          {discoverySummary && (
            <span className={`ml-1.5 px-2 py-0.5 rounded-full text-[10px] font-extrabold ${
              activeTab === "discovery" ? "bg-white/20 text-white" : "bg-blue-100 text-blue-800"
            }`}>
              {discoverySummary.total_companies}
            </span>
          )}
        </button>

        <button
          onClick={() => {
            setActiveTab("quality");
            loadQualityDashboard();
          }}
          className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center space-x-2 ${
            activeTab === "quality"
              ? "bg-blue-600 text-white shadow-xs"
              : "bg-white text-slate-600 border border-slate-200 hover:bg-slate-50"
          }`}
        >
          <Activity className="w-3.5 h-3.5" />
          <span>Global Search Quality Dashboard</span>
          {qualityDashboard && (
            <span className={`ml-1.5 px-2 py-0.5 rounded-full text-[10px] font-extrabold ${
              activeTab === "quality" ? "bg-white/20 text-white" : "bg-emerald-100 text-emerald-800"
            }`}>
              {qualityDashboard.global_active_jobs.toLocaleString()}
            </span>
          )}
        </button>
      </div>

      {activeTab === "sources" && (
        <>
          {/* System Health Metric Cards */}
          {health && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="p-5 bg-white rounded-2xl border border-slate-200/90 shadow-xs space-y-1">
            <div className="flex items-center justify-between text-xs font-bold text-slate-400 uppercase tracking-wider">
              <span>Database & Engine</span>
              <Database className="w-4 h-4 text-blue-600" />
            </div>
            <div className="text-2xl font-extrabold text-slate-900 flex items-center space-x-2">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
              <span>{health.status}</span>
            </div>
            <p className="text-[11px] text-slate-400 font-medium">PostgreSQL 17 Authoritative</p>
          </div>

          <div className="p-5 bg-white rounded-2xl border border-slate-200/90 shadow-xs space-y-1">
            <div className="flex items-center justify-between text-xs font-bold text-slate-400 uppercase tracking-wider">
              <span>Active Sources</span>
              <Server className="w-4 h-4 text-indigo-600" />
            </div>
            <div className="text-2xl font-extrabold text-slate-900">
              {health.active_sources} / {health.total_sources}
            </div>
            <p className="text-[11px] text-slate-400 font-medium">
              {health.healthy_sources} Healthy, {health.failing_sources} Degraded
            </p>
          </div>

          <div className="p-5 bg-white rounded-2xl border border-slate-200/90 shadow-xs space-y-1">
            <div className="flex items-center justify-between text-xs font-bold text-slate-400 uppercase tracking-wider">
              <span>Active Listings</span>
              <Layers className="w-4 h-4 text-emerald-600" />
            </div>
            <div className="text-2xl font-extrabold text-emerald-600">
              {health.active_jobs}
            </div>
            <p className="text-[11px] text-slate-400 font-medium">
              {health.total_jobs} total records tracked
            </p>
          </div>

          <div className="p-5 bg-white rounded-2xl border border-slate-200/90 shadow-xs space-y-1">
            <div className="flex items-center justify-between text-xs font-bold text-slate-400 uppercase tracking-wider">
              <span>Stale / Quarantine</span>
              <AlertTriangle className="w-4 h-4 text-amber-500" />
            </div>
            <div className="text-2xl font-extrabold text-amber-600">
              {health.stale_jobs}
            </div>
            <p className="text-[11px] text-slate-400 font-medium">
              {health.closed_jobs} verified closed
            </p>
          </div>
        </div>
      )}

      {/* Sync Execution Feedback Banner */}
      {syncMessage && (
        <div
          className={`p-4 rounded-xl border text-xs font-medium flex items-center justify-between ${
            syncMessage.status === "SUCCESS"
              ? "bg-emerald-50 border-emerald-200 text-emerald-800"
              : syncMessage.status === "ANOMALY_QUARANTINE"
              ? "bg-amber-50 border-amber-200 text-amber-800"
              : "bg-red-50 border-red-200 text-red-800"
          }`}
        >
          <div className="flex items-center space-x-2">
            {syncMessage.status === "SUCCESS" ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            ) : (
              <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
            )}
            <span>{syncMessage.text}</span>
          </div>
          <button
            onClick={() => setSyncMessage(null)}
            className="text-slate-400 hover:text-slate-700"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Sources Registry Table */}
      <div className="bg-white rounded-2xl border border-slate-200/90 shadow-xs overflow-hidden space-y-4 p-6">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-bold text-slate-900">
            Company Source Registry
          </h2>
          <span className="text-xs text-slate-400 font-medium">{sources.length} adapters registered</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-600">
            <thead className="bg-slate-50 text-[11px] font-bold uppercase tracking-wider text-slate-400 border-y border-slate-200">
              <tr>
                <th className="py-3 px-4">Source Name & Company</th>
                <th className="py-3 px-4">Adapter</th>
                <th className="py-3 px-4">Health & Crawl State</th>
                <th className="py-3 px-4">Latest Crawl Telemetry</th>
                <th className="py-3 px-4">Crawl Timestamps & Errors</th>
                <th className="py-3 px-4">Active Jobs</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {sources.map((s) => (
                <tr key={s.id} className="hover:bg-slate-50/50">
                  <td className="py-3 px-4 font-semibold text-slate-900">
                    <div>{s.source_name}</div>
                    <div className="text-[11px] text-slate-400 font-normal">
                      {s.company_name} • {s.access_classification}
                    </div>
                  </td>
                  <td className="py-3 px-4">
                    <span className="px-2 py-0.5 rounded font-mono text-[11px] bg-slate-100 text-slate-700 font-medium">
                      {s.source_type}
                    </span>
                  </td>
                  <td className="py-3 px-4 space-y-1">
                    <div>
                      <span
                        className={`inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                          s.health_status === "HEALTHY"
                            ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                            : "bg-amber-50 text-amber-700 border border-amber-200"
                        }`}
                      >
                        <span
                          className={`w-1.5 h-1.5 rounded-full ${
                            s.health_status === "HEALTHY" ? "bg-emerald-500" : "bg-amber-500"
                          }`}
                        />
                        <span>{s.health_status}</span>
                      </span>
                    </div>
                    <div>
                      <span
                        className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium ${
                          s.pagination_status === "PARTIALLY_CRAWLED"
                            ? "bg-amber-50 text-amber-700 border border-amber-200"
                            : "bg-slate-100 text-slate-600"
                        }`}
                      >
                        {s.pagination_status === "PARTIALLY_CRAWLED" ? "Partially Crawled (Cursor Active)" : "Fully Crawled"}
                      </span>
                    </div>
                  </td>
                  <td className="py-3 px-4 text-[11px] space-y-0.5">
                    <div className="text-slate-700">
                      Discovered: <span className="font-semibold">{s.jobs_discovered ?? 0}</span>
                    </div>
                    <div className="text-emerald-700">
                      Accepted: <span className="font-semibold">{s.jobs_accepted ?? 0}</span>
                    </div>
                    {s.jobs_rejected > 0 && (
                      <div className="text-rose-600">
                        Rejected: <span className="font-semibold">{s.jobs_rejected}</span>
                      </div>
                    )}
                  </td>
                  <td className="py-3 px-4 text-[11px] text-slate-500 space-y-0.5">
                    <div>
                      Success:{" "}
                      <span className="font-medium text-slate-700">
                        {s.last_successful_sync_at
                          ? new Date(s.last_successful_sync_at).toLocaleString()
                          : "Never synced"}
                      </span>
                    </div>
                    {s.last_failure_at && (
                      <div className="text-rose-600" title={s.last_failure_message || "Failure encountered"}>
                        Failed: {new Date(s.last_failure_at).toLocaleDateString()}{" "}
                        {s.last_failure_message ? `(${s.last_failure_message.slice(0, 30)}...)` : ""}
                      </div>
                    )}
                  </td>
                  <td className="py-3 px-4 font-bold text-slate-800">
                    {s.active_jobs}
                  </td>
                  <td className="py-3 px-4 text-right">
                    <button
                      onClick={() => handleTriggerSync(s.id)}
                      disabled={syncingId === s.id}
                      className="inline-flex items-center space-x-1 px-3 py-1.5 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-semibold disabled:opacity-50 transition-colors shadow-2xs"
                    >
                      {syncingId === s.id ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      ) : (
                        <Play className="w-3.5 h-3.5" />
                      )}
                      <span>Run Sync</span>
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Ingestion Runs Log */}
      <div className="bg-white rounded-2xl border border-slate-200/90 shadow-xs p-6 space-y-4">
        <h2 className="text-base font-bold text-slate-900">
          Recent Ingestion Runs & Telemetry
        </h2>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-600">
            <thead className="bg-slate-50 text-[11px] font-bold uppercase tracking-wider text-slate-400 border-y border-slate-200">
              <tr>
                <th className="py-3 px-4">Run ID</th>
                <th className="py-3 px-4">Source</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Discovered</th>
                <th className="py-3 px-4">Inserted</th>
                <th className="py-3 px-4">Unchanged</th>
                <th className="py-3 px-4">Rejected</th>
                <th className="py-3 px-4">Duration</th>
                <th className="py-3 px-4">Time</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-mono text-[11px]">
              {runs.map((r) => (
                <tr key={r.id} className="hover:bg-slate-50/50">
                  <td className="py-3 px-4 text-slate-400">#{r.id}</td>
                  <td className="py-3 px-4 font-sans font-semibold text-slate-800">
                    {r.source_name}
                  </td>
                  <td className="py-3 px-4 font-sans">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        r.status === "SUCCESS"
                          ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                          : r.status === "ANOMALY_QUARANTINE"
                          ? "bg-amber-50 text-amber-700 border border-amber-200"
                          : "bg-red-50 text-red-700 border border-red-200"
                      }`}
                    >
                      {r.status}
                    </span>
                  </td>
                  <td className="py-3 px-4">{r.records_discovered}</td>
                  <td className="py-3 px-4 text-emerald-600 font-bold">
                    +{r.records_inserted}
                  </td>
                  <td className="py-3 px-4">{r.records_unchanged}</td>
                  <td className="py-3 px-4 text-red-500">{r.records_rejected}</td>
                  <td className="py-3 px-4">{r.duration_seconds || 0}s</td>
                  <td className="py-3 px-4 font-sans text-slate-400">
                    {new Date(r.start_time).toLocaleTimeString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      </>
      )}

      {activeTab === "discovery" && (
        <div className="space-y-6">
          {/* Tier Overview Cards */}
          {discoverySummary && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-base font-extrabold text-slate-900">
                    Employer Discovery Network & Verification Tiers
                  </h2>
                  <p className="text-xs text-slate-500">
                    Tiered verification funnel across 20 industries and 9 global regions.
                  </p>
                </div>

                <button
                  onClick={handleTriggerDiscoveryRun}
                  disabled={triggeringDiscovery}
                  className="px-3.5 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold shadow-sm shadow-blue-500/20 flex items-center space-x-1.5 disabled:opacity-50 transition-all"
                >
                  {triggeringDiscovery ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Sparkles className="w-3.5 h-3.5" />
                  )}
                  <span>Run Discovery Batch</span>
                </button>
              </div>

              {/* Section 7: Comprehensive Discovery & Verification Telemetry Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
                <div className="p-4 bg-white rounded-2xl border border-slate-200 shadow-2xs space-y-1">
                  <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Total Registered</div>
                  <div className="text-xl font-extrabold text-slate-900">{discoverySummary.total_companies}</div>
                  <div className="text-[10px] text-slate-500">Corporate directory</div>
                </div>

                <div className="p-4 bg-white rounded-2xl border border-blue-200 shadow-2xs space-y-1 bg-gradient-to-b from-blue-50/30 to-transparent">
                  <div className="text-[10px] font-bold text-blue-600 uppercase tracking-wider">Domain Verified</div>
                  <div className="text-xl font-extrabold text-blue-700">
                    {discoverySummary.domain_verified_companies ?? discoverySummary.tiers?.DOMAIN_VERIFIED ?? 0}
                  </div>
                  <div className="text-[10px] text-blue-600/70">Official domain live</div>
                </div>

                <div className="p-4 bg-white rounded-2xl border border-indigo-200 shadow-2xs space-y-1 bg-gradient-to-b from-indigo-50/30 to-transparent">
                  <div className="text-[10px] font-bold text-indigo-600 uppercase tracking-wider">Career Pages</div>
                  <div className="text-xl font-extrabold text-indigo-700">
                    {discoverySummary.career_pages_found ?? discoverySummary.tiers?.CAREER_PAGE_FOUND ?? 0}
                  </div>
                  <div className="text-[10px] text-indigo-600/70">Hiring portal active</div>
                </div>

                <div className="p-4 bg-white rounded-2xl border border-cyan-200 shadow-2xs space-y-1 bg-gradient-to-b from-cyan-50/30 to-transparent">
                  <div className="text-[10px] font-bold text-cyan-600 uppercase tracking-wider">Verified ATS Sources</div>
                  <div className="text-xl font-extrabold text-cyan-700">
                    {discoverySummary.verified_ats_sources ?? discoverySummary.tiers?.SOURCE_VERIFIED ?? 0}
                  </div>
                  <div className="text-[10px] text-cyan-600/70">ATS endpoints linked</div>
                </div>

                <div className="p-4 bg-white rounded-2xl border border-emerald-200 shadow-2xs space-y-1 bg-gradient-to-b from-emerald-50/30 to-transparent">
                  <div className="text-[10px] font-bold text-emerald-600 uppercase tracking-wider">Active Job Sources</div>
                  <div className="text-xl font-extrabold text-emerald-700">
                    {discoverySummary.active_job_sources ?? discoverySummary.tiers?.ACTIVE_JOB_SOURCE ?? 0}
                  </div>
                  <div className="text-[10px] text-emerald-600/70">Current open vacancies</div>
                </div>

                <div className="p-4 bg-white rounded-2xl border border-amber-200 shadow-2xs space-y-1 bg-gradient-to-b from-amber-50/30 to-transparent">
                  <div className="text-[10px] font-bold text-amber-600 uppercase tracking-wider">No Current Vacancies</div>
                  <div className="text-xl font-extrabold text-amber-700">
                    {discoverySummary.no_current_vacancies ?? discoverySummary.tiers?.NO_CURRENT_VACANCIES ?? 0}
                  </div>
                  <div className="text-[10px] text-amber-600/70">Verified, 0 active jobs</div>
                </div>

                <div className="p-4 bg-white rounded-2xl border border-purple-200 shadow-2xs space-y-1 bg-gradient-to-b from-purple-50/30 to-transparent">
                  <div className="text-[10px] font-bold text-purple-600 uppercase tracking-wider">Partially Crawled</div>
                  <div className="text-xl font-extrabold text-purple-700">
                    {discoverySummary.partially_crawled_sources ?? 0}
                  </div>
                  <div className="text-[10px] text-purple-600/70">Continuation cursor saved</div>
                </div>

                <div className="p-4 bg-white rounded-2xl border border-slate-200 shadow-2xs space-y-1">
                  <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Pending Verification</div>
                  <div className="text-xl font-extrabold text-slate-700">
                    {discoverySummary.pending_verification ?? discoverySummary.tiers?.DISCOVERED ?? 0}
                  </div>
                  <div className="text-[10px] text-slate-400">In discovery queue</div>
                </div>

                <div className="p-4 bg-white rounded-2xl border border-rose-200 shadow-2xs space-y-1 bg-gradient-to-b from-rose-50/30 to-transparent">
                  <div className="text-[10px] font-bold text-rose-600 uppercase tracking-wider">Unsupported Sources</div>
                  <div className="text-xl font-extrabold text-rose-700">
                    {discoverySummary.unsupported_sources ?? discoverySummary.tiers?.UNSUPPORTED ?? 0}
                  </div>
                  <div className="text-[10px] text-rose-600/70">Blocked / dead feeds</div>
                </div>

                <div className="p-4 bg-white rounded-2xl border border-emerald-200 shadow-2xs space-y-1 bg-gradient-to-b from-emerald-50/30 to-transparent">
                  <div className="text-[10px] font-bold text-emerald-600 uppercase tracking-wider">Active Jobs Indexed</div>
                  <div className="text-xl font-extrabold text-emerald-700">
                    {discoverySummary.active_jobs_count ?? 0}
                  </div>
                  <div className="text-[10px] text-emerald-600/70">Original application URLs</div>
                </div>

                <div className="p-4 bg-white rounded-2xl border border-slate-200 shadow-2xs space-y-1">
                  <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Rejected Jobs</div>
                  <div className="text-xl font-extrabold text-slate-700">
                    {discoverySummary.jobs_rejected_count ?? 0}
                  </div>
                  <div className="text-[10px] text-slate-400">Duplicates & invalid URLs</div>
                </div>
              </div>

              {/* Country & Industry Breakdown Panels */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Country Breakdown */}
                <div className="p-5 bg-white rounded-2xl border border-slate-200 shadow-xs space-y-3">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                      Worldwide Country Distribution
                    </h3>
                    <span className="text-[11px] text-slate-400 font-medium">Top represented nations</span>
                  </div>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                    {(discoverySummary.countries || []).slice(0, 9).map((c, idx) => (
                      <div key={idx} className="p-2 rounded-xl bg-slate-50 border border-slate-100 flex items-center justify-between">
                        <span className="text-xs font-semibold text-slate-700 truncate mr-1">{c.country}</span>
                        <span className="px-1.5 py-0.5 rounded-full text-[10px] font-bold bg-white text-slate-600 border border-slate-200 shrink-0">
                          {c.count}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Industry Breakdown */}
                <div className="p-5 bg-white rounded-2xl border border-slate-200 shadow-xs space-y-3">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                      Industry Sector Coverage
                    </h3>
                    <span className="text-[11px] text-slate-400 font-medium">20 canonical categories</span>
                  </div>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                    {(discoverySummary.industries || []).slice(0, 9).map((ind, idx) => (
                      <div key={idx} className="p-2 rounded-xl bg-slate-50 border border-slate-100 flex items-center justify-between">
                        <span className="text-xs font-semibold text-slate-700 truncate mr-1">{ind.industry}</span>
                        <span className="px-1.5 py-0.5 rounded-full text-[10px] font-bold bg-white text-slate-600 border border-slate-200 shrink-0">
                          {ind.count}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* India Coverage & Hiring Diagnostics (Section 6) */}
              {discoverySummary.india_diagnostics && (
                <div className="p-6 bg-gradient-to-br from-indigo-50/40 via-white to-amber-50/30 rounded-2xl border border-indigo-100 shadow-xs space-y-5">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-indigo-100/60 pb-3">
                    <div>
                      <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                        <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse"></span>
                        India Employer & Job Coverage Diagnostics
                      </h3>
                      <p className="text-xs text-slate-500 mt-0.5">
                        Real-time telemetry of verified Indian employers, public ATS sources, and authentic live vacancies
                      </p>
                    </div>
                    <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-indigo-100 text-indigo-800 self-start sm:self-auto">
                      {discoverySummary.india_diagnostics.active_vacancies || 0} Live India Jobs
                    </span>
                  </div>

                  {/* 5 India Metric Cards */}
                  <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
                    <div className="p-3 bg-white rounded-xl border border-slate-200/80 shadow-2xs space-y-1">
                      <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Registered Employers</div>
                      <div className="text-lg font-extrabold text-slate-800">{discoverySummary.india_diagnostics.registered_employers || 0}</div>
                      <div className="text-[10px] text-slate-400">Indian corporate entities</div>
                    </div>
                    <div className="p-3 bg-white rounded-xl border border-blue-200 shadow-2xs space-y-1">
                      <div className="text-[10px] font-bold text-blue-600 uppercase tracking-wider">Domain Verified</div>
                      <div className="text-lg font-extrabold text-blue-700">{discoverySummary.india_diagnostics.verified_employers || 0}</div>
                      <div className="text-[10px] text-blue-600/70">Canonical domain active</div>
                    </div>
                    <div className="p-3 bg-white rounded-xl border border-cyan-200 shadow-2xs space-y-1">
                      <div className="text-[10px] font-bold text-cyan-600 uppercase tracking-wider">India Career Pages</div>
                      <div className="text-lg font-extrabold text-cyan-700">{discoverySummary.india_diagnostics.employers_with_career_pages || 0}</div>
                      <div className="text-[10px] text-cyan-600/70">Official portals identified</div>
                    </div>
                    <div className="p-3 bg-white rounded-xl border border-emerald-200 shadow-2xs space-y-1">
                      <div className="text-[10px] font-bold text-emerald-600 uppercase tracking-wider">Active Job Sources</div>
                      <div className="text-lg font-extrabold text-emerald-700">{discoverySummary.india_diagnostics.active_job_sources || 0}</div>
                      <div className="text-[10px] text-emerald-600/70">Verified ATS boards</div>
                    </div>
                    <div className="p-3 bg-white rounded-xl border border-indigo-200 shadow-2xs space-y-1">
                      <div className="text-[10px] font-bold text-indigo-600 uppercase tracking-wider">Live India Vacancies</div>
                      <div className="text-lg font-extrabold text-indigo-700">{discoverySummary.india_diagnostics.active_vacancies || 0}</div>
                      <div className="text-[10px] text-indigo-600/70">Authentic application URLs</div>
                    </div>
                  </div>

                  {/* City-wise and Employer-wise Vacancy Breakdown */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
                    {/* City Breakdown */}
                    <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-2xs space-y-2.5">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-slate-800 uppercase tracking-wider">India City-Wise Vacancy Distribution</span>
                        <span className="text-[10px] text-slate-400">Major Tech Hubs</span>
                      </div>
                      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                        {(discoverySummary.india_diagnostics.city_distribution || []).slice(0, 9).map((cd, idx) => (
                          <div key={idx} className="p-2 rounded-lg bg-slate-50 border border-slate-100 flex items-center justify-between">
                            <span className="text-xs font-semibold text-slate-700 truncate mr-1">{cd.city}</span>
                            <span className="px-1.5 py-0.5 rounded-md text-[10px] font-bold bg-white text-indigo-700 border border-slate-200 shrink-0">
                              {cd.count}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Top Employers */}
                    <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-2xs space-y-2.5">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-slate-800 uppercase tracking-wider">Employer-Wise Vacancy Volume</span>
                        <span className="text-[10px] text-slate-400">Live Postings</span>
                      </div>
                      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                        {(discoverySummary.india_diagnostics.employer_distribution || []).slice(0, 9).map((ed, idx) => (
                          <div key={idx} className="p-2 rounded-lg bg-slate-50 border border-slate-100 flex items-center justify-between">
                            <span className="text-xs font-semibold text-slate-700 truncate mr-1">{ed.company}</span>
                            <span className="px-1.5 py-0.5 rounded-md text-[10px] font-bold bg-white text-emerald-700 border border-slate-200 shrink-0">
                              {ed.count}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Search & Filter Toolbar */}
          <div className="bg-white rounded-2xl border border-slate-200/90 shadow-xs p-5 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="relative flex-1 max-w-md">
                <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  placeholder="Search employer name or domain..."
                  value={discoveryQuery}
                  onChange={(e) => setDiscoveryQuery(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") loadDiscoveryCompanies(1, discoveryTier, discoveryQuery);
                  }}
                  className="w-full pl-9 pr-3 py-2 text-xs rounded-xl border border-slate-200 focus:outline-none focus:border-blue-500"
                />
              </div>

              <div className="flex flex-wrap items-center gap-1.5">
                {[
                  { key: "", label: "All Tiers" },
                  { key: "ACTIVE_JOB_SOURCE", label: "Active Jobs" },
                  { key: "SOURCE_VERIFIED", label: "Source Verified" },
                  { key: "CAREER_PAGE_FOUND", label: "Career Page" },
                  { key: "DOMAIN_VERIFIED", label: "Domain Verified" },
                  { key: "NO_CURRENT_VACANCIES", label: "No Vacancies" },
                  { key: "DISCOVERED", label: "Discovered" },
                ].map((t) => (
                  <button
                    key={t.key}
                    onClick={() => {
                      setDiscoveryTier(t.key);
                      loadDiscoveryCompanies(1, t.key, discoveryQuery);
                    }}
                    className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-all ${
                      discoveryTier === t.key
                        ? "bg-slate-900 text-white shadow-2xs"
                        : "bg-slate-100 text-slate-600 hover:bg-slate-200/80"
                    }`}
                  >
                    {t.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Discovery Companies Table */}
            <div className="overflow-x-auto">
              {discoveryLoading ? (
                <div className="py-12 flex flex-col items-center justify-center space-y-2">
                  <Loader2 className="w-6 h-6 text-blue-600 animate-spin" />
                  <p className="text-xs text-slate-400">Loading discovery directory...</p>
                </div>
              ) : discoveryCompanies.length === 0 ? (
                <div className="py-12 text-center text-xs text-slate-400">
                  No company records match your search criteria.
                </div>
              ) : (
                <table className="w-full text-left text-xs text-slate-600">
                  <thead className="bg-slate-50 text-[11px] font-bold uppercase tracking-wider text-slate-400 border-y border-slate-200">
                    <tr>
                      <th className="py-3 px-4">Company Name & Domain</th>
                      <th className="py-3 px-4">Industry</th>
                      <th className="py-3 px-4">Region / Country</th>
                      <th className="py-3 px-4">Verification Tier</th>
                      <th className="py-3 px-4">Jobs</th>
                      <th className="py-3 px-4 text-right">Admin Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {discoveryCompanies.map((c) => (
                      <tr key={c.id} className="hover:bg-slate-50/50">
                        <td className="py-3 px-4">
                          <div className="font-bold text-slate-900">{c.canonical_name}</div>
                          <div className="flex items-center space-x-1.5 text-[11px] text-slate-400">
                            {c.domain && (
                              <a
                                href={c.website || `https://${c.domain}`}
                                target="_blank"
                                rel="noreferrer"
                                className="text-blue-600 hover:underline flex items-center space-x-0.5"
                              >
                                <span>{c.domain}</span>
                                <ExternalLink className="w-3 h-3" />
                              </a>
                            )}
                            {c.career_page_url && (
                              <a
                                href={c.career_page_url}
                                target="_blank"
                                rel="noreferrer"
                                className="text-indigo-600 hover:underline flex items-center space-x-0.5 ml-2"
                              >
                                <span>[Careers]</span>
                              </a>
                            )}
                          </div>
                        </td>
                        <td className="py-3 px-4">
                          <span className="font-medium text-slate-700">{c.industry || "General Enterprise"}</span>
                        </td>
                        <td className="py-3 px-4 text-slate-500">
                          <div>{c.country || "Global"}</div>
                          <div className="text-[10px] text-slate-400">{c.operating_region}</div>
                        </td>
                        <td className="py-3 px-4">
                          <span
                            className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold ${
                              c.verification_status === "ACTIVE_JOB_SOURCE"
                                ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                                : c.verification_status === "SOURCE_VERIFIED"
                                ? "bg-cyan-50 text-cyan-700 border border-cyan-200"
                                : c.verification_status === "CAREER_PAGE_FOUND"
                                ? "bg-indigo-50 text-indigo-700 border border-indigo-200"
                                : c.verification_status === "DOMAIN_VERIFIED"
                                ? "bg-blue-50 text-blue-700 border border-blue-200"
                                : c.verification_status === "NO_CURRENT_VACANCIES"
                                ? "bg-amber-50 text-amber-700 border border-amber-200"
                                : "bg-slate-100 text-slate-600"
                            }`}
                          >
                            {c.verification_status}
                          </span>
                        </td>
                        <td className="py-3 px-4 font-bold text-slate-800">
                          {c.active_jobs_count || 0}
                        </td>
                        <td className="py-3 px-4 text-right space-x-1">
                          <button
                            onClick={() => handleUpdateCompanyTier(c.id, "DOMAIN_VERIFIED")}
                            disabled={updatingCompanyId === c.id}
                            className="px-2.5 py-1 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-[11px] font-semibold text-slate-700 transition-colors"
                            title="Approve official domain"
                          >
                            Verify Domain
                          </button>
                          <button
                            onClick={() => handleUpdateCompanyTier(c.id, "UNSUPPORTED")}
                            disabled={updatingCompanyId === c.id}
                            className="px-2 py-1 rounded-lg border border-slate-200 bg-white hover:bg-rose-50 hover:text-rose-700 text-[11px] font-semibold text-slate-500 transition-colors"
                            title="Mark as unsupported / blocked"
                          >
                            Reject
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>

            {/* Pagination Controls */}
            {discoveryTotal > 20 && (
              <div className="flex items-center justify-between pt-3 border-t border-slate-100 text-xs text-slate-500">
                <div>
                  Showing {Math.min((discoveryPage - 1) * 20 + 1, discoveryTotal)} to{" "}
                  {Math.min(discoveryPage * 20, discoveryTotal)} of {discoveryTotal} employers
                </div>
                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => loadDiscoveryCompanies(discoveryPage - 1)}
                    disabled={discoveryPage <= 1}
                    className="p-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 disabled:opacity-40"
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </button>
                  <span className="font-semibold text-slate-700">
                    Page {discoveryPage} of {Math.ceil(discoveryTotal / 20)}
                  </span>
                  <button
                    onClick={() => loadDiscoveryCompanies(discoveryPage + 1)}
                    disabled={discoveryPage >= Math.ceil(discoveryTotal / 20)}
                    className="p-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 disabled:opacity-40"
                  >
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Global Search Quality Dashboard Tab */}
      {activeTab === "quality" && (
        <div className="space-y-6">
          {/* Quality Dashboard Header */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-5 bg-white rounded-2xl border border-slate-200/90 shadow-xs">
            <div>
              <div className="flex items-center space-x-2">
                <Activity className="w-5 h-5 text-blue-600" />
                <h2 className="text-base font-extrabold text-slate-900">
                  Global Universal Job Discovery & Quality Dashboard
                </h2>
                <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">
                  Live PostgreSQL Telemetry
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-1">
                Authoritative metrics and gap analysis across worldwide industries, professions, locations, and employment modalities.
              </p>
            </div>
            <div className="flex items-center space-x-3 shrink-0">
              {qualityDashboard?.timestamp && (
                <span className="text-[11px] text-slate-400 font-medium">
                  Updated: {new Date(qualityDashboard.timestamp).toLocaleTimeString()}
                </span>
              )}
              <button
                onClick={loadQualityDashboard}
                disabled={qualityLoading}
                className="px-3 py-1.5 rounded-xl border border-slate-200 bg-white text-slate-700 hover:bg-slate-50 text-xs font-bold flex items-center space-x-1.5 transition-colors shadow-2xs disabled:opacity-50"
              >
                {qualityLoading ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <RefreshCw className="w-3.5 h-3.5 text-slate-600" />
                )}
                <span>Refresh Metrics</span>
              </button>
            </div>
          </div>

          {qualityDashboard ? (
            <>
              {/* Top KPI Summary Cards */}
              <div className="grid grid-cols-2 md:grid-cols-5 gap-3.5">
                <div className="p-4 bg-white rounded-2xl border border-slate-200/90 shadow-xs space-y-1">
                  <div className="flex items-center justify-between text-xs font-bold text-slate-400 uppercase tracking-wider">
                    <span>Global Active Jobs</span>
                    <Briefcase className="w-4 h-4 text-blue-600" />
                  </div>
                  <div className="text-2xl font-extrabold text-slate-900">
                    {qualityDashboard.global_active_jobs.toLocaleString()}
                  </div>
                  <p className="text-[11px] text-emerald-600 font-semibold flex items-center space-x-1">
                    <CheckCircle2 className="w-3 h-3 inline" />
                    <span>Worldwide Indexed</span>
                  </p>
                </div>

                <div className="p-4 bg-white rounded-2xl border border-slate-200/90 shadow-xs space-y-1">
                  <div className="flex items-center justify-between text-xs font-bold text-slate-400 uppercase tracking-wider">
                    <span>Active Employers</span>
                    <Building2 className="w-4 h-4 text-indigo-600" />
                  </div>
                  <div className="text-2xl font-extrabold text-slate-900">
                    {qualityDashboard.active_employers}
                  </div>
                  <p className="text-[11px] text-slate-400 font-medium">Direct ATS verified</p>
                </div>

                <div className="p-4 bg-white rounded-2xl border border-slate-200/90 shadow-xs space-y-1">
                  <div className="flex items-center justify-between text-xs font-bold text-slate-400 uppercase tracking-wider">
                    <span>Active Sources</span>
                    <Server className="w-4 h-4 text-emerald-600" />
                  </div>
                  <div className="text-2xl font-extrabold text-slate-900">
                    {qualityDashboard.active_job_sources}
                  </div>
                  <p className="text-[11px] text-slate-400 font-medium">Public job feeds</p>
                </div>

                <div className="p-4 bg-white rounded-2xl border border-slate-200/90 shadow-xs space-y-1">
                  <div className="flex items-center justify-between text-xs font-bold text-slate-400 uppercase tracking-wider">
                    <span>Stale Listings</span>
                    <Clock className="w-4 h-4 text-amber-500" />
                  </div>
                  <div className="text-2xl font-extrabold text-amber-700">
                    {qualityDashboard.stale_jobs_count.toLocaleString()}
                  </div>
                  <p className="text-[11px] text-slate-400 font-medium">&gt; 14 days unrefreshed</p>
                </div>

                <div className="p-4 bg-white rounded-2xl border border-slate-200/90 shadow-xs space-y-1">
                  <div className="flex items-center justify-between text-xs font-bold text-slate-400 uppercase tracking-wider">
                    <span>Closed Listings</span>
                    <Archive className="w-4 h-4 text-slate-500" />
                  </div>
                  <div className="text-2xl font-extrabold text-slate-700">
                    {qualityDashboard.closed_jobs_count.toLocaleString()}
                  </div>
                  <p className="text-[11px] text-slate-400 font-medium">Archived from ATS</p>
                </div>
              </div>

              {/* Geographic Breakdown: Countries & Cities */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                {/* Countries */}
                <div className="p-5 bg-white rounded-2xl border border-slate-200/90 shadow-xs space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <Globe className="w-4 h-4 text-blue-600" />
                      <h3 className="text-sm font-bold text-slate-900">Country-Wise Vacancy Counts</h3>
                    </div>
                    <span className="text-xs font-semibold text-slate-500">
                      {qualityDashboard.country_distribution?.length || 0} Countries Represented
                    </span>
                  </div>
                  <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
                    {qualityDashboard.country_distribution?.map((item, idx) => {
                      const maxCount = qualityDashboard.country_distribution[0]?.count || 1;
                      const pct = Math.round((item.count / maxCount) * 100);
                      return (
                        <div key={idx} className="space-y-1">
                          <div className="flex justify-between text-xs font-medium text-slate-700">
                            <span className="font-semibold">{item.country || "Unspecified"}</span>
                            <span className="font-mono text-slate-600 font-bold">{item.count.toLocaleString()}</span>
                          </div>
                          <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                            <div
                              className="bg-blue-600 h-1.5 rounded-full transition-all duration-300"
                              style={{ width: `${pct}%` }}
                            />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Cities */}
                <div className="p-5 bg-white rounded-2xl border border-slate-200/90 shadow-xs space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <Layers className="w-4 h-4 text-indigo-600" />
                      <h3 className="text-sm font-bold text-slate-900">City-Wise Vacancy Counts</h3>
                    </div>
                    <span className="text-xs font-semibold text-slate-500">
                      Top {Math.min(qualityDashboard.city_distribution?.length || 0, 20)} Cities
                    </span>
                  </div>
                  <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
                    {qualityDashboard.city_distribution?.slice(0, 25).map((item, idx) => {
                      const maxCityCount = qualityDashboard.city_distribution[0]?.count || 1;
                      const pct = Math.round((item.count / maxCityCount) * 100);
                      return (
                        <div key={idx} className="space-y-1">
                          <div className="flex justify-between text-xs font-medium text-slate-700">
                            <span className="font-semibold">{item.city || "Unspecified / Remote"}</span>
                            <span className="font-mono text-slate-600 font-bold">{item.count.toLocaleString()}</span>
                          </div>
                          <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                            <div
                              className="bg-indigo-600 h-1.5 rounded-full transition-all duration-300"
                              style={{ width: `${pct}%` }}
                            />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>

              {/* Profession & Industry Coverage */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                {/* Professions */}
                <div className="p-5 bg-white rounded-2xl border border-slate-200/90 shadow-xs space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <Briefcase className="w-4 h-4 text-emerald-600" />
                      <h3 className="text-sm font-bold text-slate-900">Profession-Wise Distribution</h3>
                    </div>
                    <span className="text-xs font-semibold text-slate-500">
                      Universal Domain Coverage
                    </span>
                  </div>
                  <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
                    {qualityDashboard.profession_distribution?.map((item, idx) => {
                      const totalJobs = qualityDashboard.global_active_jobs || 1;
                      const pct = Math.round((item.count / totalJobs) * 100);
                      return (
                        <div key={idx} className="flex items-center justify-between text-xs p-2 rounded-xl bg-slate-50 border border-slate-100">
                          <div className="flex items-center space-x-2">
                            <span className="w-2 h-2 rounded-full bg-emerald-500" />
                            <span className="font-semibold text-slate-800">{item.profession}</span>
                          </div>
                          <div className="flex items-center space-x-3">
                            <span className="text-[11px] text-slate-400 font-medium">{pct}%</span>
                            <span className="font-mono font-bold text-slate-700 bg-white px-2 py-0.5 rounded-lg border border-slate-200">
                              {item.count.toLocaleString()}
                            </span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Industries */}
                <div className="p-5 bg-white rounded-2xl border border-slate-200/90 shadow-xs space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <Building2 className="w-4 h-4 text-purple-600" />
                      <h3 className="text-sm font-bold text-slate-900">Industry-Wise Distribution</h3>
                    </div>
                    <span className="text-xs font-semibold text-slate-500">
                      Verified Employer Industries
                    </span>
                  </div>
                  <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
                    {qualityDashboard.industry_distribution?.map((item, idx) => (
                      <div key={idx} className="flex items-center justify-between text-xs p-2 rounded-xl bg-slate-50 border border-slate-100">
                        <div className="flex items-center space-x-2">
                          <span className="w-2 h-2 rounded-full bg-purple-500" />
                          <span className="font-semibold text-slate-800">{item.industry || "General Industry"}</span>
                        </div>
                        <span className="font-mono font-bold text-slate-700 bg-white px-2 py-0.5 rounded-lg border border-slate-200">
                          {item.count.toLocaleString()}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Modality & Employment Type Breakdown (3 Columns) */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                {/* Employment Type */}
                <div className="p-5 bg-white rounded-2xl border border-slate-200/90 shadow-xs space-y-3">
                  <div className="flex items-center space-x-2">
                    <Clock className="w-4 h-4 text-blue-600" />
                    <h3 className="text-sm font-bold text-slate-900">Employment Types</h3>
                  </div>
                  <div className="space-y-2">
                    {qualityDashboard.employment_type_distribution?.map((item, idx) => (
                      <div key={idx} className="flex items-center justify-between text-xs py-1.5 px-2.5 rounded-lg bg-slate-50 border border-slate-100">
                        <span className="font-semibold text-slate-700">{item.employment_type}</span>
                        <span className="font-mono font-bold text-slate-800">{item.count.toLocaleString()}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Work Arrangement */}
                <div className="p-5 bg-white rounded-2xl border border-slate-200/90 shadow-xs space-y-3">
                  <div className="flex items-center space-x-2">
                    <Layers className="w-4 h-4 text-emerald-600" />
                    <h3 className="text-sm font-bold text-slate-900">Work Arrangements</h3>
                  </div>
                  <div className="space-y-2">
                    {qualityDashboard.work_arrangement_distribution?.map((item, idx) => (
                      <div key={idx} className="flex items-center justify-between text-xs py-1.5 px-2.5 rounded-lg bg-slate-50 border border-slate-100">
                        <span className="font-semibold text-slate-700">{item.work_arrangement}</span>
                        <span className="font-mono font-bold text-slate-800">{item.count.toLocaleString()}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Remote Eligibility */}
                <div className="p-5 bg-white rounded-2xl border border-slate-200/90 shadow-xs space-y-3">
                  <div className="flex items-center space-x-2">
                    <Globe className="w-4 h-4 text-indigo-600" />
                    <h3 className="text-sm font-bold text-slate-900">Remote Eligibility</h3>
                  </div>
                  <div className="space-y-2">
                    {qualityDashboard.remote_eligibility_distribution?.map((item, idx) => (
                      <div key={idx} className="flex items-center justify-between text-xs py-1.5 px-2.5 rounded-lg bg-slate-50 border border-slate-100">
                        <span className="font-semibold text-slate-700">{item.remote_eligibility}</span>
                        <span className="font-mono font-bold text-slate-800">{item.count.toLocaleString()}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Source Gaps: Zero Indexed, Failed, and Partially Crawled */}
              <div className="space-y-5">
                {/* Zero Job Sources */}
                <div className="bg-white rounded-2xl border border-slate-200/90 shadow-xs p-5 space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-sm font-bold text-slate-900 flex items-center space-x-2">
                        <AlertTriangle className="w-4 h-4 text-amber-500" />
                        <span>Sources Showing Zero Indexed Jobs</span>
                        <span className="ml-2 px-2 py-0.5 rounded-full text-xs font-bold bg-amber-100 text-amber-800">
                          {qualityDashboard.zero_job_sources?.length || 0}
                        </span>
                      </h3>
                      <p className="text-xs text-slate-500 mt-0.5">
                        Registered employer sources that currently yield 0 active listings and require ingestion re-probing or adapter configuration update.
                      </p>
                    </div>
                  </div>

                  {qualityDashboard.zero_job_sources?.length > 0 ? (
                    <div className="overflow-x-auto rounded-xl border border-slate-200 max-h-64 overflow-y-auto">
                      <table className="w-full text-left text-xs">
                        <thead className="bg-slate-50 text-slate-500 font-bold uppercase tracking-wider sticky top-0">
                          <tr>
                            <th className="py-2.5 px-3">Company</th>
                            <th className="py-2.5 px-3">Source Name</th>
                            <th className="py-2.5 px-3">Health Status</th>
                            <th className="py-2.5 px-3">Career URL</th>
                            <th className="py-2.5 px-3 text-right">Action</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 text-slate-700 font-medium">
                          {qualityDashboard.zero_job_sources.map((s, idx) => (
                            <tr key={idx} className="hover:bg-slate-50/60">
                              <td className="py-2.5 px-3 font-semibold text-slate-900">{s.company_name}</td>
                              <td className="py-2.5 px-3">{s.source_name}</td>
                              <td className="py-2.5 px-3">
                                <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                                  s.health_status === "HEALTHY"
                                    ? "bg-emerald-100 text-emerald-800"
                                    : "bg-amber-100 text-amber-800"
                                }`}>
                                  {s.health_status}
                                </span>
                              </td>
                              <td className="py-2.5 px-3 truncate max-w-xs">
                                <a
                                  href={s.career_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-blue-600 hover:underline flex items-center space-x-1"
                                >
                                  <span className="truncate">{s.career_url}</span>
                                  <ExternalLink className="w-3 h-3 shrink-0" />
                                </a>
                              </td>
                              <td className="py-2.5 px-3 text-right">
                                <button
                                  onClick={() => handleTriggerSync(s.source_id)}
                                  disabled={syncingId === s.source_id}
                                  className="px-2.5 py-1 rounded-lg border border-slate-200 text-slate-700 hover:bg-slate-100 text-[11px] font-bold"
                                >
                                  {syncingId === s.source_id ? "Syncing..." : "Sync Now"}
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <div className="p-4 rounded-xl bg-emerald-50 text-emerald-800 text-xs font-semibold flex items-center space-x-2">
                      <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                      <span>All registered job sources currently have active indexed vacancies!</span>
                    </div>
                  )}
                </div>

                {/* Failed and Partially Crawled Sources */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                  {/* Failed Sources */}
                  <div className="p-5 bg-white rounded-2xl border border-slate-200/90 shadow-xs space-y-3">
                    <div className="flex items-center space-x-2">
                      <XCircle className="w-4 h-4 text-red-500" />
                      <h3 className="text-sm font-bold text-slate-900">Failed / Degraded Sources</h3>
                      <span className="ml-2 px-2 py-0.5 rounded-full text-xs font-bold bg-red-100 text-red-800">
                        {qualityDashboard.failed_sources?.length || 0}
                      </span>
                    </div>
                    <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                      {qualityDashboard.failed_sources?.length > 0 ? (
                        qualityDashboard.failed_sources.map((s, idx) => (
                          <div key={idx} className="p-2.5 rounded-xl border border-red-100 bg-red-50/50 space-y-1 text-xs">
                            <div className="flex justify-between items-center font-bold text-slate-900">
                              <span>{s.company_name} ({s.source_name})</span>
                              <span className="px-1.5 py-0.5 rounded text-[10px] bg-red-200 text-red-800 font-extrabold">
                                {s.health_status}
                              </span>
                            </div>
                            {s.error && (
                              <p className="text-[11px] text-red-700 font-mono line-clamp-2">
                                {s.error}
                              </p>
                            )}
                          </div>
                        ))
                      ) : (
                        <p className="text-xs text-slate-400 font-medium">No failed sources detected.</p>
                      )}
                    </div>
                  </div>

                  {/* Partially Crawled Sources */}
                  <div className="p-5 bg-white rounded-2xl border border-slate-200/90 shadow-xs space-y-3">
                    <div className="flex items-center space-x-2">
                      <Clock className="w-4 h-4 text-blue-500" />
                      <h3 className="text-sm font-bold text-slate-900">Partially Crawled Sources</h3>
                      <span className="ml-2 px-2 py-0.5 rounded-full text-xs font-bold bg-blue-100 text-blue-800">
                        {qualityDashboard.partially_crawled_sources?.length || 0}
                      </span>
                    </div>
                    <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                      {qualityDashboard.partially_crawled_sources?.length > 0 ? (
                        qualityDashboard.partially_crawled_sources.map((s, idx) => (
                          <div key={idx} className="p-2.5 rounded-xl border border-blue-100 bg-blue-50/50 space-y-1 text-xs">
                            <div className="flex justify-between items-center font-bold text-slate-900">
                              <span>{s.company_name}</span>
                              <span className="px-1.5 py-0.5 rounded text-[10px] bg-blue-200 text-blue-800 font-extrabold">
                                Cursor Active
                              </span>
                            </div>
                            <p className="text-[11px] text-slate-600">
                              Source {s.source_name} has pagination cursor saved for continuation.
                            </p>
                          </div>
                        ))
                      ) : (
                        <p className="text-xs text-slate-400 font-medium">All sources fully ingested to date.</p>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </>
          ) : (
            <div className="p-12 text-center bg-white rounded-2xl border border-slate-200 shadow-xs">
              <Loader2 className="w-8 h-8 animate-spin text-blue-600 mx-auto mb-3" />
              <p className="text-xs text-slate-500 font-medium">Computing live global search metrics from PostgreSQL...</p>
            </div>
          )}
        </div>
      )}

      {/* Add Source Modal */}
      {showAddSourceModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-xl max-w-md w-full p-6 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="text-base font-bold text-slate-900">Register New Ingestion Source</h3>
              <button
                onClick={() => setShowAddSourceModal(false)}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleCreateSource} className="space-y-3.5 text-xs">
              <div>
                <label className="block font-bold uppercase tracking-wider text-slate-400 mb-1">
                  Company Name
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. OpenAI"
                  value={newSource.company_name}
                  onChange={(e) =>
                    setNewSource({ ...newSource, company_name: e.target.value })
                  }
                  className="w-full text-sm rounded-xl border border-slate-200 bg-slate-50 p-2.5 focus:bg-white focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block font-bold uppercase tracking-wider text-slate-400 mb-1">
                  Source Identifier
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. OpenAI Greenhouse Feed"
                  value={newSource.source_name}
                  onChange={(e) =>
                    setNewSource({ ...newSource, source_name: e.target.value })
                  }
                  className="w-full text-sm rounded-xl border border-slate-200 bg-slate-50 p-2.5 focus:bg-white focus:border-blue-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-bold uppercase tracking-wider text-slate-400 mb-1">
                    Adapter Type
                  </label>
                  <select
                    value={newSource.source_type}
                    onChange={(e) =>
                      setNewSource({ ...newSource, source_type: e.target.value })
                    }
                    className="w-full rounded-xl border border-slate-200 bg-slate-50 p-2.5 font-medium text-slate-800"
                  >
                    <option value="GREENHOUSE">Greenhouse ATS</option>
                    <option value="LEVER">Lever ATS</option>
                    <option value="ASHBY">Ashby Board</option>
                    <option value="GENERIC_JSON">Generic JSON API</option>
                    <option value="WEB_SCRAPER">Career Web Scraper</option>
                  </select>
                </div>

                <div>
                  <label className="block font-bold uppercase tracking-wider text-slate-400 mb-1">
                    Board / Slug Token
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. openai"
                    value={newSource.external_board_id}
                    onChange={(e) =>
                      setNewSource({ ...newSource, external_board_id: e.target.value })
                    }
                    className="w-full text-sm rounded-xl border border-slate-200 bg-slate-50 p-2.5 focus:bg-white focus:border-blue-500"
                  />
                </div>
              </div>

              <div>
                <label className="block font-bold uppercase tracking-wider text-slate-400 mb-1">
                  Canonical URL
                </label>
                <input
                  type="url"
                  required
                  placeholder="https://boards.greenhouse.io/openai"
                  value={newSource.canonical_source_url}
                  onChange={(e) =>
                    setNewSource({ ...newSource, canonical_source_url: e.target.value })
                  }
                  className="w-full text-sm rounded-xl border border-slate-200 bg-slate-50 p-2.5 focus:bg-white focus:border-blue-500"
                />
              </div>

              <div className="flex items-center justify-end space-x-2 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowAddSourceModal(false)}
                  className="px-4 py-2 rounded-xl border border-slate-200 font-semibold text-slate-600 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold shadow-sm transition-all"
                >
                  Register Source
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Auto-Discover & Probe ATS Modal */}
      {showProbeModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-xl max-w-lg w-full p-6 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center space-x-2">
                <Sparkles className="w-5 h-5 text-indigo-600" />
                <h3 className="text-base font-bold text-slate-900">Auto-Discover & Ingest ATS</h3>
              </div>
              <button
                onClick={() => {
                  setShowProbeModal(false);
                  setProbeResult(null);
                }}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-xs text-slate-500">
              Enter a company board token, slug, or career URL (e.g., <span className="font-mono bg-slate-100 px-1 py-0.5 rounded text-slate-700">stripe</span>, <span className="font-mono bg-slate-100 px-1 py-0.5 rounded text-slate-700">openai</span>, <span className="font-mono bg-slate-100 px-1 py-0.5 rounded text-slate-700">gusto</span>, or <span className="font-mono bg-slate-100 px-1 py-0.5 rounded text-slate-700">https://jobs.ashbyhq.com/figma</span>). The discovery engine probes Greenhouse, Lever, and Ashby endpoints in real time.
            </p>

            <form onSubmit={handleProbeBoard} className="space-y-3">
              <div className="flex items-center space-x-2">
                <input
                  type="text"
                  required
                  placeholder="Company token or ATS URL..."
                  value={probeQuery}
                  onChange={(e) => setProbeQuery(e.target.value)}
                  className="flex-1 text-sm rounded-xl border border-slate-200 bg-slate-50 p-2.5 focus:bg-white focus:border-indigo-500"
                />
                <button
                  type="submit"
                  disabled={probeLoading || !probeQuery.trim()}
                  className="px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold shadow-sm shadow-indigo-500/20 flex items-center space-x-1.5 transition-all disabled:opacity-50 shrink-0"
                >
                  {probeLoading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Search className="w-4 h-4" />
                  )}
                  <span>Probe</span>
                </button>
              </div>
            </form>

            {/* Probe Results Feedback */}
            {probeResult && (
              <div className={`p-4 rounded-xl border text-xs space-y-3 ${
                probeResult.found
                  ? "bg-emerald-50/60 border-emerald-200 text-slate-700"
                  : "bg-amber-50/60 border-amber-200 text-slate-700"
              }`}>
                {probeResult.found ? (
                  <>
                    <div className="flex items-center space-x-2 text-emerald-800 font-bold">
                      <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                      <span>Valid ATS Board Detected!</span>
                    </div>

                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div>
                        <span className="text-slate-400 font-bold uppercase text-[10px]">Adapter:</span>
                        <p className="font-semibold text-slate-900">{probeResult.source_type}</p>
                      </div>
                      <div>
                        <span className="text-slate-400 font-bold uppercase text-[10px]">Board Slug:</span>
                        <p className="font-semibold text-slate-900">{probeResult.board_id}</p>
                      </div>
                      <div className="col-span-2">
                        <span className="text-slate-400 font-bold uppercase text-[10px]">Canonical Feed URL:</span>
                        <p className="font-mono text-[11px] text-blue-600 truncate">{probeResult.canonical_source_url}</p>
                      </div>
                      <div>
                        <span className="text-slate-400 font-bold uppercase text-[10px]">Sample Count:</span>
                        <p className="font-semibold text-slate-900">{probeResult.sample_jobs_count} active listings</p>
                      </div>
                    </div>

                    <div className="pt-2 border-t border-emerald-200/60 space-y-2">
                      <label className="block text-[11px] font-bold text-slate-700 uppercase tracking-wider">
                        Company Name to Register
                      </label>
                      <input
                        type="text"
                        required
                        value={discoverCompanyName}
                        onChange={(e) => setDiscoverCompanyName(e.target.value)}
                        placeholder="e.g. Acme Corp"
                        className="w-full text-xs rounded-xl border border-slate-200 bg-white p-2"
                      />

                      <div className="flex items-center justify-end space-x-2 pt-2">
                        <button
                          type="button"
                          onClick={() => {
                            setShowProbeModal(false);
                            setProbeResult(null);
                          }}
                          className="px-3.5 py-1.5 rounded-xl border border-slate-200 bg-white text-xs font-semibold text-slate-600 hover:bg-slate-50"
                        >
                          Dismiss
                        </button>
                        <button
                          type="button"
                          onClick={handleAutoDiscoverAndRegister}
                          disabled={discovering || !discoverCompanyName.trim()}
                          className="px-4 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold shadow-sm shadow-emerald-500/20 flex items-center space-x-1.5 disabled:opacity-50 transition-all"
                        >
                          {discovering ? (
                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          ) : (
                            <Sparkles className="w-3.5 h-3.5" />
                          )}
                          <span>Register & Ingest Now</span>
                        </button>
                      </div>
                    </div>
                  </>
                ) : (
                  <div className="space-y-2">
                    <div className="flex items-center space-x-2 text-amber-800 font-bold">
                      <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
                      <span>No active ATS board detected for this slug</span>
                    </div>
                    <p className="text-slate-600 text-[11px]">
                      {probeResult.details || "The queried endpoint returned 404 or an empty job list across Greenhouse, Lever, and Ashby."}
                    </p>
                    <div className="flex justify-end pt-1">
                      <button
                        type="button"
                        onClick={() => {
                          setShowProbeModal(false);
                          setProbeResult(null);
                        }}
                        className="px-3 py-1 rounded-xl border border-slate-200 bg-white text-xs font-semibold text-slate-600 hover:bg-slate-50"
                      >
                        Dismiss
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
