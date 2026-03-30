"use client";

import { useState } from "react";
import { useParams, usePathname, useRouter } from "next/navigation";
import Link from "next/link";
import clsx from "clsx";

const NAV_ITEMS = [
  { href: "", label: "Dashboard", labelAr: "لوحة التحكم", icon: "📊" },
  { href: "/chat", label: "Research Chat", labelAr: "محادثة البحث", icon: "💬" },
  { href: "/reports", label: "Report Library", labelAr: "مكتبة التقارير", icon: "📁" },
];

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const params = useParams();
  const pathname = usePathname();
  const router = useRouter();
  const locale = (params.locale as string) || "en";
  const isRtl = locale === "ar";
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const toggleLocale = () => {
    const newLocale = locale === "en" ? "ar" : "en";
    const newPath = pathname.replace(`/${locale}`, `/${newLocale}`);
    router.push(newPath);
  };

  return (
    <div dir={isRtl ? "rtl" : "ltr"} className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside
        className={clsx(
          "flex flex-col bg-tam-dark-carbon text-white transition-all duration-300",
          sidebarOpen ? "w-64" : "w-16"
        )}
      >
        {/* Logo */}
        <div className="flex items-center gap-3 px-4 py-6 border-b border-white/10">
          <div className="w-8 h-8 rounded bg-tam-turquoise flex items-center justify-center font-bold text-tam-dark-carbon text-sm shrink-0">
            T
          </div>
          {sidebarOpen && (
            <div>
              <div className="font-bold text-sm tracking-wide">TAM Capital</div>
              <div className="text-[10px] text-tam-turquoise uppercase tracking-widest">
                {locale === "ar" ? "منصة البحث" : "Research Platform"}
              </div>
            </div>
          )}
        </div>

        {/* Navigation */}
        <nav className="flex-1 py-4 space-y-1 px-2">
          {NAV_ITEMS.map((item) => {
            const href = `/${locale}${item.href}`;
            const isActive =
              pathname === href || (item.href !== "" && pathname.startsWith(href));
            return (
              <Link
                key={item.href}
                href={href}
                className={clsx(
                  "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors",
                  isActive
                    ? "bg-tam-deep-blue text-white"
                    : "text-tam-soft-carbon hover:bg-white/5 hover:text-white"
                )}
              >
                <span className="text-lg">{item.icon}</span>
                {sidebarOpen && (
                  <span>{locale === "ar" ? item.labelAr : item.label}</span>
                )}
              </Link>
            );
          })}
        </nav>

        {/* Quick Reports */}
        {sidebarOpen && (
          <div className="px-4 pb-4">
            <div className="text-[10px] uppercase tracking-widest text-tam-soft-carbon mb-2">
              {locale === "ar" ? "تقارير سريعة" : "Quick Reports"}
            </div>
            <div className="grid grid-cols-2 gap-1.5">
              {[
                { label: "Aramco", ticker: "2222" },
                { label: "Al Rajhi", ticker: "1120" },
                { label: "SABIC AN", ticker: "2020" },
                { label: "STC", ticker: "7010" },
              ].map((stock) => (
                <Link
                  key={stock.ticker}
                  href={`/${locale}/chat?prompt=Full+report+on+${stock.label}+(${stock.ticker})`}
                  className="text-[11px] px-2 py-1.5 rounded bg-white/5 text-tam-soft-carbon hover:bg-tam-deep-blue hover:text-white transition-colors text-center"
                >
                  {stock.label}
                </Link>
              ))}
            </div>
          </div>
        )}

        {/* Footer controls */}
        <div className="px-4 py-3 border-t border-white/10 space-y-2">
          <button
            onClick={toggleLocale}
            className="w-full text-xs px-3 py-1.5 rounded bg-white/5 text-tam-soft-carbon hover:bg-white/10 transition-colors"
          >
            {locale === "ar" ? "English" : "العربية"}
          </button>
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="w-full text-xs px-3 py-1.5 rounded bg-white/5 text-tam-soft-carbon hover:bg-white/10 transition-colors"
          >
            {sidebarOpen ? (isRtl ? "▶" : "◀") : isRtl ? "◀" : "▶"}
          </button>
          <div className="text-[9px] text-center text-white/30 pt-1">
            TAM Capital | CMA Regulated
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">{children}</main>
    </div>
  );
}
