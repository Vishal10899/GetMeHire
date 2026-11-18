"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  Briefcase,
  Lock,
  Mail,
  AlertCircle,
  Eye,
  EyeOff,
  ShieldCheck,
  CheckCircle2,
  FileText,
  Sparkles,
} from "lucide-react";
import { useAuth } from "@/lib/authContext";
import { Button, Input } from "@/components/ui";

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(true);
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email.trim() || !password) {
      setError("Please enter both your email address and password.");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      await login(email.trim(), password);
      router.push("/jobs");
    } catch (err) {
      setError(err.message || "Invalid email or password. Please verify your credentials.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-[82vh] flex items-center justify-center py-10 px-4 sm:px-6 lg:px-8 bg-slate-50">
      <div className="w-full max-w-4xl bg-white rounded-3xl border border-slate-200/90 shadow-sm overflow-hidden grid grid-cols-1 lg:grid-cols-12">
        {/* Left Column: Platform Identity */}
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
                Welcome back
              </h1>
              <p className="text-xs text-slate-300 leading-relaxed">
                Log in to access your saved jobs, tailored resumes, and direct employer application history.
              </p>
            </div>

            <div className="space-y-4 pt-4 border-t border-slate-800">
              <div className="flex items-start space-x-3">
                <CheckCircle2 className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />
                <div>
                  <h2 className="text-xs font-bold text-white">Verified Employer Listings</h2>
                  <p className="text-[11px] text-slate-400">
                    Apply directly on official company career portals with verified provenance.
                  </p>
                </div>
              </div>

              <div className="flex items-start space-x-3">
                <CheckCircle2 className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />
                <div>
                  <h2 className="text-xs font-bold text-white">Personal Career Matches</h2>
                  <p className="text-[11px] text-slate-400">
                    Explainable scoring based on your verified skills and target preferences.
                  </p>
                </div>
              </div>
            </div>
          </div>

          <div className="pt-8 border-t border-slate-800 relative z-10 text-[11px] text-slate-400">
            <span>Encrypted candidate profiles and private resume storage.</span>
          </div>
        </div>

        {/* Right Column: Sign In Form */}
        <div className="lg:col-span-7 p-8 sm:p-10 flex flex-col justify-center">
          <div className="max-w-md w-full mx-auto space-y-6">
            <div className="space-y-1">
              <h2 className="text-xl sm:text-2xl font-extrabold tracking-tight text-slate-900">
                Sign in to your account
              </h2>
              <p className="text-xs text-slate-500">
                Enter your registered email and password to continue.
              </p>
            </div>

            {error && (
              <div className="p-3.5 bg-red-50 border border-red-200 rounded-xl text-xs text-red-800 flex items-start space-x-2.5">
                <AlertCircle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
                <span className="leading-relaxed">{error}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Email Address */}
              <Input
                label="Email Address"
                required
                type="email"
                placeholder="name@example.com"
                icon={Mail}
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
              />

              {/* Password */}
              <div className="space-y-1">
                <Input
                  label="Password"
                  required
                  type={showPassword ? "text" : "password"}
                  placeholder="••••••••••••"
                  icon={Lock}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
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
              </div>

              {/* Remember Me & Help */}
              <div className="flex items-center justify-between text-xs pt-1">
                <label className="flex items-center space-x-2 cursor-pointer select-none text-slate-600">
                  <input
                    type="checkbox"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                    className="w-4 h-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                  />
                  <span>Remember me</span>
                </label>

                <span className="text-slate-400 text-[11px]">
                  Secure authentication session
                </span>
              </div>

              {/* Submit Button */}
              <Button
                type="submit"
                variant="primary"
                size="md"
                loading={loading}
                className="w-full"
              >
                Sign In
              </Button>
            </form>

            {/* Registration Navigation */}
            <div className="pt-2 text-center text-xs text-slate-500">
              Don&apos;t have an account yet?{" "}
              <Link
                href="/register"
                className="font-bold text-blue-600 hover:text-blue-700 hover:underline"
              >
                Create an account
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
