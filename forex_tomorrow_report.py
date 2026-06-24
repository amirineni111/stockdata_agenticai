"""
Forex ML Tomorrow Predictions — standalone forward-looking HTML email report (Forex).

The forward-looking sibling of forex_bucket_report.py. Like that script it talks to
NOTHING but SQL Server and SMTP — no Claude API, no agents. Where the bucket report
BACK-TRACKS the last 3 prediction days and scores outcomes, this script reports ONLY
the single most recent set of Forex ML classifier predictions (Strategy 1) — the
freshest signals, which look ahead to the next trading day. There is NO outcome / goal,
because tomorrow has not happened yet.

Forex only has Strategy 1 (there is no AI ensemble / S2 for forex), so there is a SINGLE
section. Predictions are grouped by signal DIRECTION (Buy / Sell) rather than price bucket
— forex pairs span very different price scales (EURUSD ~1.08 vs USDJPY ~150), so price
buckets are meaningless. HOLD signals are excluded (no directional view).

Each row shows the predicted direction, the model confidence, and the latest close price
the prediction is based on.

Usage:
    py -3.12 forex_tomorrow_report.py
    py -3.12 forex_tomorrow_report.py --dry-run
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

# Recipients for the Tomorrow Predictions emails — shared with the NASDAQ/NSE reports via
# the BUCKET_REPORT_EMAIL_TO env var (comma-separated); defaults to the platform owner only.
REPORT_RECIPIENTS = [
    addr.strip()
    for addr in os.getenv("BUCKET_REPORT_EMAIL_TO", "sree.amiri@gmail.com").split(",")
    if addr.strip()
]

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
CFG = {
    "market_name": "Forex",
    "from_name": "Forex Tomorrow ML Predictions",
    "currency": "",  # forex prices carry no single currency symbol
    "ml_table": "forex_ml_predictions",
}

# Grid rows = signal direction (replaces the price buckets of the NASDAQ/NSE report)
DIRECTIONS = ["Buy", "Sell"]


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
    # prediction_date is a datetime (carries a time component) — compare on date only.
    cur.execute(f"SELECT MAX(CAST(prediction_date AS DATE)) FROM {cfg['ml_table']}")
    pred_date = _as_date(cur.fetchone()[0])
    cur.close()
    return pred_date


def fetch_signals(conn, cfg, pred_date):
    """One row per pair for BUY/SELL forex ML predictions on the latest prediction date."""
    if not pred_date:
        return []

    sql = f"""
        SELECT
            CASE WHEN predicted_signal IN ('Buy', 'BUY') THEN 'Buy' ELSE 'Sell' END AS direction,
            currency_pair AS ticker,
            ROUND(CAST(signal_confidence AS FLOAT) * 100, 1) AS confidence_pct,
            CAST(close_price AS FLOAT) AS pred_day_price
        FROM {cfg['ml_table']}
        WHERE CAST(prediction_date AS DATE) = ?
          AND predicted_signal IN ('Buy', 'BUY', 'Sell', 'SELL')
          AND close_price IS NOT NULL
    """
    cur = conn.cursor()
    cur.execute(sql, pred_date)
    rows = []
    for r in cur.fetchall():
        rows.append({
            "direction": r.direction,
            "ticker": r.ticker,
            "predicted_signal": r.direction,  # already normalized to Buy/Sell
            "confidence_pct": r.confidence_pct,
            "pred_day_price": r.pred_day_price,
        })
    cur.close()
    return rows


# ---------------------------------------------------------------------------
# Assemble report structure
# ---------------------------------------------------------------------------
def _is_buy(signal):
    return signal.strip().upper().startswith("B")


def build_sections(cfg, pred_date, signals):
    """Build the single S1 section: a direction-count matrix + one detail table."""

    def fmt_price(p):
        return f"{p:,.4f}" if p is not None else "—"

    def fmt_conf(c):
        return f"{c:,.1f}%" if c is not None else "—"

    # Index signals: direction -> [rows]
    index = {}
    for s in signals:
        index.setdefault(s["direction"], []).append(s)

    # ---- Direction-count matrix: direction (rows) x [Count] (col) ----
    matrix = []
    for direction in DIRECTIONS:
        n = len(index.get(direction, []))
        matrix.append({
            "bucket": direction,
            "cells": [
                {"text": str(n) if n else "—",
                 "color": ("#27ae60" if direction == "Buy" else "#e74c3c") if n else "#bbbbbb"},
            ],
        })

    # ---- Detail: one row per pair, ordered by direction then confidence ----
    rows_out = []
    for direction in DIRECTIONS:
        day_rows = sorted(
            index.get(direction, []),
            key=lambda s: (s["confidence_pct"] or 0),
            reverse=True,
        )
        for s in day_rows:
            buy = _is_buy(s["predicted_signal"])
            rows_out.append({
                "bucket": direction,
                "ticker": s["ticker"],
                "direction": "Buy" if buy else "Sell",
                "dir_color": "#27ae60" if buy else "#e74c3c",
                "confidence": fmt_conf(s["confidence_pct"]),
                "price": fmt_price(s["pred_day_price"]),
            })

    section = {
        "key": "S1",
        "title": "S1 Predictions Only",
        "subtitle": "Forex ML classifier Buy/Sell signals, grouped by direction. HOLD signals excluded.",
        "col_headers": ["Count"],
        "rows": rows_out,
    }
    return [section]


def render_html(cfg, pred_date, sections):
    templates_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
    env = Environment(
        loader=FileSystemLoader(templates_dir),
        autoescape=select_autoescape(["html"]),
    )
    template = env.get_template("forex_tomorrow_report.html")
    return template.render(
        market_name=cfg["market_name"],
        pred_date_str=pred_date.strftime("%A, %B %d, %Y") if pred_date else "N/A",
        generated_at=datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
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
def run(dry_run=False):
    cfg = CFG
    conn = _connect()
    try:
        pred_date = get_latest_pred_date(conn, cfg)
        if pred_date is None:
            print(f"[forex] No predictions available (pred_date={pred_date}). Aborting.")
            return 1
        signals = fetch_signals(conn, cfg, pred_date)
    finally:
        conn.close()

    sections = build_sections(cfg, pred_date, signals)
    html = render_html(cfg, pred_date, sections)

    buy_count = sum(1 for s in signals if s["direction"] == "Buy")
    sell_count = sum(1 for s in signals if s["direction"] == "Sell")
    print(f"[forex] pred_date={pred_date} | Buy rows={buy_count} Sell rows={sell_count}")

    subject = f"{cfg['market_name']} ML Tomorrow Predictions — {pred_date.strftime('%b %d, %Y')}"

    if dry_run:
        out_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "out_tomorrow_forex.html"
        )
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"[forex] DRY RUN — wrote {out_path} (no email sent).")
        return 0

    n = send_email(subject, html, from_name=cfg.get("from_name"))
    print(f"[forex] Email sent to {n} recipients: {subject}")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Forex ML Tomorrow Predictions email report.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Write HTML to out_tomorrow_forex.html instead of sending email.")
    args = parser.parse_args()
    sys.exit(run(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
