import React from "react";

const VARIANTS = {
  blue: "bg-blue-50 text-blue-700 border-blue-200/80",
  slate: "bg-slate-50 text-slate-700 border-slate-200",
  emerald: "bg-emerald-50 text-emerald-700 border-emerald-200/80",
  amber: "bg-amber-50 text-amber-800 border-amber-200/80",
  red: "bg-red-50 text-red-700 border-red-200/80",
  purple: "bg-purple-50 text-purple-700 border-purple-200/80",
  indigo: "bg-indigo-50 text-indigo-700 border-indigo-200/80",
  outline: "bg-transparent text-slate-600 border-slate-300",
};

const SIZES = {
  sm: "px-2 py-0.5 text-[10px] rounded-md gap-1",
  md: "px-2.5 py-1 text-xs rounded-lg gap-1.5",
};

export default function Badge({
  children,
  variant = "blue",
  size = "sm",
  icon: Icon,
  className = "",
  ...props
}) {
  const variantClass = VARIANTS[variant] || VARIANTS.blue;
  const sizeClass = SIZES[size] || SIZES.sm;

  return (
    <span
      className={`inline-flex items-center font-bold tracking-tight border shadow-2xs uppercase ${variantClass} ${sizeClass} ${className}`}
      {...props}
    >
      {Icon && <Icon className="w-3 h-3 shrink-0" />}
      <span>{children}</span>
    </span>
  );
}
