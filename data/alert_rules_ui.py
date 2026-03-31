"""
Alert Rules UI module for the Streamlit Watchlist page.

Provides UI components for creating and managing custom alert rules with
glass-styled cards, form builders for different rule types, and alert
triggering logic for real-time monitoring.
"""

import streamlit as st
from datetime import datetime
from typing import Dict, List, Optional, Any
import uuid
import logging

logger = logging.getLogger(__name__)

# TAM Capital Liquid Glass color palette
C_TEXT = "#E6EDF3"
C_TEXT2 = "#8B949E"
C_ACCENT = "#1A6DB6"
C_GREEN = "#22C55E"
C_RED = "#EF4444"
C_ORANGE = "#F59E0B"
C_GLASS = "rgba(34,47,98,0.12)"
C_BORDER = "rgba(108,185,182,0.08)"
C_CARD = "rgba(26,38,78,0.15)"

# Rule type icons
RULE_TYPE_ICONS = {
    "price_above": "📈",
    "price_below": "📉",
    "volume_spike": "📊",
    "percent_change": "%",
    "news_keyword": "📰",
    "technical_signal": "📡",
}


def _get_alert_rules_from_state() -> List[Dict[str, Any]]:
    """Get alert rules from session state (local fallback)."""
    if "alert_rules_local" not in st.session_state:
        st.session_state.alert_rules_local = []
    return st.session_state.alert_rules_local


def _save_alert_rule_local(rule: Dict[str, Any]) -> str:
    """Save rule to session state and return rule ID."""
    rule_id = str(uuid.uuid4())
    rule["id"] = rule_id
    rule["created_at"] = datetime.now().isoformat()
    st.session_state.alert_rules_local.append(rule)
    return rule_id


def _delete_alert_rule_local(rule_id: str) -> bool:
    """Delete rule from session state."""
    rules = _get_alert_rules_from_state()
    original_len = len(rules)
    st.session_state.alert_rules_local = [r for r in rules if r.get("id") != rule_id]
    return len(st.session_state.alert_rules_local) < original_len


def _toggle_alert_rule_status(rule_id: str) -> bool:
    """Toggle active status of a rule."""
    rules = _get_alert_rules_from_state()
    for rule in rules:
        if rule.get("id") == rule_id:
            rule["is_active"] = not rule.get("is_active", True)
            return True
    return False


def format_rule_description(rule: Dict[str, Any]) -> str:
    """
    Generate human-readable description for an alert rule.

    Args:
        rule: Rule dict with type and parameters

    Returns:
        Human-readable description string
    """
    ticker = rule.get("ticker", "UNKNOWN")
    rule_type = rule.get("rule_type", "")
    params = rule.get("parameters", {})

    descriptions = {
        "price_above": f"Alert when {ticker} price goes above {params.get('threshold', 'N/A')}",
        "price_below": f"Alert when {ticker} price goes below {params.get('threshold', 'N/A')}",
        "volume_spike": f"Alert when {ticker} volume exceeds {params.get('multiplier', 2.0)}x average",
        "percent_change": f"Alert when {ticker} changes {params.get('percent_threshold', 5)}% in a day",
        "news_keyword": f"Alert when news mentions: {params.get('keywords', 'N/A')}",
        "technical_signal": f"Alert when {ticker} triggers {params.get('signal_type', 'N/A')}",
    }

    return descriptions.get(rule_type, f"Alert rule for {ticker}")


