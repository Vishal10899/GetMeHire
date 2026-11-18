"use client";

import { MotionConfig } from "motion/react";

/**
 * MotionProvider integrates Motion at the application root level.
 * Configures `reducedMotion="user"` to strictly respect operating system and
 * browser `prefers-reduced-motion` settings across all child animations.
 */
export default function MotionProvider({ children }) {
  return (
    <MotionConfig reducedMotion="user">
      {children}
    </MotionConfig>
  );
}
