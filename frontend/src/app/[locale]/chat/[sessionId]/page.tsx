"use client";

import { useParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import clsx from "clsx";
import ReactMarkdown from "react-markdown";
import { api } from "@/lib/api-client";
import type { ChatMessage, AnalysisStatus } from "@/lib/types";

export default function ChatSessionPage() {
  const { locale, sessionId } = useParams();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [analysisStatus, setAnalysisStatus] = useState<AnalysisStatus | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const isAr = locale === "ar";

  useEffect(() => {
    api
      .get<ChatMessage[]>(`/chat/sessions/${sessionId}/messages`)
      .then(setMessages)
      .catch(() => {});
  }, [sessionId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Poll analysis status
  useEffect(() => {
    if (!analysisStatus || analysisStatus.status === "completed" || analysisStatus.status === "failed") return;

    const interval = setInterval(async () => {
      try {
        const status = await api.get<AnalysisStatus>(`/analysis/${analysisStatus.task_id}/status`);
        setAnalysisStatus(status);

        if (status.status === "completed") {
          // Add completion message
          const msg: ChatMessage = {
            id: crypto.randomUUID(),
            session_id: sessionId as string,
            role: "assistant",
            content: `Analysis complete! [View full report](/${locale}/reports/${status.report_id})`,
            metadata_json: { report_id: status.report_id },
            created_at: new Date().toISOString(),
          };
          setMessages((prev) => [...prev, msg]);
        }
      } catch {
        // Ignore polling errors
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [analysisStatus, sessionId, locale]);

  const sendMessage = async () => {
    if (!input.trim() || sending) return;
    setSending(true);

    const userMessage = input.trim();
    setInput("");

    // Optimistic add
    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      session_id: sessionId as string,
      role: "user",
      content: userMessage,
      metadata_json: {},
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);

    try {
      // Send message to backend
      await api.post(`/chat/sessions/${sessionId}/messages`, { content: userMessage });

      // Try to trigger analysis
      const tickerMatch = userMessage.match(/\((\w+(?:\.\w+)?)\)/) || userMessage.match(/\b(\d{4})\b/);
      if (tickerMatch) {
        const status = await api.post<AnalysisStatus>("/analysis/run", {
          ticker: tickerMatch[1],
          company_name: userMessage.split("(")[0]?.trim() || tickerMatch[1],
          locale: locale,
          formats: ["docx", "pdf"],
          chat_session_id: sessionId,
        });
        setAnalysisStatus(status);

        const assistantMsg: ChatMessage = {
          id: crypto.randomUUID(),
          session_id: sessionId as string,
          role: "assistant",
          content: isAr
            ? `جاري تحليل **${tickerMatch[1]}**...`
            : `Initiating analysis for **${tickerMatch[1]}**...`,
          metadata_json: {},
          created_at: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, assistantMsg]);
      }
    } catch {
      // Handle error
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Messages */}
      <div className="flex-1 overflow-auto p-6 space-y-4">
        {messages.length === 0 && (
          <div className="text-center py-20">
            <div className="text-4xl mb-3">💬</div>
            <div className="text-tam-gray font-medium">
              {isAr ? "ابدأ بإدخال اسم سهم أو رمز" : "Enter a stock name or ticker to begin"}
            </div>
            <div className="text-xs text-tam-soft-carbon mt-2">
              {isAr
                ? "مثال: تقرير كامل عن أرامكو (2222)"
                : "Example: Full report on Aramco (2222)"}
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <div
            key={msg.id}
            className={clsx("flex", msg.role === "user" ? "justify-end" : "justify-start")}
          >
            <div
              className={clsx(
                "max-w-[70%] rounded-xl px-4 py-3 text-sm",
                msg.role === "user"
                  ? "bg-tam-deep-blue text-white"
                  : "bg-white border border-slate-200 text-tam-gray"
              )}
            >
              <ReactMarkdown
                components={{
                  a: ({ children, href }) => (
                    <a href={href} className="text-tam-turquoise underline hover:text-tam-light-blue">
                      {children}
                    </a>
                  ),
                  strong: ({ children }) => (
                    <strong className={msg.role === "user" ? "text-white" : "text-tam-deep-blue"}>
                      {children}
                    </strong>
                  ),
                }}
              >
                {msg.content}
              </ReactMarkdown>
            </div>
          </div>
        ))}

        {/* Analysis progress bar */}
        {analysisStatus && analysisStatus.status === "running" && (
          <div className="bg-white border border-slate-200 rounded-xl p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-tam-deep-blue">
                {analysisStatus.current_step}
              </span>
              <span className="text-xs text-tam-soft-carbon">{analysisStatus.progress}%</span>
            </div>
            <div className="w-full bg-slate-100 rounded-full h-2">
              <div
                className="bg-tam-turquoise rounded-full h-2 transition-all duration-500"
                style={{ width: `${analysisStatus.progress}%` }}
              />
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-slate-200 bg-white p-4">
        <div className="flex gap-3">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && sendMessage()}
            placeholder={
              isAr
                ? "أدخل اسم السهم أو الرمز (مثل أرامكو 2222، AAPL)"
                : "Enter stock name or ticker (e.g. Aramco 2222, AAPL)"
            }
            className="flex-1 px-4 py-2.5 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-tam-light-blue focus:border-transparent"
            disabled={sending}
          />
          <button
            onClick={sendMessage}
            disabled={sending || !input.trim()}
            className="px-5 py-2.5 bg-tam-deep-blue text-white text-sm rounded-lg hover:bg-tam-light-blue transition-colors disabled:opacity-50"
          >
            {isAr ? "إرسال" : "Send"}
          </button>
        </div>
      </div>
    </div>
  );
}
