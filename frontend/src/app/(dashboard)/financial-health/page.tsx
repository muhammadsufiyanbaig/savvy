"use client";
import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Activity, AlertTriangle, CheckCircle, TrendingDown, Info } from "lucide-react";
import { RadialBarChart, RadialBar, ResponsiveContainer, Tooltip } from "recharts";
import Navbar from "@/components/layout/Navbar";
import GlassCard from "@/components/ui/GlassCard";
import Button from "@/components/ui/Button";
import { healthApi } from "@/lib/api";
import toast from "react-hot-toast";

interface Component {
  name: string;
  key: string;
  score: number;
  max_score: number;
  status: "good" | "warning" | "poor";
  tip: string;
}
interface HealthData {
  total_score: number;
  grade: "A" | "B" | "C" | "D" | "F";
  components: Component[];
  calculated_at: string;
}

const GRADE_CONFIG: Record<string, { color: string; label: string; ring: string }> = {
  A: { color: "text-emerald-400", label: "Excellent",  ring: "#10b981" },
  B: { color: "text-cyan-400",    label: "Good",       ring: "#0891b2" },
  C: { color: "text-amber-400",   label: "Fair",       ring: "#d97706" },
  D: { color: "text-orange-400",  label: "Poor",       ring: "#ea580c" },
  F: { color: "text-rose-400",    label: "Critical",   ring: "#e11d48" },
};

const STATUS_ICON: Record<string, JSX.Element> = {
  good:    <CheckCircle   size={14} className="text-emerald-400" />,
  warning: <AlertTriangle size={14} className="text-amber-400"  />,
  poor:    <TrendingDown  size={14} className="text-rose-400"   />,
};
const STATUS_BAR_COLOR: Record<string, string> = {
  good:    "#10b981",
  warning: "#d97706",
  poor:    "#e11d48",
};

const COMPONENT_LABELS: Record<string, string> = {
  savings_rate:       "Savings Rate",
  budget_adherence:   "Budget Adherence",
  debt_ratio:         "Debt Ratio",
  zakat_compliance:   "Zakat Compliance",
  charitable_giving:  "Charitable Giving",
  goal_progress:      "Goal Progress",
};

