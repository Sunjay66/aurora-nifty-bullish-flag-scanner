# ============================================================
# AURORA RELEASE 3.1
# PRODUCTION BULLISH FLAG ENGINE
#
# Standalone production module for GitHub Actions
#
# IMPORTANT:
# - Production 3.1 logic preserved
# - No 25% pole formation logic
# - No new indicators
# - No sector score
# - No pole-strength score
# - Frozen flag-structure scoring
# ============================================================

import yfinance as yf
import pandas as pd
import numpy as np


# ============================================================
# NIFTY 50 PRODUCTION UNIVERSE
# ============================================================

nse_symbols = [
    "HDFCBANK",
    "ICICIBANK",
    "RELIANCE",
    "BHARTIARTL",
    "LT",
    "SBIN",
    "INFY",
    "AXISBANK",
    "KOTAKBANK",
    "M&M",
    "ADANIENT",
    "ADANIPORTS",
    "APOLLOHOSP",
    "ASIANPAINT",
    "BAJAJ-AUTO",
    "BAJFINANCE",
    "BAJAJFINSV",
    "BEL",
    "CIPLA",
    "COALINDIA",
    "DRREDDY",
    "EICHERMOT",
    "ETERNAL",
    "GRASIM",
    "HCLTECH",
    "HDFCLIFE",
    "HINDALCO",
    "HINDUNILVR",
    "ITC",
    "INDIGO",
    "JSWSTEEL",
    "JIOFIN",
    "MARUTI",
    "MAXHEALTH",
    "NTPC",
    "NESTLEIND",
    "ONGC",
    "POWERGRID",
    "SBILIFE",
    "SHRIRAMFIN",
    "SUNPHARMA",
    "TCS",
    "TATACONSUM",
    "TATASTEEL",
    "TECHM",
    "TITAN",
    "TRENT",
    "ULTRACEMCO",
    "WIPRO",
]

# ============================================================
# DATA DOWNLOAD
# ============================================================

def get_stock_data(symbol, period="2y", interval="1d"):

    ticker = symbol + ".NS"

    try:

        df = yf.download(
            ticker,
            period=period,
            interval=interval,
            auto_adjust=False,
            progress=False,
            threads=False
        )

        if df is None or df.empty:
            return None

        # Handle yfinance MultiIndex columns
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        required_columns = [
            "Open",
            "High",
            "Low",
            "Close",
            "Volume"
        ]

        if not all(
            col in df.columns
            for col in required_columns
        ):
            return None

        df = df[required_columns].copy()

        df.dropna(inplace=True)

        return df

    except Exception:
        return None


# ============================================================
# BASIC TECHNICAL FEATURES
# ============================================================

def add_basic_features(df):

    df = df.copy()

    # Moving averages
    df["EMA20"] = (
        df["Close"]
        .ewm(
            span=20,
            adjust=False
        )
        .mean()
    )

    df["EMA50"] = (
        df["Close"]
        .ewm(
            span=50,
            adjust=False
        )
        .mean()
    )

    df["EMA200"] = (
        df["Close"]
        .ewm(
            span=200,
            adjust=False
        )
        .mean()
    )

    # Daily percentage change
    df["Daily_Return_%"] = (
        df["Close"].pct_change() * 100
    )

    # Volume average
    df["Volume_SMA20"] = (
        df["Volume"]
        .rolling(20)
        .mean()
    )

    # Relative volume
    df["Relative_Volume"] = (
        df["Volume"] /
        df["Volume_SMA20"]
    )

    return df


# ============================================================
# STRUCTURAL PIVOT ENGINE
# ============================================================

