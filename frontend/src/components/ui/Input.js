"use client";

import React, { forwardRef } from "react";
import { AlertCircle } from "lucide-react";

const Input = forwardRef(function Input(
  {
    label,
    error,
    helper,
    icon: Icon,
    rightElement,
    required = false,
    id,
    className = "",
    inputClassName = "",
    ...props
  },
  ref
) {
  const inputId = id || (label ? label.toLowerCase().replace(/\s+/g, "-") : undefined);

  return (
    <div className={`w-full space-y-1.5 ${className}`}>
      {label && (
        <label
          htmlFor={inputId}
          className="block text-xs font-semibold text-slate-700 tracking-wide"
        >
          {label}
          {required && <span className="text-red-500 ml-1" aria-hidden="true">*</span>}
        </label>
      )}

      <div className="relative rounded-xl shadow-2xs">
        {Icon && (
          <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
            <Icon className="w-4 h-4" />
          </div>
        )}

        <input
          id={inputId}
          ref={ref}
          required={required}
          className={`w-full text-xs sm:text-sm rounded-xl border transition-all duration-150 bg-white text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 disabled:bg-slate-50 disabled:text-slate-500 disabled:cursor-not-allowed ${
            Icon ? "pl-10" : "pl-3.5"
          } ${rightElement ? "pr-10" : "pr-3.5"} py-2.5 ${
            error
              ? "border-red-300 focus:border-red-500 focus:ring-red-500/20"
              : "border-slate-200 hover:border-slate-300 focus:border-blue-600 focus:ring-blue-500/15"
          } ${inputClassName}`}
          {...props}
        />

        {rightElement && (
          <div className="absolute inset-y-0 right-0 pr-3 flex items-center">
            {rightElement}
          </div>
        )}
      </div>

      {error ? (
        <div className="flex items-center space-x-1.5 text-xs text-red-600 pt-0.5">
          <AlertCircle className="w-3.5 h-3.5 shrink-0" />
          <span>{error}</span>
        </div>
      ) : helper ? (
        <p className="text-[11px] text-slate-500">{helper}</p>
      ) : null}
    </div>
  );
});

export default Input;
