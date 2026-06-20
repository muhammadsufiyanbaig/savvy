"use client";
import { useEffect, useState, useCallback } from "react";
import { motion } from "framer-motion";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell,
} from "recharts";
import { Wallet, TrendingUp, TrendingDown, PiggyBank, Sparkles, ArrowRight, RefreshCw } from "lucide-react";
import Navbar from "@/components/layout/Navbar";
import GlassCard from "@/components/ui/GlassCard";
import StatCard from "@/components/ui/StatCard";
import Badge from "@/components/ui/Badge";
import Button from "@/components/ui/Button";
import { expenseApi, savingsApi, budgetApi, aiApi } from "@/lib/api";
import { formatCurrency, formatRelativeTime, CATEGORY_COLORS } from "@/lib/utils";
import { useAuthStore } from "@/store/authStore";
import Link from "next/link";
import toast from "react-hot-toast";

interface ExpenseSummary {
  total_expenses: number;
  expense_count: number;
  by_category: Record<string, { total: number; count: number }>;
}

interface BudgetStatus {
  total_allocated: number;
  total_spent: number;
  percentage_used: number;
  on_track: boolean;
}

interface Recommendation {
  id: string;
  type: string;
  title: string;
  message: string;
  priority: string;
  is_urgent: boolean;
  supporting_data?: Record<string, unknown>;
}

interface TrendPoint { month: string; expenses: number; savings: number; }

