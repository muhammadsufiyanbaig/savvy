"use client";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { motion } from "framer-motion";
import { Eye, EyeOff, TrendingUp, Mail, Lock } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import toast from "react-hot-toast";
import Input from "@/components/ui/Input";
import Button from "@/components/ui/Button";
import { authApi } from "@/lib/api";
import { useAuthStore } from "@/store/authStore";

const schema = z.object({
  username: z.string().min(1, "Username required"),
  password: z.string().min(1, "Password required"),
});
type FormData = z.infer<typeof schema>;

export default function LoginPage() {
  const [showPass, setShowPass] = useState(false);
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const { setAuth } = useAuthStore();

  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  const onSubmit = async (data: FormData) => {
    setLoading(true);
    try {
      const res = await authApi.login(data.username, data.password);
      const token = res.data.access_token;
      const refreshToken = res.data.refresh_token;
      // Store tokens so me() interceptor can attach Authorization header
      localStorage.setItem("access_token", token);
      if (refreshToken) localStorage.setItem("refresh_token", refreshToken);
      const me = await authApi.me();
      setAuth(me.data, token);
      toast.success("Welcome back!");
      router.push("/dashboard");
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Invalid credentials";
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      {/* Background orbs */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -top-40 -left-40 h-96 w-96 rounded-full bg-violet-600/20 blur-3xl" />
        <div className="absolute -bottom-40 -right-40 h-96 w-96 rounded-full bg-cyan-600/15 blur-3xl" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 h-64 w-64 rounded-full bg-purple-800/10 blur-3xl" />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="relative w-full max-w-md"
      >
        {/* Card */}
        <div className="rounded-3xl border border-white/10 bg-white/5 p-8 shadow-glass backdrop-blur-2xl">
          {/* Logo */}
          <div className="mb-8 flex flex-col items-center">
            <motion.div
              animate={{ rotate: [0, 5, -5, 0] }}
              transition={{ duration: 4, repeat: Infinity }}
              className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-600 to-purple-700 shadow-glow"
            >
              <TrendingUp className="h-8 w-8 text-white" />
            </motion.div>
            <h1 className="text-2xl font-bold text-white">Welcome back</h1>
            <p className="mt-1 text-sm text-white/40">Sign in to your Savvy account</p>
          </div>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <Input
              label="Username or Email"
              placeholder="your_username"
              icon={<Mail size={16} />}
              error={errors.username?.message}
              {...register("username")}
            />
            <Input
              label="Password"
              type={showPass ? "text" : "password"}
              placeholder="••••••••"
              icon={<Lock size={16} />}
              error={errors.password?.message}
              rightIcon={
                <button type="button" onClick={() => setShowPass(!showPass)} className="hover:text-white/70">
                  {showPass ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              }
              {...register("password")}
            />

            <div className="flex justify-end">
              <Link href="/forgot-password" className="text-xs text-violet-400 hover:text-violet-300">
                Forgot password?
              </Link>
            </div>

            <Button type="submit" loading={loading} className="w-full" size="lg">
              Sign In
            </Button>
          </form>

          {/* Divider */}
          <div className="my-6 flex items-center gap-3">
            <div className="h-px flex-1 bg-white/10" />
            <span className="text-xs text-white/30">or</span>
            <div className="h-px flex-1 bg-white/10" />
          </div>

          <p className="text-center text-sm text-white/40">
            Don&apos;t have an account?{" "}
            <Link href="/register" className="font-medium text-violet-400 hover:text-violet-300">
              Create one
            </Link>
          </p>
        </div>

        {/* Floating badges */}
        <motion.div
          animate={{ y: [-4, 4, -4] }}
          transition={{ duration: 3, repeat: Infinity }}
          className="absolute -top-4 -right-4 rounded-xl border border-white/10 bg-white/5 px-3 py-1.5 backdrop-blur-xl text-xs text-white/60"
        >
          🔒 Bank-grade security
        </motion.div>
        <motion.div
          animate={{ y: [4, -4, 4] }}
          transition={{ duration: 3.5, repeat: Infinity }}
          className="absolute -bottom-4 -left-4 rounded-xl border border-white/10 bg-white/5 px-3 py-1.5 backdrop-blur-xl text-xs text-white/60"
        >
          ✨ AI-powered insights
        </motion.div>
      </motion.div>
    </div>
  );
}
