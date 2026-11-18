import React from "react";
import Button from "./Button";

export default function EmptyState({
  icon: Icon,
  title,
  description,
  actionLabel,
  onAction,
  actionHref,
  actionIcon,
  secondaryActionLabel,
  onSecondaryAction,
  className = "",
}) {
  return (
    <div
      className={`text-center py-12 sm:py-16 px-4 bg-white rounded-2xl border border-slate-200/90 shadow-2xs space-y-4 max-w-xl mx-auto ${className}`}
    >
      {Icon && (
        <div className="w-12 h-12 rounded-2xl bg-slate-100 text-slate-500 flex items-center justify-center mx-auto shadow-2xs">
          <Icon className="w-6 h-6" />
        </div>
      )}
      <div className="space-y-1">
        <h3 className="text-base sm:text-lg font-bold text-slate-900 tracking-tight">
          {title}
        </h3>
        {description && (
          <p className="text-xs sm:text-sm text-slate-500 max-w-md mx-auto leading-relaxed">
            {description}
          </p>
        )}
      </div>

      {(actionLabel || secondaryActionLabel) && (
        <div className="pt-2 flex flex-wrap items-center justify-center gap-2.5">
          {actionLabel && (
            actionHref ? (
              <a href={actionHref}>
                <Button variant="primary" size="sm" icon={actionIcon}>
                  {actionLabel}
                </Button>
              </a>
            ) : (
              <Button variant="primary" size="sm" onClick={onAction} icon={actionIcon}>
                {actionLabel}
              </Button>
            )
          )}
          {secondaryActionLabel && (
            <Button variant="secondary" size="sm" onClick={onSecondaryAction}>
              {secondaryActionLabel}
            </Button>
          )}
        </div>
      )}
    </div>
  );
}
