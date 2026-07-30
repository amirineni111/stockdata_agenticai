"""
No-LLM fallback report builder.

When the Anthropic API is unavailable (credit/token limit exhausted, auth
failure, outage), the daily briefing still needs to go out. This module runs
the same predefined SQL queries the CrewAI agents would run and renders the
results directly into HTML tables — no Claude analysis, just the raw data in a
clean, readable format that drops into the existing email template.

Each briefing section maps to one or more predefined queries. For very wide
result sets (e.g. the consolidated forex query) a curated column subset is
displayed so the tables stay email-friendly.
"""

import pyodbc

from config.settings import get_sql_connection_string
from config.sql_queries import (
    MARKET_INTEL_QUERIES,
    ML_ANALYST_QUERIES,
    TECH_SIGNAL_QUERIES,
    STRATEGY_TRADE_QUERIES,
    FOREX_QUERIES,
    RISK_QUERIES,
    CROSS_STRATEGY_QUERIES,
)

# ---------------------------------------------------------------------------
# Section -> queries mapping
# Each entry: (block_title, sql, display_columns_or_None)
# display_columns limits/orders which columns are shown (case-insensitive).
# ---------------------------------------------------------------------------

_FOREX_DISPLAY_COLS = [
    "symbol", "close_price", "daily_change_pct", "rsi", "rsi_signal",
    "macd_signal", "bb_signal", "stoch_signal", "tech_consensus",
    "ml_signal", "ml_confidence_pct", "tech_ml_agreement",
    "support_level", "resistance_level",
]

SECTIONS: dict[str, list[tuple]] = {
    "market_overview": [
        ("NASDAQ Market Breadth", MARKET_INTEL_QUERIES["nasdaq_market_summary"], None),
        ("NSE Market Breadth", MARKET_INTEL_QUERIES["nse_market_summary"], None),
        ("NASDAQ Top Movers", MARKET_INTEL_QUERIES["nasdaq_top_movers"], None),
        ("NSE Top Movers", MARKET_INTEL_QUERIES["nse_top_movers"], None),
    ],
    "ml_model_health": [
        ("AI Price-Predictor Accuracy (7d)", ML_ANALYST_QUERIES["model_accuracy_last_7_days"], None),
        ("NASDAQ ML Classifier Summary", ML_ANALYST_QUERIES["strategy1_nasdaq_ml_summary"], None),
        ("NSE ML Classifier Summary", ML_ANALYST_QUERIES["strategy1_nse_ml_summary"], None),
        ("Forex ML Signal Summary", ML_ANALYST_QUERIES["strategy1_forex_ml_summary"], None),
    ],
    "trade_opportunities": [
        ("Tier Summary (by Market)", STRATEGY_TRADE_QUERIES["tier_summary_today"], None),
        ("Top TIER 1 Opportunities", STRATEGY_TRADE_QUERIES["top_tier1_opportunities"], None),
        ("Top TIER 2 Opportunities", STRATEGY_TRADE_QUERIES["top_tier2_opportunities"], None),
    ],
    "tech_signals": [
        ("Active Signals Today", TECH_SIGNAL_QUERIES["active_signals_today"], None),
    ],
    "forex_outlook": [
        ("Forex Technical + ML Dashboard", FOREX_QUERIES["forex_comprehensive_analysis"], _FOREX_DISPLAY_COLS),
    ],
    "risk_warnings": [
        ("Conflicting ML vs Technical Signals", RISK_QUERIES["high_risk_positions"], None),
        ("Cross-Strategy Direction Conflicts", RISK_QUERIES["conflicting_signals"], None),
    ],
    "cross_strategy": [
        ("NSE 500 Aligned (both strategies agree)", CROSS_STRATEGY_QUERIES["nse_all_categories"], None),
        ("NASDAQ 100 Aligned (both strategies agree)", CROSS_STRATEGY_QUERIES["nasdaq_all_categories"], None),
    ],
}


def _run_query(sql: str) -> tuple[list[str], list[tuple]]:
    """Execute a read-only query and return (columns, rows). Raises on error."""
    conn = pyodbc.connect(get_sql_connection_string())
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        return columns, [tuple(r) for r in rows]
    finally:
        conn.close()


def _fmt(value) -> str:
    """Format a single cell value for display."""
    if value is None:
        return "-"
    if isinstance(value, float):
        # Trim needless trailing zeros while keeping small values readable.
        return f"{value:,.4f}".rstrip("0").rstrip(".") if abs(value) < 1 else f"{value:,.2f}"
    return str(value)


def _render_table(title: str, columns: list[str], rows: list[tuple],
                  display_columns: list[str] | None) -> str:
    """Render a single result set as a styled HTML table block."""
    # Optionally filter/reorder to a curated column subset.
    if display_columns:
        lower_map = {c.lower(): i for i, c in enumerate(columns)}
        idxs = [lower_map[c.lower()] for c in display_columns if c.lower() in lower_map]
        columns = [columns[i] for i in idxs]
        rows = [tuple(r[i] for i in idxs) for r in rows]

    header = (
        f'<p style="margin:14px 0 6px 0; font-weight:bold; color:#2c3e50; '
        f'font-size:14px;">{title}</p>'
    )

    if not rows:
        return header + (
            '<p style="margin:0 0 10px 0; color:#7f8c8d; font-size:12px;">'
            "No rows returned.</p>"
        )

    th_style = (
        "padding:6px 8px; font-size:11px; font-weight:bold; text-align:left; "
        "background-color:#2c3e50; color:#ffffff; border:1px solid #dee2e6; "
        "white-space:nowrap;"
    )
    td_style = (
        "padding:5px 8px; font-size:11px; border:1px solid #dee2e6; "
        "color:#333; white-space:nowrap;"
    )

    head_cells = "".join(f'<th style="{th_style}">{c}</th>' for c in columns)
    body_rows = []
    for i, row in enumerate(rows):
        bg = "#ffffff" if i % 2 == 0 else "#f8f9fa"
        cells = "".join(
            f'<td style="{td_style} background-color:{bg};">{_fmt(v)}</td>'
            for v in row
        )
        body_rows.append(f"<tr>{cells}</tr>")

    table = (
        '<div style="overflow-x:auto;">'
        '<table cellpadding="0" cellspacing="0" '
        'style="border-collapse:collapse; width:100%; margin:0 0 12px 0;">'
        f"<tr>{head_cells}</tr>"
        f'{"".join(body_rows)}'
        "</table></div>"
    )
    return header + table


def _render_section(section_key: str) -> str:
    """Render all query blocks for one briefing section into HTML."""
    blocks = SECTIONS.get(section_key, [])
    parts = []
    for title, sql, display_cols in blocks:
        try:
            columns, rows = _run_query(sql)
            parts.append(_render_table(title, columns, rows, display_cols))
        except Exception as e:
            parts.append(
                f'<p style="margin:14px 0 6px 0; font-weight:bold; color:#2c3e50; '
                f'font-size:14px;">{title}</p>'
                f'<p style="margin:0 0 10px 0; color:#e74c3c; font-size:12px;">'
                f"Data unavailable ({type(e).__name__}: {str(e)[:120]}).</p>"
            )
    return "\n".join(parts) if parts else (
        '<p style="color:#7f8c8d; font-size:12px;">No data configured.</p>'
    )


def build_data_only_sections() -> dict[str, str]:
    """Build the HTML for every briefing section directly from SQL (no LLM).

    Returns a dict keyed by the Jinja2 template variables used in
    briefing_email.html.
    """
    return {key: _render_section(key) for key in SECTIONS}
