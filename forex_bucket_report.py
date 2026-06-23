"""
Forex ML Bucket Tracker — standalone daily HTML email report (Forex).

The Forex sibling of ml_bucket_report.py. Like that script it talks to NOTHING
but SQL Server and SMTP — no Claude API, no agents. It reports how recent Forex
ML classifier predictions (Strategy 1) performed, for the last 3 trading days a
prediction was made (PrevDay / PrevDay-1 / PrevDay-2).

Forex only has Strategy 1 (there is no AI ensemble / S2 for forex), so there is
a SINGLE section. Predictions are grouped by signal DIRECTION (Buy / Sell) rather
than price bucket — forex pairs span very different price scales (EURUSD ~1.08 vs
USDJPY ~150), so price buckets are meaningless. HOLD signals are excluded (no
directional win/loss).

Each row shows the predicted direction, the close price on the prediction day,
today's close, and a goal-met indicator (Buy hits if today's close is higher than
the prediction-day price; Sell hits if lower).

Usage:
    py -3.12 forex_bucket_report.py
    py -3.12 forex_bucket_report.py --dry-run
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

# Recipients for the Bucket Tracker emails — shared with the NASDAQ/NSE bucket
# reports via the BUCKET_REPORT_EMAIL_TO env var (comma-separated); defaults to
# the platform owner only.
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
    "from_name": "Forex Back Tracking ML Predictions",
    "currency": "",  # forex prices carry no single currency symbol
    "ml_table": "forex_ml_predictions",
    "hist_table": "forex_hist_data",
}

# Grid rows = signal direction (replaces the price buckets of the NASDAQ/NSE report)
DIRECTIONS = ["Buy", "Sell"]

# Display labels for each of the 3 prediction-day tables (most recent first)
PRED_DAY_LABELS = ["PrevDay", "PrevDay-1", "PrevDay-2"]


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


def get_dates(conn, cfg):
    """Return (today_close_date, [pred_d1, pred_d2, pred_d3]) — pred dates strictly < T0."""
    cur = conn.cursor()
    cur.execute(f"SELECT MAX(trading_date) FROM {cfg['hist_table']}")
    t0 = _as_date(cur.fetchone()[0])
    if t0 is None:
        return None, []

    # prediction_date is a datetime (carries a time component) — compare on date only.
    cur.execute(
        f"SELECT DISTINCT TOP 3 CAST(prediction_date AS DATE) "
        f"FROM {cfg['ml_table']} "
        f"WHERE CAST(prediction_date AS DATE) < ? "
        f"ORDER BY CAST(prediction_date AS DATE) DESC",
        t0,
    )
    pred_dates = [_as_date(r[0]) for r in cur.fetchall()]
    cur.close()
    return t0, pred_dates


def fetch_signals(conn, cfg, pred_dates):
    """One row per pair/day for BUY/SELL forex ML predictions on the given dates."""
    if not pred_dates:
        return []

    placeholders = ", ".join("?" for _ in pred_dates)
    sql = f"""
        SELECT
            'S1' AS mode,
            CAST(prediction_date AS DATE) AS trading_date,
            CASE WHEN predicted_signal IN ('Buy', 'BUY') THEN 'Buy' ELSE 'Sell' END AS direction,
            currency_pair AS ticker,
            ROUND(CAST(signal_confidence AS FLOAT) * 100, 1) AS confidence_pct,
            CAST(close_price AS FLOAT) AS pred_day_price
        FROM {cfg['ml_table']}
        WHERE CAST(prediction_date AS DATE) IN ({placeholders})
          AND predicted_signal IN ('Buy', 'BUY', 'Sell', 'SELL')
          AND close_price IS NOT NULL
    """
    cur = conn.cursor()
    cur.execute(sql, *pred_dates)
    rows = []
    for r in cur.fetchall():
        rows.append({
            "mode": r.mode,
            "trading_date": _as_date(r.trading_date),
            "direction": r.direction,
            "ticker": r.ticker,
            "predicted_signal": r.direction,  # already normalized to Buy/Sell
            "confidence_pct": r.confidence_pct,
            "pred_day_price": r.pred_day_price,
        })
    cur.close()
    return rows


def fetch_closes(conn, cfg, window_dates):
    """Map {(symbol, date): close_price} for all pairs on the window's trading dates."""
    if not window_dates:
        return {}
    placeholders = ", ".join("?" for _ in window_dates)
    cur = conn.cursor()
    cur.execute(
        f"SELECT symbol, trading_date, CAST(close_price AS FLOAT) "
        f"FROM {cfg['hist_table']} WHERE trading_date IN ({placeholders})",
        *window_dates,
    )
    closes = {}
    for symbol, td, close in cur.fetchall():
        closes[(symbol, _as_date(td))] = close
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
    """Build the single S1 section: a hit-rate matrix + compact detail tables."""
    today_str = _fmt_date(t0)

    def fmt_price(p):
        return f"{p:,.4f}" if p is not None else "—"

    # Index signals: (pred_date, direction) -> [rows]
    index = {}
    for s in signals:
        index.setdefault((s["trading_date"], s["direction"]), []).append(s)

    # Matrix column headers, one per prediction day (most recent first)
    col_headers = [f"{lbl} ({_fmt_date(d)})" for lbl, d in zip(PRED_DAY_LABELS, pred_dates)]

    # ---- Hit-rate matrix: direction (rows) x prediction days (cols) ----
    matrix = []
    for direction in DIRECTIONS:
        cells = []
        for pred_date in pred_dates:
            met = total = 0
            for s in index.get((pred_date, direction), []):
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
        matrix.append({"bucket": direction, "cells": cells})

    # ---- Compact detail: one table per prediction day, direction as a column ----
    day_tables = []
    for label, pred_date in zip(PRED_DAY_LABELS, pred_dates):
        rows_out = []
        for direction in DIRECTIONS:
            # Show pairs ordered by model confidence (highest first)
            day_rows = sorted(
                index.get((pred_date, direction), []),
                key=lambda s: (s["confidence_pct"] or 0),
                reverse=True,
            )
            for s in day_rows:
                buy = _is_buy(s["predicted_signal"])
                t0_close = closes.get((s["ticker"], t0))
                g = _goal_met(s["predicted_signal"], s["pred_day_price"], t0_close)
                goal = "—" if g is None else ("✓" if g else "✗")
                goal_color = "#7f8c8d" if g is None else ("#27ae60" if g else "#e74c3c")
                rows_out.append({
                    "bucket": direction,
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

    section = {
        "key": "S1",
        "title": "S1 Predictions Only",
        "subtitle": "Forex ML classifier Buy/Sell signals, grouped by direction. HOLD signals excluded.",
        "col_headers": col_headers,
        "today_str": today_str,
        "matrix": matrix,
        "day_tables": day_tables,
    }
    return [section]


def render_html(cfg, t0, pred_dates, sections):
    templates_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
    env = Environment(
        loader=FileSystemLoader(templates_dir),
        autoescape=select_autoescape(["html"]),
    )
    template = env.get_template("forex_bucket_report.html")
    return template.render(
        market_name=cfg["market_name"],
        report_date=t0.strftime("%A, %B %d, %Y") if t0 else "N/A",
        generated_at=datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
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
def run(dry_run=False):
    cfg = CFG
    conn = _connect()
    try:
        t0, pred_dates = get_dates(conn, cfg)
        if t0 is None or not pred_dates:
            print(f"[forex] No data available (t0={t0}, pred_dates={pred_dates}). Aborting.")
            return 1
        signals = fetch_signals(conn, cfg, pred_dates)
        window_dates = sorted(set(pred_dates) | {t0})
        closes = fetch_closes(conn, cfg, window_dates)
    finally:
        conn.close()

    sections = build_sections(cfg, t0, pred_dates, signals, closes)
    html = render_html(cfg, t0, pred_dates, sections)

    buy_count = sum(1 for s in signals if s["direction"] == "Buy")
    sell_count = sum(1 for s in signals if s["direction"] == "Sell")
    print(f"[forex] T0={t0} pred_dates={pred_dates} | Buy rows={buy_count} Sell rows={sell_count}")

    subject = f"{cfg['market_name']} ML Bucket Tracker — {t0.strftime('%b %d, %Y')}"

    if dry_run:
        out_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "out_forex.html"
        )
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"[forex] DRY RUN — wrote {out_path} (no email sent).")
        return 0

    n = send_email(subject, html, from_name=cfg.get("from_name"))
    print(f"[forex] Email sent to {n} recipients: {subject}")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Forex ML Bucket Tracker daily email report.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Write HTML to out_forex.html instead of sending email.")
    args = parser.parse_args()
    sys.exit(run(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