def detect_structural_pivots(
    df,
    window=10,
    min_move_pct=3.0
):

    df = df.copy()

    # --------------------------------------------------------
    # Local structural highs and lows
    # --------------------------------------------------------

    rolling_high = (
        df["High"]
        .rolling(
            window=window * 2 + 1,
            center=True
        )
        .max()
    )

    rolling_low = (
        df["Low"]
        .rolling(
            window=window * 2 + 1,
            center=True
        )
        .min()
    )

    local_highs = (
        df["High"] == rolling_high
    )

    local_lows = (
        df["Low"] == rolling_low
    )

    # --------------------------------------------------------
    # Candidate pivots
    # --------------------------------------------------------

    candidates = []

    for idx in df.index:

        if local_highs.loc[idx]:

            candidates.append({
                "Date": idx,
                "Type": "HIGH",
                "Price": float(
                    df.loc[idx, "High"]
                )
            })

        elif local_lows.loc[idx]:

            candidates.append({
                "Date": idx,
                "Type": "LOW",
                "Price": float(
                    df.loc[idx, "Low"]
                )
            })

    # --------------------------------------------------------
    # Remove consecutive same-type pivots
    # and enforce minimum structural movement
    # --------------------------------------------------------

    pivots = []

    for candidate in candidates:

        if not pivots:

            pivots.append(candidate)
            continue

        previous = pivots[-1]

        # Same pivot type:
        # retain the more extreme pivot

        if candidate["Type"] == previous["Type"]:

            if candidate["Type"] == "HIGH":

                if (
                    candidate["Price"]
                    > previous["Price"]
                ):
                    pivots[-1] = candidate

            else:

                if (
                    candidate["Price"]
                    < previous["Price"]
                ):
                    pivots[-1] = candidate

            continue

        # Opposite pivot
        move_pct = (
            abs(
                candidate["Price"]
                - previous["Price"]
            )
            / previous["Price"]
            * 100
        )

        if move_pct >= min_move_pct:

            pivots.append(candidate)

    return pd.DataFrame(pivots)


# ============================================================
# STRUCTURAL BULLISH POLE ENGINE
# ============================================================

def detect_structural_bullish_poles(
    df,
    min_advance_pct=8.0,
    min_pole_sessions=3,
    max_pole_sessions=40,
    min_rvol=1.0
):

    pivots = detect_structural_pivots(df)

    if pivots is None or pivots.empty:
        return pd.DataFrame()

    poles = []

    for i in range(len(pivots) - 1):

        start = pivots.iloc[i]
        end = pivots.iloc[i + 1]

        if start["Type"] != "LOW":
            continue

        if end["Type"] != "HIGH":
            continue

        start_date = pd.to_datetime(
            start["Date"]
        )

        end_date = pd.to_datetime(
            end["Date"]
        )

        start_price = float(
            start["Price"]
        )

        high_price = float(
            end["Price"]
        )

        duration = len(
            df[
                (df.index >= start_date)
                &
                (df.index <= end_date)
            ]
        )

        if duration < min_pole_sessions:
            continue

        if duration > max_pole_sessions:
            continue

        advance_pct = (
            (high_price / start_price) - 1
        ) * 100

        if advance_pct < min_advance_pct:
            continue

        pole_data = df[
            (df.index >= start_date)
            &
            (df.index <= end_date)
        ].copy()

        if pole_data.empty:
            continue

        avg_volume = (
            pole_data["Volume"].mean()
        )

        volume_sma20 = (
            pole_data["Volume"]
            .rolling(20)
            .mean()
            .iloc[-1]
        )

        if (
            pd.isna(volume_sma20)
            or volume_sma20 <= 0
        ):
            rvol = np.nan
        else:
            rvol = (
                avg_volume /
                volume_sma20
            )

        if (
            not pd.isna(rvol)
            and rvol < min_rvol
        ):
            continue

        first_half = (
            pole_data["Volume"]
            .iloc[
                :max(
                    1,
                    len(pole_data) // 2
                )
            ]
            .mean()
        )

        second_half = (
            pole_data["Volume"]
            .iloc[
                max(
                    1,
                    len(pole_data) // 2
                ):
            ]
            .mean()
        )

        if first_half > 0:

            volume_change_pct = (
                (second_half / first_half) - 1
            ) * 100

        else:

            volume_change_pct = np.nan

        # ----------------------------------------------------
        # IMPORTANT COMPATIBILITY NORMALIZATION
        #
        # Original structural engine uses title-case names.
        # Production flag engine uses lowercase names.
        #
        # This changes only the column names, not the
        # analytical calculations.
        # ----------------------------------------------------

        poles.append({

            "pole_start_date":
                start_date,

            "pole_start_price":
                start_price,

            "pole_end_date":
                end_date,

            "pole_high_price":
                high_price,

            "pole_advance_pct":
                advance_pct,

            "pole_duration_sessions":
                duration,

            "pole_rvol":
                rvol,

            "pole_volume_change_pct":
                volume_change_pct
        })

    return pd.DataFrame(poles)


