"use client";

import React from "react";
import { Loader2 } from "lucide-react";
import { motion } from "motion/react";

const VARIANTS = {
  primary:
    "bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white shadow-xs hover:shadow-sm border border-blue-600/20 focus:ring-blue-500/30",
  secondary:
    "bg-slate-100 hover:bg-slate-200 active:bg-slate-300 text-slate-800 border border-slate-200/80 focus:ring-slate-400/20",
  outline:
    "bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 border border-slate-300 shadow-2xs focus:ring-blue-500/20",
  ghost:
    "bg-transparent hover:bg-slate-100 active:bg-slate-200/80 text-slate-600 hover:text-slate-900 focus:ring-slate-400/20",
  danger:
    "bg-red-600 hover:bg-red-700 active:bg-red-800 text-white shadow-xs focus:ring-red-500/30",
  success:
    "bg-emerald-600 hover:bg-emerald-700 active:bg-emerald-800 text-white shadow-xs focus:ring-emerald-500/30",
};

const SIZES = {
  sm: "px-2.5 py-1.5 text-xs rounded-lg min-h-[32px] gap-1.5",
  md: "px-4 py-2 text-xs sm:text-sm rounded-xl min-h-[40px] gap-2 font-semibold",
  lg: "px-5 py-2.5 text-sm sm:text-base rounded-xl min-h-[44px] gap-2 font-semibold",
};

export default function Button({
  children,
  variant = "primary",
  size = "md",
  loading = false,
  disabled = false,
  className = "",
  type = "button",
  onClick,
  icon: Icon,
  iconRight: IconRight,
  ...props
}) {
  const variantClass = VARIANTS[variant] || VARIANTS.primary;
  const sizeClass = SIZES[size] || SIZES.md;
  const isDisabled = disabled || loading;

  return (
    <motion.button
      type={type}
      onClick={isDisabled ? undefined : onClick}
      disabled={isDisabled}
      whileHover={isDisabled ? undefined : { scale: 1.01 }}
      whileTap={isDisabled ? undefined : { scale: 0.98 }}
      transition={{ duration: 0.12, ease: "easeOut" }}
      className={`inline-flex items-center justify-center font-medium transition-all duration-150 focus:outline-none focus:ring-2 select-none cursor-pointer disabled:opacity-55 disabled:cursor-not-allowed ${variantClass} ${sizeClass} ${className}`}
      {...props}
    >
      {loading ? (
        <>
          <Loader2 className="w-4 h-4 animate-spin shrink-0" />
          <span>{children}</span>
        </>
      ) : (
        <>
          {Icon && <Icon className="w-4 h-4 shrink-0" />}
          <span>{children}</span>
          {IconRight && <IconRight className="w-4 h-4 shrink-0" />}
        </>
      )}
    </motion.button>
  );
}
