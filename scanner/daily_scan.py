# ============================================================
# AURORA RELEASE 3.1
# DAILY PRODUCTION SCAN
#
# Purpose:
#   Run the validated Aurora 3.1 production engine across
#   the NIFTY 50 universe and generate machine-readable
#   scan results for the dashboard.
# ============================================================

import sys
import json
import time
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd

# ------------------------------------------------------------
# Make the scanner directory importable
# ------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from aurora_production import (
    nse_symbols,
    get_stock_data,
    add_basic_features,
    detect_structural_pivots,
    detect_structural_bullish_poles,
    detect_production_bullish_flags,
    score_flag_structure,
    AURORA_RELEASE,
    AURORA_ARCHITECTURE,
    AURORA_UNIVERSE_NAME,
)


# ============================================================
# OUTPUT PATHS
# ============================================================

REPO_ROOT = SCRIPT_DIR.parent

DATA_DIR = REPO_ROOT / "data"

DATA_DIR.mkdir(
    parents=True,
    exist_ok=True
)

ACTIVE_FLAGS_FILE = (
    DATA_DIR / "active_flags.json"
)

SCAN_SUMMARY_FILE = (
    DATA_DIR / "scan_summary.json"
)


# ============================================================
# HELPER - JSON SAFE VALUE
# ============================================================

def json_safe_value(value):

    if pd.isna(value):
        return None

    if isinstance(
        value,
        (
            pd.Timestamp,
            datetime
        )
    ):
        return value.isoformat()

    if hasattr(value, "item"):

        try:
            return value.item()

        except Exception:
            pass

    return value


# ============================================================
# CONVERT DATAFRAME TO JSON RECORDS
# ============================================================

def dataframe_to_records(df):

    if df is None or df.empty:
        return []

    records = []

    for record in df.to_dict(
        orient="records"
    ):

        clean_record = {}

        for key, value in record.items():

            clean_record[str(key)] = (
                json_safe_value(value)
            )

        records.append(clean_record)

    return records


# ============================================================
# RUN AURORA PRODUCTION SCAN
# ============================================================