# ============================================================
# FROZEN AURORA 3.1 SCORING CONFIGURATION
# ============================================================

AURORA_FLAG_CONFIG = {

    "maximum_score": 80,

    "flag_structure": {

        "maximum_score": 25,

        "retracement": {
            ">100": 0,
            "<=78.6": 4,
            "<=61.8": 10,
            "<=50": 12,
            "<=38.2": 14,
            "<=25": 15
        },

        "persistence": {
            ">20": 0,
            "<=20": 3,
            "<=10": 6,
            "<=5": 8,
            "<=2": 9,
            "0": 10
        },

        "hard_invalidation": {
            "close_retracement_gt_100": True
        }
    },

    "ema_health": {

        "maximum_score": 25,

        "ema20": {
            "maximum_score": 12,
            "bands": [
                (0, 12),
                (2, 11),
                (5, 10),
                (10, 8),
                (20, 4),
                (999, 0)
            ]
        },

        "ema50": {
            "maximum_score": 13,
            "bands": [
                (0, 13),
                (2, 11),
                (5, 9),
                (10, 7),
                (20, 3),
                (999, 0)
            ]
        }
    },

    "relative_strength": {

        "maximum_score": 15,

        "bands": [
            (5, 15),
            (2, 14),
            (0, 12),
            (-2, 9),
            (-5, 6),
            (-10, 3),
            (-999, 0)
        ]
    },

    "volume_profile": {

        "maximum_score": 5,

        "bands": {
            "ABOVE VAH": 5,
            "INSIDE VALUE AREA": 2,
            "BELOW VAL": 0
        }
    },

    "location": {

        "maximum_score": 5,
        "distance_from_52w_high_pct": 2.0,
        "score_near": 5,
        "score_otherwise": 0
    },

    "trend_alignment": {

        "maximum_score": 5,
        "condition": "PRICE >= EMA200",
        "score_aligned": 5,
        "score_weak": 0
    },

    "diagnostic_only": [
        "Pole Strength",
        "Volume Behaviour",
        "Prior Trend Context",
        "Resistance / Room Above Breakout",
        "Sector Relative Strength",
        "POC Position",
        "EMA20 Slope",
        "EMA50 Slope",
        "EMA20 vs EMA50"
    ]
}


# ============================================================
# PRODUCTION FLAG PARAMETERS
# ============================================================

MAX_FLAG_SESSIONS = 45
MIN_FLAG_SESSIONS = 3


# ============================================================
# PRODUCTION BULLISH FLAG DETECTION
# ============================================================

