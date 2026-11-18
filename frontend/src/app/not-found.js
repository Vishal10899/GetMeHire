"use client";

import Link from "next/link";
import { Compass, Search, Home, ArrowLeft, Briefcase, ArrowRight } from "lucide-react";
import { motion } from "motion/react";

export default function NotFound() {
  const quickCategories = [
    { label: "Software & Engineering", href: "/jobs?profession=ENGINEERING" },
    { label: "Data Science & AI", href: "/jobs?profession=DATA_AI" },
    { label: "Product & Design", href: "/jobs?profession=PRODUCT_DESIGN" },
    { label: "Sales & Business Dev", href: "/jobs?profession=SALES_BIZDEV" },
    { label: "Operations & Logistics", href: "/jobs?profession=OPERATIONS_LOGISTICS" },
    { label: "Customer Support", href: "/jobs?profession=CUSTOMER_SUPPORT" },
  ];

  return (
    <div className="min-h-[70vh] flex items-center justify-center px-4 sm:px-6 lg:px-8 py-16">
      <div className="max-w-xl w-full text-center space-y-8">
        {/* Animated Brand / Compass Icon */}
        <div className="flex justify-center">
          <motion.div
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.3 }}
            className="w-16 h-16 rounded-2xl bg-blue-50 border border-blue-200/80 flex items-center justify-center text-blue-600 shadow-sm shadow-blue-500/10"
          >
            <Compass className="w-8 h-8 animate-pulse-subtle" />
          </motion.div>
        </div>

        {/* Status code and messaging */}
        <div className="space-y-2">
          <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-bold bg-slate-100 text-slate-700">
            Error 404 — Page Not Found
          </span>
          <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-900 tracking-tight">
            We couldn&apos;t find that page
          </h1>
          <p className="text-sm text-slate-500 max-w-md mx-auto leading-relaxed">
            The career listing, profile, or link you are looking for may have been archived, removed, or relocated to a new address.
          </p>
        </div>

        {/* Primary Action Buttons */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
          <Link
            href="/jobs"
            className="w-full sm:w-auto inline-flex items-center justify-center space-x-2 px-6 py-3 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs sm:text-sm shadow-sm shadow-blue-500/20 transition-all hover:scale-[1.02] active:scale-[0.98]"
          >
            <Search className="w-4 h-4" />
            <span>Find Verified Jobs</span>
          </Link>

          <Link
            href="/"
            className="w-full sm:w-auto inline-flex items-center justify-center space-x-2 px-6 py-3 rounded-xl bg-white border border-slate-200 hover:bg-slate-50 hover:border-slate-300 text-slate-700 font-bold text-xs sm:text-sm transition-all"
          >
            <Home className="w-4 h-4 text-slate-400" />
            <span>Return to Homepage</span>
          </Link>
        </div>

        {/* Quick Category Jump */}
        <div className="pt-6 border-t border-slate-200/80 space-y-3">
          <p className="text-xs font-bold uppercase tracking-wider text-slate-400">
            Explore Active Career Tracks
          </p>
          <div className="flex flex-wrap justify-center gap-2">
            {quickCategories.map((cat) => (
              <Link
                key={cat.href}
                href={cat.href}
                className="px-3 py-1.5 rounded-lg bg-slate-50 hover:bg-blue-50 hover:text-blue-700 border border-slate-200/80 text-xs font-medium text-slate-600 transition-colors"
              >
                {cat.label}
              </Link>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
