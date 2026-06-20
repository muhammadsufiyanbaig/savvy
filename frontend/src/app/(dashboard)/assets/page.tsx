"use client";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { motion, AnimatePresence } from "framer-motion";
import {
  Plus, X, TrendingUp, TrendingDown, BarChart3,
  Building2, Coins, Landmark, Home, Gem, Bitcoin, Briefcase,
  ChevronDown, ChevronUp, Edit2, Trash2,
} from "lucide-react";
import {
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from "recharts";
import Navbar from "@/components/layout/Navbar";
import GlassCard from "@/components/ui/GlassCard";
import Button from "@/components/ui/Button";
import Input from "@/components/ui/Input";
import Badge from "@/components/ui/Badge";
import { assetApi } from "@/lib/api";
import { formatCurrency } from "@/lib/utils";
import toast from "react-hot-toast";

// ── Types ─────────────────────────────────────────────────────────────────────

const CATEGORIES = [
  { value: "equities",         label: "Equities (Stocks)",          icon: TrendingUp,  color: "#7c3aed" },
  { value: "fixed_income",     label: "Fixed Income (Bonds)",       icon: Landmark,    color: "#0891b2" },
  { value: "cash_equivalents", label: "Cash & Cash Equivalents",    icon: Coins,       color: "#059669" },
  { value: "real_estate",      label: "Real Estate",                icon: Home,        color: "#d97706" },
  { value: "commodities",      label: "Commodities",                icon: Gem,         color: "#db2777" },
  { value: "alternatives",     label: "Alternative Investments",    icon: Briefcase,   color: "#7c3aed" },
  { value: "crypto",           label: "Cryptocurrencies",           icon: Bitcoin,     color: "#ea580c" },
] as const;

const CATEGORY_PLACEHOLDER: Record<string, string> = {
  equities:         "NASDAQ, PSX, LSE",
  fixed_income:     "SBP, Treasury, NSS",
  cash_equivalents: "HBL, Meezan, MCB",
  real_estate:      "DHA Phase 5, Gulshan",
  commodities:      "Home Safe, Bank Vault, Goldfield",
  alternatives:     "Fund name, Gallery",
  crypto:           "Binance, Ledger, Trust Wallet",
};

const DETAIL_PLACEHOLDER: Record<string, string> = {
  equities:         "Account no. or brokerage name",
  fixed_income:     "Bond series, maturity date",
  cash_equivalents: "Account no. XXXX-1234",
  real_estate:      "Plot no. / property address",
  commodities:      "Locker no. / vault ID",
  alternatives:     "Fund ID / certificate no.",
  crypto:           "Wallet address (optional)",
};

const PIE_COLORS = ["#7c3aed","#0891b2","#059669","#d97706","#db2777","#ea580c","#6366f1"];

interface Asset {
  id: number;
  name: string;
  category: string;
  ticker_symbol?: string;
  currency: string;
  purchase_date: string;
  quantity: number;
  purchase_price_per_unit: number;
  current_price_per_unit: number;
  location?: string;
  location_detail?: string;
  notes?: string;
  is_active: boolean;
  purchase_value: number;
  current_value: number;
  gain_loss: number;
  gain_loss_pct: number;
}

interface Analytics {
  total_current_value: number;
  total_purchase_value: number;
  total_gain_loss: number;
  total_gain_loss_pct: number;
  total_assets: number;
  active_assets: number;
  by_category: {
    category: string; label: string; count: number;
    current_value: number; purchase_value: number;
    gain_loss: number; gain_loss_pct: number;
    percentage_of_portfolio: number;
  }[];
  yearly_growth: {
    year: number; total_value: number; total_invested: number;
    gain_loss: number; gain_loss_pct: number;
  }[];
  top_performer?: { id: number; name: string; gain_loss_pct: number };
  worst_performer?: { id: number; name: string; gain_loss_pct: number };
}

// ── Schema ────────────────────────────────────────────────────────────────────

const schema = z.object({
  name: z.string().min(1, "Required"),
  category: z.string().min(1, "Required"),
  ticker_symbol: z.string().optional(),
  currency: z.string().default("USD"),
  purchase_date: z.string().min(1, "Required"),
  quantity: z.coerce.number().positive("Must be > 0"),
  purchase_price_per_unit: z.coerce.number().min(0),
  current_price_per_unit: z.coerce.number().min(0),
  location: z.string().optional(),
  location_detail: z.string().optional(),
  notes: z.string().optional(),
});
type FormData = z.infer<typeof schema>;

// ── Helpers ───────────────────────────────────────────────────────────────────

function getCatMeta(cat: string) {
  return CATEGORIES.find((c) => c.value === cat) ?? CATEGORIES[0];
}

function GainBadge({ pct }: { pct: number }) {
  if (pct > 0) return (
    <span className="flex items-center gap-1 text-emerald-400 text-xs font-medium">
      <TrendingUp size={12} />+{pct.toFixed(2)}%
    </span>
  );
  if (pct < 0) return (
    <span className="flex items-center gap-1 text-rose-400 text-xs font-medium">
      <TrendingDown size={12} />{pct.toFixed(2)}%
    </span>
  );
  return <span className="text-white/40 text-xs">0.00%</span>;
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function AssetsPage() {
  const [assets, setAssets]       = useState<Asset[]>([]);
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [loading, setLoading]     = useState(true);
  const [showForm, setShowForm]   = useState(false);
  const [editing, setEditing]     = useState<Asset | null>(null);
  const [saving, setSaving]       = useState(false);
  const [activeTab, setActiveTab] = useState<"list" | "analytics">("list");
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const { register, handleSubmit, reset, watch, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { currency: "USD" },
  });
  const selectedCategory = watch("category");

  const load = async () => {
    try {
      const [listRes, analyticsRes] = await Promise.allSettled([
        assetApi.list(),
        assetApi.analytics(),
      ]);
      if (listRes.status === "fulfilled") setAssets(listRes.value.data.assets ?? []);
      if (analyticsRes.status === "fulfilled") setAnalytics(analyticsRes.value.data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const openCreate = () => {
    setEditing(null);
    reset({ currency: "USD" });
    setShowForm(true);
  };

  const openEdit = (asset: Asset) => {
    setEditing(asset);
    reset({
      name: asset.name,
      category: asset.category,
      ticker_symbol: asset.ticker_symbol ?? "",
      currency: asset.currency,
      purchase_date: asset.purchase_date,
      quantity: asset.quantity,
      purchase_price_per_unit: asset.purchase_price_per_unit,
      current_price_per_unit: asset.current_price_per_unit,
      location: asset.location ?? "",
      location_detail: asset.location_detail ?? "",
      notes: asset.notes ?? "",
    });
    setShowForm(true);
  };

  const onSubmit = async (data: FormData) => {
    setSaving(true);
    try {
      if (editing) {
        await assetApi.update(editing.id, data);
        toast.success("Asset updated!");
      } else {
        await assetApi.create(data);
        toast.success("Asset added!");
      }
      setShowForm(false);
      load();
    } catch { toast.error("Failed to save asset"); }
    finally { setSaving(false); }
  };

  const onDelete = async (id: number) => {
    if (!confirm("Delete this asset?")) return;
    try {
      await assetApi.delete(id);
      toast.success("Asset deleted");
      load();
    } catch { toast.error("Failed to delete"); }
  };

  // ── Summary cards data ──────────────────────────────────────────────────────
  const summaryCards = analytics ? [
    {
      label: "Portfolio Value",
      value: formatCurrency(analytics.total_current_value),
      sub: `Invested: ${formatCurrency(analytics.total_purchase_value)}`,
      color: "text-violet-400",
    },
    {
      label: "Total Gain / Loss",
      value: `${analytics.total_gain_loss >= 0 ? "+" : ""}${formatCurrency(analytics.total_gain_loss)}`,
      sub: `${analytics.total_gain_loss_pct >= 0 ? "+" : ""}${analytics.total_gain_loss_pct.toFixed(2)}% overall`,
      color: analytics.total_gain_loss >= 0 ? "text-emerald-400" : "text-rose-400",
    },
    {
      label: "Active Assets",
      value: String(analytics.active_assets),
      sub: `${analytics.total_assets} total`,
      color: "text-cyan-400",
    },
    {
      label: "Best Performer",
      value: analytics.top_performer ? `+${analytics.top_performer.gain_loss_pct.toFixed(1)}%` : "—",
      sub: analytics.top_performer?.name ?? "No assets yet",
      color: "text-emerald-400",
    },
  ] : [];

  // ── Render ──────────────────────────────────────────────────────────────────
  return (
    <div className="flex flex-col h-full">
      <Navbar title="Assets" subtitle="Track your investment portfolio" />

      <div className="flex-1 overflow-y-auto p-6 space-y-6">

        {/* Summary Cards */}
        {analytics && (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {summaryCards.map((c, i) => (
              <GlassCard key={i} className="p-4" hover={false}>
                <p className="text-xs text-white/40 mb-1">{c.label}</p>
                <p className={`text-xl font-bold ${c.color}`}>{c.value}</p>
                <p className="text-xs text-white/30 mt-0.5">{c.sub}</p>
              </GlassCard>
            ))}
          </div>
        )}

        {/* Tabs + Add button */}
        <div className="flex items-center justify-between">
          <div className="flex gap-1 rounded-xl bg-white/5 p-1">
            {(["list", "analytics"] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-all capitalize ${
                  activeTab === tab
                    ? "bg-violet-600 text-white"
                    : "text-white/40 hover:text-white"
                }`}
              >
                {tab}
              </button>
            ))}
          </div>
          <Button icon={<Plus size={14} />} onClick={openCreate} size="sm">
            Add Asset
          </Button>
        </div>

        {/* ── LIST TAB ──────────────────────────────────────────────────────── */}
        {activeTab === "list" && (
          <div className="space-y-3">
            {loading ? (
              Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="h-20 rounded-2xl bg-white/5 animate-pulse" />
              ))
            ) : assets.length === 0 ? (
              <GlassCard className="p-12 text-center" hover={false}>
                <BarChart3 size={40} className="mx-auto text-white/20 mb-3" />
                <p className="text-white/40 text-sm">No assets yet. Add your first investment.</p>
              </GlassCard>
            ) : (
              assets.map((asset) => {
                const meta = getCatMeta(asset.category);
                const Icon = meta.icon;
                const expanded = expandedId === asset.id;
                return (
                  <GlassCard key={asset.id} className="overflow-hidden" hover={false}>
                    {/* Row */}
                    <div
                      className="flex items-center gap-4 p-4 cursor-pointer"
                      onClick={() => setExpandedId(expanded ? null : asset.id)}
                    >
                      <div
                        className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl"
                        style={{ backgroundColor: `${meta.color}22` }}
                      >
                        <Icon size={18} style={{ color: meta.color }} />
                      </div>

                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <p className="text-sm font-semibold text-white truncate">{asset.name}</p>
                          {asset.ticker_symbol && (
                            <span className="text-xs text-white/30 font-mono">{asset.ticker_symbol}</span>
                          )}
                          {!asset.is_active && (
                            <Badge variant="danger">Closed</Badge>
                          )}
                        </div>
                        <p className="text-xs text-white/40">{meta.label}</p>
                      </div>

                      <div className="text-right shrink-0">
                        <p className="text-sm font-bold text-white">
                          {formatCurrency(asset.current_value)}
                        </p>
                        <GainBadge pct={asset.gain_loss_pct} />
                      </div>

                      <div className="text-white/30">
                        {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                      </div>
                    </div>

                    {/* Expanded detail */}
                    <AnimatePresence>
                      {expanded && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: "auto", opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          className="overflow-hidden border-t border-white/8"
                        >
                          <div className="p-4 space-y-4">
                            {/* Stats grid */}
                            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                              {[
                                { label: "Quantity",       value: asset.quantity },
                                { label: "Buy Price",      value: formatCurrency(asset.purchase_price_per_unit) },
                                { label: "Current Price",  value: formatCurrency(asset.current_price_per_unit) },
                                { label: "Invested",       value: formatCurrency(asset.purchase_value) },
                                { label: "Current Value",  value: formatCurrency(asset.current_value) },
                                { label: "Gain / Loss",    value: `${asset.gain_loss >= 0 ? "+" : ""}${formatCurrency(asset.gain_loss)}` },
                                { label: "Purchase Date",  value: asset.purchase_date },
                                { label: "Currency",       value: asset.currency },
                              ].map(({ label, value }) => (
                                <div key={label} className="rounded-xl bg-white/5 p-3">
                                  <p className="text-xs text-white/40 mb-0.5">{label}</p>
                                  <p className="text-sm font-medium text-white">{value}</p>
                                </div>
                              ))}
                            </div>

                            {/* Location */}
                            {(asset.location || asset.location_detail) && (
                              <div className="rounded-xl bg-white/5 p-3 space-y-1">
                                <p className="text-xs text-white/40">Location</p>
                                {asset.location && (
                                  <p className="text-sm text-white font-medium">{asset.location}</p>
                                )}
                                {asset.location_detail && (
                                  <p className="text-xs text-white/50 font-mono">{asset.location_detail}</p>
                                )}
                              </div>
                            )}

                            {asset.notes && (
                              <p className="text-xs text-white/40 italic">{asset.notes}</p>
                            )}

                            {/* Actions */}
                            <div className="flex gap-2">
                              <Button
                                size="sm"
                                variant="secondary"
                                icon={<Edit2 size={12} />}
                                onClick={() => openEdit(asset)}
                              >Edit</Button>
                              <Button
                                size="sm"
                                variant="danger"
                                icon={<Trash2 size={12} />}
                                onClick={() => onDelete(asset.id)}
                              >Delete</Button>
                            </div>
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </GlassCard>
                );
              })
            )}
          </div>
        )}

        {/* ── ANALYTICS TAB ─────────────────────────────────────────────────── */}
        {activeTab === "analytics" && analytics && (
          <div className="space-y-6">

            {/* Portfolio Allocation Pie */}
            <GlassCard className="p-6" hover={false}>
              <h3 className="text-sm font-semibold text-white mb-4">Portfolio Allocation</h3>
              <div className="flex flex-col lg:flex-row gap-6 items-center">
                <ResponsiveContainer width={220} height={220}>
                  <PieChart>
                    <Pie
                      data={analytics.by_category}
                      dataKey="current_value"
                      nameKey="label"
                      cx="50%" cy="50%"
                      innerRadius={60} outerRadius={90}
                      paddingAngle={3}
                    >
                      {analytics.by_category.map((_, i) => (
                        <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip
                      formatter={(v: number) => formatCurrency(v)}
                      contentStyle={{ background: "#1e1b2e", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 12 }}
                    />
                  </PieChart>
                </ResponsiveContainer>

                <div className="flex-1 space-y-2 w-full">
                  {analytics.by_category.map((cat, i) => (
                    <div key={cat.category}>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs text-white/60">{cat.label}</span>
                        <div className="flex items-center gap-3">
                          <span className="text-xs text-white/40">{cat.percentage_of_portfolio.toFixed(1)}%</span>
                          <GainBadge pct={cat.gain_loss_pct} />
                          <span className="text-xs font-medium text-white">{formatCurrency(cat.current_value)}</span>
                        </div>
                      </div>
                      <div className="h-1.5 rounded-full bg-white/8 overflow-hidden">
                        <div
                          className="h-full rounded-full transition-all"
                          style={{
                            width: `${cat.percentage_of_portfolio}%`,
                            backgroundColor: PIE_COLORS[i % PIE_COLORS.length],
                          }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </GlassCard>

            {/* Yearly Growth Chart */}
            {analytics.yearly_growth.length > 0 && (
              <GlassCard className="p-6" hover={false}>
                <h3 className="text-sm font-semibold text-white mb-4">Yearly Portfolio Growth</h3>
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={analytics.yearly_growth} barGap={4}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                    <XAxis dataKey="year" tick={{ fill: "rgba(255,255,255,0.4)", fontSize: 12 }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fill: "rgba(255,255,255,0.4)", fontSize: 11 }} axisLine={false} tickLine={false}
                      tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} />
                    <Tooltip
                      contentStyle={{ background: "#1e1b2e", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 12 }}
                      formatter={(v: number, name: string) => [formatCurrency(v), name === "total_invested" ? "Invested" : "Portfolio Value"]}
                    />
                    <Legend
                      formatter={(v) => v === "total_invested" ? "Invested" : "Portfolio Value"}
                      wrapperStyle={{ fontSize: 12, color: "rgba(255,255,255,0.5)" }}
                    />
                    <Bar dataKey="total_invested" fill="rgba(124,58,237,0.3)" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="total_value"    fill="#7c3aed"             radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </GlassCard>
            )}

            {/* Gain/Loss trend line */}
            {analytics.yearly_growth.length > 1 && (
              <GlassCard className="p-6" hover={false}>
                <h3 className="text-sm font-semibold text-white mb-4">Gain / Loss Over Years</h3>
                <ResponsiveContainer width="100%" height={200}>
                  <AreaChart data={analytics.yearly_growth}>
                    <defs>
                      <linearGradient id="glGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#10b981" stopOpacity={0.3} />
                        <stop offset="100%" stopColor="#10b981" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                    <XAxis dataKey="year" tick={{ fill: "rgba(255,255,255,0.4)", fontSize: 12 }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fill: "rgba(255,255,255,0.4)", fontSize: 11 }} axisLine={false} tickLine={false}
                      tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} />
                    <Tooltip
                      contentStyle={{ background: "#1e1b2e", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 12 }}
                      formatter={(v: number) => [formatCurrency(v), "Gain / Loss"]}
                    />
                    <Area type="monotone" dataKey="gain_loss" stroke="#10b981" fill="url(#glGrad)" strokeWidth={2} dot={false} />
                  </AreaChart>
                </ResponsiveContainer>
              </GlassCard>
            )}

            {/* Per-category breakdown table */}
            <GlassCard className="p-6 overflow-x-auto" hover={false}>
              <h3 className="text-sm font-semibold text-white mb-4">Category Breakdown</h3>
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-xs text-white/40 border-b border-white/8">
                    <th className="pb-2 text-left font-medium">Category</th>
                    <th className="pb-2 text-right font-medium">Assets</th>
                    <th className="pb-2 text-right font-medium">Invested</th>
                    <th className="pb-2 text-right font-medium">Current</th>
                    <th className="pb-2 text-right font-medium">Gain/Loss</th>
                    <th className="pb-2 text-right font-medium">Return</th>
                  </tr>
                </thead>
                <tbody>
                  {analytics.by_category.map((cat) => (
                    <tr key={cat.category} className="border-b border-white/5 hover:bg-white/3 transition-colors">
                      <td className="py-2.5 text-white font-medium">{cat.label}</td>
                      <td className="py-2.5 text-right text-white/50">{cat.count}</td>
                      <td className="py-2.5 text-right text-white/70">{formatCurrency(cat.purchase_value)}</td>
                      <td className="py-2.5 text-right text-white font-medium">{formatCurrency(cat.current_value)}</td>
                      <td className={`py-2.5 text-right font-medium ${cat.gain_loss >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                        {cat.gain_loss >= 0 ? "+" : ""}{formatCurrency(cat.gain_loss)}
                      </td>
                      <td className="py-2.5 text-right">
                        <GainBadge pct={cat.gain_loss_pct} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </GlassCard>
          </div>
        )}
      </div>

      {/* ── Add/Edit Form Modal ────────────────────────────────────────────── */}
      <AnimatePresence>
        {showForm && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
            onClick={(e) => e.target === e.currentTarget && setShowForm(false)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="w-full max-w-2xl rounded-2xl border border-white/10 bg-[#1a1528] shadow-2xl max-h-[90vh] overflow-y-auto"
            >
              <div className="flex items-center justify-between p-6 border-b border-white/8">
                <h2 className="text-base font-semibold text-white">
                  {editing ? "Edit Asset" : "Add New Asset"}
                </h2>
                <button onClick={() => setShowForm(false)} className="text-white/30 hover:text-white">
                  <X size={18} />
                </button>
              </div>

              <form onSubmit={handleSubmit(onSubmit)} className="p-6 space-y-5">
                {/* Category selector */}
                <div>
                  <label className="block text-xs font-medium text-white/60 mb-2">Category *</label>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                    {CATEGORIES.map(({ value, label, icon: Icon, color }) => {
                      const selected = selectedCategory === value;
                      return (
                        <label key={value} className="cursor-pointer">
                          <input type="radio" value={value} {...register("category")} className="sr-only" />
                          <div
                            className={`rounded-xl border p-2.5 text-center transition-all ${
                              selected
                                ? "border-violet-500/50 bg-violet-600/15"
                                : "border-white/8 hover:border-white/20"
                            }`}
                          >
                            <Icon size={18} className="mx-auto mb-1" style={{ color: selected ? color : "rgba(255,255,255,0.3)" }} />
                            <p className="text-[10px] leading-tight text-white/60">{label}</p>
                          </div>
                        </label>
                      );
                    })}
                  </div>
                  {errors.category && (
                    <p className="text-xs text-rose-400 mt-1">{errors.category.message}</p>
                  )}
                </div>

                {/* Name + Ticker */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div className="sm:col-span-2">
                    <Input label="Asset Name *" error={errors.name?.message} {...register("name")}
                      placeholder="Apple Inc., Gold 24K, DHA Plot..." />
                  </div>
                  <Input label="Ticker / Symbol" {...register("ticker_symbol")}
                    placeholder="AAPL, BTC, XAU" />
                </div>

                {/* Purchase info */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                  <Input label="Purchase Date *" type="date" error={errors.purchase_date?.message}
                    {...register("purchase_date")} />
                  <Input label="Quantity *" type="number" step="any" error={errors.quantity?.message}
                    {...register("quantity")} placeholder="1" />
                  <Input label="Buy Price / Unit *" type="number" step="any"
                    error={errors.purchase_price_per_unit?.message}
                    {...register("purchase_price_per_unit")} placeholder="0.00" />
                  <Input label="Current Price / Unit *" type="number" step="any"
                    error={errors.current_price_per_unit?.message}
                    {...register("current_price_per_unit")} placeholder="0.00" />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <Input label="Currency" {...register("currency")} placeholder="USD" />
                  <div />
                </div>

                {/* Location */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <Input
                    label="Where is it held?"
                    {...register("location")}
                    placeholder={selectedCategory ? CATEGORY_PLACEHOLDER[selectedCategory] : "Bank, Exchange, Location..."}
                  />
                  <Input
                    label="Account / Address / Detail"
                    {...register("location_detail")}
                    placeholder={selectedCategory ? DETAIL_PLACEHOLDER[selectedCategory] : "Account number, address..."}
                  />
                </div>

                <Input label="Notes (optional)" {...register("notes")} placeholder="Any additional notes..." />

                {/* Live value preview */}
                {watch("quantity") && watch("purchase_price_per_unit") && watch("current_price_per_unit") && (
                  <div className="rounded-xl bg-white/5 p-4 grid grid-cols-3 gap-4 text-center">
                    {(() => {
                      const qty = Number(watch("quantity")) || 0;
                      const buy = Number(watch("purchase_price_per_unit")) || 0;
                      const cur = Number(watch("current_price_per_unit")) || 0;
                      const invested = qty * buy;
                      const current  = qty * cur;
                      const gl       = current - invested;
                      const glPct    = invested ? (gl / invested * 100) : 0;
                      return (
                        <>
                          <div>
                            <p className="text-xs text-white/40">Invested</p>
                            <p className="text-sm font-bold text-white">{formatCurrency(invested)}</p>
                          </div>
                          <div>
                            <p className="text-xs text-white/40">Current Value</p>
                            <p className="text-sm font-bold text-violet-400">{formatCurrency(current)}</p>
                          </div>
                          <div>
                            <p className="text-xs text-white/40">Gain / Loss</p>
                            <p className={`text-sm font-bold ${gl >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                              {gl >= 0 ? "+" : ""}{formatCurrency(gl)} ({glPct >= 0 ? "+" : ""}{glPct.toFixed(1)}%)
                            </p>
                          </div>
                        </>
                      );
                    })()}
                  </div>
                )}

                <div className="flex justify-end gap-3 pt-2">
                  <Button type="button" variant="secondary" onClick={() => setShowForm(false)}>Cancel</Button>
                  <Button type="submit" loading={saving}>
                    {editing ? "Update Asset" : "Add Asset"}
                  </Button>
                </div>
              </form>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
