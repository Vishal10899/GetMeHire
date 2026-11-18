"use client";

import React from "react";
import { motion } from "motion/react";

export default function Tabs({
  tabs = [],
  activeTab,
  onChange,
  className = "",
  variant = "pill", // "pill" | "underline"
}) {
  return (
    <div
      role="tablist"
      className={`flex items-center gap-1.5 p-1 bg-slate-100/90 rounded-2xl border border-slate-200/80 overflow-x-auto no-scrollbar ${className}`}
    >
      {tabs.map((tab) => {
        const isActive = activeTab === tab.id;
        const Icon = tab.icon;

        return (
          <button
            key={tab.id}
            role="tab"
            aria-selected={isActive}
            onClick={() => onChange(tab.id)}
            className={`relative flex items-center space-x-2 px-3.5 py-2 text-xs font-bold rounded-xl transition-all duration-150 whitespace-nowrap cursor-pointer select-none focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 min-h-[36px] ${
              isActive
                ? "text-blue-700 bg-white shadow-2xs"
                : "text-slate-600 hover:text-slate-900 hover:bg-slate-200/60"
            }`}
          >
            {Icon && (
              <Icon
                className={`w-3.5 h-3.5 transition-colors ${
                  isActive ? "text-blue-600" : "text-slate-400"
                }`}
              />
            )}
            <span>{tab.label}</span>
            {tab.count !== undefined && (
              <span
                className={`text-[10px] font-extrabold px-1.5 py-0.2 rounded-full ${
                  isActive
                    ? "bg-blue-100 text-blue-800"
                    : "bg-slate-200 text-slate-600"
                }`}
              >
                {tab.count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
