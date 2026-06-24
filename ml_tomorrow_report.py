"""
ML Tomorrow Predictions — standalone forward-looking HTML email report (NASDAQ + NSE).

The forward-looking sibling of ml_bucket_report.py. Where that script BACK-TRACKS the
last 3 prediction days and scores their outcome against today's close, this script does
the opposite: it reports ONLY the single most recent set of ML classifier predictions
(S1) — i.e. the freshest signals, which look ahead to the next trading day — organized
by price bucket. There is NO outcome / goal / hit-rate, because tomorrow has not happened
yet. Two views are produced:

    * "S1 / S2 Both Aligned" — ML signal agrees with the AI ensemble direction.
    * "S1 Predictions Only"  — ML classifier signals on their own.

Each row shows the predicted direction, the model confidence, and the latest close price
the prediction is based on. Top-N per bucket are ranked by confidence.

Usage:
    py -3.12 ml_tomorrow_report.py --market nasdaq
    py -3.12 ml_tomorrow_report.py --market nse --dry-run
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

# Recipients for the Tomorrow Predictions emails — reuse the same distribution as the
# Bucket Tracker reports via BUCKET_REPORT_EMAIL_TO (comma-separated); defaults to the
# platform owner only.
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
        "from_name": "NASDAQ Tomorrow ML Predictions",
        "currency": "$",
        "ml_table": "ml_trading_predictions",
        "hist_table": "nasdaq_100_hist_data",
        "company_table": "nasdaq_top100",
    },
    "nse": {
        "market_name": "NSE 500",
        "from_name": "NSE Tomorrow ML Predictions",
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

# Top N predictions to show per price bucket (ranked by confidence).
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


# ---------------------------------------------------------------------------
# SQL access
# ---------------------------------------------------------------------------
def _connect():
    return pyodbc.connect(get_sql_connection_string())


def get_latest_pred_date(conn, cfg):
    """Return the most recent prediction date in the ML table (the forward-looking set)."""
    cur = conn.cursor()
    cur.execute(f"SELECT MAX(trading_date) FROM {cfg['ml_table']}")
    pred_date = _as_date(cur.fetchone()[0])
    cur.close()
    return pred_date


def fetch_signals(conn, cfg, pred_date):
    """Top-N-per-bucket S1 and S1^S2 rows for the single latest prediction date."""
    if not pred_date:
        return []

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
            WHERE ml.trading_date = ?
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
            WHERE ai.prediction_date = ?
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
                ROW_NUMBER() OVER (PARTITION BY f.price_category
                                   ORDER BY f.confidence_pct DESC, f.ticker) AS rn
            FROM flagged f
        ),
        ranked_s1s2 AS (
            SELECT 'S1S2' AS mode, f.*,
                ROW_NUMBER() OVER (PARTITION BY f.price_category
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
    cur.execute(sql, pred_date, pred_date)
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


# ---------------------------------------------------------------------------
# Assemble report structure
# ---------------------------------------------------------------------------
def _is_buy(signal):
    return signal.strip().upper().startswith("B")


def build_sections(cfg, pred_date, signals):
    """Build, per mode, a direction-count matrix + a single detail table per bucket."""
    currency = cfg["currency"]

    def fmt_price(p):
        return f"{currency}{p:,.2f}" if p is not None else "—"

    def fmt_conf(c):
        return f"{c:,.1f}%" if c is not None else "—"

    # Index signals: (mode, bucket) -> [rows] (already top-N, confidence DESC)
    index = {}
    for s in signals:
        index.setdefault((s["mode"], s["price_category"]), []).append(s)

    section_defs = [
        ("S1S2", "S1 ∧ S2 — Both Aligned",
         "ML classifier signal agrees with the AI ensemble direction (Buy+BULLISH or Sell+BEARISH). Highest conviction."),
        ("S1", "S1 Predictions Only",
         "ML classifier signals on their own, regardless of AI ensemble agreement."),
    ]

    sections = []
    for mode, title, subtitle in section_defs:
        # ---- Direction-count matrix: buckets (rows) x [Buy, Sell] (cols) ----
        matrix = []
        for b in BUCKETS:
            rows_b = index.get((mode, b), [])
            buy_n = sum(1 for s in rows_b if _is_buy(s["predicted_signal"]))
            sell_n = len(rows_b) - buy_n
            matrix.append({
                "bucket": f"{currency}{BUCKET_BOUNDS[b]}",
                "cells": [
                    {"text": str(buy_n) if buy_n else "—",
                     "color": "#27ae60" if buy_n else "#bbbbbb"},
                    {"text": str(sell_n) if sell_n else "—",
                     "color": "#e74c3c" if sell_n else "#bbbbbb"},
                ],
            })

        # ---- Detail: one row per top-N prediction, bucket as a column ----
        rows_out = []
        for b in BUCKETS:
            for s in index.get((mode, b), []):
                buy = _is_buy(s["predicted_signal"])
                rows_out.append({
                    "bucket": f"{currency}{BUCKET_BOUNDS[b]}",
                    "ticker": s["ticker"],
                    "direction": "Buy" if buy else "Sell",
                    "dir_color": "#27ae60" if buy else "#e74c3c",
                    "confidence": fmt_conf(s["confidence_pct"]),
                    "price": fmt_price(s["pred_day_price"]),
                })

        sections.append({
            "key": mode,
            "title": title,
            "subtitle": subtitle,
            "col_headers": ["Buy", "Sell"],
            "rows": rows_out,
        })
    return sections


def render_html(cfg, pred_date, sections):
    templates_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
    env = Environment(
        loader=FileSystemLoader(templates_dir),
        autoescape=select_autoescape(["html"]),
    )
    template = env.get_template("ml_tomorrow_report.html")
    return template.render(
        market_name=cfg["market_name"],
        pred_date_str=pred_date.strftime("%A, %B %d, %Y") if pred_date else "N/A",
        generated_at=datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        top_n=TOP_N_PER_BUCKET,
        sections=sections,
    )


# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------
def send_email(subject, html_body, from_name=None):
    if not REPORT_RECIPIENTS:
        raise RuntimeError("No Tomorrow Predictions recipients configured (set BUCKET_REPORT_EMAIL_TO).")

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
        pred_date = get_latest_pred_date(conn, cfg)
        if pred_date is None:
            print(f"[{market}] No predictions available (pred_date={pred_date}). Aborting.")
            return 1
        signals = fetch_signals(conn, cfg, pred_date)
    finally:
        conn.close()

    sections = build_sections(cfg, pred_date, signals)
    html = render_html(cfg, pred_date, sections)

    s1_count = sum(1 for s in signals if s["mode"] == "S1")
    s1s2_count = sum(1 for s in signals if s["mode"] == "S1S2")
    print(f"[{market}] pred_date={pred_date} | S1 rows={s1_count} S1^S2 rows={s1s2_count}")

    subject = f"{cfg['market_name']} ML Tomorrow Predictions — {pred_date.strftime('%b %d, %Y')}"

    if dry_run:
        out_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), f"out_tomorrow_{market}.html"
        )
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"[{market}] DRY RUN — wrote {out_path} (no email sent).")
        return 0

    n = send_email(subject, html, from_name=cfg.get("from_name"))
    print(f"[{market}] Email sent to {n} recipients: {subject}")
    return 0


def main():
    parser = argparse.ArgumentParser(description="ML Tomorrow Predictions email report.")
    parser.add_argument("--market", required=True, choices=["nasdaq", "nse"],
                        help="Which market to report on.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Write HTML to out_tomorrow_<market>.html instead of sending email.")
    args = parser.parse_args()
    sys.exit(run(args.market, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
