"""
ML Bucket Tracker — standalone daily HTML email report (NASDAQ + NSE).

Unlike the CrewAI daily briefing, this script talks to NOTHING but SQL Server and
SMTP — no Claude API, no agents. It reports how recent ML classifier predictions
(S1) performed, organized by price bucket, for the last 3 trading days a prediction
was made (PrevDay / PrevDay-1 / PrevDay-2). Two views are produced:

    * "S1 / S2 Both Aligned" — ML signal agrees with the AI ensemble direction.
    * "S1 Predictions Only"  — ML classifier signals on their own.

Each row shows the predicted direction, the price on the prediction day, every
subsequent closing price up to today, and a goal-met indicator (Buy hits if today's
close is higher than the prediction-day price; Sell hits if lower).

Usage:
    py -3.12 ml_bucket_report.py --market nasdaq
    py -3.12 ml_bucket_report.py --market nse --dry-run
"""

import argparse
import datetime
import os
import smtplib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import pyodbc
from jinja2 import Environment, FileSystemLoader, select_autoescape

from config.settings import (
    EMAIL_FROM,
    EMAIL_FROM_NAME,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_SERVER,
    SMTP_USERNAME,
    get_sql_connection_string,
)

# Recipients for the Bucket Tracker emails — intentionally SEPARATE from the
# shared daily_briefing distribution. Override via the BUCKET_REPORT_EMAIL_TO
# env var (comma-separated); defaults to the platform owner only.
REPORT_RECIPIENTS = [
    addr.strip()
    for addr in os.getenv("BUCKET_REPORT_EMAIL_TO", "sree.amiri@gmail.com").split(",")
    if addr.strip()
]

# ---------------------------------------------------------------------------
# Per-market configuration
# ---------------------------------------------------------------------------
MARKET_CONFIG = {
    "nasdaq": {
        "market_name": "NASDAQ 100",
        "from_name": "NASDAQ Back Tracking ML Predictions",
        "currency": "$",
        "ml_table": "ml_trading_predictions",
        "hist_table": "nasdaq_100_hist_data",
        "company_table": "nasdaq_top100",
    },
    "nse": {
        "market_name": "NSE 500",
        "from_name": "NSE Backtrack ML predictions",
        "currency": "₹",  # ₹
        "ml_table": "ml_nse_trading_predictions",
        "hist_table": "nse_500_hist_data",
        "company_table": "nse_500",
    },
}

# Price buckets (same numeric boundaries for both markets, per spec)
BUCKETS = ["Below20", "20-100", "100-200", "200+"]
BUCKET_BOUNDS = {  # display label suffix; currency prefix added at render time
    "Below20": "0–20",
    "20-100": "20–100",
    "100-200": "100–200",
    "200+": "200+",
}

# Display labels for each of the 3 prediction-day tables (most recent first)
PRED_DAY_LABELS = ["PrevDay", "PrevDay-1", "PrevDay-2"]

# Top N predictions to show per price bucket, per prediction day (ranked by confidence).
# The hit-rate matrix and the compact detail tables both summarize this same set.
TOP_N_PER_BUCKET = 5


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------
def _as_date(value):
    """Normalize a pyodbc date/datetime to datetime.date for stable comparison/keys."""
    if isinstance(value, datetime.datetime):
        return value.date()
    return value


def _fmt_date(d):
    """Short human label, e.g. 'Jun 12'."""
    return d.strftime("%b %d") if d else "—"


def _bucket_of(price):
    if price < 20:
        return "Below20"
    if price < 100:
        return "20-100"
    if price < 200:
        return "100-200"
    return "200+"


# ---------------------------------------------------------------------------
# SQL access
# ---------------------------------------------------------------------------
def _connect():
    return pyodbc.connect(get_sql_connection_string())


