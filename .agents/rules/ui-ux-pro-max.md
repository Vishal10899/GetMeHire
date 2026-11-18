---
description: Persistent instructions to use UI/UX Pro Max and motion/react for all frontend and design tasks in GlobalJobs
globs: frontend/**
alwaysApply: true
---

# UI/UX Pro Max & Frontend Design Directives

1. **Design System & Guidance:**
   - Always apply UI/UX Pro Max rules (`.agents/skills/ui-ux-pro-max/`) and the project design system in `design-system/globaljobs/MASTER.md`.
   - Run `python .agents/skills/ui-ux-pro-max/scripts/search.py "<query>" --domain <domain>` when needing UX, accessibility, or component guidance.

2. **Motion & Interaction Patterns:**
   - Use `motion/react` from the installed `motion` package.
   - Do NOT install `framer-motion` or other animation packages.
   - Reusable motion variants and animated wrappers reside in `frontend/src/components/animations/`.
   - Keep transitions subtle (150ms–250ms), purposeful, and ensure `reducedMotion="user"` is preserved via `MotionProvider`.
   - Never use hover-only actions or non-interactive faux buttons.

3. **Core Stack & Architecture:**
   - Next.js 14 App Router, React 18, Tailwind CSS, JavaScript only (No TypeScript).
   - Maintain established API paths, authentication tokens, and direct ATS application workflows.
