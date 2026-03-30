"use client";

import { useParams, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import clsx from "clsx";
import { api } from "@/lib/api-client";

interface ComparisonData {
  ticker: string;
  reports: Array<{ id: string; company_name: string; created_at: string }>;
  snapshots: Array<{
    current_price: number | null;
    pe_ratio: number | null;
    forward_pe: number | null;
    dividend_yield: number | null;
    rating: string | null;
    price_target: number | null;
    risk_level: string | null;
  }>;
  changes: {
    price_target_change?: number;
    price_change?: number;
    rating_change?: { from: string; to: string };
    new_risks?: string[];
    removed_risks?: string[];
  };
}

export default function CompareReportsPage() {
  const { locale } = useParams();
  const searchParams = useSearchParams();
  const ticker = searchParams.get("ticker") || "";
  const [data, setData] = useState<ComparisonData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const isAr = locale === "ar";

  useEffect(() => {
    if (!ticker) return;
    api
      .get<ComparisonData>(`/reports/compare/${ticker}`)
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [ticker]);

  if (!ticker) {
    return (
      <div className="p-8 text-center py-20 text-tam-soft-carbon">
        {isAr ? "يرجى تحديد رمز السهم" : "Please specify a ticker to compare"}
      </div>
    );
  }

  if (loading) {
    return (
      <div className="p-8 text-center py-20 text-tam-soft-carbon">
        {isAr ? "جاري تحميل المقارنة..." : "Loading comparison..."}
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-8 text-center py-20 text-red-500">
        {error || (isAr ? "خطأ في تحميل البيانات" : "Error loading data")}
      </div>
    );
  }

  const formatChange = (value: number | undefined) => {
    if (value === undefined) return null;
    const isPositive = value > 0;
    return (
      <span className={clsx("font-medium", isPositive ? "text-green-600" : "text-red-600")}>
        {isPositive ? "▲" : "▼"} {Math.abs(value).toFixed(2)}
      </span>
    );
  };

  const metrics = [
    { key: "current_price", label: isAr ? "السعر" : "Price" },
    { key: "pe_ratio", label: isAr ? "مكرر الربحية" : "P/E Ratio" },
    { key: "forward_pe", label: isAr ? "مكرر الربحية المستقبلي" : "Forward P/E" },
    { key: "dividend_yield", label: isAr ? "عائد التوزيعات" : "Dividend Yield", format: "pct" },
    { key: "price_target", label: isAr ? "السعر المستهدف" : "Price Target" },
    { key: "rating", label: isAr ? "التقييم" : "Rating" },
    { key: "risk_level", label: isAr ? "مستوى المخاطر" : "Risk Level" },
  ];

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-tam-deep-blue">
          {isAr ? "مقارنة التقارير" : "Report Comparison"} — {ticker}
        </h1>
        <p className="text-sm text-tam-gray mt-1">
          {isAr
            ? `مقارنة ${data.reports.length} تقارير على مر الزمن`
            : `Comparing ${data.reports.length} reports over time`}
        </p>
      </div>

      {/* Changes summary */}
      {Object.keys(data.changes).length > 0 && (
        <div className="bg-white border border-slate-200 rounded-xl p-5 mb-6">
          <h3 className="font-semibold text-tam-deep-blue mb-3">
            {isAr ? "التغييرات الرئيسية" : "Key Changes"}
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {data.changes.price_target_change !== undefined && (
              <div className="p-3 bg-slate-50 rounded-lg">
                <div className="text-[10px] uppercase tracking-widest text-tam-soft-carbon">
                  {isAr ? "السعر المستهدف" : "Price Target"}
                </div>
                <div className="text-lg mt-1">{formatChange(data.changes.price_target_change)}</div>
              </div>
            )}
            {data.changes.rating_change && (
              <div className="p-3 bg-slate-50 rounded-lg">
                <div className="text-[10px] uppercase tracking-widest text-tam-soft-carbon">
                  {isAr ? "تغيير التقييم" : "Rating Change"}
                </div>
                <div className="text-sm mt-1 text-tam-deep-blue font-medium">
                  {data.changes.rating_change.from} → {data.changes.rating_change.to}
                </div>
              </div>
            )}
            {data.changes.price_change !== undefined && (
              <div className="p-3 bg-slate-50 rounded-lg">
                <div className="text-[10px] uppercase tracking-widest text-tam-soft-carbon">
                  {isAr ? "تغير السعر" : "Price Change"}
                </div>
                <div className="text-lg mt-1">{formatChange(data.changes.price_change)}</div>
              </div>
            )}
          </div>

          {(data.changes.new_risks?.length ?? 0) > 0 && (
            <div className="mt-4">
              <div className="text-xs font-medium text-red-600 mb-1">
                {isAr ? "مخاطر جديدة:" : "New Risks:"}
              </div>
              <ul className="text-xs text-tam-gray space-y-1">
                {data.changes.new_risks?.map((risk, i) => (
                  <li key={i}>• {risk}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Comparison table */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-tam-deep-blue text-white">
              <th className="text-left px-4 py-3 font-medium">{isAr ? "المقياس" : "Metric"}</th>
              {data.reports.map((report, i) => (
                <th key={report.id} className="text-center px-4 py-3 font-medium">
                  {new Date(report.created_at).toLocaleDateString(
                    locale === "ar" ? "ar-SA" : "en-US",
                    { month: "short", day: "numeric", year: "numeric" }
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {metrics.map((metric, rowIdx) => (
              <tr
                key={metric.key}
                className={clsx(rowIdx % 2 === 0 ? "bg-tam-light-bg" : "bg-white")}
              >
                <td className="px-4 py-3 font-medium text-tam-deep-blue">{metric.label}</td>
                {data.snapshots.map((snap, i) => {
                  const val = (snap as Record<string, unknown>)[metric.key];
                  let display = "—";
                  if (val !== null && val !== undefined) {
                    if (metric.format === "pct" && typeof val === "number") {
                      display = `${(val * 100).toFixed(1)}%`;
                    } else if (typeof val === "number") {
                      display = val.toFixed(2);
                    } else {
                      display = String(val);
                    }
                  }
                  return (
                    <td key={i} className="text-center px-4 py-3 text-tam-gray">
                      {display}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
