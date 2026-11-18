"use client";

import { useEffect } from "react";
import { motion, AnimatePresence } from "motion/react";
import { backdropVariants, dialogVariants } from "./variants";

/**
 * AnimatedDialog renders an accessible modal dialog with subtle fade/scale transitions.
 */
export default function AnimatedDialog({
  isOpen,
  onClose,
  children,
  className = "relative w-full max-w-lg bg-white rounded-2xl shadow-2xl p-6 z-10 border border-slate-200",
}) {
  useEffect(() => {
    function handleKeyDown(e) {
      if (e.key === "Escape" && isOpen && onClose) {
        onClose();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 overflow-y-auto flex items-center justify-center p-4">
          {/* Backdrop */}
          <motion.div
            variants={backdropVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs"
            onClick={onClose}
            aria-hidden="true"
          />

          {/* Dialog Container */}
          <motion.div
            variants={dialogVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            role="dialog"
            aria-modal="true"
            className={className}
          >
            {children}
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