export default function FinancialHealthPage() {
  const [data,     setData]     = useState<HealthData | null>(null);
  const [loading,  setLoading]  = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = async (refresh = false) => {
    if (refresh) setRefreshing(true); else setLoading(true);
    try {
      const res = await healthApi.score();
      setData(res.data);
    } catch { toast.error("Failed to load health score"); } finally {
      setLoading(false); setRefreshing(false);
    }
  };
  useEffect(() => { load(); }, []);

  const grade = data?.grade ?? "F";
  const gc    = GRADE_CONFIG[grade] ?? GRADE_CONFIG.F;
  const score = data?.total_score ?? 0;

  const radialData = [{ name: "Score", value: score, fill: gc.ring }];

  return (
    <div className="flex flex-col h-full">
      <Navbar title="Financial Health Score" subtitle="Overall Islamic financial wellness" />
      <div className="flex-1 overflow-y-auto p-6 space-y-6">

        {loading ? (
          <div className="space-y-4">
            <div className="h-56 rounded-2xl bg-white/5 animate-pulse" />
            <div className="h-64 rounded-2xl bg-white/5 animate-pulse" />
          </div>
        ) : !data ? (
          <GlassCard className="p-12 text-center" hover={false}>
            <Activity size={40} className="mx-auto text-white/20 mb-3" />
            <p className="text-white/40 text-sm">Could not load health score.</p>
            <Button className="mt-4" size="sm" onClick={() => load()}>Retry</Button>
          </GlassCard>
        ) : (
          <>
            {/* Score card */}
            <GlassCard className="p-6" hover={false}>
              <div className="flex flex-col lg:flex-row items-center gap-6">
                {/* Radial gauge */}
                <div className="relative w-48 h-48 shrink-0">
                  <ResponsiveContainer width="100%" height="100%">
                    <RadialBarChart cx="50%" cy="50%" innerRadius="70%" outerRadius="90%"
                      data={radialData} startAngle={220} endAngle={-40} barSize={12}>
                      <RadialBar background={{ fill: "rgba(255,255,255,0.05)" }} dataKey="value" max={100} cornerRadius={6} />
                    </RadialBarChart>
                  </ResponsiveContainer>
                  {/* Center text */}
                  <div className="absolute inset-0 flex flex-col items-center justify-center">
                    <p className={`text-5xl font-black ${gc.color}`}>{grade}</p>
                    <p className="text-xs text-white/40 mt-1">{score}/100</p>
                  </div>
                </div>

                {/* Summary */}
                <div className="flex-1 text-center lg:text-left">
                  <h2 className={`text-2xl font-bold ${gc.color}`}>{gc.label}</h2>
                  <p className="text-sm text-white/50 mt-1">Your Islamic financial wellness score</p>
                  <div className="mt-4 h-3 rounded-full bg-white/8 overflow-hidden">
                    <motion.div className="h-full rounded-full" style={{ backgroundColor: gc.ring }}
                      initial={{ width: 0 }} animate={{ width: `${score}%` }} transition={{ duration: 1, ease: "easeOut" }} />
                  </div>
                  <p className="text-xs text-white/30 mt-1.5">{score} out of 100 points</p>
                  {data.calculated_at && (
                    <p className="text-xs text-white/20 mt-2">
                      Last calculated: {new Date(data.calculated_at).toLocaleString()}
                    </p>
                  )}
                  <Button size="sm" className="mt-4" loading={refreshing} onClick={() => load(true)}>Recalculate</Button>
                </div>
              </div>
            </GlassCard>

            {/* Components */}
            <div className="space-y-3">
              <h3 className="text-sm font-semibold text-white/60 px-1">Score Breakdown</h3>
              {data.components.map((comp, i) => {
                const pct = comp.max_score > 0 ? (comp.score / comp.max_score) * 100 : 0;
                const barColor = STATUS_BAR_COLOR[comp.status] ?? "#7c3aed";
                return (
                  <motion.div key={comp.key} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.07 }}>
                    <GlassCard className="p-4" hover={false}>
                      <div className="flex items-start gap-3">
                        <div className="mt-0.5">{STATUS_ICON[comp.status]}</div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between mb-2">
                            <p className="text-sm font-medium text-white">
                              {COMPONENT_LABELS[comp.key] ?? comp.name}
                            </p>
                            <span className="text-sm font-bold" style={{ color: barColor }}>
                              {comp.score}/{comp.max_score}
                            </span>
                          </div>
                          {/* Progress bar */}
                          <div className="h-1.5 rounded-full bg-white/8 overflow-hidden mb-2">
                            <motion.div className="h-full rounded-full" style={{ backgroundColor: barColor }}
                              initial={{ width: 0 }} animate={{ width: `${pct}%` }} transition={{ duration: 0.8, delay: i * 0.07 }} />
                          </div>
                          {/* Tip */}
                          <div className="flex items-start gap-1.5 mt-1">
                            <Info size={11} className="text-white/25 mt-0.5 shrink-0" />
                            <p className="text-xs text-white/40">{comp.tip}</p>
                          </div>
                        </div>
                      </div>
                    </GlassCard>
                  </motion.div>
                );
              })}
            </div>

            {/* Grade scale legend */}
            <GlassCard className="p-4" hover={false}>
              <p className="text-xs font-semibold text-white/40 mb-3">Grade Scale</p>
              <div className="flex gap-2 flex-wrap">
                {Object.entries(GRADE_CONFIG).map(([g, cfg]) => (
                  <div key={g} className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold ${grade === g ? "ring-1 ring-white/20 bg-white/8" : "opacity-40"}`}>
                    <span className={cfg.color}>{g}</span>
                    <span className="text-white/50">{cfg.label}</span>
                  </div>
                ))}
              </div>
              <div className="mt-3 grid grid-cols-2 gap-1 text-xs text-white/30">
                <span>A: 85–100 · Excellent</span>
                <span>B: 70–84 · Good</span>
                <span>C: 55–69 · Fair</span>
                <span>D: 40–54 · Poor</span>
                <span>F: 0–39 · Critical</span>
              </div>
            </GlassCard>
          </>
        )}
      </div>
    </div>
  );
}
