"use client";

import { motion } from "motion/react";

/**
 * FadeIn renders an animated container that smoothly fades and slides in.
 * Direction options: "up", "down", "left", "right", "none".
 */
export default function FadeIn({
  children,
  direction = "up",
  delay = 0,
  duration = 0.25,
  className = "",
  ...props
}) {
  const getOffset = () => {
    switch (direction) {
      case "up":
        return { y: 12 };
      case "down":
        return { y: -12 };
      case "left":
        return { x: 12 };
      case "right":
        return { x: -12 };
      case "none":
      default:
        return {};
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, ...getOffset() }}
      animate={{ opacity: 1, x: 0, y: 0 }}
      transition={{
        duration,
        delay,
        ease: [0.16, 1, 0.3, 1],
      }}
      className={className}
      {...props}
    >
      {children}
    </motion.div>
  );
}
