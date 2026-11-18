"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  Briefcase,
  Lock,
  Mail,
  User,
  AlertCircle,
  Eye,
  EyeOff,
  CheckCircle2,
  ShieldCheck,
  Globe2,
  FileCheck,
  Building2,
  ArrowRight,
} from "lucide-react";
import { useAuth } from "@/lib/authContext";
import { api } from "@/lib/api";
import { Button, Input } from "@/components/ui";

function calculatePasswordStrength(pass) {
  if (!pass) return { score: 0, label: "", color: "bg-slate-200" };
  let score = 0;
  if (pass.length >= 8) score++;
  if (pass.length >= 12) score++;
  if (/[A-Z]/.test(pass)) score++;
  if (/[0-9]/.test(pass)) score++;
  if (/[^A-Za-z0-9]/.test(pass)) score++;

  if (score <= 1) return { score: 1, label: "Weak", color: "bg-red-500", text: "text-red-600" };
  if (score <= 3) return { score: 2, label: "Medium", color: "bg-amber-500", text: "text-amber-600" };
  return { score: 3, label: "Strong", color: "bg-emerald-500", text: "text-emerald-600" };
}

export default function RegisterPage() {
  const router = useRouter();
  const { register, refreshUser } = useAuth();

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [agreeTerms, setAgreeTerms] = useState(false);

  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const strength = calculatePasswordStrength(password);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    // Client-side validations
    if (!fullName.trim()) {
      setError("Please enter your full name.");
      return;
    }
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email.trim())) {
      setError("Please enter a valid email address.");
      return;
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters long.");
      return;
    }
    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    if (!agreeTerms) {
      setError("You must accept the Terms of Service and Privacy Policy to continue.");
      return;
    }

    setLoading(true);
    try {
      await register(email.trim(), password);
      // Update profile with full name if provided
      if (fullName.trim()) {
        try {
          await api.updateProfile({ full_name: fullName.trim() });
          await refreshUser();
        } catch (nameErr) {
          console.warn("Could not set full name during registration:", nameErr);
        }
      }
      router.push("/profile?new_user=true");
    } catch (err) {
      setError(err.message || "Registration failed. Please check your details and try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-[82vh] flex items-center justify-center py-10 px-4 sm:px-6 lg:px-8 bg-slate-50">
      <div className="w-full max-w-5xl bg-white rounded-3xl border border-slate-200/90 shadow-sm overflow-hidden grid grid-cols-1 lg:grid-cols-12">
        {/* Left Column: Value Proposition & Platform Provenance */}
        <div className="lg:col-span-5 bg-slate-900 p-8 sm:p-10 text-white flex flex-col justify-between relative overflow-hidden">
          <div className="space-y-6 relative z-10">
            <div className="flex items-center space-x-2.5">
              <div className="w-9 h-9 rounded-xl bg-blue-600 flex items-center justify-center text-white shadow-xs">
                <Briefcase className="w-4 h-4" />
              </div>
              <span className="text-xl font-extrabold tracking-tight">
                GetMe<span className="text-blue-400">Hire</span>
              </span>
            </div>

            <div className="space-y-2">
              <h1 className="text-2xl font-bold tracking-tight text-white">
                Start your job search
              </h1>
              <p className="text-xs text-slate-300 leading-relaxed">
                Connect directly with verified employer job feeds. Authentic listings, direct application links, and zero intermediaries.
              </p>
            </div>

            <div className="space-y-4 pt-4 border-t border-slate-800">
              <div className="flex items-start space-x-3">
                <ShieldCheck className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />
                <div>
                  <h2 className="text-xs font-bold text-white">Direct ATS Integration</h2>
                  <p className="text-[11px] text-slate-400">
                    Positions sync live with official Greenhouse, Lever, Ashby, and Workday systems.
                  </p>
                </div>
              </div>

              <div className="flex items-start space-x-3">
                <FileCheck className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />
                <div>
                  <h2 className="text-xs font-bold text-white">Resume Studio</h2>
                  <p className="text-[11px] text-slate-400">
                    Benchmark keyword fit against employer job descriptions and export clean resumes.
                  </p>
                </div>
              </div>

              <div className="flex items-start space-x-3">
                <Globe2 className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />
                <div>
                  <h2 className="text-xs font-bold text-white">Global Career Discovery</h2>
                  <p className="text-[11px] text-slate-400">
                    Filter by remote flexibility, structured career tracks, verified salaries, and locations.
                  </p>
                </div>
              </div>
            </div>
          </div>

          <div className="pt-8 border-t border-slate-700/60 relative z-10 text-[11px] text-slate-400">
            <span>Direct employer redirection. Verified application links only.</span>
          </div>
        </div>

        {/* Right Column: Registration Form */}
        <div className="lg:col-span-7 p-8 sm:p-10 flex flex-col justify-center">
          <div className="max-w-md w-full mx-auto space-y-6">
            <div className="space-y-1">
              <h2 className="text-xl sm:text-2xl font-extrabold tracking-tight text-slate-900">
                Create candidate account
              </h2>
              <p className="text-xs text-slate-500">
                Sign up in seconds to discover verified opportunities and track applications.
              </p>
            </div>

            {error && (
              <div className="p-3.5 bg-red-50 border border-red-200 rounded-xl text-xs text-red-800 flex items-start space-x-2.5">
                <AlertCircle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
                <span className="leading-relaxed">{error}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Full Name */}
              <Input
                label="Full Name"
                required
                type="text"
                placeholder="e.g. Alex Morgan"
                icon={User}
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                autoComplete="name"
              />

              {/* Email Address */}
              <Input
                label="Email Address"
                required
                type="email"
                placeholder="alex@example.com"
                icon={Mail}
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
              />

              {/* Password */}
              <div className="space-y-1.5">
                <Input
                  label="Password"
                  required
                  type={showPassword ? "text" : "password"}
                  placeholder="At least 8 characters"
                  icon={Lock}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="new-password"
                  rightElement={
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="text-slate-400 hover:text-slate-600 p-1 cursor-pointer focus:outline-none"
                      aria-label={showPassword ? "Hide password" : "Show password"}
                    >
                      {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  }
                />

                {/* Password Strength Indicator */}
                {password.length > 0 && (
                  <div className="space-y-1 pt-1">
                    <div className="flex items-center justify-between text-[11px]">
                      <span className="text-slate-500">Password strength:</span>
                      <span className={`font-bold ${strength.text}`}>{strength.label}</span>
                    </div>
                    <div className="grid grid-cols-3 gap-1.5 h-1.5">
                      <div className={`h-full rounded-full transition-colors ${strength.score >= 1 ? strength.color : "bg-slate-200"}`} />
                      <div className={`h-full rounded-full transition-colors ${strength.score >= 2 ? strength.color : "bg-slate-200"}`} />
                      <div className={`h-full rounded-full transition-colors ${strength.score >= 3 ? strength.color : "bg-slate-200"}`} />
                    </div>
                  </div>
                )}
              </div>

              {/* Confirm Password */}
              <Input
                label="Confirm Password"
                required
                type={showConfirmPassword ? "text" : "password"}
                placeholder="Re-enter your password"
                icon={Lock}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                autoComplete="new-password"
                rightElement={
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="text-slate-400 hover:text-slate-600 p-1 cursor-pointer focus:outline-none"
                    aria-label={showConfirmPassword ? "Hide password" : "Show password"}
                  >
                    {showConfirmPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                }
              />

              {/* Terms and Privacy Checkbox */}
              <div className="flex items-start space-x-2.5 pt-1">
                <input
                  id="agree-terms"
                  type="checkbox"
                  checked={agreeTerms}
                  onChange={(e) => setAgreeTerms(e.target.checked)}
                  className="mt-0.5 w-4 h-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500 cursor-pointer"
                />
                <label htmlFor="agree-terms" className="text-xs text-slate-600 leading-snug cursor-pointer select-none">
                  I agree to the{" "}
                  <span className="text-slate-900 font-semibold hover:underline">Terms of Service</span>{" "}
                  and{" "}
                  <span className="text-slate-900 font-semibold hover:underline">Privacy Policy</span>.
                </label>
              </div>

              {/* Submit Button */}
              <Button
                type="submit"
                variant="primary"
                size="md"
                loading={loading}
                className="w-full"
              >
                Create Account
              </Button>
            </form>

            {/* Login Link */}
            <div className="pt-2 text-center text-xs text-slate-500">
              Already have an account?{" "}
              <Link
                href="/login"
                className="font-bold text-blue-600 hover:text-blue-700 hover:underline"
              >
                Sign in
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
