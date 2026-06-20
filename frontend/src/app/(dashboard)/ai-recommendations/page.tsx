"use client";
import { useEffect, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Sparkles, RefreshCw, TrendingDown, TrendingUp, PiggyBank, ShieldAlert,
  Lightbulb, Target, ChevronDown, ChevronUp,
} from "lucide-react";
import Navbar from "@/components/layout/Navbar";
import GlassCard from "@/components/ui/GlassCard";
import Button from "@/components/ui/Button";
import Badge from "@/components/ui/Badge";
import { aiApi } from "@/lib/api";
import toast from "react-hot-toast";

interface Recommendation {
  id: string;
  type: string;
  title: string;
  message: string;
  priority: string;
  is_urgent: boolean;
  supporting_data?: Record<string, unknown>;
}

const TYPE_CONFIG: Record<string, { icon: React.ReactNode; gradient: string; border: string }> = {
  spending_alert: {
    icon: <ShieldAlert size={18} />,
    gradient: "from-rose-600/20 to-rose-600/5",
    border: "border-rose-500/20",
  },
  savings_opportunity: {
    icon: <PiggyBank size={18} />,
    gradient: "from-emerald-600/20 to-emerald-600/5",
    border: "border-emerald-500/20",
  },
  budget_optimization: {
    icon: <Target size={18} />,
    gradient: "from-amber-600/20 to-amber-600/5",
    border: "border-amber-500/20",
  },
  investment_tip: {
    icon: <TrendingUp size={18} />,
    gradient: "from-cyan-600/20 to-cyan-600/5",
    border: "border-cyan-500/20",
  },
  expense_reduction: {
    icon: <TrendingDown size={18} />,
    gradient: "from-orange-600/20 to-orange-600/5",
    border: "border-orange-500/20",
  },
  general: {
    icon: <Lightbulb size={18} />,
    gradient: "from-violet-600/20 to-violet-600/5",
    border: "border-violet-500/20",
  },
};

const typeConfig = (type: string) => TYPE_CONFIG[type] || TYPE_CONFIG.general;

const priorityVariant = (p: string): "danger" | "warning" | "info" | "default" => {
  if (p === "high") return "danger";
  if (p === "medium") return "warning";
  if (p === "low") return "info";
  return "default";
};

const typeLabel = (type: string) =>
  type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