export default function DashboardPage() {
  const { user } = useAuthStore();
  const [summary, setSummary] = useState<ExpenseSummary | null>(null);
  const [budgetStatus, setBudgetStatus] = useState<BudgetStatus | null>(null);
  const [savingsGoals, setSavingsGoals] = useState<unknown[]>([]);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [recentExpenses, setRecentExpenses] = useState<unknown[]>([]);
  const [trendData, setTrendData] = useState<TrendPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [aiLoading, setAiLoading] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true);
    const now = new Date();
    const startDate = new Date(now.getFullYear(), now.getMonth(), 1).toISOString().slice(0, 10);
    const endDate = new Date(now.getFullYear(), now.getMonth() + 1, 0).toISOString().slice(0, 10);
    try {
      const [expSum, budStat, sav, recs, recent, trend] = await Promise.allSettled([
        expenseApi.summary({ start_date: startDate, end_date: endDate }),
        budgetApi.status("monthly"),
        savingsApi.list(),
        aiApi.recommendations(),
        expenseApi.list({ limit: 5, offset: 0 }),
        expenseApi.trend(6),
      ]);
      if (expSum.status === "fulfilled") setSummary(expSum.value.data);
      if (budStat.status === "fulfilled") setBudgetStatus(budStat.value.data);
      if (sav.status === "fulfilled") setSavingsGoals(sav.value.data?.goals || []);
      if (recs.status === "fulfilled") setRecommendations((recs.value.data?.insights || recs.value.data?.recommendations || []).slice(0, 3));
      if (recent.status === "fulfilled") setRecentExpenses(recent.value.data?.expenses?.slice(0, 5) || []);
      if (trend.status === "fulfilled") setTrendData(trend.value.data?.trend || []);
    } catch {}
    setLoading(false);
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const generateAI = async () => {
    setAiLoading(true);
    try {
      await aiApi.generate();
      toast.success("AI recommendations generated!");
      fetchData();
    } catch { toast.error("Failed to generate AI insights"); }
    finally { setAiLoading(false); }
  };

  const categoryPieData = summary?.by_category
    ? Object.entries(summary.by_category).map(([name, data]) => ({ name, value: data.total }))
    : [];

  const greeting = () => {
    const h = new Date().getHours();
    if (h < 12) return "Good morning";
    if (h < 17) return "Good afternoon";
    return "Good evening";
  };

  return (
    <div className="flex flex-col h-full">
      <Navbar title="Dashboard" subtitle={`${greeting()}, ${user?.full_name?.split(" ")[0] || user?.username}!`} />

      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {/* Stat Cards */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard
            title="Monthly Expenses"
            value={formatCurrency(summary?.total_expenses || 0)}
            subtitle={`${summary?.expense_count || 0} transactions`}
            icon={<TrendingDown className="h-5 w-5" />}
            trend={{ value: -8.2, label: "vs last month" }}
            gradient="bg-gradient-to-br from-rose-600 to-orange-600"
            delay={0}
          />
          <StatCard
            title="Budget Used"
            value={`${Math.round(budgetStatus?.percentage_used || 0)}%`}
            subtitle={`${formatCurrency(budgetStatus?.total_spent || 0)} of ${formatCurrency(budgetStatus?.total_allocated || 0)}`}
            icon={<Wallet className="h-5 w-5" />}
            trend={{ value: budgetStatus?.on_track ? 5 : -5, label: budgetStatus?.on_track ? "on track" : "over budget" }}
            gradient="bg-gradient-to-br from-amber-600 to-yellow-600"
            delay={0.1}
          />
          <StatCard
            title="Savings Goals"
            value={`${(savingsGoals as { status: string }[]).filter((g) => (g as { status: string }).status === "active").length}`}
            subtitle="active goals"
            icon={<PiggyBank className="h-5 w-5" />}
            gradient="bg-gradient-to-br from-emerald-600 to-teal-600"
            delay={0.2}
          />
          <StatCard
            title="AI Insights"
            value={`${recommendations.length}`}
            subtitle="recommendations ready"
            icon={<Sparkles className="h-5 w-5" />}
            gradient="bg-gradient-to-br from-violet-600 to-purple-600"
            delay={0.3}
          />
        </div>

        {/* Charts row */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* Trend chart */}
          <GlassCard className="lg:col-span-2 p-6" hover={false}>
            <div className="mb-4 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold text-white">Spending Trend</h3>
                <p className="text-xs text-white/40">Expenses vs Savings — last 6 months</p>
              </div>
              <Badge variant="purple">Monthly</Badge>
            </div>
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={trendData}>
                <defs>
                  <linearGradient id="gradExp" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#f43f5e" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="gradSav" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="month" stroke="rgba(255,255,255,0.3)" tick={{ fontSize: 11 }} />
                <YAxis stroke="rgba(255,255,255,0.3)" tick={{ fontSize: 11 }} tickFormatter={(v) => `$${v}`} />
                <Tooltip
                  contentStyle={{ background: "rgba(15,10,30,0.9)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 12 }}
                  labelStyle={{ color: "rgba(255,255,255,0.7)" }}
                  itemStyle={{ color: "rgba(255,255,255,0.8)" }}
                />
                <Area type="monotone" dataKey="expenses" stroke="#f43f5e" fill="url(#gradExp)" strokeWidth={2} name="Expenses" />
                <Area type="monotone" dataKey="savings" stroke="#10b981" fill="url(#gradSav)" strokeWidth={2} name="Savings" />
              </AreaChart>
            </ResponsiveContainer>
          </GlassCard>

          {/* Pie chart */}
          <GlassCard className="p-6" hover={false}>
            <div className="mb-4">
              <h3 className="text-sm font-semibold text-white">By Category</h3>
              <p className="text-xs text-white/40">This month</p>
            </div>
            {categoryPieData.length > 0 ? (
              <>
                <ResponsiveContainer width="100%" height={160}>
                  <PieChart>
                    <Pie data={categoryPieData} cx="50%" cy="50%" innerRadius={45} outerRadius={70} paddingAngle={3} dataKey="value">
                      {categoryPieData.map((entry, i) => (
                        <Cell key={i} fill={CATEGORY_COLORS[entry.name] || "#6b7280"} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{ background: "rgba(15,10,30,0.9)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 12 }}
                      formatter={(value: number) => formatCurrency(value)}
                    />
                  </PieChart>
                </ResponsiveContainer>
                <div className="mt-2 space-y-1.5">
                  {categoryPieData.slice(0, 4).map((item) => (
                    <div key={item.name} className="flex items-center justify-between text-xs">
                      <div className="flex items-center gap-2">
                        <div className="h-2 w-2 rounded-full" style={{ background: CATEGORY_COLORS[item.name] || "#6b7280" }} />
                        <span className="text-white/60">{item.name}</span>
                      </div>
                      <span className="text-white/80 font-medium">{formatCurrency(item.value)}</span>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <div className="flex h-40 items-center justify-center text-sm text-white/30">No expense data yet</div>
            )}
          </GlassCard>
        </div>

        {/* Bottom row */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* Recent Expenses */}
          <GlassCard className="p-6" hover={false}>
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-white">Recent Expenses</h3>
              <Link href="/expenses">
                <Button variant="ghost" size="sm" icon={<ArrowRight size={14} />}>View all</Button>
              </Link>
            </div>
            <div className="space-y-3">
              {(recentExpenses as Record<string, unknown>[]).length === 0 ? (
                <p className="text-center text-sm text-white/30 py-6">No expenses yet</p>
              ) : (
                (recentExpenses as Record<string, unknown>[]).map((exp) => (
                  <motion.div
                    key={exp.id as number}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    className="flex items-center justify-between rounded-xl border border-white/5 bg-white/3 p-3"
                  >
                    <div className="flex items-center gap-3">
                      <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-white/8 text-base">
                        {exp.category === "Food" ? "🍔" : exp.category === "Transport" ? "🚗" : "📦"}
                      </div>
                      <div>
                        <p className="text-sm font-medium text-white truncate max-w-32">{exp.description as string || exp.category as string}</p>
                        <p className="text-xs text-white/40">{exp.merchant_name as string || exp.category as string}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-semibold text-rose-400">-{formatCurrency(exp.amount as number)}</p>
                      <p className="text-xs text-white/30">{formatRelativeTime(exp.transaction_date as string)}</p>
                    </div>
                  </motion.div>
                ))
              )}
            </div>
          </GlassCard>

          {/* AI Recommendations */}
          <GlassCard className="p-6" hover={false}>
            <div className="mb-4 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold text-white">AI Insights</h3>
                <p className="text-xs text-white/40">Personalized recommendations</p>
              </div>
              <Button variant="ghost" size="sm" loading={aiLoading} onClick={generateAI} icon={<RefreshCw size={14} />}>
                Refresh
              </Button>
            </div>
            <div className="space-y-3">
              {recommendations.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-8 text-center">
                  <Sparkles className="mb-3 h-10 w-10 text-violet-400/40" />
                  <p className="text-sm text-white/40">No insights yet</p>
                  <Button variant="primary" size="sm" className="mt-3" loading={aiLoading} onClick={generateAI}>
                    Generate Insights
                  </Button>
                </div>
              ) : (
                recommendations.map((rec) => (
                  <motion.div
                    key={rec.id}
                    initial={{ opacity: 0, x: 10 }}
                    animate={{ opacity: 1, x: 0 }}
                    className="rounded-xl border border-violet-500/15 bg-violet-500/5 p-3"
                  >
                    <div className="flex items-start gap-2">
                      <Sparkles className="mt-0.5 h-3.5 w-3.5 shrink-0 text-violet-400" />
                      <div>
                        <p className="text-xs font-medium text-violet-300">{rec.title}</p>
                        <p className="mt-0.5 text-xs text-white/50 line-clamp-2">{rec.message}</p>
                        <div className="mt-1.5 flex items-center gap-2">
                          <span className={`text-xs px-1.5 py-0.5 rounded-full ${
                            rec.priority === "high" ? "bg-rose-500/20 text-rose-300" :
                            rec.priority === "medium" ? "bg-amber-500/20 text-amber-300" :
                            "bg-white/10 text-white/30"
                          }`}>{rec.priority}</span>
                        </div>
                      </div>
                    </div>
                  </motion.div>
                ))
              )}
            </div>
          </GlassCard>
        </div>
      </div>
    </div>
  );
}
