import type { Metadata } from "next";
import "@/styles/globals.css";

export const metadata: Metadata = {
  title: "TAM Capital — Research & Reporting Platform",
  description: "Institutional-grade AI-powered equity research by TAM Capital",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" dir="ltr">
      <body className="min-h-screen bg-slate-50">{children}</body>
    </html>
  );
}
