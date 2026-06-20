"use client";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { motion } from "framer-motion";
import { User, Lock, Bell, Palette, Shield, Save, Eye, EyeOff } from "lucide-react";
import Navbar from "@/components/layout/Navbar";
import GlassCard from "@/components/ui/GlassCard";
import Button from "@/components/ui/Button";
import Input from "@/components/ui/Input";
import { authApi, notificationApi } from "@/lib/api";
import { useAuthStore } from "@/store/authStore";
import { getInitials } from "@/lib/utils";
import toast from "react-hot-toast";

const profileSchema = z.object({
  full_name: z.string().min(1, "Required"),
  email: z.string().email("Invalid email"),
  username: z.string().min(3, "Min 3 chars"),
});

const passwordSchema = z.object({
  current_password: z.string().min(1, "Required"),
  new_password: z.string().min(8, "Min 8 chars"),
  confirm_password: z.string(),
}).refine((d) => d.new_password === d.confirm_password, {
  message: "Passwords don't match",
  path: ["confirm_password"],
});

type ProfileForm = z.infer<typeof profileSchema>;
type PasswordForm = z.infer<typeof passwordSchema>;

const SECTIONS = [
  { id: "profile", label: "Profile", icon: User },
  { id: "security", label: "Security", icon: Lock },
  { id: "notifications", label: "Notifications", icon: Bell },
  { id: "appearance", label: "Appearance", icon: Palette },
];

