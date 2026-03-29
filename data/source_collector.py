"""Track and format data sources for citation in reports."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Source:
    """A single data source used in the research."""
    source_type: str        # "yahoo_finance", "news_article", "web_search", "sector_news"
    title: str
    url: str
    accessed_at: datetime
    description: str = ""
    reliability: str = ""   # "primary_data", "news", "analysis", "market_data"


class SourceCollector:
    """Collect and manage sources throughout the research pipeline."""

    def __init__(self):
        self.sources: list[Source] = []
        self._seen_urls: set = set()

    def add(self, source_type: str, title: str, url: str = "",
            description: str = "", reliability: str = "") -> int:
        """Add a source and return its citation index (1-based)."""
        # Deduplicate by URL
        if url and url in self._seen_urls:
            # Return existing index
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
        )
        self.sources.append(source)
        if url:
            self._seen_urls.add(url)
        return len(self.sources)

    def _infer_reliability(self, source_type: str) -> str:
        """Infer reliability level from source type."""
        mapping = {
            "yahoo_finance": "primary_data",
            "news_article": "news",
            "web_search": "news",
            "sector_news": "analysis",
            "financial_statements": "primary_data",
        }
        return mapping.get(source_type, "news")

    def format_for_prompt(self) -> str:
        """Format sources as a numbered list for AI prompts."""
        if not self.sources:
            return "No external sources available."

        lines = []
        for i, s in enumerate(self.sources, 1):
            line = f"[Source {i}] {s.title}"
            if s.url:
                line += f" | {s.url}"
            if s.description:
                line += f" | {s.description}"
            lines.append(line)

        return "\n".join(lines)

    def format_for_docx(self) -> list[dict]:
        """Return structured source data for document appendix."""
        result = []
        for i, s in enumerate(self.sources, 1):
            result.append({
                "index": i,
                "type": s.source_type,
                "title": s.title,
                "url": s.url,
                "accessed": s.accessed_at.strftime("%B %d, %Y at %H:%M"),
                "reliability": s.reliability,
                "description": s.description,
            })
        return result

    def format_for_pptx(self) -> str:
        """Format sources as compact text for a PPTX slide."""
        if not self.sources:
            return "No sources."

        lines = []
        for i, s in enumerate(self.sources, 1):
            line = f"{i}. {s.title}"
            if s.url:
                line += f"\n   {s.url}"
            lines.append(line)

        return "\n".join(lines)

    def format_for_display(self) -> str:
        """Format sources as markdown for Streamlit display."""
        if not self.sources:
            return "No sources tracked."

        # Group by type
        groups = {}
        for s in self.sources:
            type_label = {
                "yahoo_finance": "Market Data",
                "financial_statements": "Financial Statements",
                "news_article": "News & Analysis",
                "web_search": "Web Research",
                "sector_news": "Sector Research",
            }.get(s.source_type, "Other")

            if type_label not in groups:
                groups[type_label] = []
            groups[type_label].append(s)

        lines = []
        for group_name, sources in groups.items():
            lines.append(f"**{group_name}**")
            for s in sources:
                if s.url:
                    lines.append(f"- [{s.title}]({s.url})")
                else:
                    lines.append(f"- {s.title}")
            lines.append("")

        return "\n".join(lines)

    def to_dict(self) -> list[dict]:
        """Serialize for JSON storage."""
        return [
            {
                "source_type": s.source_type,
                "title": s.title,
                "url": s.url,
                "accessed_at": s.accessed_at.isoformat(),
                "description": s.description,
                "reliability": s.reliability,
            }
            for s in self.sources
        ]

    def __len__(self):
        return len(self.sources)
