# ============================================================
# AURORA 3.1 — VALIDATED DAILY SCAN
# Uses the exact Production 3.1 engine in aurora_production.py
# ============================================================

import json
import time
from datetime import datetime

import pandas as pd

from aurora_production import (
    nse_symbols,
    get_stock_data,
    add_basic_features,
    detect_structural_pivots,
    detect_structural_bullish_poles,
    detect_production_bullish_flags,
    score_flag_structure,
)

OUTPUT_ACTIVE = "data/active_flags.json"
OUTPUT_SUMMARY = "data/scan_summary.json"


def _json_value(value):
    if pd.isna(value):
        return None
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    return value


def _records(df):
    if df is None or df.empty:
        return []
    clean = df.copy()
    for col in clean.columns:
        clean[col] = clean[col].map(_json_value)
    return clean.to_dict(orient="records")


def run_scan():
    start_time = time.time()
    all_flags = []
    scan_log = []

    print("=" * 70)
    print("AURORA 3.1 — DAILY PRODUCTION SCAN")
    print("=" * 70)
    print(f"Stocks to scan: {len(nse_symbols)}")
    print("=" * 70)

    for n, symbol in enumerate(nse_symbols, start=1):
        try:
            print(
                f"[{n:02d}/{len(nse_symbols)}] "
                f"{symbol:<15}",
                end=" "
            )

            stock_df = get_stock_data(
                symbol,
                period="2y",
                interval="1d"
            )

            if stock_df is None or stock_df.empty:
                print("NO DATA")
                scan_log.append({
                    "Symbol": symbol,
                    "Rows": 0,
                    "Pivots": 0,
                    "Poles": 0,
                    "Flags": 0,
                    "Status": "NO DATA"
                })
                continue

            stock_df = add_basic_features(stock_df)

            stock_pivots = detect_structural_pivots(
                stock_df,
                window=10,
                min_move_pct=3.0
            )

            stock_poles = detect_structural_bullish_poles(
                stock_df
            )

            stock_flags = detect_production_bullish_flags(
                stock_df,
                stock_poles
            )

            flag_count = 0

            if stock_flags is not None and not stock_flags.empty:
                flag_scores = stock_flags.apply(
                    score_flag_structure,
                    axis=1
                )

                stock_flags_scored = pd.concat(
                    [
                        stock_flags.reset_index(drop=True),
                        flag_scores.reset_index(drop=True)
                    ],
                    axis=1
                )

                stock_flags_scored.insert(
                    0,
                    "Symbol",
                    symbol
                )

                all_flags.append(stock_flags_scored)
                flag_count = len(stock_flags_scored)

            scan_log.append({
                "Symbol": symbol,
                "Rows": len(stock_df),
                "Pivots": len(stock_pivots),
                "Poles": len(stock_poles),
                "Flags": flag_count,
                "Status": "OK"
            })

            print(
                f"Rows={len(stock_df):3d}  "
                f"Pivots={len(stock_pivots):2d}  "
                f"Poles={len(stock_poles):2d}  "
                f"Flags={flag_count:2d}"
            )

        except Exception as e:
            print(f"ERROR: {str(e)[:80]}")
            scan_log.append({
                "Symbol": symbol,
                "Rows": 0,
                "Pivots": 0,
                "Poles": 0,
                "Flags": 0,
                "Status": f"ERROR: {str(e)[:100]}"
            })

    batch_flags = (
        pd.concat(all_flags, ignore_index=True)
        if all_flags
        else pd.DataFrame()
    )

    scan_log_df = pd.DataFrame(scan_log)

    if not batch_flags.empty:
        active_flags = (
            batch_flags[
                batch_flags["status"] == "ACTIVE FLAG"
            ]
            .copy()
            .sort_values(
                "Flag_Structure_Score",
                ascending=False
            )
            .reset_index(drop=True)
        )
    else:
        active_flags = pd.DataFrame()

    elapsed = time.time() - start_time
    generated_at = datetime.now().astimezone().isoformat(timespec="seconds")

    active_payload = {
        "scanner": "Aurora Bullish Flag Scanner",
        "release": "3.1",
        "universe": "NIFTY 50",
        "architecture": "Frozen 80-point scoring model",
        "generated_at": generated_at,
        "count": len(active_flags),
        "active_flags": _records(active_flags)
    }

    summary_payload = {
        "scanner": "Aurora Bullish Flag Scanner",
        "release": "3.1",
        "universe": "NIFTY 50",
        "architecture": "Frozen 80-point scoring model",
        "generated_at": generated_at,
        "summary": {
            "stocks_scanned": len(nse_symbols),
            "successful_scans": int(
                (scan_log_df["Status"] == "OK").sum()
            ),
            "total_production_structures": len(batch_flags),
            "active_flags": len(active_flags),
            "breakouts": int(
                (batch_flags["status"] == "BREAKOUT").sum()
            ) if not batch_flags.empty else 0,
            "highest_structure_score": int(
                batch_flags["Flag_Structure_Score"].max()
            ) if not batch_flags.empty else 0,
            "scan_time_seconds": round(elapsed, 2)
        },
        "scan_log": _records(scan_log_df)
    }

    with open(OUTPUT_ACTIVE, "w", encoding="utf-8") as f:
        json.dump(active_payload, f, indent=2, ensure_ascii=False)

    with open(OUTPUT_SUMMARY, "w", encoding="utf-8") as f:
        json.dump(summary_payload, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 70)
    print("AURORA 3.1 — SCAN COMPLETE")
    print("=" * 70)
    print(f"Stocks scanned       : {len(nse_symbols)}")
    print(
        f"Successful scans     : "
        f"{(scan_log_df['Status'] == 'OK').sum()}"
    )
    print(f"Production structures: {len(batch_flags)}")
    print(f"Active flags         : {len(active_flags)}")
    print(
        f"Breakouts            : "
        f"{(batch_flags['status'] == 'BREAKOUT').sum() if not batch_flags.empty else 0}"
    )
    print(
        f"Highest structure score: "
        f"{batch_flags['Flag_Structure_Score'].max() if not batch_flags.empty else 0}"
    )
    print(f"Scan time            : {elapsed:.2f} seconds")
    print("=" * 70)
    print(f"Active flags file    : {OUTPUT_ACTIVE}")
    print(f"Summary file         : {OUTPUT_SUMMARY}")

    return batch_flags, active_flags, scan_log_df


if __name__ == "__main__":
    run_scan()
