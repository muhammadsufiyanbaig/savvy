"use client";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { motion } from "framer-motion";
import { Lock, Eye, EyeOff, TrendingUp } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import toast from "react-hot-toast";
import Input from "@/components/ui/Input";
import Button from "@/components/ui/Button";

const schema = z.object({
  new_password: z.string().min(8, "Min 8 characters"),
  confirm_password: z.string(),
}).refine((d) => d.new_password === d.confirm_password, {
  message: "Passwords don't match",
  path: ["confirm_password"],
});
type FormData = z.infer<typeof schema>;

export default function ResetPasswordPage() {
  const [loading, setLoading] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token");

  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  const onSubmit = async (data: FormData) => {
    if (!token) {
      toast.error("Invalid or missing reset token");
      return;
    }
    setLoading(true);
    try {
      await new Promise((res) => setTimeout(res, 800));
      toast.success("Password reset successfully!");
      router.push("/login");
    } catch {
      toast.error("Failed to reset password. Link may have expired.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -top-40 -left-40 h-96 w-96 rounded-full bg-violet-600/20 blur-3xl" />
        <div className="absolute -bottom-40 -right-40 h-96 w-96 rounded-full bg-cyan-600/15 blur-3xl" />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="relative w-full max-w-md"
      >
        <div className="rounded-3xl border border-white/10 bg-white/5 p-8 shadow-glass backdrop-blur-2xl">
          <div className="mb-8 flex flex-col items-center">
            <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-600 to-purple-700 shadow-glow">
              <TrendingUp className="h-8 w-8 text-white" />
            </div>
            <h1 className="text-2xl font-bold text-white">New password</h1>
            <p className="mt-1 text-sm text-white/40">Choose a strong password</p>
          </div>

          {!token ? (
            <div className="rounded-xl border border-rose-500/20 bg-rose-500/10 p-4 text-center">
              <p className="text-sm font-medium text-rose-300">Invalid reset link</p>
              <p className="mt-1 text-xs text-white/40">Request a new one from the forgot password page.</p>
              <Link href="/forgot-password" className="mt-3 inline-block text-xs text-violet-400 hover:text-violet-300">
                Request new link
              </Link>
            </div>
          ) : (
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              <div className="relative">
                <Input
                  label="New Password"
                  type={showNew ? "text" : "password"}
                  placeholder="••••••••"
                  icon={<Lock size={16} />}
                  error={errors.new_password?.message}
                  {...register("new_password")}
                />
                <button
                  type="button"
                  onClick={() => setShowNew(!showNew)}
                  className="absolute right-3 top-9 text-white/30 hover:text-white"
                >
                  {showNew ? <EyeOff size={14} /> : <Eye size={14} />}
                </button>
              </div>
              <Input
                label="Confirm Password"
                type="password"
                placeholder="••••••••"
                error={errors.confirm_password?.message}
                {...register("confirm_password")}
              />
              <Button type="submit" loading={loading} className="w-full" size="lg">
                Reset Password
              </Button>
            </form>
          )}

          <div className="mt-6 text-center">
            <Link href="/login" className="text-sm text-white/40 hover:text-white">
              Back to login
            </Link>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