export default function SettingsPage() {
  const { user, updateUser } = useAuthStore();
  const [activeSection, setActiveSection] = useState("profile");
  const [savingProfile, setSavingProfile] = useState(false);
  const [savingPassword, setSavingPassword] = useState(false);
  const [showCurrent, setShowCurrent] = useState(false);
  const [showNew, setShowNew] = useState(false);

  const profileForm = useForm<ProfileForm>({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      full_name: user?.full_name || "",
      email: user?.email || "",
      username: user?.username || "",
    },
  });

  const passwordForm = useForm<PasswordForm>({ resolver: zodResolver(passwordSchema) });

  useEffect(() => {
    if (user) {
      profileForm.reset({
        full_name: user.full_name || "",
        email: user.email || "",
        username: user.username || "",
      });
    }
  }, [user]);

  const onSaveProfile = async (data: ProfileForm) => {
    setSavingProfile(true);
    try {
      await authApi.updateMe(data);
      updateUser(data);
      toast.success("Profile updated!");
    } catch { toast.error("Failed to update profile"); }
    finally { setSavingProfile(false); }
  };

  const onChangePassword = async (data: PasswordForm) => {
    setSavingPassword(true);
    try {
      await authApi.changePassword({ current_password: data.current_password, new_password: data.new_password });
      toast.success("Password changed!");
      passwordForm.reset();
    } catch { toast.error("Failed to change password"); }
    finally { setSavingPassword(false); }
  };

  const notifPrefs = [
    { key: "budget_alerts",         label: "Budget Alerts",       desc: "Notify when spending reaches threshold" },
    { key: "goal_updates",          label: "Savings Reminders",   desc: "Weekly progress updates for goals" },
    { key: "recommendations",       label: "AI Insights",         desc: "New personalized recommendations" },
    { key: "weekly_summary",        label: "Weekly Summary",      desc: "Spending summary every Monday" },
    { key: "expense_notifications", label: "Expense Alerts",      desc: "Notify on new expenses added" },
    { key: "push_enabled",          label: "Push Notifications",  desc: "Browser/mobile push alerts" },
    { key: "email_enabled",         label: "Email Notifications", desc: "Send alerts to your email" },
    { key: "in_app_enabled",        label: "In-App Alerts",       desc: "Show alerts inside the app" },
  ];

  const [notifEnabled, setNotifEnabled] = useState<Record<string, boolean>>({
    budget_alerts: true,
    goal_updates: true,
    recommendations: true,
    weekly_summary: false,
    expense_notifications: false,
    push_enabled: true,
    email_enabled: true,
    in_app_enabled: true,
  });
  const [loadingPrefs, setLoadingPrefs] = useState(false);
  const [savingPrefs, setSavingPrefs] = useState(false);

  // Appearance — persisted to localStorage
  const [activeTheme, setActiveTheme] = useState(() =>
    typeof window !== "undefined" ? (localStorage.getItem("savvy-theme") || "dark") : "dark"
  );
  const [activeAccent, setActiveAccent] = useState(() =>
    typeof window !== "undefined" ? (localStorage.getItem("savvy-accent") || "violet") : "violet"
  );
  const [savingAppearance, setSavingAppearance] = useState(false);

  useEffect(() => {
    setLoadingPrefs(true);
    notificationApi.getPreferences()
      .then((res) => {
        const p = res.data;
        setNotifEnabled({
          budget_alerts:         p.budget_alerts         ?? true,
          goal_updates:          p.goal_updates          ?? true,
          recommendations:       p.recommendations       ?? true,
          weekly_summary:        p.weekly_summary        ?? false,
          expense_notifications: p.expense_notifications ?? false,
          push_enabled:          p.push_enabled          ?? true,
          email_enabled:         p.email_enabled         ?? true,
          in_app_enabled:        p.in_app_enabled        ?? true,
        });
      })
      .catch(() => { /* use defaults on error */ })
      .finally(() => setLoadingPrefs(false));
  }, []);

  const onSavePreferences = async () => {
    setSavingPrefs(true);
    try {
      await notificationApi.updatePreferences(notifEnabled);
      toast.success("Preferences saved!");
    } catch { toast.error("Failed to save preferences"); }
    finally { setSavingPrefs(false); }
  };

  const onSaveAppearance = () => {
    setSavingAppearance(true);
    localStorage.setItem("savvy-theme", activeTheme);
    localStorage.setItem("savvy-accent", activeAccent);
    setTimeout(() => {
      setSavingAppearance(false);
      toast.success("Appearance saved!");
    }, 300);
  };

  return (
    <div className="flex flex-col h-full">
      <Navbar title="Settings" subtitle="Manage your account" />
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-4xl mx-auto flex gap-6">

          {/* Sidebar nav */}
          <div className="w-48 shrink-0 space-y-1">
            {SECTIONS.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setActiveSection(id)}
                className={`w-full flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all ${
                  activeSection === id
                    ? "bg-violet-600/20 text-violet-300 border border-violet-500/20"
                    : "text-white/40 hover:bg-white/5 hover:text-white"
                }`}
              >
                <Icon size={16} className="shrink-0" />
                {label}
              </button>
            ))}
          </div>

          {/* Content */}
          <div className="flex-1 space-y-6">

            {activeSection === "profile" && (
              <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
                {/* Avatar */}
                <GlassCard className="p-6" hover={false}>
                  <h3 className="text-sm font-semibold text-white mb-4">Profile Picture</h3>
                  <div className="flex items-center gap-4">
                    <div className="flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-600 to-purple-700 text-2xl font-bold text-white shadow-glow">
                      {user ? getInitials(user.full_name || user.username) : "?"}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-white">{user?.full_name || user?.username}</p>
                      <p className="text-xs text-white/40 mt-0.5">{user?.email}</p>
                      <p className="text-xs text-white/30 mt-2">Avatar is auto-generated from your initials</p>
                    </div>
                  </div>
                </GlassCard>

                {/* Profile form */}
                <GlassCard className="p-6" hover={false}>
                  <h3 className="text-sm font-semibold text-white mb-4">Personal Information</h3>
                  <form onSubmit={profileForm.handleSubmit(onSaveProfile)} className="space-y-4">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <Input
                        label="Full Name"
                        error={profileForm.formState.errors.full_name?.message}
                        {...profileForm.register("full_name")}
                      />
                      <Input
                        label="Username"
                        error={profileForm.formState.errors.username?.message}
                        {...profileForm.register("username")}
                      />
                      <Input
                        label="Email"
                        type="email"
                        error={profileForm.formState.errors.email?.message}
                        {...profileForm.register("email")}
                        className="sm:col-span-2"
                      />
                    </div>
                    <Button type="submit" icon={<Save size={14} />} loading={savingProfile}>Save Changes</Button>
                  </form>
                </GlassCard>
              </motion.div>
            )}

            {activeSection === "security" && (
              <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
                <GlassCard className="p-6" hover={false}>
                  <h3 className="text-sm font-semibold text-white mb-1">Change Password</h3>
                  <p className="text-xs text-white/40 mb-4">Use a strong password with at least 8 characters</p>
                  <form onSubmit={passwordForm.handleSubmit(onChangePassword)} className="space-y-4">
                    <div className="relative">
                      <Input
                        label="Current Password"
                        type={showCurrent ? "text" : "password"}
                        error={passwordForm.formState.errors.current_password?.message}
                        {...passwordForm.register("current_password")}
                      />
                      <button
                        type="button"
                        onClick={() => setShowCurrent(!showCurrent)}
                        className="absolute right-3 top-9 text-white/30 hover:text-white"
                      >
                        {showCurrent ? <EyeOff size={14} /> : <Eye size={14} />}
                      </button>
                    </div>
                    <div className="relative">
                      <Input
                        label="New Password"
                        type={showNew ? "text" : "password"}
                        error={passwordForm.formState.errors.new_password?.message}
                        {...passwordForm.register("new_password")}
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
                      label="Confirm New Password"
                      type="password"
                      error={passwordForm.formState.errors.confirm_password?.message}
                      {...passwordForm.register("confirm_password")}
                    />
                    <Button type="submit" icon={<Shield size={14} />} loading={savingPassword}>Update Password</Button>
                  </form>
                </GlassCard>

                <GlassCard className="p-6" hover={false}>
                  <h3 className="text-sm font-semibold text-white mb-1">Active Sessions</h3>
                  <p className="text-xs text-white/40 mb-4">Manage where you're logged in</p>
                  <div className="rounded-xl border border-white/8 bg-white/3 p-4 flex items-center justify-between">
                    <div>
                      <p className="text-sm text-white font-medium">Current Session</p>
                      <p className="text-xs text-white/40">This device · Active now</p>
                    </div>
                    <span className="h-2 w-2 rounded-full bg-emerald-500" />
                  </div>
                </GlassCard>
              </motion.div>
            )}

            {activeSection === "notifications" && (
              <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
                <GlassCard className="p-6" hover={false}>
                  <h3 className="text-sm font-semibold text-white mb-1">Notification Preferences</h3>
                  <p className="text-xs text-white/40 mb-5">Choose what you want to be notified about</p>
                  {loadingPrefs ? (
                    <div className="space-y-4">
                      {notifPrefs.map(({ key }) => (
                        <div key={key} className="flex items-center justify-between animate-pulse">
                          <div className="space-y-1">
                            <div className="h-3 w-32 rounded bg-white/10" />
                            <div className="h-2 w-48 rounded bg-white/5" />
                          </div>
                          <div className="h-6 w-11 rounded-full bg-white/10" />
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {notifPrefs.map(({ key, label, desc }) => (
                        <div key={key} className="flex items-center justify-between">
                          <div>
                            <p className="text-sm font-medium text-white">{label}</p>
                            <p className="text-xs text-white/40">{desc}</p>
                          </div>
                          <button
                            onClick={() => setNotifEnabled((p) => ({ ...p, [key]: !p[key] }))}
                            className={`relative h-6 w-11 rounded-full transition-colors ${
                              notifEnabled[key] ? "bg-violet-600" : "bg-white/10"
                            }`}
                          >
                            <span
                              className={`absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform ${
                                notifEnabled[key] ? "translate-x-5" : "translate-x-0.5"
                              }`}
                            />
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                  <div className="mt-5">
                    <Button icon={<Save size={14} />} onClick={onSavePreferences} loading={savingPrefs}>
                      Save Preferences
                    </Button>
                  </div>
                </GlassCard>
              </motion.div>
            )}

            {activeSection === "appearance" && (
              <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
                <GlassCard className="p-6" hover={false}>
                  <h3 className="text-sm font-semibold text-white mb-1">Appearance</h3>
                  <p className="text-xs text-white/40 mb-5">Customize your interface</p>
                  <div className="space-y-4">
                    <div>
                      <p className="text-sm font-medium text-white mb-2">Theme</p>
                      <div className="grid grid-cols-3 gap-3">
                        {[
                          { id: "dark",     label: "Dark",     bg: "from-gray-900 to-gray-800" },
                          { id: "purple",   label: "Purple",   bg: "from-violet-900 to-purple-900" },
                          { id: "midnight", label: "Midnight", bg: "from-blue-950 to-slate-900" },
                        ].map((theme) => (
                          <button
                            key={theme.id}
                            onClick={() => setActiveTheme(theme.id)}
                            className={`rounded-xl border p-3 text-center transition-all hover:border-violet-500/40 ${
                              activeTheme === theme.id
                                ? "border-violet-500/40 ring-1 ring-violet-500/30"
                                : "border-white/10"
                            }`}
                          >
                            <div className={`h-12 rounded-lg bg-gradient-to-br ${theme.bg} mb-2`} />
                            <p className="text-xs text-white/60">{theme.label}</p>
                          </button>
                        ))}
                      </div>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-white mb-2">Accent Color</p>
                      <div className="flex gap-3">
                        {[
                          { id: "violet",  color: "bg-violet-600",  ring: "ring-violet-500" },
                          { id: "cyan",    color: "bg-cyan-600",    ring: "ring-cyan-500" },
                          { id: "emerald", color: "bg-emerald-600", ring: "ring-emerald-500" },
                          { id: "rose",    color: "bg-rose-600",    ring: "ring-rose-500" },
                          { id: "amber",   color: "bg-amber-600",   ring: "ring-amber-500" },
                        ].map(({ id, color, ring }) => (
                          <button
                            key={id}
                            onClick={() => setActiveAccent(id)}
                            className={`h-8 w-8 rounded-full ${color} transition-all hover:scale-110 ${
                              activeAccent === id ? `ring-2 ${ring} ring-offset-2 ring-offset-transparent` : ""
                            }`}
                          />
                        ))}
                      </div>
                    </div>
                  </div>
                  <div className="mt-5">
                    <Button icon={<Save size={14} />} onClick={onSaveAppearance} loading={savingAppearance}>
                      Save Appearance
                    </Button>
                  </div>
                </GlassCard>
              </motion.div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
