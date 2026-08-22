import json
from pathlib import Path

import pandas as pd
import yfinance as yf

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

# SAMPLE IPO LIST
# Replace with automated IPO discovery later

IPOS = [
    {
        "ticker": "SCTX",
        "company": "Scribe Therapeutics",
        "exchange": "NASDAQ",
        "ipo_date": "2026-08-14"
    },
    {
        "ticker": "IOND",
        "company": "Ionic Digital",
        "exchange": "NASDAQ",
        "ipo_date": "2026-08-12"
    }
]


def calculate_avwap(ticker, ipo_date):

    history = yf.Ticker(ticker).history(
        start=ipo_date,
        interval="1d",
        auto_adjust=False
    )

    history = history.dropna(
        subset=["Open", "High", "Low", "Close", "Volume"]
    )

    if history.empty:
        raise ValueError("No OHLCV data")

    if history["Volume"].sum() == 0:
        raise ValueError("No volume")

    history["ohlc4"] = (
        history["Open"]
        + history["High"]
        + history["Low"]
        + history["Close"]
    ) / 4

    history["pv"] = (
        history["ohlc4"] * history["Volume"]
    )

    history["cum_pv"] = history["pv"].cumsum()
    history["cum_vol"] = history["Volume"].cumsum()

    history["avwap"] = (
        history["cum_pv"]
        / history["cum_vol"]
    )

    latest = history.iloc[-1]

    current_close = float(latest["Close"])
    avwap = float(latest["avwap"])

    distance_pct = (
        (current_close / avwap) - 1
    ) * 100

    return {
        "currentPrice": round(current_close, 2),
        "ipoAvwap": round(avwap, 2),
        "distancePct": round(distance_pct, 2),
        "historyRows": len(history),
        "latestBarDate": str(
            history.index[-1].date()
        ),
        "status": (
            "Above"
            if current_close >= avwap
            else "Below"
        ),
        "dataMode": "live"
    }


rows = []

for ipo in IPOS:

    try:

        data = calculate_avwap(
            ipo["ticker"],
            ipo["ipo_date"]
        )

    except Exception as e:

        data = {
            "currentPrice": None,
            "ipoAvwap": None,
            "distancePct": None,
            "historyRows": None,
            "latestBarDate": None,
            "status": "Unavailable",
            "dataMode": "unavailable"
        }

        print(
            f"Failed: {ipo['ticker']} -> {e}"
        )

    rows.append({
        "ticker": ipo["ticker"],
        "company": ipo["company"],
        "exchange": ipo["exchange"],
        "ipoDate": ipo["ipo_date"],
        **data,
        "tvSymbol": (
            f"{ipo['exchange']}:{ipo['ticker']}"
        )
    })

dataset = {
    "generatedAtUtc":
        pd.Timestamp.utcnow().isoformat(),
    "rows": rows
}

with open(
    DATA_DIR / "ipos-live.json",
    "w"
) as f:
    json.dump(dataset, f, indent=2)

pd.DataFrame(rows).to_csv(
    DATA_DIR / "ipos-live.csv",
    index=False
)

watchlist = ",".join(
    row["tvSymbol"]
    for row in rows
)

with open(
    DATA_DIR / "tradingview-watchlist.txt",
    "w"
) as f:
    f.write(watchlist)

print("Completed")
