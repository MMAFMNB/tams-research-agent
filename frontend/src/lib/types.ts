export interface ChatSession {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  id: string;
  session_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  metadata_json: Record<string, unknown>;
  created_at: string;
}

export interface Report {
  id: string;
  ticker: string;
  company_name: string;
  locale: string;
  status: "pending" | "running" | "completed" | "failed";
  report_type: string;
  created_at: string;
  completed_at: string | null;
}

export interface ReportDetail extends Report {
  sections: ReportSection[];
  files: ReportFile[];
  sources: ReportSource[];
  snapshot: ReportSnapshot | null;
}

export interface ReportSection {
  id: string;
  section_key: string;
  title: string;
  content: string;
  sort_order: number;
}

export interface ReportFile {
  id: string;
  file_type: "docx" | "pdf" | "pptx";
  storage_path: string;
  file_size: number;
  created_at: string;
}

export interface ReportSource {
  id: string;
  source_type: string;
  title: string;
  url: string | null;
  accessed_at: string;
  reliability: string;
  is_realtime: boolean;
  delay_minutes: number;
  description: string | null;
}

export interface ReportSnapshot {
  current_price: number | null;
  market_cap: number | null;
  pe_ratio: number | null;
  forward_pe: number | null;
  eps_ttm: number | null;
  dividend_yield: number | null;
  rating: string | null;
  price_target: number | null;
  risk_level: string | null;
  key_catalysts: Record<string, unknown> | null;
  key_risks: Record<string, unknown> | null;
}

export interface AnalysisStatus {
  task_id: string;
  report_id: string;
  status: string;
  progress: number;
  current_step: string;
}

export interface StockQuote {
  ticker: string;
  name: string;
  sector: string;
  industry: string;
  currency: string;
  current_price: number;
  market_cap: number;
  pe_ratio: number | null;
  dividend_yield: number | null;
  is_realtime: boolean;
  delay_minutes: number;
  fetched_at: string;
}
