"""
Weekly Stock Screening Report — standalone Excel-attachment email report.

Unlike the CrewAI daily briefing, this script talks to NOTHING but SQL Server and
SMTP — no Claude API, no agents. It exports the latest weekly snapshot of 7
fundamental screening views (growth, GARP, value, quality, fundamental scoring,
fair value, dividend) for one market (NASDAQ or NSE), plus a week-over-week
Top 10 Gain / Top 10 Loss workbook per view (ranked by that view's own score
column moving up or down vs. the prior snapshot). That's 2 Excel files per view,
14 files total, attached to a single summary email. Files are deleted after the
email sends successfully; on failure or --dry-run they are left in exports/.

Views used (all live in dbo, joined on ticker across weekly fetch_date snapshots):
    vw_growth_stocks_screen      -> growth_score      / growth_category
    vw_garp_stocks_screen        -> garp_score         / garp_signal
    vw_value_stocks_screen       -> value_score        / valuation_category
    vw_quality_stocks_screen     -> quality_score      / quality_category
    vw_fundamental_scoring       -> total_score        / overall_rating   (no market col — derived from ticker suffix: .NS/.BO = NSE)
    vw_fair_value_estimates      -> margin_of_safety_pct / valuation_verdict
    vw_dividend_stocks_screen    -> dividend_score     / dividend_category (no market col — derived from ticker suffix: .NS/.BO = NSE)

Usage:
    py -3.12 weekly_screening_report.py --market nasdaq
    py -3.12 weekly_screening_report.py --market nse --dry-run
"""

import argparse
import datetime
import os
import smtplib
import sys
import warnings
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import pandas as pd
import pyodbc

from config.settings import (
    EMAIL_FROM,
    EMAIL_FROM_NAME,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_SERVER,
    SMTP_USERNAME,
    get_sql_connection_string,
)

warnings.filterwarnings("ignore", message=".*pandas only supports SQLAlchemy.*")

EXPORT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exports")

# Ticker suffix used to tell NSE apart from NASDAQ in the 2 views that don't
# carry their own `market` column (fundamental scoring, dividend screen).
# nse_500 tickers are 100% covered by .NS (2071) or the one legacy .BO ticker
# (TAPARIA.BO); nasdaq_top100 tickers never carry a dot suffix.
MARKET_EXPR_DERIVED = "CASE WHEN ticker LIKE '%.NS' OR ticker LIKE '%.BO' THEN 'NSE' ELSE 'NASDAQ' END"

MARKET_CONFIG = {
    "nasdaq": {
        "market_value": "NASDAQ",
        "market_name": "NASDAQ 100",
        "from_name": "NASDAQ Weekly Screening Report",
        "recipients_env": "SCREENING_REPORT_EMAIL_TO_NASDAQ",
    },
    "nse": {
        "market_value": "NSE",
        "market_name": "NSE 500",
        "from_name": "NSE Weekly Screening Report",
        "recipients_env": "SCREENING_REPORT_EMAIL_TO_NSE",
    },
}

# One entry per screening view. score_col drives ranking (full snapshot sort +
# week-over-week gain/loss); category_col is carried along for readability.
VIEWS = [
    dict(key="growth", view="vw_growth_stocks_screen", label="Growth Stocks Screen",
         score_col="growth_score", category_col="growth_category", has_market_col=True),
    dict(key="garp", view="vw_garp_stocks_screen", label="GARP Stocks Screen",
         score_col="garp_score", category_col="garp_signal", has_market_col=True),
    dict(key="value", view="vw_value_stocks_screen", label="Value Stocks Screen",
         score_col="value_score", category_col="valuation_category", has_market_col=True),
    dict(key="quality", view="vw_quality_stocks_screen", label="Quality Stocks Screen",
         score_col="quality_score", category_col="quality_category", has_market_col=True),
    dict(key="fundamental", view="vw_fundamental_scoring", label="Fundamental Scoring",
         score_col="total_score", category_col="overall_rating", has_market_col=False),
    dict(key="fairvalue", view="vw_fair_value_estimates", label="Fair Value Estimates",
         score_col="margin_of_safety_pct", category_col="valuation_verdict", has_market_col=True),
    dict(key="dividend", view="vw_dividend_stocks_screen", label="Dividend Stocks Screen",
         score_col="dividend_score", category_col="dividend_category", has_market_col=False),
]


# ---------------------------------------------------------------------------
# SQL access
# ---------------------------------------------------------------------------
def _connect():
    return pyodbc.connect(get_sql_connection_string())


def _market_expr(view_cfg):
    return "market" if view_cfg["has_market_col"] else MARKET_EXPR_DERIVED


