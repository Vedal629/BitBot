import argparse
import os
import time
import math
import requests
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Tuple

import pandas as pd
import pyupbit
from dotenv import load_dotenv

# -----------------------------
# 설정/유틸
# -----------------------------
@dataclass
class Config:
    ticker: str = "KRW-BTC"
    interval: str = "minute1"     # pyupbit 지원 분봉/일봉 문자열
    window: int = 20              # 볼밴 기간
    mult: float = 2.0             # 표준편차 배수 k
    refresh_sec: int = 5          # 루프 주기(초)
    cooldown_sec: int = 300       # 알림 쿨다운(초)
    ohlcv_count: int = 200        # 최근 n개 캔들로 밴드 계산(여유 있게)
    tz: str = "Asia/Seoul"

def now_kst_str() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")

def send_telegram(text: str) -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        print("[경고] TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID 환경 변수가 설정되지 않았습니다. 메시지를 전송하지 않습니다.")
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    try:
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code != 200:
            print(f"[텔레그램 오류] {r.status_code} {r.text}")
    except Exception as e:
        print(f"[텔레그램 예외] {e}")

def fetch_ohlcv(ticker: str, interval: str, count: int) -> pd.DataFrame:
    # pyupbit.get_ohlcv는 KST 기준으로 반환합니다.
    df = pyupbit.get_ohlcv(ticker, interval=interval, count=count)
    if df is None or df.empty:
        raise RuntimeError("OHLCV 데이터를 가져오지 못했습니다.")
    return df

def compute_bbands(close: pd.Series, window: int, mult: float) -> Tuple[pd.Series, pd.Series, pd.Series]:
    mid = close.rolling(window=window).mean()
    std = close.rolling(window=window).std(ddof=0)
    upper = mid + mult * std
    lower = mid - mult * std
    return lower, mid, upper

def get_current_price(ticker: str) -> float:
    price = pyupbit.get_current_price(ticker)
    if price is None or (isinstance(price, float) and (math.isnan(price) or price <= 0)):
        raise RuntimeError("현재가를 가져오지 못했습니다.")
    return float(price)

# -----------------------------
# 메인 로직
# -----------------------------
def run(cfg: Config):
    print(f"[시작] {cfg.ticker} 볼밴 하단 돌파 알림 | interval={cfg.interval}, window={cfg.window}, k={cfg.mult}")
    print(f"[정보] 루프 {cfg.refresh_sec}s, 쿨다운 {cfg.cooldown_sec}s")
    last_alert_ts = 0.0
    was_above_lower = True  # 직전 상태: 하단선 위에 있었다고 가정

    # 초기 OHLCV & 밴드 계산
    df = fetch_ohlcv(cfg.ticker, cfg.interval, cfg.ohlcv_count)
    lower, mid, upper = compute_bbands(df["close"], cfg.window, cfg.mult)

    while True:
        try:
            # 주기적으로 최신 캔들로 밴드 갱신
            # (분봉이 바뀌면 pyupbit OHLCV가 업데이트됨)
            df = fetch_ohlcv(cfg.ticker, cfg.interval, cfg.ohlcv_count)
            lower, mid, upper = compute_bbands(df["close"], cfg.window, cfg.mult)

            # 가장 최근 밴드 값
            lb = float(lower.iloc[-1])
            mb = float(mid.iloc[-1])
            ub = float(upper.iloc[-1])

            # 현재가
            price = get_current_price(cfg.ticker)

            # 상태 판정
            currently_below = price < lb
            crossed_down = (was_above_lower is True) and currently_below

            # 콘솔 로깅(필요 시 주석)
            print(f"[{now_kst_str()}] P={price:.2f} | BB(lower={lb:.2f}, mid={mb:.2f}, upper={ub:.2f}) | crossed_down={crossed_down}")

            # 교차 하향 시 알림(쿨다운 고려)
            now_ts = time.time()
            if crossed_down and (now_ts - last_alert_ts >= cfg.cooldown_sec):
                msg = (
                    f"[업비트 알림]\n"
                    f"{cfg.ticker}가 볼린저밴드 하단선 하향 돌파\n"
                    f"- 현재가: {price:,.0f} KRW\n"
                    f"- 하단선: {lb:,.0f} KRW (기간={cfg.window}, k={cfg.mult})\n"
                    f"- 구간: {cfg.interval}\n"
                    f"- 시각: {now_kst_str()}"
                )
                send_telegram(msg)
                last_alert_ts = now_ts

            # 상태 업데이트
            # 하단선 위로 다시 복귀하면 다음 번 하향 돌파를 새 이벤트로 인정
            was_above_lower = (price >= lb)

        except Exception as e:
            print(f"[에러] {e}")

        time.sleep(cfg.refresh_sec)

# -----------------------------
# 엔트리 포인트
# -----------------------------
def parse_args() -> Config:
    p = argparse.ArgumentParser(description="Upbit Bollinger Band Lower Break Alert to Telegram")
    p.add_argument("--ticker", default="KRW-BTC", help="예: KRW-BTC, KRW-ETH …")
    p.add_argument("--interval", default="minute1", help="분봉: minute1|3|5|10|15|30|60|240, 일봉: day")
    p.add_argument("--window", type=int, default=20, help="볼린저 기간 n")
    p.add_argument("--mult", type=float, default=2.0, help="표준편차 배수 k")
    p.add_argument("--refresh-sec", type=int, default=5, help="루프 주기(초)")
    p.add_argument("--cooldown-sec", type=int, default=300, help="알림 최소 간격(초)")
    p.add_argument("--ohlcv-count", type=int, default=200, help="밴드 계산에 사용할 최근 캔들 수")
    args = p.parse_args()
    return Config(
        ticker=args.ticker,
        interval=args.interval,
        window=args.window,
        mult=args.mult,
        refresh_sec=args.refresh_sec,
        cooldown_sec=args.cooldown_sec,
        ohlcv_count=args.ohlcv_count,
    )

if __name__ == "__main__":
    load_dotenv()
    cfg = parse_args()
    run(cfg)
