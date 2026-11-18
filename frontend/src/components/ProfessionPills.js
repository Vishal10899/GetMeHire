"use client";

import { useState, useEffect } from "react";
import {
  Layers,
  Headphones,
  Code2,
  HeartPulse,
  TrendingUp,
  Megaphone,
  Landmark,
  Brain,
  Users,
  Truck,
  GraduationCap,
  Hammer,
  Store,
  Scale,
  Palette,
  Briefcase,
} from "lucide-react";
import { api } from "@/lib/api";

const PROFESSION_ICONS = {
  ALL: Layers,
  CUSTOMER_SUPPORT: Headphones,
  ENGINEERING: Code2,
  SOFTWARE_IT: Code2,
  HEALTHCARE_MEDICAL: HeartPulse,
  SALES_BIZDEV: TrendingUp,
  MARKETING_GROWTH: Megaphone,
  FINANCE_ACCOUNTING: Landmark,
  DATA_AI: Brain,
  HR_RECRUITMENT: Users,
  OPERATIONS_LOGISTICS: Truck,
  EDUCATION_TRAINING: GraduationCap,
  MANUFACTURING_TRADES: Hammer,
  HOSPITALITY_RETAIL: Store,
  LEGAL_ADMIN: Scale,
  PRODUCT_DESIGN: Palette,
};

export default function ProfessionPills({ selectedProfession, onSelectProfession }) {
  const [professions, setProfessions] = useState([]);
  const [totalJobs, setTotalJobs] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadProfessions();
  }, []);

  const loadProfessions = async () => {
    try {
      const data = await api.getProfessions();
      // Filter out duplicate legacy alias from visual pills if both present
      const uniqueProfs = (data.professions || []).filter(
        (p) => p.key !== "SOFTWARE_IT" || !data.professions.some((x) => x.key === "ENGINEERING")
      );
      setProfessions(uniqueProfs);
      setTotalJobs(data.total_jobs || 0);
    } catch (err) {
      console.error("Failed to load professions:", err);
    } finally {
      setLoading(false);
    }
  };

  const isAllSelected = !selectedProfession || selectedProfession === "";

  return (
    <div className="w-full">
      <div className="flex items-center space-x-2 overflow-x-auto pb-2 scrollbar-none no-scrollbar">
        {/* All Professions Pill */}
        <button
          onClick={() => onSelectProfession("")}
          className={`flex items-center space-x-2 px-3.5 py-2 rounded-xl text-xs font-bold whitespace-nowrap transition-all shrink-0 ${
            isAllSelected
              ? "bg-slate-900 text-white shadow-sm ring-1 ring-slate-900"
              : "bg-white text-slate-600 hover:text-slate-900 hover:bg-slate-50 border border-slate-200"
          }`}
        >
          <Layers className={`w-3.5 h-3.5 ${isAllSelected ? "text-white" : "text-slate-400"}`} />
          <span>All Professions</span>
          <span
            className={`px-1.5 py-0.2 rounded-full text-[10px] ${
              isAllSelected ? "bg-slate-800 text-slate-200" : "bg-slate-100 text-slate-500"
            }`}
          >
            {totalJobs > 0 ? totalJobs.toLocaleString() : "..."}
          </span>
        </button>

        {/* Dynamic Profession Pills */}
        {professions.map((prof) => {
          const isSelected = selectedProfession === prof.key;
          const Icon = PROFESSION_ICONS[prof.key] || Briefcase;

          return (
            <button
              key={prof.key}
              onClick={() => onSelectProfession(isSelected ? "" : prof.key)}
              className={`flex items-center space-x-2 px-3.5 py-2 rounded-xl text-xs font-bold whitespace-nowrap transition-all shrink-0 ${
                isSelected
                  ? "bg-blue-600 text-white shadow-sm shadow-blue-500/20 ring-1 ring-blue-600"
                  : "bg-white text-slate-600 hover:text-slate-900 hover:bg-slate-50 border border-slate-200"
              }`}
            >
              <Icon className={`w-3.5 h-3.5 ${isSelected ? "text-white" : "text-slate-400"}`} />
              <span>{prof.label}</span>
              <span
                className={`px-1.5 py-0.2 rounded-full text-[10px] ${
                  isSelected ? "bg-blue-700 text-blue-100" : "bg-slate-100 text-slate-500"
                }`}
              >
                {prof.count.toLocaleString()}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