def _render_rule_card(rule: Dict[str, Any], col_index: int = 0) -> None:
    """
    Render a single alert rule as a glass-styled card.

    Args:
        rule: Rule dict with all fields
        col_index: Column index for layout
    """
    rule_id = rule.get("id", "unknown")
    is_active = rule.get("is_active", True)
    ticker = rule.get("ticker", "N/A")
    rule_type = rule.get("rule_type", "")

    icon = RULE_TYPE_ICONS.get(rule_type, "🔔")
    status_color = C_GREEN if is_active else C_TEXT2
    status_text = "Active" if is_active else "Inactive"

    description = format_rule_description(rule)

    # Glass card styling
    card_html = f"""
    <div style="
        background: {C_GLASS};
        border: 1px solid {C_BORDER};
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
        backdrop-filter: blur(10px);
    ">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
            <div style="display: flex; align-items: center; gap: 8px;">
                <span style="font-size: 20px;">{icon}</span>
                <div>
                    <div style="color: {C_TEXT}; font-weight: 600; font-size: 14px;">{ticker}</div>
                    <div style="color: {C_TEXT2}; font-size: 12px;">{rule_type.replace('_', ' ').title()}</div>
                </div>
            </div>
            <div style="
                background: rgba(34, 197, 94, 0.15);
                color: {status_color};
                padding: 4px 8px;
                border-radius: 6px;
                font-size: 11px;
                font-weight: 600;
            ">{status_text}</div>
        </div>

        <div style="color: {C_TEXT2}; font-size: 13px; margin-bottom: 12px; line-height: 1.4;">
            {description}
        </div>

        <div style="display: flex; gap: 8px;">
            <button style="
                flex: 1;
                background: transparent;
                color: {C_ACCENT};
                border: 1px solid {C_ACCENT};
                padding: 6px 12px;
                border-radius: 6px;
                cursor: pointer;
                font-size: 12px;
                transition: all 0.2s;
            " onclick="this.style.background='{C_ACCENT}'; this.style.color='white';">
                Edit
            </button>
            <button style="
                flex: 1;
                background: transparent;
                color: {C_ORANGE};
                border: 1px solid {C_ORANGE};
                padding: 6px 12px;
                border-radius: 6px;
                cursor: pointer;
                font-size: 12px;
                transition: all 0.2s;
            " onclick="this.style.background='{C_ORANGE}'; this.style.color='white';">
                Toggle
            </button>
        </div>
    </div>
    """

    st.markdown(card_html, unsafe_allow_html=True)


