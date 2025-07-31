import yfinance as yf
import pandas as pd

btc = yf.download("BTC-USD", start="2022-06-10", end="2025-06-10", interval="1d", auto_adjust=True)

# 다중 컬럼 정리
if isinstance(btc.columns, pd.MultiIndex):
    btc.columns = btc.columns.get_level_values(0)

btc.reset_index(inplace=True)
btc.set_index("Date", inplace=True)

# 지표 계산
btc["ma15"] = btc["Close"].rolling(window=15).mean()
btc["ma50"] = btc["Close"].rolling(window=50).mean()
mean20 = btc["Close"].rolling(window=20).mean()
std20 = btc["Close"].rolling(window=20).std()
btc["bb_lower"] = mean20 - 2 * std20
btc["bb_upper"] = mean20 + 2 * std20
btc["vol_ma20"] = btc["Volume"].rolling(window=20).mean()

# 조건 설정
btc["buy"] = (
    (btc["Close"] < btc["ma15"]) &
    (btc["Close"] < btc["ma50"]) &
    (btc["Close"] < btc["bb_lower"]) &
    (btc["Volume"] > btc["vol_ma20"])
)
btc["sell"] = (
    (btc["Close"] > btc["ma15"]) &
    (btc["Close"] > btc["ma50"]) &
    (btc["Close"] > btc["bb_upper"]) &
    (btc["Volume"] > btc["vol_ma20"])
)

# NaN 값은 매수/매도 조건을 만족하지 않는 것으로 간주
btc["buy"].fillna(False, inplace=True)
btc["sell"].fillna(False, inplace=True)

# 초기 자산
cash = 10000
btc_holdings = 0
btc_cost_basis = 0
entry_log = []

# 시뮬레이션
for idx, row in btc.iterrows():
    price = row["Close"]

    # 매수 (50% 현금으로)
    if row["buy"] and cash > 0:
        buy_cash = cash * 0.5
        buy_btc = buy_cash / price
        btc_holdings += buy_btc
        btc_cost_basis += buy_cash
        cash -= buy_cash
        entry_log.append((idx, "BUY", buy_cash, price))

    # 전량 매도 (조건 만족 + 수익일 경우)
    elif row["sell"] and btc_holdings > 0:
        avg_buy_price = btc_cost_basis / btc_holdings if btc_holdings > 0 else 0

        if price >= avg_buy_price:
            sell_btc = btc_holdings  # 전량 매도
            sell_cash = sell_btc * price
            btc_holdings = 0
            btc_cost_basis = 0
            cash += sell_cash
            entry_log.append((idx, "SELL", sell_cash, price))

# 종료 평가
final_value = cash + btc_holdings * btc["Close"].iloc[-1]
profit = final_value - 10000
profit_percent = (profit / 10000) * 100

print(f"최종 자산: ${final_value:.2f}")
print(f"순이익: ${profit:.2f}")
print(f"수익률: {profit_percent:.2f}%")

# 로그 출력
pd.set_option("display.max_rows", None)
df_log = pd.DataFrame(entry_log, columns=["날짜", "행동", "금액", "단가"])
print(df_log)

# 선택 저장
# df_log.to_csv("btc_log_full_sell.csv", index=False)
