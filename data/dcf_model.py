"""
Discounted Cash Flow (DCF) valuation calculator for stock research.

Provides DCF analysis, sensitivity tables, and scenario analysis
for fundamental stock valuation.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class DCFResult:
    """Container for DCF calculation results."""
    projected_fcf: List[float]
    terminal_value: float
    enterprise_value: float
    equity_value: float
    implied_price: float
    upside_pct: float
    year_labels: List[str]
    assumptions: Dict
    current_price: float


class DCFModel:
    """
    Discounted Cash Flow valuation model for equity analysis.

    Implements DCF valuation with support for sensitivity analysis
    and scenario modeling.
    """

    def __init__(self, stock_data: Dict):
        """
        Initialize DCF model with stock data.

        Args:
            stock_data: Dictionary with keys like revenue, net_income,
                       free_cash_flow, shares_outstanding, market_cap,
                       price, beta, total_debt, total_cash, etc.
        """
        self.stock_data = stock_data
        self._validate_stock_data()

    def _validate_stock_data(self) -> None:
        """Validate that essential stock data is present."""
        # These fields should ideally be present; we'll use defaults if missing
        self.price = self.stock_data.get('price', 0)
        self.revenue = self.stock_data.get('revenue', 0)
        self.free_cash_flow = self.stock_data.get('free_cash_flow', 0)
        self.shares_outstanding = self.stock_data.get('shares_outstanding', 1)
        self.total_debt = self.stock_data.get('total_debt', 0)
        self.total_cash = self.stock_data.get('total_cash', 0)
        self.beta = self.stock_data.get('beta', 1.0)
        self.operating_margin = self.stock_data.get('operating_margin', 0.1)

    def calculate(self, assumptions: Dict) -> Dict:
        """
        Run the DCF calculation with given assumptions.

        Args:
            assumptions: Dictionary containing:
                - revenue_growth_rates (List[float]): 5 years of growth rates
                - operating_margin (float): Operating margin as decimal
                - tax_rate (float): Tax rate as decimal
                - wacc (float): Weighted average cost of capital as decimal
                - terminal_growth_rate (float): Terminal growth rate as decimal
                - capex_pct_revenue (float): CapEx as % of revenue

        Returns:
            Dictionary with DCF results including projected_fcf, terminal_value,
            enterprise_value, equity_value, implied_price, upside_pct, year_labels
        """
        # Extract assumptions
        revenue_growth_rates = assumptions.get('revenue_growth_rates', [0.05] * 5)
        op_margin = assumptions.get('operating_margin', 0.1)
        tax_rate = assumptions.get('tax_rate', 0.20)
        wacc = assumptions.get('wacc', 0.08)
        terminal_growth = assumptions.get('terminal_growth_rate', 0.025)
        capex_pct = assumptions.get('capex_pct_revenue', 0.03)

        # Validate inputs
        if wacc <= terminal_growth:
            wacc = terminal_growth + 0.05  # Ensure wacc > terminal_growth

        # Project revenues and FCFs
        base_revenue = self.revenue if self.revenue > 0 else 1000  # Default to 1000 if missing
        projected_revenues = []
        projected_fcf = []

        current_revenue = base_revenue
        for i, growth_rate in enumerate(revenue_growth_rates):
            current_revenue = current_revenue * (1 + growth_rate)
            projected_revenues.append(current_revenue)

            # FCF = Revenue × Op Margin × (1 - Tax Rate) - CapEx
            nopat = current_revenue * op_margin * (1 - tax_rate)
            capex = current_revenue * capex_pct
            fcf = nopat - capex
            projected_fcf.append(fcf)

        # Calculate terminal value
        # Terminal Value = FCF_year5 × (1 + terminal_growth) / (WACC - terminal_growth)
        fcf_terminal = projected_fcf[-1] * (1 + terminal_growth)
        terminal_value = fcf_terminal / (wacc - terminal_growth)

        # Discount all cash flows to present value
        discount_factors = [(1 + wacc) ** -(i + 1) for i in range(5)]
        discounted_fcf = [fcf * df for fcf, df in zip(projected_fcf, discount_factors)]

        # Discount terminal value
        discounted_terminal = terminal_value * discount_factors[-1]

        # Calculate enterprise value
        enterprise_value = sum(discounted_fcf) + discounted_terminal

        # Calculate equity value
        net_debt = self.total_debt - self.total_cash
        equity_value = enterprise_value - net_debt

        # Ensure equity value is positive
        if equity_value <= 0:
            equity_value = max(enterprise_value * 0.1, 1)

        # Calculate implied price
        shares_out = self.shares_outstanding if self.shares_outstanding > 0 else 1
        implied_price = equity_value / shares_out

        # Calculate upside/downside
        current_price = self.price if self.price > 0 else 1
        upside_pct = ((implied_price - current_price) / current_price) * 100 if current_price > 0 else 0

        # Generate year labels
        year_labels = [f"Year {i+1}" for i in range(5)]

        return {
            'projected_fcf': projected_fcf,
            'projected_revenues': projected_revenues,
            'discounted_fcf': discounted_fcf,
            'terminal_value': terminal_value,
            'discounted_terminal_value': discounted_terminal,
            'enterprise_value': enterprise_value,
            'net_debt': net_debt,
            'equity_value': equity_value,
            'implied_price': implied_price,
            'current_price': current_price,
            'upside_pct': upside_pct,
            'year_labels': year_labels,
            'assumptions': assumptions,
            'discount_factors': discount_factors,
        }

    def auto_wacc(self, risk_free_rate: float = 0.045,
                  equity_risk_premium: float = 0.065) -> float:
        """
        Calculate WACC from beta using CAPM for cost of equity.

        Simplified WACC = Cost of Equity (assumes minimal debt component)
        Cost of Equity = Rf + Beta × ERP

        Args:
            risk_free_rate: Risk-free rate (default 4.5% for Saudi)
            equity_risk_premium: Market equity risk premium (default 6.5%)

        Returns:
            WACC as decimal
        """
        beta = self.beta if self.beta > 0 else 1.0
        cost_of_equity = risk_free_rate + (beta * equity_risk_premium)

        # For simplicity, assuming WACC ≈ Cost of Equity for high equity-financed companies
        # In practice, would weight Cost of Debt and Cost of Equity by market values
        return cost_of_equity

    def sensitivity_table(self, base_assumptions: Dict,
                         wacc_range: Optional[List[float]] = None,
                         terminal_range: Optional[List[float]] = None) -> Dict:
        """
        Generate 2D sensitivity matrix for implied price.

        Args:
            base_assumptions: Base DCF assumptions
            wacc_range: List of WACC values to test (default: ±2% around base)
            terminal_range: List of terminal growth rates to test (default: ±1% around base)

        Returns:
            Dictionary with wacc_values, terminal_values, and matrix of implied prices
        """
        base_wacc = base_assumptions.get('wacc', 0.08)
        base_terminal = base_assumptions.get('terminal_growth_rate', 0.025)

        # Generate ranges if not provided
        if wacc_range is None:
            wacc_range = [base_wacc - 0.02, base_wacc - 0.01, base_wacc,
                         base_wacc + 0.01, base_wacc + 0.02]

        if terminal_range is None:
            terminal_range = [base_terminal - 0.01, base_terminal - 0.005,
                             base_terminal, base_terminal + 0.005, base_terminal + 0.01]

        # Generate matrix of implied prices
        matrix = []
        for terminal_rate in terminal_range:
            row = []
            for wacc_value in wacc_range:
                # Skip invalid combinations
                if wacc_value <= terminal_rate:
                    row.append(None)
                    continue

                # Run DCF with these parameters
                test_assumptions = base_assumptions.copy()
                test_assumptions['wacc'] = wacc_value
                test_assumptions['terminal_growth_rate'] = terminal_rate

                result = self.calculate(test_assumptions)
                row.append(result['implied_price'])

            matrix.append(row)

        return {
            'wacc_values': wacc_range,
            'terminal_values': terminal_range,
            'matrix': matrix,
        }

    def scenario_analysis(self, base_assumptions: Dict) -> Dict:
        """
        Generate bull, base, and bear case scenarios.

        Creates three scenarios by adjusting key assumptions:
        - Bull: Higher growth, lower WACC
        - Base: Base case assumptions
        - Bear: Lower growth, higher WACC

        Args:
            base_assumptions: Base DCF assumptions

        Returns:
            Dictionary with 'bull', 'base', 'bear' keys containing full DCF results
        """
        base_growth_rates = base_assumptions.get('revenue_growth_rates', [0.05] * 5)
        base_wacc = base_assumptions.get('wacc', 0.08)
        base_terminal = base_assumptions.get('terminal_growth_rate', 0.025)

        # Bear case: reduce growth by 30%, increase WACC by 1%
        bear_assumptions = base_assumptions.copy()
        bear_assumptions['revenue_growth_rates'] = [g * 0.7 for g in base_growth_rates]
        bear_assumptions['wacc'] = base_wacc + 0.01
        bear_assumptions['terminal_growth_rate'] = base_terminal * 0.8

        # Bull case: increase growth by 30%, decrease WACC by 1%
        bull_assumptions = base_assumptions.copy()
        bull_assumptions['revenue_growth_rates'] = [g * 1.3 for g in base_growth_rates]
        bull_assumptions['wacc'] = max(base_wacc - 0.01, 0.02)
        bull_assumptions['terminal_growth_rate'] = min(base_terminal * 1.2, 0.035)

        return {
            'bull': self.calculate(bull_assumptions),
            'base': self.calculate(base_assumptions),
            'bear': self.calculate(bear_assumptions),
        }


def get_default_assumptions(stock_data: Dict) -> Dict:
    """
    Auto-populate reasonable DCF assumptions from stock data.

    Uses historical revenue growth trends with mean reversion,
    estimates operating margins from recent financials, and
    derives WACC from beta.

    Args:
        stock_data: Dictionary with stock financial data

    Returns:
        Dictionary with DCF assumptions
    """
    # Extract historical growth if available
    historical_growth = stock_data.get('historical_revenue_growth', [0.05] * 5)

    # Mean reversion: assume growth reverts toward GDP growth over 5 years
    gdp_growth = 0.03  # Default to 3% GDP growth
    revenue_growth_rates = []

    for i, hist_growth in enumerate(historical_growth[:5]):
        # Gradually shift from historical to GDP growth
        weight_hist = max(0, 1 - (i * 0.15))
        mean_reverted = (hist_growth * weight_hist) + (gdp_growth * (1 - weight_hist))
        revenue_growth_rates.append(max(mean_reverted, 0.01))  # Floor at 1%

    # Estimate operating margin from recent financials
    operating_margin = stock_data.get('operating_margin', 0.10)
    if operating_margin is None or operating_margin == 0:
        operating_margin = 0.10  # Default 10%

    # Calculate WACC from beta
    beta = stock_data.get('beta', 1.0)
    if beta is None or beta == 0:
        beta = 1.0

    risk_free_rate = 0.045  # 4.5% for Saudi market
    equity_risk_premium = 0.065  # 6.5% market risk premium
    wacc = risk_free_rate + (beta * equity_risk_premium)

    return {
        'revenue_growth_rates': revenue_growth_rates,
        'operating_margin': operating_margin,
        'tax_rate': 0.20,  # Saudi corporate tax rate
        'wacc': wacc,
        'terminal_growth_rate': 0.025,  # 2.5% long-term growth
        'capex_pct_revenue': 0.03,  # 3% of revenue
    }


def format_dcf_for_display(dcf_result: Dict) -> Dict:
    """
    Format DCF results for display with appropriate units and precision.

    Converts large numbers to SAR millions, formats percentages, etc.

    Args:
        dcf_result: Dictionary with DCF calculation results

    Returns:
        Dictionary with formatted display strings
    """
    def format_currency(value: float, decimals: int = 1) -> str:
        """Format as SAR millions."""
        if value is None or np.isnan(value) or np.isinf(value):
            return "N/A"

        millions = value / 1_000_000
        if abs(millions) >= 1000:
            return f"SAR {millions/1000:.{decimals}f}B"
        return f"SAR {millions:.{decimals}f}M"

    def format_percentage(value: float, decimals: int = 1) -> str:
        """Format as percentage."""
        if value is None or np.isnan(value) or np.isinf(value):
            return "N/A"
        return f"{value:.{decimals}f}%"

    def format_price(value: float, decimals: int = 2) -> str:
        """Format as price."""
        if value is None or np.isnan(value) or np.isinf(value):
            return "N/A"
        return f"SAR {value:.{decimals}f}"

    # Format projected FCFs
    formatted_fcf = [format_currency(fcf) for fcf in dcf_result.get('projected_fcf', [])]

    # Format key metrics
    formatted_result = {
        'projected_fcf': formatted_fcf,
        'projected_fcf_raw': dcf_result.get('projected_fcf', []),
        'terminal_value': format_currency(dcf_result.get('terminal_value', 0)),
        'terminal_value_raw': dcf_result.get('terminal_value', 0),
        'enterprise_value': format_currency(dcf_result.get('enterprise_value', 0)),
        'enterprise_value_raw': dcf_result.get('enterprise_value', 0),
        'net_debt': format_currency(dcf_result.get('net_debt', 0)),
        'net_debt_raw': dcf_result.get('net_debt', 0),
        'equity_value': format_currency(dcf_result.get('equity_value', 0)),
        'equity_value_raw': dcf_result.get('equity_value', 0),
        'implied_price': format_price(dcf_result.get('implied_price', 0)),
        'implied_price_raw': dcf_result.get('implied_price', 0),
        'current_price': format_price(dcf_result.get('current_price', 0)),
        'current_price_raw': dcf_result.get('current_price', 0),
        'upside_pct': format_percentage(dcf_result.get('upside_pct', 0)),
        'upside_pct_raw': dcf_result.get('upside_pct', 0),
        'year_labels': dcf_result.get('year_labels', []),
    }

    # Format assumptions
    assumptions = dcf_result.get('assumptions', {})
    formatted_assumptions = {
        'revenue_growth_rates': [format_percentage(g * 100) for g in assumptions.get('revenue_growth_rates', [])],
        'operating_margin': format_percentage(assumptions.get('operating_margin', 0) * 100),
        'tax_rate': format_percentage(assumptions.get('tax_rate', 0) * 100),
        'wacc': format_percentage(assumptions.get('wacc', 0) * 100),
        'terminal_growth_rate': format_percentage(assumptions.get('terminal_growth_rate', 0) * 100),
        'capex_pct_revenue': format_percentage(assumptions.get('capex_pct_revenue', 0) * 100),
    }
    formatted_result['assumptions'] = formatted_assumptions

    return formatted_result


def format_sensitivity_for_display(sensitivity_result: Dict) -> Dict:
    """
    Format sensitivity analysis results for display.

    Args:
        sensitivity_result: Dictionary with sensitivity table data

    Returns:
        Dictionary with formatted display data
    """
    def format_price(value):
        """Format as price."""
        if value is None or (isinstance(value, float) and (np.isnan(value) or np.isinf(value))):
            return "N/A"
        return f"SAR {value:.2f}" if isinstance(value, (int, float)) else "N/A"

    wacc_values = sensitivity_result.get('wacc_values', [])
    terminal_values = sensitivity_result.get('terminal_values', [])
    matrix = sensitivity_result.get('matrix', [])

    # Format wacc and terminal values as percentages
    wacc_labels = [f"{w*100:.1f}%" for w in wacc_values]
    terminal_labels = [f"{t*100:.2f}%" for t in terminal_values]

    # Format matrix values
    formatted_matrix = []
    for row in matrix:
        formatted_row = [format_price(val) for val in row]
        formatted_matrix.append(formatted_row)

    return {
        'wacc_labels': wacc_labels,
        'terminal_labels': terminal_labels,
        'formatted_matrix': formatted_matrix,
        'raw_matrix': matrix,
    }


def format_scenarios_for_display(scenarios: Dict) -> Dict:
    """
    Format scenario analysis results for display.

    Args:
        scenarios: Dictionary with bull, base, bear scenario results

    Returns:
        Dictionary with formatted display results for each scenario
    """
    formatted_scenarios = {}

    for scenario_name in ['bull', 'base', 'bear']:
        if scenario_name in scenarios:
            formatted_scenarios[scenario_name] = format_dcf_for_display(scenarios[scenario_name])

    return formatted_scenarios
