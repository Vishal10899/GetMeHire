import "./globals.css";
import { AuthProvider } from "@/lib/authContext";
import MotionProvider from "@/components/animations/MotionProvider";
import Navbar from "@/components/Navbar";
import BackToTop from "@/components/BackToTop";
import Link from "next/link";
import {
  Briefcase,
  ShieldCheck,
  CheckCircle2,
  ExternalLink,
  Layers,
  Sparkles,
  Zap,
  Lock,
} from "lucide-react";

const siteUrl =
  process.env.NEXT_PUBLIC_SITE_URL ||
  (process.env.VERCEL_URL ? `https://${process.env.VERCEL_URL}` : "http://localhost:3000");

export const metadata = {
  metadataBase: new URL(siteUrl),
  title: {
    default: "GetMeHire — Direct-to-Employer Career Discovery Platform",
    template: "%s | GetMeHire",
  },
  description:
    "Discover verified career opportunities aggregated directly from official Greenhouse, Lever, Ashby, and Workday enterprise career boards.",
  keywords: ["jobs", "careers", "tech jobs", "remote work", "Greenhouse", "Lever", "Ashby", "direct apply"],
  authors: [{ name: "Vishal Chaudhary" }],
  creator: "Vishal Chaudhary",
  openGraph: {
    title: "GetMeHire — Direct-to-Employer Career Discovery Platform",
    description:
      "Discover verified career opportunities aggregated directly from official Greenhouse, Lever, Ashby, and Workday enterprise career boards.",
    siteName: "GetMeHire",
    type: "website",
  },
  icons: {
    icon: "/favicon.ico",
  },
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" className="scroll-smooth">
      <body className="min-h-screen bg-slate-50 text-slate-900 antialiased font-sans flex flex-col selection:bg-blue-100 selection:text-blue-900">
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-[100] focus:px-4 focus:py-2.5 focus:bg-blue-600 focus:text-white focus:rounded-xl focus:shadow-lg focus:font-bold focus:text-xs focus:ring-2 focus:ring-white focus:outline-none transition-all"
        >
          Skip to main content
        </a>
        <AuthProvider>
          <MotionProvider>
            <Navbar />
            <main id="main-content" className="flex-1">
              {children}
            </main>
            <BackToTop />

            {/* Platform Footer */}
          <footer className="bg-white border-t border-slate-200 mt-20 pt-12 pb-8">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-10">
              {/* 4 Columns Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-12 gap-8 items-start">
                {/* Column 1: Brand & Platform */}
                <div className="md:col-span-4 space-y-3">
                  <Link href="/" className="inline-flex items-center space-x-2.5">
                    <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white shadow-xs">
                      <Briefcase className="w-4 h-4" />
                    </div>
                    <span className="text-lg font-extrabold tracking-tight text-slate-900">
                      GetMe<span className="text-blue-600">Hire</span>
                    </span>
                  </Link>
                  <p className="text-xs text-slate-500 max-w-sm leading-relaxed">
                    Global job discovery platform connecting candidates directly to official employer career opportunities with verified provenance.
                  </p>
                </div>

                {/* Column 2: Candidate Solutions */}
                <div className="md:col-span-3 space-y-3">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-900">
                    Candidate Solutions
                  </h4>
                  <ul className="space-y-2 text-xs text-slate-600">
                    <li>
                      <Link href="/jobs" className="hover:text-blue-600 transition-colors">
                        Find Jobs
                      </Link>
                    </li>
                    <li>
                      <Link href="/#tracks" className="hover:text-blue-600 transition-colors">
                        Career Tracks
                      </Link>
                    </li>
                    <li>
                      <Link href="/matches" className="hover:text-blue-600 transition-colors">
                        My Matches
                      </Link>
                    </li>
                    <li>
                      <Link href="/resume-studio" className="hover:text-blue-600 transition-colors">
                        Resume Studio
                      </Link>
                    </li>
                    <li>
                      <Link href="/saved" className="hover:text-blue-600 transition-colors">
                        Saved Jobs
                      </Link>
                    </li>
                    <li>
                      <Link href="/alerts" className="hover:text-blue-600 transition-colors">
                        Job Alerts
                      </Link>
                    </li>
                    <li>
                      <Link href="/profile" className="hover:text-blue-600 transition-colors">
                        My Profile
                      </Link>
                    </li>
                  </ul>
                </div>

                {/* Column 3: Ingested Pathways */}
                <div className="md:col-span-3 space-y-3">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-900">
                    Career Pathways
                  </h4>
                  <ul className="space-y-2 text-xs text-slate-600">
                    <li>
                      <Link href="/jobs?profession=ENGINEERING" className="hover:text-blue-600 transition-colors">
                        Software &amp; Engineering
                      </Link>
                    </li>
                    <li>
                      <Link href="/jobs?profession=DATA_AI" className="hover:text-blue-600 transition-colors">
                        Data Science &amp; AI
                      </Link>
                    </li>
                    <li>
                      <Link href="/jobs?profession=PRODUCT_DESIGN" className="hover:text-blue-600 transition-colors">
                        Product &amp; Design
                      </Link>
                    </li>
                    <li>
                      <Link href="/jobs?profession=SALES_BIZDEV" className="hover:text-blue-600 transition-colors">
                        Sales &amp; Business Dev
                      </Link>
                    </li>
                    <li>
                      <Link href="/jobs?profession=OPERATIONS_LOGISTICS" className="hover:text-blue-600 transition-colors">
                        Operations &amp; People
                      </Link>
                    </li>
                    <li>
                      <Link href="/jobs?profession=CUSTOMER_SUPPORT" className="hover:text-blue-600 transition-colors">
                        Customer Support &amp; Success
                      </Link>
                    </li>
                  </ul>
                </div>

                {/* Column 4: Platform Trust & Governance */}
                <div className="md:col-span-2 space-y-3">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-900">
                    Trust &amp; Privacy
                  </h4>
                  <ul className="space-y-2 text-xs text-slate-600">
                    <li className="flex items-center space-x-1.5">
                      <CheckCircle2 className="w-3.5 h-3.5 text-blue-600 shrink-0" />
                      <span>Direct Apply Only</span>
                    </li>
                    <li className="flex items-center space-x-1.5">
                      <Lock className="w-3.5 h-3.5 text-blue-600 shrink-0" />
                      <span>Encrypted Resumes</span>
                    </li>
                    <li className="flex items-center space-x-1.5">
                      <Zap className="w-3.5 h-3.5 text-blue-600 shrink-0" />
                      <span>Real-time Ingestion</span>
                    </li>
                    <li className="flex items-center space-x-1.5">
                      <ShieldCheck className="w-3.5 h-3.5 text-blue-600 shrink-0" />
                      <span>Anti-Ghost Verification</span>
                    </li>
                  </ul>
                </div>
              </div>

              {/* Bottom Copyright and Creator Credit */}
              <div className="pt-6 border-t border-slate-100 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-400">
                <p>© 2026 GetMeHire. All rights reserved.</p>
                <p className="text-slate-500 font-medium text-[11px]">
                  Designed &amp; Developed by{" "}
                  <span className="text-slate-700 font-semibold">Vishal Chaudhary</span>
                </p>
              </div>
            </div>
          </footer>
        </MotionProvider>
      </AuthProvider>
    </body>
    </html>
  );
}