def detect_production_bullish_flags(
    df,
    poles
):

    results = []

    if df is None or df.empty:
        return pd.DataFrame()

    if poles is None or poles.empty:
        return pd.DataFrame()

    data = df.copy()

    for _, pole in poles.iterrows():

        pole_start_date = pd.to_datetime(
            pole["pole_start_date"]
        )

        pole_end_date = pd.to_datetime(
            pole["pole_end_date"]
        )

        pole_start_price = float(
            pole["pole_start_price"]
        )

        pole_high_price = float(
            pole["pole_high_price"]
        )

        pole_advance_pct = float(
            pole["pole_advance_pct"]
        )

        # ----------------------------------------------------
        # DATA AFTER CONFIRMED POLE END
        # ----------------------------------------------------

        post_pole_full = data[
            data.index > pole_end_date
        ].copy()

        if post_pole_full.empty:
            continue

        # ----------------------------------------------------
        # 45-SESSION OBSERVATION WINDOW
        # ----------------------------------------------------

        post_pole = post_pole_full.iloc[
            :MAX_FLAG_SESSIONS
        ].copy()

        if len(post_pole) < MIN_FLAG_SESSIONS:
            continue

        # ----------------------------------------------------
        # POLE MIDPOINT
        # ----------------------------------------------------

        pole_midpoint = (
            pole_start_price
            + pole_high_price
        ) / 2.0

        pole_range = (
            pole_high_price
            - pole_start_price
        )

        if pole_range <= 0:
            continue

        # ----------------------------------------------------
        # BREAKOUT DETECTION
        # Daily CLOSE at or above pole high
        # ----------------------------------------------------

        breakout_mask = (
            post_pole["Close"]
            >= pole_high_price
        )

        breakout_date = None
        breakout_price = np.nan

        if breakout_mask.any():

            breakout_date = (
                breakout_mask[
                    breakout_mask
                ].index[0]
            )

            breakout_price = float(
                post_pole.loc[
                    breakout_date,
                    "Close"
                ]
            )

            flag_data = post_pole.loc[
                post_pole.index < breakout_date
            ].copy()

        else:

            flag_data = post_pole.copy()

        if flag_data.empty:

            flag_data = (
                post_pole
                .iloc[:1]
                .copy()
            )

        # ----------------------------------------------------
        # FLAG HIGH / LOW
        # ----------------------------------------------------

        flag_high = float(
            flag_data["High"].max()
        )

        flag_low = float(
            flag_data["Low"].min()
        )

        flag_high_date = (
            flag_data["High"].idxmax()
        )

        flag_low_date = (
            flag_data["Low"].idxmin()
        )

        # ----------------------------------------------------
        # LOW RETRACEMENT
        # ----------------------------------------------------

        low_retracement_pct = (
            (
                pole_high_price
                - flag_low
            )
            / pole_range
        ) * 100

        # ----------------------------------------------------
        # CLOSING RETRACEMENT
        # ----------------------------------------------------

        lowest_close = float(
            flag_data["Close"].min()
        )

        lowest_close_date = (
            flag_data["Close"].idxmin()
        )

        close_retracement_pct = (
            (
                pole_high_price
                - lowest_close
            )
            / pole_range
        ) * 100

        # ----------------------------------------------------
        # PERSISTENCE BELOW 50% POLE RETRACEMENT
        # ----------------------------------------------------

        below_50 = (
            flag_data["Close"]
            < pole_midpoint
        )

        closes_below_50 = int(
            below_50.sum()
        )

        # ----------------------------------------------------
        # EMA PERSISTENCE
        # ----------------------------------------------------

        ema20_below_close = 0
        ema50_below_close = 0
        ema20_below_low = 0
        ema50_below_low = 0

        if "EMA20" in flag_data.columns:

            ema20_below_close = int(
                (
                    flag_data["Close"]
                    < flag_data["EMA20"]
                ).sum()
            )

            ema20_below_low = int(
                (
                    flag_data["Low"]
                    < flag_data["EMA20"]
                ).sum()
            )

        if "EMA50" in flag_data.columns:

            ema50_below_close = int(
                (
                    flag_data["Close"]
                    < flag_data["EMA50"]
                ).sum()
            )

            ema50_below_low = int(
                (
                    flag_data["Low"]
                    < flag_data["EMA50"]
                ).sum()
            )

        # ----------------------------------------------------
        # FLAG RANGE
        # ----------------------------------------------------

        flag_range_pct = (
            (
                flag_high
                - flag_low
            )
            / flag_high
        ) * 100

        # ----------------------------------------------------
        # STRUCTURAL INVALIDATION
        # ----------------------------------------------------

        structurally_invalidated = (
            close_retracement_pct > 100
        )

        # ----------------------------------------------------
        # CURRENT STATUS
        # ----------------------------------------------------

        if structurally_invalidated:

            status = "INVALIDATED"

        elif breakout_date is not None:

            status = "BREAKOUT"

        elif (
            len(post_pole_full)
            >= MAX_FLAG_SESSIONS
        ):

            status = "STALE"

        else:

            status = "ACTIVE FLAG"

        # ----------------------------------------------------
        # RESULT
        # ----------------------------------------------------

        results.append({

            "pole_start_date":
                pole_start_date,

            "pole_start_price":
                pole_start_price,

            "pole_end_date":
                pole_end_date,

            "pole_high_price":
                pole_high_price,

            "pole_advance_pct":
                pole_advance_pct,

            "flag_start_date":
                flag_data.index.min(),

            "flag_end_date":
                flag_data.index.max(),

            "flag_duration_sessions":
                len(flag_data),

            "flag_high_date":
                flag_high_date,

            "flag_high":
                flag_high,

            "flag_low_date":
                flag_low_date,

            "flag_low":
                flag_low,

            "lowest_close_date":
                lowest_close_date,

            "lowest_close":
                lowest_close,

            "pole_midpoint":
                pole_midpoint,

            "low_retracement_pct":
                low_retracement_pct,

            "close_retracement_pct":
                close_retracement_pct,

            "closes_below_50":
                closes_below_50,

            "ema20_below_close":
                ema20_below_close,

            "ema50_below_close":
                ema50_below_close,

            "ema20_below_low":
                ema20_below_low,

            "ema50_below_low":
                ema50_below_low,

            "flag_range_pct":
                flag_range_pct,

            "breakout_date":
                breakout_date,

            "breakout_price":
                breakout_price,

            "status":
                status
        })

    return pd.DataFrame(results)