export default function AIRecommendationsPage() {
  const [recs, setRecs] = useState<Recommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [filterType, setFilterType] = useState("");

  const fetchRecs = useCallback(async () => {
    setLoading(true);
    try {
      const res = await aiApi.recommendations();
      setRecs(res.data?.insights || res.data?.recommendations || []);
    } catch {}
    setLoading(false);
  }, []);

  useEffect(() => { fetchRecs(); }, [fetchRecs]);

  const generate = async () => {
    setGenerating(true);
    try {
      await aiApi.generate();
      toast.success("New AI insights generated!");
      fetchRecs();
    } catch { toast.error("Generation failed"); }
    finally { setGenerating(false); }
  };

  const filtered = filterType ? recs.filter((r) => r.type === filterType) : recs;
  const types = Array.from(new Set(recs.map((r) => r.type)));

  const highPriorityCount = recs.filter((r) => r.priority === "high" || r.is_urgent).length;

  return (
    <div className="flex flex-col h-full">
      <Navbar title="AI Insights" subtitle="Powered by Claude AI" />
      <div className="flex-1 overflow-y-auto p-6 space-y-6">

        {/* Header stats */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {[
            { label: "Total Insights", value: recs.length, sub: "recommendations", color: "text-violet-400" },
            { label: "Urgent", value: recs.filter((r) => r.is_urgent).length, sub: "need immediate action", color: "text-cyan-400" },
            { label: "High Priority", value: highPriorityCount, sub: "need attention", color: "text-rose-400" },
          ].map((item) => (
            <GlassCard key={item.label} className="p-4 text-center">
              <p className="text-xs text-white/40">{item.label}</p>
              <p className={`text-2xl font-bold mt-1 ${item.color}`}>{item.value}</p>
              <p className="text-xs text-white/30 mt-0.5">{item.sub}</p>
            </GlassCard>
          ))}
        </div>

        {/* Toolbar */}
        <div className="flex flex-wrap items-center gap-3">
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="h-9 rounded-xl border border-white/8 bg-white/5 px-3 text-sm text-white/70 focus:border-violet-500/40 focus:outline-none"
          >
            <option value="">All Types</option>
            {types.map((t) => <option key={t} value={t}>{typeLabel(t)}</option>)}
          </select>
          <div className="ml-auto">
            <Button icon={<RefreshCw size={16} />} loading={generating} onClick={generate}>
              Generate New
            </Button>
          </div>
        </div>

        {/* Recommendations */}
        {loading ? (
          <div className="space-y-3">
            {Array.from({ length: 4 }).map((_, i) => <div key={i} className="h-24 rounded-2xl shimmer" />)}
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <motion.div
              animate={{ scale: [1, 1.05, 1] }}
              transition={{ repeat: Infinity, duration: 3 }}
              className="mb-4 flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-600/30 to-purple-600/20 border border-violet-500/20"
            >
              <Sparkles className="h-10 w-10 text-violet-400" />
            </motion.div>
            <p className="text-base font-semibold text-white/60">No insights yet</p>
            <p className="text-sm text-white/30 mt-1 mb-4">Generate personalized AI recommendations based on your financial data</p>
            <Button loading={generating} onClick={generate} icon={<Sparkles size={16} />}>
              Generate Insights
            </Button>
          </div>
        ) : (
          <div className="space-y-3">
            <AnimatePresence>
              {filtered.map((rec, i) => {
                const cfg = typeConfig(rec.type);
                const isOpen = expanded === rec.id;
                return (
                  <motion.div
                    key={rec.id}
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.04 }}
                    className={`rounded-2xl border bg-gradient-to-br ${cfg.gradient} ${cfg.border} backdrop-blur-xl overflow-hidden`}
                  >
                    <button
                      className="w-full text-left p-5"
                      onClick={() => setExpanded(isOpen ? null : rec.id)}
                    >
                      <div className="flex items-start gap-3">
                        <div className="mt-0.5 shrink-0 text-white/70">{cfg.icon}</div>
                        <div className="flex-1 min-w-0">
                          <div className="flex flex-wrap items-center gap-2 mb-1">
                            <p className="text-sm font-semibold text-white">{rec.title}</p>
                            {rec.is_urgent && <Badge variant="danger">Urgent</Badge>}
                            <Badge variant={priorityVariant(rec.priority || "low")}>
                              {rec.priority || "low"}
                            </Badge>
                            <Badge variant="purple">{typeLabel(rec.type)}</Badge>
                          </div>
                          {!isOpen && (
                            <p className="text-xs text-white/50 line-clamp-2">{rec.message}</p>
                          )}
                          <div className="mt-2 flex items-center gap-2">
                            <span className="text-xs text-white/20">{typeLabel(rec.type)}</span>
                          </div>
                        </div>
                        <div className="text-white/30 shrink-0">
                          {isOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                        </div>
                      </div>
                    </button>

                    <AnimatePresence>
                      {isOpen && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: "auto", opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          className="border-t border-white/8 px-5 py-4"
                        >
                          <p className="text-sm text-white/70 leading-relaxed">{rec.message}</p>
                          {rec.supporting_data && Object.keys(rec.supporting_data).length > 0 && (
                            <div className="mt-3 grid grid-cols-2 gap-2">
                              {Object.entries(rec.supporting_data).slice(0, 4).map(([k, v]) => (
                                <div key={k} className="rounded-lg bg-white/5 px-3 py-2">
                                  <p className="text-xs text-white/30 capitalize">{k.replace(/_/g, " ")}</p>
                                  <p className="text-sm font-medium text-white mt-0.5">{String(v)}</p>
                                </div>
                              ))}
                            </div>
                          )}
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </motion.div>
                );
              })}
            </AnimatePresence>
          </div>
        )}
      </div>
    </div>
  );
}