def render_alert_rules_panel(user_id: str = None) -> None:
    """
    Main UI function for alert rules management in Streamlit.

    Renders existing rules in glass-styled cards and provides a form
    to create new alert rules with dynamic parameters based on rule type.

    Args:
        user_id: Optional user ID for Supabase integration
    """
    st.markdown("### Alert Rules")
    st.markdown("Create custom alerts to monitor your watchlist in real-time.")

    # Try to use Supabase if available, otherwise use local state
    use_supabase = False
    rules = []

    try:
        from data import data_layer
        if user_id:
            data_layer.set_current_user(user_id)
            rules = data_layer.get_alert_rules()
            use_supabase = True
    except Exception as e:
        logger.debug(f"Supabase unavailable: {e}")
        rules = _get_alert_rules_from_state()

    # Display existing rules
    st.markdown("#### Your Alert Rules", help="Glass-styled cards showing all active and inactive alerts")

    if rules:
        cols = st.columns(2)
        for idx, rule in enumerate(rules):
            with cols[idx % 2]:
                _render_rule_card(rule, idx)

                # Action buttons for local rules
                if not use_supabase:
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Toggle", key=f"toggle_{rule.get('id')}"):
                            _toggle_alert_rule_status(rule.get("id"))
                            st.rerun()
                    with col2:
                        if st.button("Delete", key=f"delete_{rule.get('id')}"):
                            _delete_alert_rule_local(rule.get("id"))
                            st.rerun()
    else:
        st.info("No alert rules yet. Create one to get started!")

    # Add new rule form
    st.markdown("---")
    st.markdown("#### Add New Rule")

    with st.expander("Create Alert Rule", expanded=False):
        col1, col2 = st.columns(2)

        with col1:
            ticker = st.text_input(
                "Ticker Symbol",
                placeholder="e.g., AAPL or 2222.SR",
                help="Stock ticker to monitor"
            )

        with col2:
            rule_type = st.selectbox(
                "Rule Type",
                [
                    "price_above",
                    "price_below",
                    "volume_spike",
                    "percent_change",
                    "news_keyword",
                    "technical_signal",
                ],
                format_func=lambda x: x.replace("_", " ").title(),
                help="Type of alert to monitor"
            )

        # Dynamic parameter inputs based on rule type
        parameters = {}

        if rule_type == "price_above":
            parameters["threshold"] = st.number_input(
                "Price Threshold",
                min_value=0.0,
                step=0.5,
                help="Alert when price exceeds this value"
            )

        elif rule_type == "price_below":
            parameters["threshold"] = st.number_input(
                "Price Threshold",
                min_value=0.0,
                step=0.5,
                help="Alert when price falls below this value"
            )

        elif rule_type == "volume_spike":
            parameters["multiplier"] = st.number_input(
                "Volume Multiplier",
                min_value=1.0,
                max_value=10.0,
                value=2.0,
                step=0.1,
                help="Alert when volume exceeds X times the 20-day average"
            )

        elif rule_type == "percent_change":
            parameters["percent_threshold"] = st.number_input(
                "Percent Change (%)",
                min_value=0.0,
                max_value=100.0,
                value=5.0,
                step=0.5,
                help="Alert when daily change exceeds this percentage"
            )

        elif rule_type == "news_keyword":
            keywords_input = st.text_input(
                "Keywords (comma-separated)",
                placeholder="e.g., earnings, acquisition, dividend",
                help="Alert when news mentions these keywords"
            )
            parameters["keywords"] = keywords_input

        elif rule_type == "technical_signal":
            signal_type = st.selectbox(
                "Technical Signal",
                [
                    "rsi_overbought",
                    "rsi_oversold",
                    "macd_crossover",
                    "ma_crossover",
                ],
                format_func=lambda x: x.replace("_", " ").title(),
                help="Technical condition to monitor"
            )
            parameters["signal_type"] = signal_type

        # Notification preferences
        st.markdown("**Notification Preferences**")
        col1, col2 = st.columns(2)
        with col1:
            notify_in_app = st.checkbox("In-App Notification", value=True)
        with col2:
            notify_email = st.checkbox("Email Notification", value=False)

        parameters["notify_in_app"] = notify_in_app
        parameters["notify_email"] = notify_email

        # Save button
        if st.button("Save Alert Rule", type="primary"):
            if not ticker:
                st.error("Please enter a ticker symbol")
            elif not parameters or (rule_type in ["price_above", "price_below"] and parameters.get("threshold") is None):
                st.error("Please fill in all required fields")
            else:
                new_rule = {
                    "ticker": ticker.upper(),
                    "rule_type": rule_type,
                    "parameters": parameters,
                    "is_active": True,
                }

                if use_supabase:
                    try:
                        from data import data_layer
                        rule = data_layer.create_alert_rule(
                            ticker.upper(),
                            rule_type,
                            parameters
                        )
                        if rule:
                            st.success(f"Alert rule created for {ticker}!")
                            st.rerun()
                        else:
                            st.error("Failed to create rule in Supabase")
                    except Exception as e:
                        st.error(f"Error creating rule: {e}")
                else:
                    _save_alert_rule_local(new_rule)
                    st.success(f"Alert rule created for {ticker}!")
                    st.rerun()


