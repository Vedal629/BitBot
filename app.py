# app.py
import os
from flask import Flask, render_template, request, jsonify
import pandas as pd
from binance.client import Client

# Binance API 키가 없어도 public 데이터는 사용 가능
client = Client()
app = Flask(__name__)
DATA_PATH = "data/BTC_USDT.csv"

def download_data():
    """Binance BTC/USDT 일봉 데이터 다운로드"""
    os.makedirs("data", exist_ok=True)
    klines = client.get_historical_klines(
        "BTCUSDT",
        Client.KLINE_INTERVAL_1DAY,
        "1 Jan, 2022"  # 시작일 (원하면 바꾸기)
    )

    df = pd.DataFrame(klines, columns=[
        "timestamp", "open", "high", "low", "close", "volume",
        "close_time", "quote_asset_volume", "num_trades",
        "taker_buy_base", "taker_buy_quote", "ignore"
    ])
    df["date"] = pd.to_datetime(df["timestamp"], unit="ms")
    df = df[["date", "open", "high", "low", "close", "volume"]].copy()
    df[["open","high","low","close","volume"]] = df[["open","high","low","close","volume"]].astype(float)
    df.to_csv(DATA_PATH, index=False)


def load_data():
    if not os.path.exists(DATA_PATH):
        download_data()
    return pd.read_csv(DATA_PATH, parse_dates=["date"])

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/simulate", methods=["POST"])
def simulate():
    # 사용자 입력
    initial_balance = float(request.form["balance"])
    balance = initial_balance
    ma_period = int(request.form["ma_period"])
    bb_k = float(request.form["bb_k"])
    start_date = pd.to_datetime(request.form["start_date"])
    end_date = pd.to_datetime(request.form["end_date"])

    # 데이터 로드 및 필터
    df = load_data()
    df = df[(df["date"] >= start_date) & (df["date"] <= end_date)].reset_index(drop=True)

    # 지표 계산
    df["MA"] = df["close"].rolling(ma_period).mean()
    df["STD"] = df["close"].rolling(ma_period).std()
    df["BB_upper"] = df["MA"] + bb_k * df["STD"]
    df["BB_lower"] = df["MA"] - bb_k * df["STD"]

    trades = []  # 매매 로그
    coin = 0
    for i in range(ma_period, len(df)):
        today = df.iloc[i]
        date_str = today["date"].strftime('%Y-%m-%d')
        # 매수: 종가 < MA & 종가 < BB_lower
        if today["close"] < today["MA"] and today["close"] < today["BB_lower"] and balance > 0:
            # 매수 실행
            coin = balance / today["close"]
            balance = 0
            trades.append({"date": date_str, "type": "BUY", "price": today["close"]})
        # 매도: 종가 > MA & 종가 > BB_upper
        elif today["close"] > today["MA"] and today["close"] > today["BB_upper"] and coin > 0:
            # 매도 실행
            balance = coin * today["close"]
            coin = 0
            trades.append({"date": date_str, "type": "SELL", "price": today["close"]})

    final_value = balance + coin * df.iloc[-1]["close"]
    profit = final_value - initial_balance

    return jsonify({
        "final_value": round(final_value, 2),
        "profit": round(profit, 2),
        "trades": trades
    })

if __name__ == "__main__":
    app.run(debug=True)