"use client";

import { useState } from "react";
import { Building2 } from "lucide-react";

/**
 * Clean initials generator from company name.
 * e.g. "Scale AI" -> "SA", "Stripe" -> "ST", "Palantir Technologies" -> "PT"
 */
export function getCompanyInitials(name) {
  if (!name || typeof name !== "string") return "CO";
  const clean = name.trim().replace(/[^\w\s]/g, "");
  const words = clean.split(/\s+/).filter(Boolean);
  if (words.length >= 2) {
    return (words[0][0] + words[1][0]).toUpperCase();
  }
  if (clean.length >= 2) {
    return clean.substring(0, 2).toUpperCase();
  }
  return clean.toUpperCase() || "CO";
}

/**
 * Filter out known stock photos / placeholder assets that damage credibility.
 * E.g., seeded Unsplash portrait photos of people in suits or stock office charts.
 */
function isTrustworthyLogoUrl(url) {
  if (!url || typeof url !== "string") return false;
  const lower = url.toLowerCase();
  // Filter out stock photos
  if (lower.includes("images.unsplash.com")) return false;
  if (lower.includes("placeholder") || lower.includes("stock-photo")) return false;
  // Must be an absolute http/https or valid local path
  if (!lower.startsWith("http://") && !lower.startsWith("https://") && !lower.startsWith("/")) {
    return false;
  }
  return true;
}

export default function CompanyAvatar({
  name,
  logoUrl,
  size = "md",
  className = "",
}) {
  const [hasError, setHasError] = useState(false);
  const initials = getCompanyInitials(name);
  const canDisplayLogo = !hasError && isTrustworthyLogoUrl(logoUrl);

  const sizeClasses = {
    sm: "w-9 h-9 text-xs rounded-lg",
    md: "w-11 h-11 text-xs sm:text-sm rounded-xl",
    lg: "w-14 h-14 sm:w-16 sm:h-16 text-base sm:text-lg rounded-2xl",
  }[size] || "w-11 h-11 text-xs rounded-xl";

  const iconSizes = {
    sm: "w-4 h-4",
    md: "w-5 h-5",
    lg: "w-7 h-7",
  }[size] || "w-5 h-5";

  return (
    <div
      className={`relative shrink-0 flex items-center justify-center overflow-hidden border border-slate-200/90 bg-slate-100 text-slate-700 font-bold select-none transition-colors ${sizeClasses} ${className}`}
      title={name || "Employer"}
      aria-label={name ? `${name} logo` : "Company avatar"}
    >
      {canDisplayLogo ? (
        <img
          src={logoUrl}
          alt={name ? `${name} logo` : "Company logo"}
          onError={() => setHasError(true)}
          className="w-full h-full object-contain p-1 bg-white"
          loading="lazy"
        />
      ) : initials ? (
        <span className="font-extrabold tracking-tight text-slate-700">
          {initials}
        </span>
      ) : (
        <Building2 className={`${iconSizes} text-slate-400`} />
      )}
    </div>
  );
}
