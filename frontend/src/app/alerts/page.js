"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  Bell,
  Plus,
  Trash2,
  Play,
  CheckCircle2,
  Clock,
  Sparkles,
  Loader2,
  Mail,
  X,
  AlertTriangle,
  AlertCircle,
  Globe,
  DollarSign,
} from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/authContext";
import AnimatedDialog from "@/components/animations/AnimatedDialog";
import { Button, Input, Card, Badge, EmptyState } from "@/components/ui";

export default function AlertsPage() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();

  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [evaluatingId, setEvaluatingId] = useState(null);
  const [evalResult, setEvalResult] = useState(null);
  const [deleteAlertId, setDeleteAlertId] = useState(null);
  const [deletingAlert, setDeletingAlert] = useState(false);
  const [modalError, setModalError] = useState(null);
  const [actionNotice, setActionNotice] = useState(null);

  // New alert form state
  const [newAlert, setNewAlert] = useState({
    title: "",
    keywords: "",
    country: "",
    city: "",
    remote_only: false,
    min_salary: "",
    frequency: "DAILY",
  });

  useEffect(() => {
    if (!authLoading && !user) {
      router.push("/login?redirect=/alerts");
      return;
    }
    if (user) {
      fetchAlerts();
    }
  }, [user, authLoading]);

  const fetchAlerts = async () => {
    setLoading(true);
    try {
      const data = await api.getAlerts();
      setAlerts(data || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateAlert = async (e) => {
    e.preventDefault();
    if (!newAlert.title.trim()) return;
    setModalError(null);

    try {
      await api.createAlert({
        title: newAlert.title.trim(),
        frequency: newAlert.frequency,
        criteria: {
          keywords: newAlert.keywords || null,
          country: newAlert.country || null,
          city: newAlert.city || null,
          remote_only: newAlert.remote_only,
          min_salary: newAlert.min_salary ? parseFloat(newAlert.min_salary) : null,
          skills: [],
        },
      });
      setShowModal(false);
      setNewAlert({
        title: "",
        keywords: "",
        country: "",
        city: "",
        remote_only: false,
        min_salary: "",
        frequency: "DAILY",
      });
      setActionNotice({ type: "success", message: "Job alert subscription created successfully." });
      fetchAlerts();
    } catch (err) {
      setModalError(err.message || "Failed to create alert");
    }
  };

  const confirmDeleteAlert = async () => {
    if (!deleteAlertId) return;
    setDeletingAlert(true);
    try {
      await api.deleteAlert(deleteAlertId);
      setDeleteAlertId(null);
      setActionNotice({ type: "success", message: "Job alert subscription removed." });
      fetchAlerts();
    } catch (err) {
      setActionNotice({ type: "error", message: err.message || "Failed to delete alert" });
    } finally {
      setDeletingAlert(false);
    }
  };

  const handleEvaluate = async (alertId) => {
    setEvaluatingId(alertId);
    setEvalResult(null);
    try {
      const res = await api.evaluateAlert(alertId);
      setEvalResult({ alertId, message: res.message, delivered: res.delivered });
      fetchAlerts();
    } catch (err) {
      setActionNotice({ type: "error", message: err.message || "Failed to evaluate alert criteria" });
    } finally {
      setEvaluatingId(null);
    }
  };

  if (loading || authLoading) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-20 flex flex-col items-center justify-center">
        <Loader2 className="w-8 h-8 text-blue-600 animate-spin mb-3" />
        <p className="text-sm font-semibold text-slate-500">Loading your job alerts...</p>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200/90">
        <div className="space-y-1">
          <div className="flex items-center space-x-2.5">
            <div className="w-9 h-9 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center shrink-0 border border-blue-200">
              <Bell className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
                Job Alerts &amp; Notifications
              </h1>
            </div>
          </div>
          <p className="text-xs text-slate-500">
            Automated alerts when newly aggregated listings match your criteria.
          </p>
        </div>

        <Button variant="primary" size="md" icon={Plus} onClick={() => setShowModal(true)}>
          Create New Alert
        </Button>
      </div>

      {actionNotice && (
        <div
          className={`p-3.5 rounded-2xl text-xs flex items-center justify-between ${
            actionNotice.type === "error"
              ? "bg-red-50 border border-red-200 text-red-800"
              : "bg-emerald-50 border border-emerald-200 text-emerald-800"
          }`}
        >
          <div className="flex items-center space-x-2">
            {actionNotice.type === "error" ? (
              <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
            ) : (
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            )}
            <span>{actionNotice.message}</span>
          </div>
          <button
            onClick={() => setActionNotice(null)}
            className="text-slate-400 hover:text-slate-600 p-1 cursor-pointer"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Alerts list */}
      {alerts.length === 0 ? (
        <EmptyState
          icon={Mail}
          title="No active alerts configured"
          description="Create custom search alerts to get notified whenever new matching jobs are discovered by our ingestion engine."
          actionLabel="Create Alert"
          actionIcon={Plus}
          onAction={() => setShowModal(true)}
        />
      ) : (
        <div className="space-y-4">
          {alerts.map((alert) => (
            <Card key={alert.id} padding="md" className="space-y-3">
              <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3.5 sm:gap-4">
                <div className="space-y-1.5 flex-1 min-w-0">
                  <h3 className="text-base font-bold text-slate-900">{alert.title}</h3>
                  <div className="flex flex-wrap items-center gap-1.5 pt-1 text-xs text-slate-600">
                    <Badge variant="blue">{alert.frequency}</Badge>
                    {alert.criteria?.keywords && (
                      <span className="px-2.5 py-0.5 rounded-md bg-slate-100 font-medium text-[11px] text-slate-700 border border-slate-200">
                        Keywords: {alert.criteria.keywords}
                      </span>
                    )}
                    {alert.criteria?.remote_only && (
                      <Badge variant="emerald">Remote Only</Badge>
                    )}
                    {alert.criteria?.min_salary && (
                      <span className="px-2.5 py-0.5 rounded-md bg-slate-100 font-medium text-[11px] text-slate-700 border border-slate-200">
                        Min: ${Number(alert.criteria.min_salary).toLocaleString()}
                      </span>
                    )}
                  </div>
                </div>

                <div className="flex items-center space-x-2 pt-2 sm:pt-0 border-t sm:border-t-0 border-slate-100 shrink-0 w-full sm:w-auto">
                  <Button
                    variant="outline"
                    size="sm"
                    icon={evaluatingId === alert.id ? Loader2 : Play}
                    loading={evaluatingId === alert.id}
                    onClick={() => handleEvaluate(alert.id)}
                  >
                    Check Now
                  </Button>

                  <Button
                    variant="ghost"
                    size="sm"
                    icon={Trash2}
                    className="text-slate-400 hover:text-red-600 hover:bg-red-50"
                    onClick={() => setDeleteAlertId(alert.id)}
                  />
                </div>
              </div>

              {evalResult && evalResult.alertId === alert.id && (
                <div className="p-3 bg-emerald-50 rounded-xl border border-emerald-200 text-xs text-emerald-800 font-medium flex items-center space-x-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                  <span>{evalResult.message}</span>
                </div>
              )}

              <div className="flex items-center justify-between pt-2 border-t border-slate-100 text-[11px] text-slate-400">
                <span>
                  Last evaluated:{" "}
                  {alert.last_evaluated_at
                    ? new Date(alert.last_evaluated_at).toLocaleString()
                    : "Scheduled"}
                </span>
                <span>{alert.deliveries_count || 0} notifications logged</span>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* CREATE ALERT MODAL */}
      <AnimatedDialog
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        title="Create Job Alert"
      >
        <form onSubmit={handleCreateAlert} className="space-y-4">
          {modalError && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-xs text-red-800">
              {modalError}
            </div>
          )}

          <Input
            label="Alert Name"
            required
            placeholder="e.g. Remote Backend Python Roles"
            value={newAlert.title}
            onChange={(e) => setNewAlert({ ...newAlert, title: e.target.value })}
          />

          <Input
            label="Keywords / Skills"
            placeholder="e.g. Python, FastAPI, Docker"
            value={newAlert.keywords}
            onChange={(e) => setNewAlert({ ...newAlert, keywords: e.target.value })}
          />

          <div className="grid grid-cols-2 gap-3">
            <Input
              label="Country"
              placeholder="e.g. United States, India"
              value={newAlert.country}
              onChange={(e) => setNewAlert({ ...newAlert, country: e.target.value })}
            />
            <Input
              label="City"
              placeholder="e.g. San Francisco"
              value={newAlert.city}
              onChange={(e) => setNewAlert({ ...newAlert, city: e.target.value })}
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <Input
              label="Min Salary (USD)"
              type="number"
              placeholder="e.g. 100000"
              value={newAlert.min_salary}
              onChange={(e) => setNewAlert({ ...newAlert, min_salary: e.target.value })}
            />

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Frequency
              </label>
              <select
                value={newAlert.frequency}
                onChange={(e) => setNewAlert({ ...newAlert, frequency: e.target.value })}
                className="w-full text-xs rounded-xl border border-slate-200 bg-white py-2.5 px-3 focus:outline-none focus:border-blue-600 font-medium"
              >
                <option value="DAILY">Daily Digest</option>
                <option value="WEEKLY">Weekly Summary</option>
                <option value="INSTANT">Immediate Notice</option>
              </select>
            </div>
          </div>

          <label className="flex items-center space-x-2.5 text-xs text-slate-700 cursor-pointer pt-1">
            <input
              type="checkbox"
              checked={newAlert.remote_only}
              onChange={(e) => setNewAlert({ ...newAlert, remote_only: e.target.checked })}
              className="w-4 h-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500 cursor-pointer"
            />
            <span>Only notify me for remote positions</span>
          </label>

          <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
            <Button variant="outline" size="sm" onClick={() => setShowModal(false)}>
              Cancel
            </Button>
            <Button variant="primary" size="sm" type="submit">
              Save Alert
            </Button>
          </div>
        </form>
      </AnimatedDialog>

      {/* DELETE CONFIRMATION MODAL */}
      <AnimatedDialog
        isOpen={!!deleteAlertId}
        onClose={() => setDeleteAlertId(null)}
        title="Delete Job Alert"
      >
        <div className="space-y-4">
          <p className="text-xs text-slate-600 leading-relaxed">
            Are you sure you want to remove this job alert? You will no longer receive notifications for this criteria.
          </p>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" size="sm" onClick={() => setDeleteAlertId(null)}>
              Cancel
            </Button>
            <Button
              variant="danger"
              size="sm"
              loading={deletingAlert}
              onClick={confirmDeleteAlert}
            >
              Confirm Delete
            </Button>
          </div>
        </div>
      </AnimatedDialog>
    </div>
  );
}
