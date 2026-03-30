"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import Link from "next/link";
import clsx from "clsx";
import { api } from "@/lib/api-client";
import type { Report } from "@/lib/types";

export default function ReportLibraryPage() {
  const { locale } = useParams();
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [tickerFilter, setTickerFilter] = useState("");
  const isAr = locale === "ar";

  useEffect(() => {
    const params: Record<string, string> = { limit: "50" };
    if (tickerFilter) params.ticker = tickerFilter;

    api
      .get<Report[]>("/reports", params)
      .then(setReports)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [tickerFilter]);

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-tam-deep-blue">
            {isAr ? "مكتبة التقارير" : "Report Library"}
          </h1>
          <p className="text-sm text-tam-gray mt-1">
            {isAr ? "جميع التقارير المُنشأة" : "All generated research reports"}
          </p>
        </div>

        <input
          type="text"
          placeholder={isAr ? "فلترة حسب الرمز..." : "Filter by ticker..."}
          value={tickerFilter}
          onChange={(e) => setTickerFilter(e.target.value.toUpperCase())}
          className="px-3 py-2 border border-slate-200 rounded-lg text-sm w-48 focus:outline-none focus:ring-2 focus:ring-tam-light-blue"
        />
      </div>

      {loading ? (
        <div className="text-center py-12 text-tam-soft-carbon text-sm">
          {isAr ? "جاري التحميل..." : "Loading..."}
        </div>
      ) : reports.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-xl border border-slate-200">
          <div className="text-4xl mb-3">📁</div>
          <div className="text-tam-gray font-medium">
            {isAr ? "لا توجد تقارير" : "No reports found"}
          </div>
          <Link
            href={`/${locale}/chat`}
            className="inline-block mt-4 px-4 py-2 bg-tam-deep-blue text-white text-sm rounded-lg hover:bg-tam-light-blue transition-colors"
          >
            {isAr ? "إنشاء تقرير" : "Generate a Report"}
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {reports.map((report) => (
            <Link
              key={report.id}
              href={`/${locale}/reports/${report.id}`}
              className="bg-white rounded-xl border border-slate-200 p-5 hover:shadow-lg transition-shadow"
            >
              <div className="flex items-start justify-between mb-3">
                <div>
                  <div className="font-semibold text-tam-deep-blue">{report.company_name}</div>
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-tam-light-bg text-tam-light-blue font-medium">
                    {report.ticker}
                  </span>
                </div>
                <span
                  className={clsx(
                    "text-[10px] px-2 py-0.5 rounded-full font-medium",
                    report.status === "completed" && "bg-green-50 text-green-700",
                    report.status === "running" && "bg-blue-50 text-blue-700",
                    report.status === "failed" && "bg-red-50 text-red-700",
                    report.status === "pending" && "bg-slate-50 text-slate-500"
                  )}
                >
                  {report.status}
                </span>
              </div>

              <div className="text-xs text-tam-soft-carbon">
                {new Date(report.created_at).toLocaleDateString(
                  locale === "ar" ? "ar-SA" : "en-US",
                  { year: "numeric", month: "long", day: "numeric" }
                )}
              </div>

              <div className="mt-3 flex items-center gap-2">
                <span className="text-[10px] px-2 py-0.5 rounded bg-slate-100 text-tam-gray">
                  {report.report_type}
                </span>
                <span className="text-[10px] text-tam-soft-carbon">{report.locale.toUpperCase()}</span>
              </div>
            </Link>
          ))}
        </div>
      )}

      {/* Compare link */}
      {reports.length >= 2 && tickerFilter && (
        <div className="mt-6 text-center">
          <Link
            href={`/${locale}/reports/compare?ticker=${tickerFilter}`}
            className="inline-flex items-center gap-2 px-4 py-2 bg-tam-turquoise text-white text-sm rounded-lg hover:bg-tam-light-blue transition-colors"
          >
            {isAr ? "مقارنة التقارير" : "Compare Reports"} ({reports.length})
          </Link>
        </div>
      )}
    </div>
  );
}
