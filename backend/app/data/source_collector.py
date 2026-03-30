"""Track and format data sources for citation in reports."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Source:
    """A single data source used in the research."""
    source_type: str
    title: str
    url: str
    accessed_at: datetime
    description: str = ""
    reliability: str = ""
    is_realtime: bool = False
    delay_minutes: int = 0


class SourceCollector:
    """Collect and manage sources throughout the research pipeline."""

    def __init__(self):
        self.sources: list[Source] = []
        self._seen_urls: set = set()

    def add(self, source_type: str, title: str, url: str = "",
            description: str = "", reliability: str = "",
            is_realtime: bool = False, delay_minutes: int = 0) -> int:
        """Add a source and return its citation index (1-based)."""
        if url and url in self._seen_urls:
            for i, s in enumerate(self.sources):
                if s.url == url:
                    return i + 1
            return len(self.sources)

        source = Source(
            source_type=source_type,
            title=title,
            url=url,
            accessed_at=datetime.now(),
            description=description,
            reliability=reliability or self._infer_reliability(source_type),
            is_realtime=is_realtime,
            delay_minutes=delay_minutes,
        )
        self.sources.append(source)
        if url:
            self._seen_urls.add(url)
        return len(self.sources)

    def _infer_reliability(self, source_type: str) -> str:
        mapping = {
            "yahoo_finance": "primary_data",
            "news_article": "news",
            "web_search": "news",
            "sector_news": "analysis",
            "financial_statements": "primary_data",
            "tadawul": "primary_data",
            "argaam": "primary_data",
        }
        return mapping.get(source_type, "news")

    def format_for_prompt(self) -> str:
        if not self.sources:
            return "No external sources available."
        lines = []
        for i, s in enumerate(self.sources, 1):
            line = f"[Source {i}] {s.title}"
            if s.url:
                line += f" | {s.url}"
            if s.description:
                line += f" | {s.description}"
            freshness = "Real-time" if s.is_realtime else f"Delayed ~{s.delay_minutes}min"
            line += f" | {freshness}"
            lines.append(line)
        return "\n".join(lines)

    def format_for_display(self) -> str:
        if not self.sources:
            return "No sources tracked."
        groups = {}
        for s in self.sources:
            type_label = {
                "yahoo_finance": "Market Data",
                "financial_statements": "Financial Statements",
                "news_article": "News & Analysis",
                "web_search": "Web Research",
                "sector_news": "Sector Research",
                "tadawul": "Saudi Exchange (Tadawul)",
                "argaam": "Argaam Financial Data",
            }.get(s.source_type, "Other")
            if type_label not in groups:
                groups[type_label] = []
            groups[type_label].append(s)

        lines = []
        for group_name, sources in groups.items():
            lines.append(f"**{group_name}**")
            for s in sources:
                freshness = "Real-time" if s.is_realtime else f"Delayed ~{s.delay_minutes}min"
                ts = s.accessed_at.strftime("%H:%M:%S")
                if s.url:
                    lines.append(f"- [{s.title}]({s.url}) -- {freshness} at {ts}")
                else:
                    lines.append(f"- {s.title} -- {freshness} at {ts}")
            lines.append("")
        return "\n".join(lines)

    def to_dict_list(self) -> list[dict]:
        return [
            {
                "source_type": s.source_type,
                "title": s.title,
                "url": s.url,
                "accessed_at": s.accessed_at.isoformat(),
                "description": s.description,
                "reliability": s.reliability,
                "is_realtime": s.is_realtime,
                "delay_minutes": s.delay_minutes,
            }
            for s in self.sources
        ]

    def __len__(self):
        return len(self.sources)