# ============================================================
# FLAG STRUCTURE SCORE
# ============================================================

def score_flag_structure(row):

    score = 0

    # --------------------------------------------------------
    # CLOSING RETRACEMENT - 15 POINTS
    # --------------------------------------------------------

    retracement = (
        row["close_retracement_pct"]
    )

    if pd.isna(retracement):

        retracement_score = 0

    elif retracement > 100:

        retracement_score = 0

    elif retracement <= 25:

        retracement_score = 15

    elif retracement <= 38.2:

        retracement_score = 14

    elif retracement <= 50:

        retracement_score = 12

    elif retracement <= 61.8:

        retracement_score = 10

    elif retracement <= 78.6:

        retracement_score = 8

    else:

        retracement_score = 4

    # --------------------------------------------------------
    # PERSISTENCE BELOW 50% - 10 POINTS
    # --------------------------------------------------------

    persistence = (
        row["closes_below_50"]
    )

    if pd.isna(persistence):

        persistence_score = 0

    elif persistence == 0:

        persistence_score = 10

    elif persistence <= 2:

        persistence_score = 9

    elif persistence <= 5:

        persistence_score = 8

    elif persistence <= 10:

        persistence_score = 6

    elif persistence <= 20:

        persistence_score = 3

    else:

        persistence_score = 0

    # --------------------------------------------------------
    # TOTAL
    # --------------------------------------------------------

    score = (
        retracement_score
        + persistence_score
    )

    # --------------------------------------------------------
    # HARD INVALIDATION
    # --------------------------------------------------------

    if retracement > 100:

        interpretation = "INVALIDATED"

    elif score >= 21:

        interpretation = (
            "STRONG FLAG STRUCTURE"
        )

    elif score >= 16:

        interpretation = (
            "GOOD FLAG STRUCTURE"
        )

    elif score >= 9:

        interpretation = (
            "WATCH FLAG STRUCTURE"
        )

    else:

        interpretation = (
            "WEAK FLAG STRUCTURE"
        )

    return pd.Series({

        "Flag_Retracement_Score":
            retracement_score,

        "Flag_Persistence_Score":
            persistence_score,

        "Flag_Structure_Score":
            score,

        "Flag_Structure_Interpretation":
            interpretation
    })


# ============================================================
# ENGINE IDENTIFICATION
# ============================================================

AURORA_RELEASE = "3.1"
AURORA_ARCHITECTURE = (
    "Frozen 80-point scoring model"
)
AURORA_UNIVERSE_NAME = "NIFTY 50"
