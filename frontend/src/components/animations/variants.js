/**
 * Motion animation presets and variants for GetMeHire.
 * Follows UI/UX Pro Max guidelines: subtle, high-performance, and non-distracting.
 */

export const transitions = {
  micro: { duration: 0.15, ease: "easeOut" },
  default: { duration: 0.22, ease: [0.16, 1, 0.3, 1] },
  gentle: { duration: 0.32, ease: [0.16, 1, 0.3, 1] },
  spring: { type: "spring", stiffness: 350, damping: 28 },
};

/**
 * Dropdown menu enter/exit animation (e.g. Navbar user account menu).
 */
export const dropdownVariants = {
  hidden: { opacity: 0, scale: 0.95, y: -6 },
  visible: {
    opacity: 1,
    scale: 1,
    y: 0,
    transition: { duration: 0.16, ease: [0.16, 1, 0.3, 1] },
  },
  exit: {
    opacity: 0,
    scale: 0.95,
    y: -6,
    transition: { duration: 0.1, ease: "easeIn" },
  },
};

/**
 * Mobile drawer collapsible menu animation (accordion style).
 */
export const mobileMenuVariants = {
  hidden: { opacity: 0, height: 0, overflow: "hidden" },
  visible: {
    opacity: 1,
    height: "auto",
    transition: { duration: 0.22, ease: [0.16, 1, 0.3, 1] },
  },
  exit: {
    opacity: 0,
    height: 0,
    transition: { duration: 0.18, ease: "easeIn" },
  },
};

/**
 * Slide-over drawer variants (e.g. Find Jobs mobile filter sheet).
 */
export const slideOverDrawerVariants = {
  hidden: { x: "100%", opacity: 0.9 },
  visible: {
    x: 0,
    opacity: 1,
    transition: { type: "spring", damping: 32, stiffness: 340 },
  },
  exit: {
    x: "100%",
    opacity: 0.9,
    transition: { duration: 0.2, ease: [0.4, 0, 1, 1] },
  },
};

/**
 * Modal / dialog scale and fade variants.
 */
export const dialogVariants = {
  hidden: { opacity: 0, scale: 0.95, y: 8 },
  visible: {
    opacity: 1,
    scale: 1,
    y: 0,
    transition: { duration: 0.2, ease: [0.16, 1, 0.3, 1] },
  },
  exit: {
    opacity: 0,
    scale: 0.95,
    y: 8,
    transition: { duration: 0.15, ease: "easeIn" },
  },
};

/**
 * Backdrop overlay fade variants.
 */
export const backdropVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { duration: 0.2 },
  },
  exit: {
    opacity: 0,
    transition: { duration: 0.15 },
  },
};

/**
 * Fade-in up variant for page sections / cards.
 */
export const fadeInUpVariants = {
  hidden: { opacity: 0, y: 10 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.25, ease: [0.16, 1, 0.3, 1] },
  },
  exit: {
    opacity: 0,
    y: 10,
    transition: { duration: 0.15 },
  },
};

/**
 * Stagger container for list items (e.g. Job cards).
 */
export const staggerListVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.04,
      delayChildren: 0.02,
    },
  },
};

/**
 * Individual card item in a staggered list.
 */
export const staggerItemVariants = {
  hidden: { opacity: 0, y: 8 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.22, ease: "easeOut" },
  },
};

/**
 * Accordion content expand/collapse animation (e.g. explainable match scoring breakdown).
 */
export const accordionVariants = {
  hidden: { opacity: 0, height: 0, overflow: "hidden" },
  visible: {
    opacity: 1,
    height: "auto",
    transition: { duration: 0.22, ease: [0.16, 1, 0.3, 1] },
  },
  exit: {
    opacity: 0,
    height: 0,
    transition: { duration: 0.16, ease: "easeIn" },
  },
};

/**
 * Tab content transition animation for single-page settings/profiles.
 */
export const tabContentVariants = {
  hidden: { opacity: 0, y: 6 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.2, ease: [0.16, 1, 0.3, 1] },
  },
  exit: {
    opacity: 0,
    y: -4,
    transition: { duration: 0.12, ease: "easeIn" },
  },
};