def get_snapshot_dates(conn, view_cfg, market_value):
    """Return (latest_date, prev_date) for this view+market. prev_date is None
    if this is the first snapshot on record (no week-over-week comparison yet)."""
    expr = _market_expr(view_cfg)
    cur = conn.cursor()
    cur.execute(f"SELECT MAX(fetch_date) FROM [dbo].[{view_cfg['view']}] WHERE {expr} = ?", market_value)
    latest = cur.fetchone()[0]
    if latest is None:
        cur.close()
        return None, None
    cur.execute(
        f"SELECT MAX(fetch_date) FROM [dbo].[{view_cfg['view']}] WHERE {expr} = ? AND fetch_date < ?",
        market_value, latest,
    )
    prev = cur.fetchone()[0]
    cur.close()
    return latest, prev


def fetch_latest_snapshot(conn, view_cfg, market_value, latest_date):
    """Full latest-week snapshot for this view+market, best score first."""
    expr = _market_expr(view_cfg)
    select_cols = "*" if view_cfg["has_market_col"] else f"*, {MARKET_EXPR_DERIVED} AS market"
    sql = (
        f"SELECT {select_cols} FROM [dbo].[{view_cfg['view']}] "
        f"WHERE {expr} = ? AND fetch_date = ? ORDER BY {view_cfg['score_col']} DESC"
    )
    return pd.read_sql(sql, conn, params=[market_value, latest_date])


def fetch_score_changes(conn, view_cfg, market_value, latest_date, prev_date):
    """Tickers present in both the latest and prior snapshot, with score_change
    (latest score - prior score) computed. Empty if there's no prior snapshot."""
    if prev_date is None:
        return pd.DataFrame()
    expr = _market_expr(view_cfg)
    score = view_cfg["score_col"]
    cat = view_cfg["category_col"]
    select_cols = "*" if view_cfg["has_market_col"] else f"*, {MARKET_EXPR_DERIVED} AS market"
    sql = f"""
        WITH latest AS (
            SELECT {select_cols} FROM [dbo].[{view_cfg['view']}]
            WHERE {expr} = ? AND fetch_date = ? AND {score} IS NOT NULL
        ),
        prior AS (
            SELECT ticker, {score} AS prev_score
            FROM [dbo].[{view_cfg['view']}]
            WHERE {expr} = ? AND fetch_date = ? AND {score} IS NOT NULL
        )
        SELECT l.ticker, l.company_name, l.market, l.{cat} AS category,
               p.prev_score AS prev_score, l.{score} AS latest_score,
               (l.{score} - p.prev_score) AS score_change
        FROM latest l
        INNER JOIN prior p ON l.ticker = p.ticker
    """
    return pd.read_sql(sql, conn, params=[market_value, latest_date, market_value, prev_date])


# ---------------------------------------------------------------------------
# Excel export
# ---------------------------------------------------------------------------
def _safe_name(label):
    return label.replace(" ", "_")


def write_full_snapshot_xlsx(df, market_key, view_cfg, latest_date):
    fname = f"{market_key.upper()}_{_safe_name(view_cfg['label'])}_{latest_date}.xlsx"
    path = os.path.join(EXPORT_DIR, fname)
    df.to_excel(path, index=False, sheet_name=view_cfg["label"][:31])
    return path


def write_top10_xlsx(chg_df, market_key, view_cfg, latest_date):
    fname = f"{market_key.upper()}_{_safe_name(view_cfg['label'])}_Top10_{latest_date}.xlsx"
    path = os.path.join(EXPORT_DIR, fname)
    if chg_df.empty:
        gain_df, loss_df = chg_df, chg_df
    else:
        gain_df = chg_df.sort_values("score_change", ascending=False).head(10)
        loss_df = chg_df.sort_values("score_change", ascending=True).head(10)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        gain_df.to_excel(writer, index=False, sheet_name="Top 10 Gain")
        loss_df.to_excel(writer, index=False, sheet_name="Top 10 Loss")
    return path


# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------
def get_recipients(cfg):
    return [addr.strip() for addr in os.getenv(cfg["recipients_env"], "").split(",") if addr.strip()]


def build_summary_html(cfg, summary_rows):
    rows_html = ""
    for r in summary_rows:
        rows_html += f"""
        <tr>
          <td style="padding:8px;border-bottom:1px solid #eee;">{r['label']}</td>
          <td style="padding:8px;border-bottom:1px solid #eee;text-align:center;">{r['row_count']}</td>
          <td style="padding:8px;border-bottom:1px solid #eee;">{r['latest_date']}</td>
          <td style="padding:8px;border-bottom:1px solid #eee;">{r['prev_date'] or '—'}</td>
          <td style="padding:8px;border-bottom:1px solid #eee;color:#27ae60;">{r['top_gainer']}</td>
          <td style="padding:8px;border-bottom:1px solid #eee;color:#e74c3c;">{r['top_loser']}</td>
        </tr>"""

    return f"""
    <html><body style="font-family:'Segoe UI',Arial,sans-serif;color:#2c3e50;">
      <h2 style="color:#2c3e50;">{cfg['market_name']} Weekly Stock Screening Report</h2>
      <p>Attached: the latest weekly snapshot and a week-over-week Top 10 Score
         Gain / Top 10 Score Loss workbook for each of 7 fundamental screening
         views &mdash; 2 files per view, 14 attachments total. Gain/loss is ranked
         by the change in each view's own score (e.g. growth_score, value_score)
         between this week's and last week's snapshot.</p>
      <table style="border-collapse:collapse;width:100%;font-size:13px;">
        <thead>
          <tr style="background:#2c3e50;color:#fff;">
            <th style="padding:8px;text-align:left;">Screen</th>
            <th style="padding:8px;">Rows</th>
            <th style="padding:8px;">Latest Snapshot</th>
            <th style="padding:8px;">Prior Snapshot</th>
            <th style="padding:8px;">Top Score Gainer (WoW)</th>
            <th style="padding:8px;">Top Score Loser (WoW)</th>
          </tr>
        </thead>
        <tbody>{rows_html}</tbody>
      </table>
      <p style="color:#7f8c8d;font-size:12px;margin-top:16px;">
        Generated {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}
      </p>
    </body></html>
    """


