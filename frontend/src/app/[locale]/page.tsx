"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import Link from "next/link";
import clsx from "clsx";
import { api } from "@/lib/api-client";
import type { Report } from "@/lib/types";

export default function DashboardPage() {
  const { locale } = useParams();
  const [recentReports, setRecentReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const isAr = locale === "ar";

  useEffect(() => {
    api
      .get<Report[]>("/reports", { limit: "6" })
      .then(setRecentReports)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-tam-deep-blue">
          {isAr ? "لوحة التحكم" : "Dashboard"}
        </h1>
        <p className="text-sm text-tam-gray mt-1">
          {isAr
            ? "أبحاث الاستثمار المؤسسي المدعومة بالذكاء الاصطناعي"
            : "Institutional-grade AI-powered investment research"}
        </p>
      </div>

      {/* Feature cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <Link
          href={`/${locale}/chat`}
          className="group rounded-xl bg-gradient-to-br from-tam-deep-blue to-[#2A3A70] p-6 text-white hover:shadow-xl transition-shadow"
        >
          <div className="text-[10px] uppercase tracking-widest text-tam-turquoise mb-2">
            {isAr ? "تحليل الأسهم" : "Equity Analysis"}
          </div>
          <div className="font-semibold mb-2">
            {isAr ? "تقارير بحثية كاملة" : "Full Research Reports"}
          </div>
          <div className="text-xs text-tam-soft-carbon">
            {isAr
              ? "تحليل أساسي، فني، أرباح، توزيعات، مخاطر، وأكثر"
              : "Goldman-style fundamentals, JPMorgan earnings, Morgan Stanley technicals"}
          </div>
        </Link>

        <Link
          href={`/${locale}/reports`}
          className="group rounded-xl bg-gradient-to-br from-tam-deep-blue to-[#2A3A70] p-6 text-white hover:shadow-xl transition-shadow"
        >
          <div className="text-[10px] uppercase tracking-widest text-tam-turquoise mb-2">
            {isAr ? "مكتبة التقارير" : "Report Library"}
          </div>
          <div className="font-semibold mb-2">
            {isAr ? "جميع التقارير والمقارنات" : "Past Reports & Comparison"}
          </div>
          <div className="text-xs text-tam-soft-carbon">
            {isAr
              ? "عرض ومقارنة التقارير على مر الزمن"
              : "View, compare, and share reports over time"}
          </div>
        </Link>

        <div className="rounded-xl bg-gradient-to-br from-tam-deep-blue to-[#2A3A70] p-6 text-white">
          <div className="text-[10px] uppercase tracking-widest text-tam-turquoise mb-2">
            {isAr ? "التسليمات" : "Deliverables"}
          </div>
          <div className="font-semibold mb-2">
            {isAr ? "تقارير بعلامة TAM التجارية" : "TAM-Branded Reports"}
          </div>
          <div className="text-xs text-tam-soft-carbon">
            {isAr
              ? "وورد، PDF، باوربوينت على ورق TAM Capital الرسمي"
              : "Word, PDF & PowerPoint on TAM Capital letterhead"}
          </div>
        </div>
      </div>

      {/* Recent Reports */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-tam-deep-blue">
            {isAr ? "التقارير الأخيرة" : "Recent Reports"}
          </h2>
          <Link href={`/${locale}/reports`} className="text-xs text-tam-light-blue hover:underline">
            {isAr ? "عرض الكل" : "View all"}
          </Link>
        </div>

        {loading ? (
          <div className="text-center py-12 text-tam-soft-carbon text-sm">
            {isAr ? "جاري التحميل..." : "Loading..."}
          </div>
        ) : recentReports.length === 0 ? (
          <div className="text-center py-12 bg-white rounded-xl border border-slate-200">
            <div className="text-4xl mb-3">📊</div>
            <div className="text-tam-gray font-medium">
              {isAr ? "لا توجد تقارير بعد" : "No reports yet"}
            </div>
            <div className="text-sm text-tam-soft-carbon mt-1">
              {isAr
                ? "ابدأ بطلب تحليل من محادثة البحث"
                : "Start by requesting an analysis from Research Chat"}
            </div>
            <Link
              href={`/${locale}/chat`}
              className="inline-block mt-4 px-4 py-2 bg-tam-deep-blue text-white text-sm rounded-lg hover:bg-tam-light-blue transition-colors"
            >
              {isAr ? "بدء البحث" : "Start Research"}
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {recentReports.map((report) => (
              <Link
                key={report.id}
                href={`/${locale}/reports/${report.id}`}
                className="bg-white rounded-xl border border-slate-200 p-4 hover:shadow-md transition-shadow"
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="font-semibold text-tam-deep-blue">{report.company_name}</span>
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-tam-light-bg text-tam-light-blue font-medium">
                    {report.ticker}
                  </span>
                </div>
                <div className="text-xs text-tam-soft-carbon">
                  {new Date(report.created_at).toLocaleDateString(
                    locale === "ar" ? "ar-SA" : "en-US",
                    { year: "numeric", month: "short", day: "numeric" }
                  )}
                </div>
                <div className="mt-2">
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
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