def get_dates(conn, cfg):
    """Return (today_close_date, [pred_d1, pred_d2, pred_d3]) — pred dates strictly < T0."""
    cur = conn.cursor()
    cur.execute(f"SELECT MAX(trading_date) FROM {cfg['hist_table']}")
    t0 = _as_date(cur.fetchone()[0])
    if t0 is None:
        return None, []

    cur.execute(
        f"SELECT DISTINCT TOP 3 trading_date FROM {cfg['ml_table']} "
        f"WHERE trading_date < ? ORDER BY trading_date DESC",
        t0,
    )
    pred_dates = [_as_date(r[0]) for r in cur.fetchall()]
    cur.close()
    return t0, pred_dates


def fetch_signals(conn, cfg, pred_dates):
    """Top-10-per-bucket S1 and S1^S2 rows for the given prediction dates."""
    if not pred_dates:
        return []

    placeholders = ", ".join("?" for _ in pred_dates)
    sql = f"""
        WITH s1 AS (
            SELECT
                ml.ticker,
                cm.company_name,
                ml.trading_date,
                ml.predicted_signal,
                ROUND(ml.confidence_percentage, 1) AS confidence_pct,
                TRY_CAST(ml.close_price AS FLOAT) AS pred_day_price,
                CASE
                    WHEN TRY_CAST(ml.close_price AS FLOAT) < 20 THEN 'Below20'
                    WHEN TRY_CAST(ml.close_price AS FLOAT) < 100 THEN '20-100'
                    WHEN TRY_CAST(ml.close_price AS FLOAT) < 200 THEN '100-200'
                    ELSE '200+'
                END AS price_category
            FROM {cfg['ml_table']} ml
            LEFT JOIN {cfg['company_table']} cm ON ml.ticker = cm.ticker
            WHERE ml.trading_date IN ({placeholders})
              AND TRY_CAST(ml.close_price AS FLOAT) IS NOT NULL
        ),
        s2 AS (
            SELECT
                ai.ticker,
                ai.prediction_date,
                MAX(CASE
                        WHEN ai.predicted_price > CAST(h.close_price AS FLOAT) THEN 'BULLISH'
                        WHEN ai.predicted_price < CAST(h.close_price AS FLOAT) THEN 'BEARISH'
                        ELSE 'NEUTRAL'
                    END) AS ai_direction
            FROM ai_prediction_history ai
            INNER JOIN {cfg['hist_table']} h
                ON ai.ticker = h.ticker AND ai.prediction_date = h.trading_date
            WHERE ai.prediction_date IN ({placeholders})
              AND ai.days_ahead = 7
              AND ai.model_name = 'Ensemble'
            GROUP BY ai.ticker, ai.prediction_date
        ),
        flagged AS (
            SELECT
                s1.ticker, s1.company_name, s1.trading_date, s1.predicted_signal,
                s1.confidence_pct, s1.pred_day_price, s1.price_category,
                CASE
                    WHEN (s1.predicted_signal IN ('Buy', 'BUY') AND s2.ai_direction = 'BULLISH')
                      OR (s1.predicted_signal IN ('Sell', 'SELL') AND s2.ai_direction = 'BEARISH')
                    THEN 1 ELSE 0
                END AS is_aligned
            FROM s1
            LEFT JOIN s2 ON s1.ticker = s2.ticker AND s1.trading_date = s2.prediction_date
        ),
        ranked_s1 AS (
            SELECT 'S1' AS mode, f.*,
                ROW_NUMBER() OVER (PARTITION BY f.trading_date, f.price_category
                                   ORDER BY f.confidence_pct DESC, f.ticker) AS rn
            FROM flagged f
        ),
        ranked_s1s2 AS (
            SELECT 'S1S2' AS mode, f.*,
                ROW_NUMBER() OVER (PARTITION BY f.trading_date, f.price_category
                                   ORDER BY f.confidence_pct DESC, f.ticker) AS rn
            FROM flagged f
            WHERE f.is_aligned = 1
        )
        SELECT mode, trading_date, price_category, ticker, company_name,
               predicted_signal, confidence_pct, pred_day_price, is_aligned
        FROM ranked_s1 WHERE rn <= {TOP_N_PER_BUCKET}
        UNION ALL
        SELECT mode, trading_date, price_category, ticker, company_name,
               predicted_signal, confidence_pct, pred_day_price, is_aligned
        FROM ranked_s1s2 WHERE rn <= {TOP_N_PER_BUCKET}
    """
    cur = conn.cursor()
    cur.execute(sql, *(pred_dates + pred_dates))
    rows = []
    for r in cur.fetchall():
        rows.append({
            "mode": r.mode,
            "trading_date": _as_date(r.trading_date),
            "price_category": r.price_category,
            "ticker": r.ticker,
            "company_name": r.company_name,
            "predicted_signal": (r.predicted_signal or "").strip(),
            "confidence_pct": r.confidence_pct,
            "pred_day_price": r.pred_day_price,
            "is_aligned": r.is_aligned,
        })
    cur.close()
    return rows