def run_scan():

    print("=" * 70)
    print(
        "AURORA 3.1 - DAILY PRODUCTION SCAN"
    )
    print("=" * 70)

    start_time = time.time()

    all_flags = []
    scan_log = []

    print(
        f"Stocks to scan: "
        f"{len(nse_symbols)}"
    )

    print("=" * 70)

    # --------------------------------------------------------
    # STOCK LOOP
    # --------------------------------------------------------

    for n, symbol in enumerate(
        nse_symbols,
        start=1
    ):

        try:

            print(
                f"[{n:02d}/{len(nse_symbols)}] "
                f"{symbol:<15}",
                end=" "
            )

            # ------------------------------------------------
            # DOWNLOAD
            # ------------------------------------------------

            stock_df = get_stock_data(
                symbol,
                period="2y",
                interval="1d"
            )

            if (
                stock_df is None
                or stock_df.empty
            ):

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

            # ------------------------------------------------
            # FEATURES
            # ------------------------------------------------

            stock_df = (
                add_basic_features(
                    stock_df
                )
            )

            # ------------------------------------------------
            # STRUCTURAL PIVOTS
            # ------------------------------------------------

            stock_pivots = (
                detect_structural_pivots(
                    stock_df,
                    window=10,
                    min_move_pct=3.0
                )
            )

            # ------------------------------------------------
            # STRUCTURAL POLES
            # ------------------------------------------------

            stock_poles = (
                detect_structural_bullish_poles(
                    stock_df
                )
            )

            # ------------------------------------------------
            # PRODUCTION FLAGS
            # ------------------------------------------------

            stock_flags = (
                detect_production_bullish_flags(
                    stock_df,
                    stock_poles
                )
            )

            flag_count = 0

            if (
                stock_flags is not None
                and not stock_flags.empty
            ):

                # --------------------------------------------
                # PRODUCTION 3.1 FLAG STRUCTURE SCORE
                # --------------------------------------------

                flag_scores = (
                    stock_flags.apply(
                        score_flag_structure,
                        axis=1
                    )
                )

                stock_flags_scored = (
                    pd.concat(
                        [
                            stock_flags
                            .reset_index(
                                drop=True
                            ),

                            flag_scores
                            .reset_index(
                                drop=True
                            )
                        ],
                        axis=1
                    )
                )

                # --------------------------------------------
                # SYMBOL
                # --------------------------------------------

                stock_flags_scored.insert(
                    0,
                    "Symbol",
                    symbol
                )

                all_flags.append(
                    stock_flags_scored
                )

                flag_count = len(
                    stock_flags_scored
                )

            # ------------------------------------------------
            # LOG
            # ------------------------------------------------

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

        except Exception as error:

            print(
                "ERROR: "
                f"{str(error)[:100]}"
            )

            scan_log.append({

                "Symbol": symbol,
                "Rows": 0,
                "Pivots": 0,
                "Poles": 0,
                "Flags": 0,
                "Status":
                    f"ERROR: "
                    f"{str(error)[:100]}"
            })

    # ========================================================
    # COMBINE RESULTS
    # ========================================================

    if all_flags:

        batch_flags = pd.concat(
            all_flags,
            ignore_index=True
        )

    else:

        batch_flags = pd.DataFrame()

    scan_log_df = pd.DataFrame(
        scan_log
    )

    elapsed = (
        time.time()
        - start_time
    )

    # ========================================================
    # CURRENT ACTIVE FLAGS
    # ========================================================

    if batch_flags.empty:

        active_flags = (
            pd.DataFrame()
        )

    else:

        active_flags = (
            batch_flags[
                batch_flags["status"]
                == "ACTIVE FLAG"
            ]
            .copy()
        )

    # ========================================================
    # CURRENT BREAKOUTS
    # ========================================================

    if batch_flags.empty:

        breakout_flags = (
            pd.DataFrame()
        )

    else:

        breakout_flags = (
            batch_flags[
                batch_flags["status"]
                == "BREAKOUT"
            ]
            .copy()
        )

    # ========================================================
    # SUMMARY
    # ========================================================

    successful_scans = 0

    stocks_with_data = 0

    if not scan_log_df.empty:

        successful_scans = int(
            (
                scan_log_df["Status"]
                == "OK"
            ).sum()
        )

        stocks_with_data = int(
            (
                scan_log_df["Rows"]
                > 0
            ).sum()
        )

    highest_score = None

    if not batch_flags.empty:

        highest_score = int(
            batch_flags[
                "Flag_Structure_Score"
            ]
            .max()
        )

    generated_at = (
        datetime.now(
            timezone.utc
        )
        .isoformat()
    )

    # ========================================================
    # ACTIVE FLAGS JSON
    # ========================================================

    active_payload = {

        "scanner":
            "Aurora Bullish Flag Scanner",

        "release":
            AURORA_RELEASE,

        "universe":
            AURORA_UNIVERSE_NAME,

        "architecture":
            AURORA_ARCHITECTURE,

        "generated_at":
            generated_at,

        "count":
            len(active_flags),

        "active_flags":
            dataframe_to_records(
                active_flags
            )
    }

    with open(
        ACTIVE_FLAGS_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            active_payload,
            file,
            indent=2,
            allow_nan=False
        )

    # ========================================================
    # SCAN SUMMARY JSON
    # ========================================================

    summary_payload = {

        "scanner":
            "Aurora Bullish Flag Scanner",

        "release":
            AURORA_RELEASE,

        "universe":
            AURORA_UNIVERSE_NAME,

        "architecture":
            AURORA_ARCHITECTURE,

        "generated_at":
            generated_at,

        "summary": {

            "stocks_to_scan":
                len(nse_symbols),

            "stocks_scanned":
                len(nse_symbols),

            "successful_scans":
                successful_scans,

            "stocks_with_data":
                stocks_with_data,

            "total_production_structures":
                len(batch_flags),

            "current_active_flags":
                len(active_flags),

            "current_breakouts":
                len(breakout_flags),

            "highest_flag_structure_score":
                highest_score,

            "scan_time_seconds":
                round(
                    elapsed,
                    2
                )
        },

        "scan_log":
            dataframe_to_records(
                scan_log_df
            )
    }

    with open(
        SCAN_SUMMARY_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            summary_payload,
            file,
            indent=2,
            allow_nan=False
        )

    # ========================================================
    # FINAL CONSOLE SUMMARY
    # ========================================================

    print()
    print("=" * 70)
    print(
        "AURORA 3.1 - SCAN COMPLETE"
    )
    print("=" * 70)

    print(
        f"Stocks scanned       : "
        f"{len(nse_symbols)}"
    )

    print(
        f"Successful scans     : "
        f"{successful_scans}"
    )

    print(
        f"Production structures: "
        f"{len(batch_flags)}"
    )

    print(
        f"Active flags         : "
        f"{len(active_flags)}"
    )

    print(
        f"Breakouts            : "
        f"{len(breakout_flags)}"
    )

    print(
        f"Highest structure score: "
        f"{highest_score}"
    )

    print(
        f"Scan time            : "
        f"{elapsed:.2f} seconds"
    )

    print("=" * 70)

    print(
        f"Active flags file    : "
        f"{ACTIVE_FLAGS_FILE}"
    )

    print(
        f"Summary file         : "
        f"{SCAN_SUMMARY_FILE}"
    )

    print("=" * 70)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    run_scan()
