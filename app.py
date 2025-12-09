import os
from flask import Flask, render_template, request, jsonify
import pandas as pd
from binance.client import Client

# Binance public client
client = Client()

# Flask 애플리케이션 설정
#  - static_folder="data"        → 프로젝트 루트의 data/ 폴더를 정적 파일 폴더로 지정
#  - static_url_path="/data"     → URL에서 /data/... 로 접근 가능
#  - template_folder="templates" → 템플릿 파일은 templates/ 에서 불러옴
app = Flask(
    __name__,
    static_folder="data",
    static_url_path="docs/data",
    template_folder="templates"
)

# CSV 경로를 static_folder 기준으로 지정
DATA_PATH = os.path.join(app.static_folder, "BTC_USDT.csv")

def download_data():
    """Binance BTC/USDT 일봉 데이터 다운로드 및 data/BTC_USDT.csv 저장"""
    os.makedirs(app.static_folder, exist_ok=True)
    klines = client.get_historical_klines(
        "BTCUSDT",
        Client.KLINE_INTERVAL_1DAY,
        "1 Jan, 2022"
    )

    df = pd.DataFrame(klines, columns=[
        "timestamp", "open", "high", "low", "close", "volume",
        "close_time", "quote_asset_volume", "num_trades",
        "taker_buy_base", "taker_buy_quote", "ignore"
    ])
    df["date"] = pd.to_datetime(df["timestamp"], unit="ms")
    df = df[["date", "open", "high", "low", "close", "volume"]].copy()
    df[["open","high","low","close","volume"]] = \
        df[["open","high","low","close","volume"]].astype(float)
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

    # 데이터 로드 및 기간 필터
    df = load_data()
    df = df[(df["date"] >= start_date) & (df["date"] <= end_date)].reset_index(drop=True)

    # 지표 계산
    df["MA"] = df["close"].rolling(ma_period).mean()
    df["STD"] = df["close"].rolling(ma_period).std()
    df["BB_upper"] = df["MA"] + bb_k * df["STD"]
    df["BB_lower"] = df["MA"] - bb_k * df["STD"]

    trades = []
    coin = 0
    # 시뮬레이션 로직
    for i in range(ma_period, len(df)):
        today = df.iloc[i]
        date_str = today["date"].strftime('%Y-%m-%d')

        # 매수 조건
        if today["close"] < today["MA"] and today["close"] < today["BB_lower"] and balance > 0:
            coin = balance / today["close"]
            balance = 0
            trades.append({"date": date_str, "type": "BUY", "price": today["close"]})

        # 매도 조건
        elif today["close"] > today["MA"] and today["close"] > today["BB_upper"] and coin > 0:
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
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
