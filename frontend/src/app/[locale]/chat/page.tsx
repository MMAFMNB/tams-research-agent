"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api-client";
import type { ChatSession } from "@/lib/types";

export default function ChatListPage() {
  const { locale } = useParams();
  const router = useRouter();
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [loading, setLoading] = useState(true);
  const isAr = locale === "ar";

  useEffect(() => {
    api
      .get<ChatSession[]>("/chat/sessions")
      .then(setSessions)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const createNewChat = async () => {
    try {
      const session = await api.post<ChatSession>("/chat/sessions", {
        title: isAr ? "محادثة جديدة" : "New Chat",
      });
      router.push(`/${locale}/chat/${session.id}`);
    } catch {
      // Handle error
    }
  };

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-tam-deep-blue">
            {isAr ? "محادثة البحث" : "Research Chat"}
          </h1>
          <p className="text-sm text-tam-gray mt-1">
            {isAr
              ? "اطلب تحليل أي سهم أو اسأل أسئلة مالية"
              : "Request analysis on any stock or ask financial questions"}
          </p>
        </div>
        <button
          onClick={createNewChat}
          className="px-4 py-2 bg-tam-deep-blue text-white text-sm rounded-lg hover:bg-tam-light-blue transition-colors"
        >
          {isAr ? "محادثة جديدة" : "New Chat"}
        </button>
      </div>

      {loading ? (
        <div className="text-center py-12 text-tam-soft-carbon text-sm">
          {isAr ? "جاري التحميل..." : "Loading..."}
        </div>
      ) : sessions.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-xl border border-slate-200">
          <div className="text-4xl mb-3">💬</div>
          <div className="text-tam-gray font-medium">
            {isAr ? "لا توجد محادثات بعد" : "No conversations yet"}
          </div>
          <div className="text-sm text-tam-soft-carbon mt-1 mb-4">
            {isAr
              ? "ابدأ محادثة جديدة لتحليل الأسهم"
              : "Start a new chat to analyze stocks"}
          </div>
          <button
            onClick={createNewChat}
            className="px-4 py-2 bg-tam-deep-blue text-white text-sm rounded-lg hover:bg-tam-light-blue transition-colors"
          >
            {isAr ? "بدء محادثة" : "Start Chat"}
          </button>
        </div>
      ) : (
        <div className="space-y-2">
          {sessions.map((session) => (
            <Link
              key={session.id}
              href={`/${locale}/chat/${session.id}`}
              className="block bg-white rounded-xl border border-slate-200 p-4 hover:shadow-md transition-shadow"
            >
              <div className="flex items-center justify-between">
                <div className="font-medium text-tam-deep-blue">{session.title}</div>
                <div className="text-xs text-tam-soft-carbon">
                  {new Date(session.updated_at).toLocaleDateString(
                    locale === "ar" ? "ar-SA" : "en-US",
                    { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }
                  )}
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