def check_alert_rules(
    rules: List[Dict[str, Any]],
    ticker: str,
    stock_data: Dict[str, Any],
    technicals: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Check which alert rules are triggered given current market data.

    Args:
        rules: List of alert rule dicts
        ticker: Stock ticker symbol
        stock_data: Current stock data dict with keys:
            - current_price: Current stock price
            - previous_close: Previous close price
            - volume: Current trading volume
            - avg_volume: Average volume (usually 20-day)
        technicals: Optional dict with technical indicators:
            - rsi: RSI value (0-100)
            - macd: MACD value
            - macd_signal: MACD signal line
            - sma_50: 50-day moving average
            - sma_200: 200-day moving average

    Returns:
        List of triggered alerts: [{
            "rule_id": str,
            "ticker": str,
            "rule_type": str,
            "message": str,
            "severity": "low|medium|high"
        }]
    """
    triggered = []

    for rule in rules:
        if not rule.get("is_active", True):
            continue

        if rule.get("ticker", "").upper() != ticker.upper():
            continue

        rule_type = rule.get("rule_type", "")
        params = rule.get("parameters", {})
        rule_id = rule.get("id", "unknown")

        # Price Above
        if rule_type == "price_above":
            threshold = params.get("threshold", 0)
            current_price = stock_data.get("current_price", 0)
            if current_price > threshold:
                triggered.append({
                    "rule_id": rule_id,
                    "ticker": ticker,
                    "rule_type": rule_type,
                    "message": f"{ticker} price ({current_price}) exceeded threshold ({threshold})",
                    "severity": "medium",
                })

        # Price Below
        elif rule_type == "price_below":
            threshold = params.get("threshold", float("inf"))
            current_price = stock_data.get("current_price", 0)
            if current_price < threshold:
                triggered.append({
                    "rule_id": rule_id,
                    "ticker": ticker,
                    "rule_type": rule_type,
                    "message": f"{ticker} price ({current_price}) fell below threshold ({threshold})",
                    "severity": "medium",
                })

        # Volume Spike
        elif rule_type == "volume_spike":
            multiplier = params.get("multiplier", 2.0)
            current_volume = stock_data.get("volume", 0)
            avg_volume = stock_data.get("avg_volume", 1)

            if current_volume > (avg_volume * multiplier):
                triggered.append({
                    "rule_id": rule_id,
                    "ticker": ticker,
                    "rule_type": rule_type,
                    "message": f"{ticker} volume spike: {current_volume / avg_volume:.1f}x average",
                    "severity": "high",
                })

        # Percent Change
        elif rule_type == "percent_change":
            threshold = params.get("percent_threshold", 5)
            current = stock_data.get("current_price", 0)
            previous = stock_data.get("previous_close", 0)

            if previous > 0:
                pct_change = ((current - previous) / previous) * 100
                if abs(pct_change) >= threshold:
                    direction = "up" if pct_change > 0 else "down"
                    triggered.append({
                        "rule_id": rule_id,
                        "ticker": ticker,
                        "rule_type": rule_type,
                        "message": f"{ticker} moved {direction} {abs(pct_change):.1f}%",
                        "severity": "high" if abs(pct_change) >= threshold * 1.5 else "medium",
                    })

        # Technical Signal
        elif rule_type == "technical_signal" and technicals:
            signal_type = params.get("signal_type", "")

            if signal_type == "rsi_overbought":
                rsi = technicals.get("rsi", 0)
                if rsi > 70:
                    triggered.append({
                        "rule_id": rule_id,
                        "ticker": ticker,
                        "rule_type": rule_type,
                        "message": f"{ticker} RSI overbought ({rsi:.0f})",
                        "severity": "medium",
                    })

            elif signal_type == "rsi_oversold":
                rsi = technicals.get("rsi", 100)
                if rsi < 30:
                    triggered.append({
                        "rule_id": rule_id,
                        "ticker": ticker,
                        "rule_type": rule_type,
                        "message": f"{ticker} RSI oversold ({rsi:.0f})",
                        "severity": "medium",
                    })

            elif signal_type == "macd_crossover":
                macd = technicals.get("macd", 0)
                signal = technicals.get("macd_signal", 0)
                if abs(macd - signal) < 0.01:  # Lines nearly crossed
                    triggered.append({
                        "rule_id": rule_id,
                        "ticker": ticker,
                        "rule_type": rule_type,
                        "message": f"{ticker} MACD crossover detected",
                        "severity": "high",
                    })

            elif signal_type == "ma_crossover":
                sma_50 = technicals.get("sma_50", 0)
                sma_200 = technicals.get("sma_200", 0)
                if sma_50 and sma_200:
                    if abs(sma_50 - sma_200) < (sma_200 * 0.02):  # Within 2%
                        triggered.append({
                            "rule_id": rule_id,
                            "ticker": ticker,
                            "rule_type": rule_type,
                            "message": f"{ticker} moving average crossover",
                            "severity": "high",
                        })

    return triggered
