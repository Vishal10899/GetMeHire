"use client";

import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Briefcase,
  Compass,
  Bookmark,
  Bell,
  User,
  ShieldCheck,
  Layers,
  LogOut,
  LogIn,
  Menu,
  X,
  ChevronDown,
  Sparkles,
  FileText,
  CheckCircle2,
} from "lucide-react";
import { useAuth } from "@/lib/authContext";
import { motion, AnimatePresence } from "motion/react";
import { dropdownVariants, mobileMenuVariants } from "@/components/animations/variants";

function formatUserLabel(user) {
  if (user?.full_name?.trim()) {
    return user.full_name.trim();
  }
  return "My Account";
}

function getUserInitials(user) {
  if (user?.full_name?.trim()) {
    const parts = user.full_name.trim().split(/\s+/).filter(Boolean);
    if (parts.length >= 2) {
      return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
    }
    return parts[0].slice(0, 2).toUpperCase();
  }
  if (user?.email) {
    return user.email[0].toUpperCase();
  }
  return "GMH";
}

export default function Navbar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [profileDropdownOpen, setProfileDropdownOpen] = useState(false);
  const dropdownRef = useRef(null);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setProfileDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Close mobile drawer and dropdown on route change
  useEffect(() => {
    setMobileMenuOpen(false);
    setProfileDropdownOpen(false);
  }, [pathname]);

  const navLinks = [
    { href: "/jobs", label: "Find Jobs", icon: Compass },
    { href: "/#tracks", label: "Career Tracks", icon: Layers },
    { href: "/matches", label: "My Matches", icon: Sparkles, auth: true },
    { href: "/resume-studio", label: "Resume Studio", icon: FileText, auth: true },
    { href: "/saved", label: "Saved Jobs", icon: Bookmark, auth: true },
    { href: "/alerts", label: "Job Alerts", icon: Bell, auth: true },
    { href: "/admin", label: "Admin", icon: ShieldCheck, auth: true, adminOnly: true },
  ].filter((link) => !link.adminOnly || user?.role === "ADMIN");

  return (
    <header className="sticky top-0 z-50 bg-white/95 backdrop-blur-md border-b border-slate-200/90 shadow-2xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Brand Logo */}
          <div className="flex items-center space-x-3">
            <Link href="/" className="flex items-center space-x-2.5 group">
              <div className="w-9 h-9 rounded-xl bg-blue-600 flex items-center justify-center text-white shadow-xs group-hover:bg-blue-700 transition-colors">
                <Briefcase className="w-4 h-4" />
              </div>
              <div className="flex items-baseline space-x-1.5">
                <span className="text-xl font-extrabold tracking-tight text-slate-900">
                  GetMe<span className="text-blue-600">Hire</span>
                </span>
                <span className="hidden lg:inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-600 border border-slate-200 uppercase tracking-wider">
                  Verified ATS
                </span>
              </div>
            </Link>
          </div>

          {/* Desktop Navigation Links */}
          <nav className="hidden md:flex items-center space-x-1" aria-label="Main Navigation">
            {navLinks.map((link) => {
              if (link.auth && !user) return null;
              const Icon = link.icon;
              const isActive =
                pathname === link.href ||
                (link.href !== "/" && link.href !== "/#tracks" && pathname.startsWith(link.href));

              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`flex items-center space-x-1.5 px-3 py-2 rounded-xl text-xs font-semibold transition-all duration-150 ${
                    isActive
                      ? "bg-blue-50 text-blue-700 border border-blue-200/80 shadow-2xs font-bold"
                      : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
                  }`}
                >
                  <Icon className={`w-3.5 h-3.5 ${isActive ? "text-blue-600" : "text-slate-400"}`} />
                  <span>{link.label}</span>
                </Link>
              );
            })}
          </nav>

          {/* Authenticated / Guest User Actions */}
          <div className="hidden md:flex items-center space-x-3">
            {user ? (
              <div className="relative" ref={dropdownRef}>
                <button
                  onClick={() => setProfileDropdownOpen(!profileDropdownOpen)}
                  className={`flex items-center space-x-2 px-3 py-1.5 rounded-xl border text-xs font-semibold transition-all duration-150 cursor-pointer ${
                    profileDropdownOpen || pathname === "/profile"
                      ? "border-blue-500 bg-blue-50/60 text-blue-700 shadow-2xs ring-2 ring-blue-500/10"
                      : "border-slate-200 text-slate-700 hover:bg-slate-50 hover:border-slate-300"
                  }`}
                  aria-expanded={profileDropdownOpen}
                  aria-haspopup="true"
                  aria-label="User account menu"
                >
                  <div className="w-6 h-6 rounded-full bg-blue-100 border border-blue-200 text-blue-700 flex items-center justify-center font-bold text-[11px] uppercase shrink-0">
                    {getUserInitials(user)}
                  </div>
                  <span className="max-w-[130px] truncate text-slate-800 font-semibold">
                    {formatUserLabel(user)}
                  </span>
                  <ChevronDown
                    className={`w-3.5 h-3.5 text-slate-400 transition-transform duration-200 ${
                      profileDropdownOpen ? "rotate-180 text-blue-600" : ""
                    }`}
                  />
                </button>

                {/* Profile Dropdown Menu */}
                <AnimatePresence>
                  {profileDropdownOpen && (
                    <motion.div
                      variants={dropdownVariants}
                      initial="hidden"
                      animate="visible"
                      exit="exit"
                      className="absolute right-0 mt-2 w-64 bg-white rounded-2xl border border-slate-200/90 shadow-lg py-2 z-50 divide-y divide-slate-100 origin-top-right"
                    >
                      {/* User info banner */}
                      <div className="px-4 py-2.5">
                        <p className="text-xs font-bold text-slate-900 truncate">
                          {formatUserLabel(user)}
                        </p>
                        <p className="text-[11px] text-slate-500 truncate mt-0.5">
                          {user.email}
                        </p>
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-100 uppercase mt-1.5">
                          <CheckCircle2 className="w-2.5 h-2.5" />
                          {user.role === "ADMIN" ? "Platform Admin" : "Candidate Account"}
                        </span>
                      </div>

                      {/* Navigation choices */}
                      <div className="py-1">
                        <Link
                          href="/profile"
                          onClick={() => setProfileDropdownOpen(false)}
                          className={`flex items-center space-x-2.5 px-4 py-2 text-xs font-semibold transition-colors ${
                            pathname === "/profile"
                              ? "bg-blue-50 text-blue-700 font-bold"
                              : "text-slate-700 hover:bg-slate-50 hover:text-blue-600"
                          }`}
                        >
                          <User className="w-3.5 h-3.5 text-slate-400" />
                          <span>My Profile</span>
                        </Link>

                        <Link
                          href="/resume-studio"
                          onClick={() => setProfileDropdownOpen(false)}
                          className={`flex items-center space-x-2.5 px-4 py-2 text-xs font-semibold transition-colors ${
                            pathname === "/resume-studio"
                              ? "bg-blue-50 text-blue-700 font-bold"
                              : "text-slate-700 hover:bg-slate-50 hover:text-blue-600"
                          }`}
                        >
                          <FileText className="w-3.5 h-3.5 text-slate-400" />
                          <span>Resume Studio</span>
                        </Link>

                        <Link
                          href="/matches"
                          onClick={() => setProfileDropdownOpen(false)}
                          className="flex items-center space-x-2.5 px-4 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 hover:text-blue-600 transition-colors"
                        >
                          <Sparkles className="w-3.5 h-3.5 text-slate-400" />
                          <span>My Matches</span>
                        </Link>

                        <Link
                          href="/saved"
                          onClick={() => setProfileDropdownOpen(false)}
                          className="flex items-center space-x-2.5 px-4 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 hover:text-blue-600 transition-colors"
                        >
                          <Bookmark className="w-3.5 h-3.5 text-slate-400" />
                          <span>Saved Jobs</span>
                        </Link>

                        <Link
                          href="/alerts"
                          onClick={() => setProfileDropdownOpen(false)}
                          className="flex items-center space-x-2.5 px-4 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 hover:text-blue-600 transition-colors"
                        >
                          <Bell className="w-3.5 h-3.5 text-slate-400" />
                          <span>Job Alerts</span>
                        </Link>

                        {user.role === "ADMIN" && (
                          <Link
                            href="/admin"
                            onClick={() => setProfileDropdownOpen(false)}
                            className="flex items-center space-x-2.5 px-4 py-2 text-xs font-semibold text-purple-700 hover:bg-purple-50 transition-colors"
                          >
                            <ShieldCheck className="w-3.5 h-3.5 text-purple-600" />
                            <span>Admin Telemetry</span>
                          </Link>
                        )}
                      </div>

                      {/* Sign out */}
                      <div className="pt-1">
                        <button
                          onClick={() => {
                          setProfileDropdownOpen(false);
                            logout();
                          }}
                          className="w-full flex items-center space-x-2 px-4 py-2 text-xs font-semibold text-red-600 hover:bg-red-50 text-left transition-colors cursor-pointer"
                        >
                          <LogOut className="w-3.5 h-3.5 text-red-500" />
                          <span>Sign Out</span>
                        </button>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            ) : (
              <div className="flex items-center space-x-2">
                <Link
                  href="/login"
                  className="px-3.5 py-2 text-xs font-semibold text-slate-700 hover:text-slate-900 hover:bg-slate-50 rounded-xl transition-colors"
                >
                  Sign In
                </Link>
                <Link
                  href="/register"
                  className="px-4 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-xl shadow-2xs transition-colors"
                >
                  Create Account
                </Link>
              </div>
            )}
          </div>

          {/* Mobile menu trigger button */}
          <div className="flex md:hidden items-center space-x-2">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2.5 min-w-[44px] min-h-[44px] flex items-center justify-center rounded-xl text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition-colors cursor-pointer"
              aria-label="Toggle navigation menu"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Drawer Menu */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <motion.div
            variants={mobileMenuVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            className="md:hidden border-t border-slate-200 bg-white px-4 pt-3 pb-6 space-y-2 shadow-lg"
          >
            {navLinks.map((link) => {
              if (link.auth && !user) return null;
              const Icon = link.icon;
              const isActive = pathname === link.href;

              return (
                <Link
                  key={link.href}
                  href={link.href}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`flex items-center space-x-3 px-3.5 py-3 rounded-xl text-xs font-semibold transition-colors min-h-[44px] ${
                    isActive
                      ? "bg-blue-50 text-blue-700 border border-blue-200/80 font-bold"
                      : "text-slate-700 hover:bg-slate-50"
                  }`}
                >
                  <Icon className={`w-4 h-4 ${isActive ? "text-blue-600" : "text-slate-400"}`} />
                  <span>{link.label}</span>
                </Link>
              );
            })}

            {user ? (
              <div className="pt-3 border-t border-slate-100 space-y-2">
                <Link
                  href="/profile"
                  onClick={() => setMobileMenuOpen(false)}
                  className="flex items-center space-x-3 px-3.5 py-3 rounded-xl text-xs font-semibold text-slate-700 hover:bg-slate-50 min-h-[44px]"
                >
                  <User className="w-4 h-4 text-slate-400" />
                  <span>My Profile ({formatUserLabel(user)})</span>
                </Link>
                <button
                  onClick={() => {
                    setMobileMenuOpen(false);
                    logout();
                  }}
                  className="w-full flex items-center space-x-3 px-3.5 py-3 rounded-xl text-xs font-semibold text-red-600 hover:bg-red-50 text-left min-h-[44px] cursor-pointer"
                >
                  <LogOut className="w-4 h-4 text-red-500" />
                  <span>Sign Out</span>
                </button>
              </div>
            ) : (
              <div className="pt-3 border-t border-slate-100 grid grid-cols-2 gap-2">
                <Link
                  href="/login"
                  onClick={() => setMobileMenuOpen(false)}
                  className="flex items-center justify-center py-2.5 px-3 rounded-xl border border-slate-200 text-xs font-semibold text-slate-700 hover:bg-slate-50 text-center min-h-[44px]"
                >
                  Sign In
                </Link>
                <Link
                  href="/register"
                  onClick={() => setMobileMenuOpen(false)}
                  className="flex items-center justify-center py-2.5 px-3 rounded-xl bg-blue-600 text-white text-xs font-semibold hover:bg-blue-700 text-center shadow-2xs min-h-[44px]"
                >
                  Create Account
                </Link>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
}