def fetch_closes(conn, cfg, window_dates):
    """Map {(ticker, date): close_price} for all tickers on the window's trading dates."""
    if not window_dates:
        return {}
    placeholders = ", ".join("?" for _ in window_dates)
    cur = conn.cursor()
    cur.execute(
        f"SELECT ticker, trading_date, CAST(close_price AS FLOAT) "
        f"FROM {cfg['hist_table']} WHERE trading_date IN ({placeholders})",
        *window_dates,
    )
    closes = {}
    for ticker, td, close in cur.fetchall():
        closes[(ticker, _as_date(td))] = close
    cur.close()
    return closes


# ---------------------------------------------------------------------------
# Assemble report structure
# ---------------------------------------------------------------------------
def _is_buy(signal):
    return signal.strip().upper().startswith("B")


def _goal_met(signal, pred_price, t0_close):
    """True if the prediction's goal was met by today's close, None if undeterminable."""
    if t0_close is None or pred_price is None:
        return None
    return (t0_close > pred_price) if _is_buy(signal) else (t0_close < pred_price)


def _hitrate_color(pct):
    if pct >= 60:
        return "#27ae60"
    if pct >= 40:
        return "#e67e22"
    return "#e74c3c"


def build_sections(cfg, t0, pred_dates, signals, closes):
    """Build the hybrid structure: a hit-rate matrix + compact detail tables per section."""
    currency = cfg["currency"]
    today_str = _fmt_date(t0)

    def fmt_price(p):
        return f"{currency}{p:,.2f}" if p is not None else "—"

    # Index signals: (mode, pred_date, bucket) -> [rows] (already top-N, confidence DESC)
    index = {}
    for s in signals:
        index.setdefault((s["mode"], s["trading_date"], s["price_category"]), []).append(s)

    section_defs = [
        ("S1S2", "S1 ∧ S2 — Both Aligned",
         "ML classifier signal agrees with the AI ensemble direction (Buy+BULLISH or Sell+BEARISH). Highest conviction."),
        ("S1", "S1 Predictions Only",
         "ML classifier signals on their own, regardless of AI ensemble agreement."),
    ]

    # Matrix column headers, one per prediction day (most recent first)
    col_headers = [f"{lbl} ({_fmt_date(d)})" for lbl, d in zip(PRED_DAY_LABELS, pred_dates)]

    sections = []
    for mode, title, subtitle in section_defs:
        # ---- Hit-rate matrix: buckets (rows) x prediction days (cols) ----
        matrix = []
        for b in BUCKETS:
            cells = []
            for pred_date in pred_dates:
                met = total = 0
                for s in index.get((mode, pred_date, b), []):
                    g = _goal_met(s["predicted_signal"], s["pred_day_price"], closes.get((s["ticker"], t0)))
                    if g is None:
                        continue
                    total += 1
                    met += 1 if g else 0
                if total == 0:
                    cells.append({"text": "—", "color": "#bbbbbb"})
                else:
                    pct = round(100 * met / total)
                    cells.append({"text": f"{met}/{total} · {pct}%", "color": _hitrate_color(pct)})
            matrix.append({"bucket": f"{currency}{BUCKET_BOUNDS[b]}", "cells": cells})

        # ---- Compact detail: one table per prediction day, bucket as a column ----
        day_tables = []
        for label, pred_date in zip(PRED_DAY_LABELS, pred_dates):
            rows_out = []
            for b in BUCKETS:
                for s in index.get((mode, pred_date, b), []):
                    buy = _is_buy(s["predicted_signal"])
                    t0_close = closes.get((s["ticker"], t0))
                    g = _goal_met(s["predicted_signal"], s["pred_day_price"], t0_close)
                    goal = "—" if g is None else ("✓" if g else "✗")
                    goal_color = "#7f8c8d" if g is None else ("#27ae60" if g else "#e74c3c")
                    rows_out.append({
                        "bucket": f"{currency}{BUCKET_BOUNDS[b]}",
                        "ticker": s["ticker"],
                        "direction": "Buy" if buy else "Sell",
                        "dir_color": "#27ae60" if buy else "#e74c3c",
                        "price": fmt_price(s["pred_day_price"]),
                        "today": fmt_price(t0_close),
                        "goal": goal,
                        "goal_color": goal_color,
                    })
            day_tables.append({
                "label": label,
                "pred_date_str": _fmt_date(pred_date),
                "rows": rows_out,
            })

        sections.append({
            "key": mode,
            "title": title,
            "subtitle": subtitle,
            "col_headers": col_headers,
            "today_str": today_str,
            "matrix": matrix,
            "day_tables": day_tables,
        })
    return sections


