"use client";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { motion } from "framer-motion";
import { Eye, EyeOff, TrendingUp, Mail, Lock, User } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import toast from "react-hot-toast";
import Input from "@/components/ui/Input";
import Button from "@/components/ui/Button";
import { authApi } from "@/lib/api";

const schema = z.object({
  full_name: z.string().min(2, "At least 2 characters"),
  username: z.string().min(3, "At least 3 characters").regex(/^[a-zA-Z0-9_]+$/, "Letters, numbers, underscores only"),
  email: z.string().email("Invalid email"),
  password: z.string().min(8, "At least 8 characters"),
  confirm_password: z.string(),
}).refine((d) => d.password === d.confirm_password, { message: "Passwords don't match", path: ["confirm_password"] });

type FormData = z.infer<typeof schema>;

export default function RegisterPage() {
  const [showPass, setShowPass] = useState(false);
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  const onSubmit = async (data: FormData) => {
    setLoading(true);
    try {
      await authApi.register({ username: data.username, email: data.email, password: data.password, full_name: data.full_name });
      toast.success("Account created! Please sign in.");
      router.push("/login");
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Registration failed";
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -top-40 -right-40 h-96 w-96 rounded-full bg-cyan-600/15 blur-3xl" />
        <div className="absolute -bottom-40 -left-40 h-96 w-96 rounded-full bg-violet-600/20 blur-3xl" />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="w-full max-w-md"
      >
        <div className="rounded-3xl border border-white/10 bg-white/5 p-8 shadow-glass backdrop-blur-2xl">
          <div className="mb-8 flex flex-col items-center">
            <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-600 to-purple-700 shadow-glow">
              <TrendingUp className="h-8 w-8 text-white" />
            </div>
            <h1 className="text-2xl font-bold text-white">Create account</h1>
            <p className="mt-1 text-sm text-white/40">Start your financial journey today</p>
          </div>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <Input label="Full Name" placeholder="John Doe" icon={<User size={16} />}
              error={errors.full_name?.message} {...register("full_name")} />
            <Input label="Username" placeholder="john_doe" icon={<User size={16} />}
              error={errors.username?.message} {...register("username")} />
            <Input label="Email" type="email" placeholder="john@example.com" icon={<Mail size={16} />}
              error={errors.email?.message} {...register("email")} />
            <Input label="Password" type={showPass ? "text" : "password"} placeholder="••••••••"
              icon={<Lock size={16} />} error={errors.password?.message}
              rightIcon={
                <button type="button" onClick={() => setShowPass(!showPass)} className="hover:text-white/70">
                  {showPass ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              }
              {...register("password")} />
            <Input label="Confirm Password" type={showPass ? "text" : "password"} placeholder="••••••••"
              icon={<Lock size={16} />} error={errors.confirm_password?.message}
              {...register("confirm_password")} />

            <Button type="submit" loading={loading} className="w-full" size="lg">
              Create Account
            </Button>
          </form>

          <p className="mt-6 text-center text-sm text-white/40">
            Already have an account?{" "}
            <Link href="/login" className="font-medium text-violet-400 hover:text-violet-300">Sign in</Link>
          </p>
        </div>
      </motion.div>
    </div>
  );
}
