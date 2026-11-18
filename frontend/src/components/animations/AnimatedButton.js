"use client";

import { motion } from "motion/react";

/**
 * AnimatedButton provides subtle micro-interactions on hover and tap.
 * Automatically disables transforms when the button is disabled or when
 * reduced motion is active.
 */
export default function AnimatedButton({
  children,
  className = "",
  disabled = false,
  type = "button",
  onClick,
  ...props
}) {
  return (
    <motion.button
      type={type}
      disabled={disabled}
      onClick={onClick}
      whileHover={disabled ? undefined : { scale: 1.015 }}
      whileTap={disabled ? undefined : { scale: 0.98 }}
      transition={{ duration: 0.12, ease: "easeOut" }}
      className={className}
      {...props}
    >
      {children}
    </motion.button>
  );
}
