"""
Migration script to move data from JSON files to Supabase.

This script reads existing JSON data files and inserts them into Supabase tables.
It supports dry-run mode and idempotency (skips existing records).

Usage:
    python data/migrate_json_to_supabase.py [--dry-run]
"""

import json
import os
import sys
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Try to import Supabase
try:
    from data.supabase_client import (
        SUPABASE_AVAILABLE,
        WatchlistDAO,
        PortfolioDAO,
        ReportDAO,
        AlertDAO,
    )
except ImportError:
    logger.error("Cannot import Supabase DAOs. Ensure supabase-py is installed.")
    sys.exit(1)

# Admin user ID (mmalki@tamcapital.sa)
ADMIN_USER_ID = "mmalki@tamcapital.sa"


class MigrationRunner:
    """Handles migration of JSON data to Supabase."""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.project_root = Path(__file__).parent.parent
        self.stats = {
            "watchlists_migrated": 0,
            "watchlist_items_migrated": 0,
            "positions_migrated": 0,
            "reports_migrated": 0,
            "alerts_migrated": 0,
            "errors": 0,
        }

    def log_status(self, message: str):
        """Log migration status."""
        prefix = "[DRY RUN] " if self.dry_run else ""
        logger.info(f"{prefix}{message}")

    def log_error(self, message: str):
        """Log migration error."""
        logger.error(message)
        self.stats["errors"] += 1

    def migrate_watchlists(self) -> bool:
        """Migrate watchlist data from JSON to Supabase."""
        watchlist_file = self.project_root / "watchlist_data" / "watchlist.json"

        if not watchlist_file.exists():
            self.log_status("Watchlist file not found, skipping...")
            return True

        try:
            with open(watchlist_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            self.log_error(f"Error reading watchlist JSON: {e}")
            return False

        watchlists = data.get("watchlists", [])
        self.log_status(f"Found {len(watchlists)} watchlists to migrate")

        for wl in watchlists:
            try:
                wl_id = str(uuid.uuid4())
                name = wl.get("name", "")
                description = wl.get("description", "")
                is_default = wl.get("is_default", False)

                if self.dry_run:
                    self.log_status(
                        f"  Would create watchlist: {name} (ID: {wl_id})"
                    )
                else:
                    # Create watchlist
                    created = WatchlistDAO.create(
                        user_id=ADMIN_USER_ID,
                        name=name,
                        description=description,
                        is_default=is_default,
                    )

                    if not created:
                        self.log_error(f"Failed to create watchlist: {name}")
                        continue

                    wl_id = created.get("id")
                    self.log_status(
                        f"  Created watchlist: {name} (ID: {wl_id})"
                    )

                    # Add items to watchlist
                    items = wl.get("items", [])
                    for item in items:
                        ticker = item.get("ticker", "")
                        company_name = item.get("name", "")

                        item_created = WatchlistDAO.add_item(
                            watchlist_id=wl_id,
                            ticker=ticker,
                            company_name=company_name,
                        )

                        if item_created:
                            self.stats["watchlist_items_migrated"] += 1
                            self.log_status(f"    Added item: {ticker}")
                        else:
                            self.log_error(f"Failed to add item {ticker} to watchlist")

                self.stats["watchlists_migrated"] += 1

            except Exception as e:
                self.log_error(f"Error migrating watchlist: {e}")

        return True

    def migrate_portfolio(self) -> bool:
        """Migrate portfolio positions from JSON to Supabase."""
        portfolio_file = self.project_root / "watchlist_data" / "portfolio.json"

        if not portfolio_file.exists():
            self.log_status("Portfolio file not found, skipping...")
            return True

        try:
            with open(portfolio_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            self.log_error(f"Error reading portfolio JSON: {e}")
            return False

        positions = data.get("positions", [])
        self.log_status(f"Found {len(positions)} portfolio positions to migrate")

        for pos in positions:
            try:
                ticker = pos.get("ticker", "")
                name = pos.get("name", "")
                shares = float(pos.get("shares", 0))
                cost_basis = float(pos.get("cost_basis", 0))

                if self.dry_run:
                    self.log_status(
                        f"  Would create position: {ticker} ({shares} shares @ ${cost_basis})"
                    )
                else:
                    created = PortfolioDAO.add_position(
                        user_id=ADMIN_USER_ID,
                        ticker=ticker,
                        company_name=name,
                        shares=shares,
                        cost_basis=cost_basis,
                    )

                    if created:
                        self.stats["positions_migrated"] += 1
                        self.log_status(
                            f"  Created position: {ticker} (ID: {created.get('id')})"
                        )
                    else:
                        self.log_error(f"Failed to create position: {ticker}")

            except (ValueError, TypeError) as e:
                self.log_error(f"Error parsing position data: {e}")

        return True

    def migrate_reports(self) -> bool:
        """Migrate reports from JSON files to Supabase."""
        report_dir = self.project_root / "report_history"

        if not report_dir.exists():
            self.log_status("Report history directory not found, skipping...")
            return True

        # Find all report JSON files (exclude _versions.json index files)
        report_files = [
            f for f in report_dir.glob("*.json")
            if not f.name.endswith("_versions.json")
        ]

        self.log_status(f"Found {len(report_files)} reports to migrate")

        for report_file in report_files:
            try:
                with open(report_file, "r", encoding="utf-8") as f:
                    report = json.load(f)

                report_id = report.get("id", "")
                ticker = report.get("ticker", "")
                stock_name = report.get("stock_name", "")
                sections = report.get("sections", {})
                files = report.get("files", {})

                # Check if report already exists (idempotency)
                if not self.dry_run:
                    existing = ReportDAO.get_by_id(report_id)
                    if existing:
                        self.log_status(
                            f"  Report already exists, skipping: {report_id}"
                        )
                        continue

                if self.dry_run:
                    self.log_status(
                        f"  Would create report: {stock_name} ({ticker}) ID: {report_id}"
                    )
                else:
                    created = ReportDAO.save(
                        user_id=ADMIN_USER_ID,
                        ticker=ticker,
                        company_name=stock_name,
                        sections=sections,
                        files=files,
                        metadata={
                            "migrated_from": "json",
                            "original_id": report_id,
                        },
                    )

                    if created:
                        self.stats["reports_migrated"] += 1
                        self.log_status(f"  Created report: {stock_name}")
                    else:
                        self.log_error(f"Failed to create report: {report_id}")

            except (json.JSONDecodeError, IOError, KeyError) as e:
                self.log_error(f"Error reading report file {report_file.name}: {e}")

        return True

    def migrate_alerts(self) -> bool:
        """Migrate alert history from JSON to Supabase."""
        alert_file = self.project_root / "watchlist_data" / "alert_history.json"

        if not alert_file.exists():
            self.log_status("Alert history file not found, skipping...")
            return True

        try:
            with open(alert_file, "r", encoding="utf-8") as f:
                alerts = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            self.log_error(f"Error reading alert history JSON: {e}")
            return False

        # Handle both list format (array) and dict format ({"alerts": [...]})
        if isinstance(alerts, dict):
            alerts = alerts.get("alerts", [])

        self.log_status(f"Found {len(alerts)} alerts to migrate")

        for alert in alerts:
            try:
                ticker = alert.get("ticker", "")
                alert_type = alert.get("type", "unknown")
                severity = alert.get("severity", "moderate")
                message = alert.get("message", "")

                if self.dry_run:
                    self.log_status(
                        f"  Would create alert: {ticker} ({alert_type})"
                    )
                else:
                    created = AlertDAO.create_alert(
                        user_id=ADMIN_USER_ID,
                        ticker=ticker,
                        alert_type=alert_type,
                        severity=severity,
                        message=message,
                        context={"migrated_from": "json"},
                    )

                    if created:
                        self.stats["alerts_migrated"] += 1
                        self.log_status(
                            f"  Created alert: {ticker} ({alert_type})"
                        )
                    else:
                        self.log_error(
                            f"Failed to create alert: {ticker} ({alert_type})"
                        )

            except Exception as e:
                self.log_error(f"Error migrating alert: {e}")

        return True

    def run(self) -> bool:
        """Run the full migration."""
        if self.dry_run:
            logger.info("=" * 60)
            logger.info("DRY RUN MODE - No data will be written to Supabase")
            logger.info("=" * 60)

        if not SUPABASE_AVAILABLE:
            logger.error("Supabase is not available. Check your configuration.")
            return False

        logger.info("Starting migration from JSON to Supabase...")
        logger.info(f"Admin user ID: {ADMIN_USER_ID}")

        success = True

        success = self.migrate_watchlists() and success
        success = self.migrate_portfolio() and success
        success = self.migrate_reports() and success
        success = self.migrate_alerts() and success

        logger.info("=" * 60)
        logger.info("Migration Summary:")
        logger.info(f"  Watchlists: {self.stats['watchlists_migrated']}")
        logger.info(f"  Watchlist Items: {self.stats['watchlist_items_migrated']}")
        logger.info(f"  Portfolio Positions: {self.stats['positions_migrated']}")
        logger.info(f"  Reports: {self.stats['reports_migrated']}")
        logger.info(f"  Alerts: {self.stats['alerts_migrated']}")
        logger.info(f"  Errors: {self.stats['errors']}")
        logger.info("=" * 60)

        return success and self.stats["errors"] == 0


def main():
    """Main entry point."""
    dry_run = "--dry-run" in sys.argv

    runner = MigrationRunner(dry_run=dry_run)
    success = runner.run()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
