# GlobalJobs — Agent Instructions & Design System Reference

## 1. UI/UX Pro Max Skill & Design System Integration

For all frontend design, page development, component styling, layout fixes, and animation tasks in this project:

- **Primary UI/UX Intelligence:** Always consult and utilize the **UI/UX Pro Max** skill located in `.agents/skills/ui-ux-pro-max/`.
  - CLI Script: `python .agents/skills/ui-ux-pro-max/scripts/search.py "<query>" --domain <domain>`
- **Design System Source of Truth:** Consult `design-system/globaljobs/MASTER.md` for verified design tokens, color scales, typography, and UX patterns.
  - Page-specific overrides are stored in `design-system/globaljobs/pages/[page-name].md`.

## 2. Animation & Motion Architecture

- **Library:** Use `motion/react` provided by the installed `motion` package (`^14.6.0`).
- **No Duplicate Libraries:** Do **not** install `framer-motion` or secondary animation libraries.
- **Root Provider:** All animations must remain under `<MotionProvider>` (`MotionConfig` with `reducedMotion="user"`).
- **Reduced Motion:** Always respect `prefers-reduced-motion`. Never enforce motion if reduced motion is requested by the user.
- **Performance & Restraint:** Animations must be subtle, performant micro-interactions (durations 150ms–250ms with ease-out curves), non-distracting, and never cause layout shift or block user actions.
- **Reusable Patterns:** Reference and extend `src/components/animations/`:
  - `variants.js`: Centralized motion variants (`dropdownVariants`, `mobileMenuVariants`, `dialogVariants`, `fadeInUpVariants`, `staggerListVariants`).
  - `AnimatedButton.js`: Tactile interactive buttons.
  - `AnimatedDialog.js`: Accessible modal dialogs with backdrop blur and escape key handling.
  - `FadeIn.js`: Smooth scroll and entrance transitions.

## 3. Strict Architecture & Technology Constraints

- **Frontend:** Next.js 14 (App Router), React 18, Tailwind CSS, JavaScript only (`.js`, `.jsx`). **NO TypeScript**.
- **Backend:** FastAPI (Python), PostgreSQL, SQLAlchemy, Alembic.
- **Preserved Core Workflows:**
  - Direct-to-employer career discovery with original ATS application links and provenance tracking.
  - Unified single-page candidate profile editor at `/profile` (basic details, encrypted resume storage, skills, preferences, salary, application history).
  - Explainable career recommendations algorithm.
  - Ingestion telemetry and source management at `/admin`.
