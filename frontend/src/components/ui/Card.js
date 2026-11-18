import React from "react";

const PADDINGS = {
  none: "p-0",
  sm: "p-3 sm:p-4",
  md: "p-5 sm:p-6",
  lg: "p-6 sm:p-8",
};

export default function Card({
  children,
  padding = "md",
  hover = false,
  className = "",
  as: Component = "div",
  ...props
}) {
  const paddingClass = PADDINGS[padding] || PADDINGS.md;
  const hoverClass = hover
    ? "transition-all duration-200 hover:border-slate-300 hover:shadow-sm"
    : "";

  return (
    <Component
      className={`bg-white rounded-2xl border border-slate-200/90 shadow-2xs ${paddingClass} ${hoverClass} ${className}`}
      {...props}
    >
      {children}
    </Component>
  );
}