def render_html(cfg, t0, pred_dates, sections):
    templates_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
    env = Environment(
        loader=FileSystemLoader(templates_dir),
        autoescape=select_autoescape(["html"]),
    )
    template = env.get_template("ml_bucket_report.html")
    return template.render(
        market_name=cfg["market_name"],
        report_date=t0.strftime("%A, %B %d, %Y") if t0 else "N/A",
        generated_at=datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        top_n=TOP_N_PER_BUCKET,
        sections=sections,
    )


# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------
def send_email(subject, html_body, from_name=None):
    if not REPORT_RECIPIENTS:
        raise RuntimeError("No Bucket Tracker recipients configured (set BUCKET_REPORT_EMAIL_TO).")

    display_name = from_name or EMAIL_FROM_NAME
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{display_name} <{EMAIL_FROM}>" if display_name else EMAIL_FROM
    msg["To"] = ", ".join(REPORT_RECIPIENTS)
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.sendmail(EMAIL_FROM, REPORT_RECIPIENTS, msg.as_string())
    return len(REPORT_RECIPIENTS)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def run(market, dry_run=False):
    cfg = MARKET_CONFIG[market]
    conn = _connect()
    try:
        t0, pred_dates = get_dates(conn, cfg)
        if t0 is None or not pred_dates:
            print(f"[{market}] No data available (t0={t0}, pred_dates={pred_dates}). Aborting.")
            return 1
        signals = fetch_signals(conn, cfg, pred_dates)
        window_dates = sorted(set(pred_dates) | {t0})
        closes = fetch_closes(conn, cfg, window_dates)
    finally:
        conn.close()

    sections = build_sections(cfg, t0, pred_dates, signals, closes)
    html = render_html(cfg, t0, pred_dates, sections)

    s1_count = sum(1 for s in signals if s["mode"] == "S1")
    s1s2_count = sum(1 for s in signals if s["mode"] == "S1S2")
    print(f"[{market}] T0={t0} pred_dates={pred_dates} | S1 rows={s1_count} S1^S2 rows={s1s2_count}")

    subject = f"{cfg['market_name']} ML Bucket Tracker — {t0.strftime('%b %d, %Y')}"

    if dry_run:
        out_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), f"out_{market}.html"
        )
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"[{market}] DRY RUN — wrote {out_path} (no email sent).")
        return 0

    n = send_email(subject, html, from_name=cfg.get("from_name"))
    print(f"[{market}] Email sent to {n} recipients: {subject}")
    return 0


def main():
    parser = argparse.ArgumentParser(description="ML Bucket Tracker daily email report.")
    parser.add_argument("--market", required=True, choices=["nasdaq", "nse"],
                        help="Which market to report on.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Write HTML to out_<market>.html instead of sending email.")
    args = parser.parse_args()
    sys.exit(run(args.market, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