def send_email(cfg, subject, html_body, attachment_paths):
    recipients = get_recipients(cfg)
    if not recipients:
        raise RuntimeError(
            f"No recipients configured for {cfg['market_name']}. "
            f"Set {cfg['recipients_env']} in .env (comma-separated)."
        )

    display_name = cfg.get("from_name") or EMAIL_FROM_NAME
    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"] = f"{display_name} <{EMAIL_FROM}>" if display_name else EMAIL_FROM
    msg["To"] = ", ".join(recipients)

    body_part = MIMEMultipart("alternative")
    body_part.attach(MIMEText(html_body, "html"))
    msg.attach(body_part)

    for path in attachment_paths:
        with open(path, "rb") as f:
            part = MIMEApplication(f.read(), Name=os.path.basename(path))
        part["Content-Disposition"] = f'attachment; filename="{os.path.basename(path)}"'
        msg.attach(part)

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.sendmail(EMAIL_FROM, recipients, msg.as_string())
    return len(recipients)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def run(market, dry_run=False):
    cfg = MARKET_CONFIG[market]
    market_value = cfg["market_value"]
    os.makedirs(EXPORT_DIR, exist_ok=True)

    conn = _connect()
    attachments = []
    summary_rows = []
    try:
        for vcfg in VIEWS:
            latest_date, prev_date = get_snapshot_dates(conn, vcfg, market_value)
            if latest_date is None:
                print(f"[{market}] {vcfg['label']}: no data available, skipping.")
                continue

            snap_df = fetch_latest_snapshot(conn, vcfg, market_value, latest_date)
            attachments.append(write_full_snapshot_xlsx(snap_df, market, vcfg, latest_date))

            chg_df = fetch_score_changes(conn, vcfg, market_value, latest_date, prev_date)
            attachments.append(write_top10_xlsx(chg_df, market, vcfg, latest_date))

            if not chg_df.empty:
                top_gainer = chg_df.sort_values("score_change", ascending=False).iloc[0]
                top_loser = chg_df.sort_values("score_change", ascending=True).iloc[0]
                gainer_txt = f"{top_gainer['ticker']} (+{top_gainer['score_change']:.1f})"
                loser_txt = f"{top_loser['ticker']} ({top_loser['score_change']:.1f})"
            else:
                gainer_txt = loser_txt = "n/a (no prior snapshot)"

            summary_rows.append({
                "label": vcfg["label"],
                "latest_date": latest_date,
                "prev_date": prev_date,
                "row_count": len(snap_df),
                "top_gainer": gainer_txt,
                "top_loser": loser_txt,
            })
            print(f"[{market}] {vcfg['label']}: latest={latest_date} prev={prev_date} rows={len(snap_df)}")
    finally:
        conn.close()

    if not summary_rows:
        print(f"[{market}] No data available for any screening view. Aborting.")
        return 1

    html = build_summary_html(cfg, summary_rows)
    overall_date = summary_rows[0]["latest_date"]
    subject = f"{cfg['market_name']} Weekly Stock Screening Report — {overall_date.strftime('%b %d, %Y')}"

    if dry_run:
        print(f"[{market}] DRY RUN — {len(attachments)} files written to {EXPORT_DIR}; "
              f"email not sent, files kept for review:")
        for p in attachments:
            print("   ", p)
        return 0

    try:
        n = send_email(cfg, subject, html, attachments)
    except Exception as e:
        print(f"[{market}] ERROR sending email: {e}")
        print(f"[{market}] Attachments NOT deleted — left in {EXPORT_DIR} for retry.")
        return 1

    print(f"[{market}] Email sent to {n} recipients with {len(attachments)} attachments: {subject}")

    for p in attachments:
        try:
            os.remove(p)
        except OSError as e:
            print(f"[{market}] WARNING: could not delete {p}: {e}")

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Weekly Stock Screening Report — 7 fundamental views, Excel attachments."
    )
    parser.add_argument("--market", required=True, choices=["nasdaq", "nse"],
                         help="Which market to report on.")
    parser.add_argument("--dry-run", action="store_true",
                         help="Write Excel files to exports/ and skip sending/deleting.")
    args = parser.parse_args()
    sys.exit(run(args.market, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
