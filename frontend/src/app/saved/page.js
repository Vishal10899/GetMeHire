"use client";

import { useState, useEffect, useMemo } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  Bookmark,
  Search,
  Trash2,
  ArrowRight,
  Loader2,
  Sparkles,
  Building2,
  Briefcase,
} from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/authContext";
import JobCard from "@/components/JobCard";
import { motion } from "motion/react";
import { staggerListVariants, staggerItemVariants } from "@/components/animations/variants";
import { Button, Input, Card, Badge, EmptyState } from "@/components/ui";

export default function SavedJobsPage() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();

  const [savedItems, setSavedItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    if (!authLoading && !user) {
      router.push("/login?redirect=/saved");
      return;
    }
    if (user) {
      fetchSavedJobs();
    }
  }, [user, authLoading]);

  const fetchSavedJobs = async () => {
    setLoading(true);
    try {
      const res = await api.getSavedJobs();
      setSavedItems(res.items || []);
    } catch (err) {
      console.error("Saved jobs fetch error:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleJobUnsaved = (jobId) => {
    setSavedItems((prev) => prev.filter((item) => item.job_id !== jobId));
  };

  const filteredItems = useMemo(() => {
    if (!searchQuery.trim()) return savedItems;
    const q = searchQuery.toLowerCase();
    return savedItems.filter((item) => {
      const title = (item.job?.title || "").toLowerCase();
      const comp = (item.job?.company_name || "").toLowerCase();
      const loc = (item.job?.location || "").toLowerCase();
      return title.includes(q) || comp.includes(q) || loc.includes(q);
    });
  }, [savedItems, searchQuery]);

  if (loading || authLoading) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-20 flex flex-col items-center justify-center">
        <Loader2 className="w-8 h-8 text-blue-600 animate-spin mb-3" />
        <p className="text-sm font-semibold text-slate-500">Loading saved positions...</p>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200/90">
        <div className="space-y-1">
          <div className="flex items-center space-x-2.5">
            <div className="w-9 h-9 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center shrink-0 border border-amber-200">
              <Bookmark className="w-5 h-5 fill-current" />
            </div>
            <div>
              <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
                Saved Positions
              </h1>
            </div>
          </div>
          <p className="text-xs text-slate-500">
            {savedItems.length} verified role{savedItems.length === 1 ? "" : "s"} bookmarked for your application pipeline.
          </p>
        </div>

        <Link href="/jobs">
          <Button variant="primary" size="md" iconRight={ArrowRight}>
            Discover More Jobs
          </Button>
        </Link>
      </div>

      {/* Filter / Search Bar if items exist */}
      {savedItems.length > 0 && (
        <div className="flex items-center justify-between gap-3 bg-white p-3 rounded-2xl border border-slate-200/90 shadow-2xs">
          <div className="relative flex-1 max-w-sm">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Filter saved jobs by title or company..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 text-xs rounded-xl border border-slate-200 bg-slate-50 focus:bg-white focus:outline-none focus:border-blue-600"
            />
          </div>

          <span className="text-xs text-slate-500 font-medium">
            Showing {filteredItems.length} of {savedItems.length}
          </span>
        </div>
      )}

      {/* Main List */}
      {savedItems.length === 0 ? (
        <EmptyState
          icon={Bookmark}
          title="No saved positions yet"
          description="Browse genuine employer opportunities and click the bookmark icon on any job card to save it for later review."
          actionLabel="Find Verified Opportunities"
          actionHref="/jobs"
          actionIcon={Search}
        />
      ) : filteredItems.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-2xl border border-slate-200 p-6 space-y-3">
          <p className="text-sm font-semibold text-slate-700">No saved positions match &quot;{searchQuery}&quot;</p>
          <Button variant="secondary" size="sm" onClick={() => setSearchQuery("")}>
            Clear Filter
          </Button>
        </div>
      ) : (
        <motion.div
          variants={staggerListVariants}
          initial="hidden"
          animate="visible"
          className="space-y-4"
        >
          {filteredItems.map((item) => (
            <motion.div key={item.id} variants={staggerItemVariants} className="space-y-2">
              <JobCard
                job={item.job}
                onSaveToggle={() => handleJobUnsaved(item.job_id)}
              />
              {item.notes && (
                <div className="ml-4 px-3 py-1.5 bg-amber-50 rounded-xl border border-amber-200 text-xs text-amber-900 font-medium inline-block">
                  Note: {item.notes}
                </div>
              )}
            </motion.div>
          ))}
        </motion.div>
      )}
    </div>
  );
}
