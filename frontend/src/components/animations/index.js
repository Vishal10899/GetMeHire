"use client";

export { default as MotionProvider } from "./MotionProvider";
export { default as AnimatedButton } from "./AnimatedButton";
export { default as FadeIn } from "./FadeIn";
export { default as AnimatedDialog } from "./AnimatedDialog";

export {
  transitions,
  dropdownVariants,
  mobileMenuVariants,
  slideOverDrawerVariants,
  dialogVariants,
  backdropVariants,
  fadeInUpVariants,
  staggerListVariants,
  staggerItemVariants,
  accordionVariants,
  tabContentVariants,
} from "./variants";

// Convenient re-exports directly from modern motion/react
export { motion, AnimatePresence, useReducedMotion } from "motion/react";
