"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import clsx from "clsx";
import ReactMarkdown from "react-markdown";
import { api } from "@/lib/api-client";
import type { ReportDetail, ReportFile } from "@/lib/types";

export default function ReportDetailPage() {
  const { locale, reportId } = useParams();
  const [report, setReport] = useState<ReportDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(["executive_summary"]));
  const [shareUrl, setShareUrl] = useState<string | null>(null);
  const isAr = locale === "ar";

  useEffect(() => {
    api
      .get<ReportDetail>(`/reports/${reportId}`)
      .then(setReport)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [reportId]);

  const toggleSection = (key: string) => {
    setExpandedSections((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const createShareLink = async () => {
    try {
      const result = await api.post<{ share_url: string }>(`/exports/reports/${reportId}/share`, {
        file_type: "pdf",
      });
      setShareUrl(window.location.origin + result.share_url);
    } catch {
      // Handle error
    }
  };

  if (loading) {
    return (
      <div className="p-8 text-center py-20 text-tam-soft-carbon">
        {isAr ? "جاري تحميل التقرير..." : "Loading report..."}
      </div>
    );
  }

  if (!report) {
    return (
      <div className="p-8 text-center py-20 text-red-500">
        {isAr ? "التقرير غير موجود" : "Report not found"}
      </div>
    );
  }

  const sortedSections = [...report.sections].sort((a, b) => a.sort_order - b.sort_order);

  return (
    <div className="p-8 max-w-5xl mx-auto">
      {/* Header */}
      <div className="bg-gradient-to-r from-tam-deep-blue to-[#2A3A70] rounded-xl p-6 text-white mb-6">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold">{report.company_name}</h1>
            <div className="flex items-center gap-3 mt-2">
              <span className="text-sm bg-white/10 px-3 py-1 rounded-full">{report.ticker}</span>
              <span className="text-xs text-tam-soft-carbon">
                {new Date(report.created_at).toLocaleDateString(
                  locale === "ar" ? "ar-SA" : "en-US",
                  { year: "numeric", month: "long", day: "numeric" }
                )}
              </span>
              <span
                className={clsx(
                  "text-xs px-2 py-0.5 rounded-full",
                  report.status === "completed" ? "bg-green-500/20 text-green-300" : "bg-yellow-500/20 text-yellow-300"
                )}
              >
                {report.status}
              </span>
            </div>
          </div>
          <div className="text-right">
            <div className="text-[10px] uppercase tracking-widest text-tam-turquoise">TAM Capital</div>
            <div className="text-[10px] text-tam-soft-carbon mt-1">CMA Regulated</div>
          </div>
        </div>
      </div>

      {/* Download & Share buttons */}
      <div className="flex items-center gap-3 mb-6">
        {report.files.map((file: ReportFile) => (
          <a
            key={file.id}
            href={`/api/v1/exports/reports/${reportId}/files/${file.id}/download`}
            className="px-4 py-2 bg-white border border-slate-200 text-tam-deep-blue text-sm rounded-lg hover:bg-tam-light-bg transition-colors"
          >
            {file.file_type.toUpperCase()} ({(file.file_size / 1024).toFixed(0)} KB)
          </a>
        ))}

        <button
          onClick={createShareLink}
          className="px-4 py-2 bg-tam-turquoise text-white text-sm rounded-lg hover:bg-tam-light-blue transition-colors"
        >
          {isAr ? "مشاركة" : "Share"}
        </button>
      </div>

      {shareUrl && (
        <div className="mb-6 p-3 bg-green-50 border border-green-200 rounded-lg text-sm">
          <span className="text-green-700 font-medium">{isAr ? "رابط المشاركة:" : "Share link:"}</span>{" "}
          <code className="text-green-800 bg-green-100 px-2 py-0.5 rounded text-xs">{shareUrl}</code>
        </div>
      )}

      {/* Snapshot metrics */}
      {report.snapshot && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
          {[
            { label: isAr ? "السعر" : "Price", value: report.snapshot.current_price?.toFixed(2) },
            { label: isAr ? "مكرر الربحية" : "P/E", value: report.snapshot.pe_ratio?.toFixed(1) },
            { label: isAr ? "العائد" : "Div Yield", value: report.snapshot.dividend_yield ? `${(report.snapshot.dividend_yield * 100).toFixed(1)}%` : null },
            { label: isAr ? "التقييم" : "Rating", value: report.snapshot.rating },
          ].map(
            (metric) =>
              metric.value && (
                <div key={metric.label} className="bg-white border border-slate-200 rounded-lg p-3">
                  <div className="text-[10px] uppercase tracking-widest text-tam-soft-carbon">{metric.label}</div>
                  <div className="text-lg font-bold text-tam-deep-blue mt-1">{metric.value}</div>
                </div>
              )
          )}
        </div>
      )}

      {/* Report sections */}
      <div className="space-y-3 mb-8">
        {sortedSections.map((section) => (
          <div key={section.id} className="bg-white border border-slate-200 rounded-xl overflow-hidden">
            <button
              onClick={() => toggleSection(section.section_key)}
              className="w-full flex items-center justify-between px-5 py-4 text-left hover:bg-slate-50 transition-colors"
            >
              <span className="font-semibold text-tam-deep-blue text-sm">{section.title}</span>
              <span className="text-tam-soft-carbon">{expandedSections.has(section.section_key) ? "▼" : "▶"}</span>
            </button>
            {expandedSections.has(section.section_key) && (
              <div className="px-5 pb-5 prose prose-sm max-w-none text-tam-gray">
                <ReactMarkdown>{section.content}</ReactMarkdown>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Data sources */}
      {report.sources.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-xl p-5">
          <h3 className="font-semibold text-tam-deep-blue mb-3">
            {isAr ? "مصادر البيانات" : "Data Sources"} ({report.sources.length})
          </h3>
          <div className="space-y-2">
            {report.sources.map((source) => (
              <div key={source.id} className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <span
                    className={clsx(
                      "px-1.5 py-0.5 rounded text-[9px] font-medium",
                      source.is_realtime ? "bg-green-50 text-green-700" : "bg-yellow-50 text-yellow-700"
                    )}
                  >
                    {source.is_realtime ? (isAr ? "مباشر" : "Real-time") : `${isAr ? "متأخر" : "Delayed"} ${source.delay_minutes}min`}
                  </span>
                  <span className="text-tam-gray">{source.title}</span>
                </div>
                <span className="text-tam-soft-carbon">
                  {new Date(source.accessed_at).toLocaleTimeString()}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
