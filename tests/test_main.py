import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

import yfinance as yf
import pandas as pd
from ta.trend import SMAIndicator
from ta.volatility import BollingerBands

class BacktesterGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("비트코인 백테스트 GUI")
        self._create_widgets()
        self._layout_widgets()

    def _create_widgets(self):
        # 상단 설정 프레임
        self.frame_settings = ttk.LabelFrame(self, text="기본 설정", padding=10)
        self.symbol_var = tk.StringVar(value="BTC-USD")
        self.interval_var = tk.StringVar(value="1d")
        self.start_var = tk.StringVar(value="2023-01-01")
        self.end_var = tk.StringVar(value="2023-02-01")

        # 전략 설정 프레임
        self.frame_strategy = ttk.LabelFrame(self, text="전략 설정", padding=10)
        self.sma_var = tk.BooleanVar(value=True)
        self.ma_short_var = tk.IntVar(value=5)
        self.ma_long_var = tk.IntVar(value=20)
        self.boll_var = tk.BooleanVar(value=False)
        self.boll_window_var = tk.IntVar(value=20)
        self.boll_std_var = tk.DoubleVar(value=2.0)
        self.tp_var = tk.DoubleVar(value=3.0)
        self.sl_var = tk.DoubleVar(value=2.0)
        self.log_var = tk.BooleanVar(value=False)

        # 버튼 및 결과 영역
        self.run_button = ttk.Button(self, text="백테스트 실행", command=self.backtest)
        self.output = scrolledtext.ScrolledText(self, width=80, height=20)

    def _layout_widgets(self):
        # 기본 설정
        self.frame_settings.grid(row=0, column=0, padx=10, pady=5, sticky="ew")
        for i, (label, var) in enumerate([
            ("심볼", self.symbol_var),
            ("간격", self.interval_var),
            ("시작일", self.start_var),
            ("종료일", self.end_var)
        ]):
            ttk.Label(self.frame_settings, text=label).grid(row=i, column=0, sticky="w", padx=(0,5))
            ttk.Entry(self.frame_settings, textvariable=var, width=15).grid(row=i, column=1, sticky="w")

        # 전략 설정
        self.frame_strategy.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        ttk.Checkbutton(self.frame_strategy, text="SMA 사용", variable=self.sma_var).grid(row=0, column=0, sticky="w")
        ttk.Label(self.frame_strategy, text="단기 MA").grid(row=0, column=1, sticky="e")
        ttk.Spinbox(self.frame_strategy, from_=1, to=200, textvariable=self.ma_short_var, width=5).grid(row=0, column=2)
        ttk.Label(self.frame_strategy, text="장기 MA").grid(row=0, column=3, sticky="e")
        ttk.Spinbox(self.frame_strategy, from_=1, to=200, textvariable=self.ma_long_var, width=5).grid(row=0, column=4)

        ttk.Checkbutton(self.frame_strategy, text="Bollinger 사용", variable=self.boll_var).grid(row=1, column=0, sticky="w")
        ttk.Label(self.frame_strategy, text="기간").grid(row=1, column=1, sticky="e")
        ttk.Spinbox(self.frame_strategy, from_=5, to=200, textvariable=self.boll_window_var, width=5).grid(row=1, column=2)
        ttk.Label(self.frame_strategy, text="편차").grid(row=1, column=3, sticky="e")
        ttk.Spinbox(self.frame_strategy, from_=1.0, to=5.0, increment=0.1, textvariable=self.boll_std_var, width=5).grid(row=1, column=4)

        ttk.Label(self.frame_strategy, text="익절 %").grid(row=2, column=1, sticky="e")
        ttk.Spinbox(self.frame_strategy, from_=0.1, to=10.0, increment=0.1, textvariable=self.tp_var, width=5).grid(row=2, column=2)
        ttk.Label(self.frame_strategy, text="손절 %").grid(row=2, column=3, sticky="e")
        ttk.Spinbox(self.frame_strategy, from_=0.1, to=10.0, increment=0.1, textvariable=self.sl_var, width=5).grid(row=2, column=4)
        ttk.Checkbutton(self.frame_strategy, text="로그 표시", variable=self.log_var).grid(row=2, column=0, sticky="w")

        # 실행 버튼 및 출력
        self.run_button.grid(row=2, column=0, padx=10, pady=10, sticky="ew")
        self.output.grid(row=3, column=0, padx=10, pady=5)

        self.grid_columnconfigure(0, weight=1)
        self.frame_settings.grid_columnconfigure(1, weight=1)
        self.frame_strategy.grid_columnconfigure(4, weight=1)

    def backtest(self):
        # 입력
        symbol = self.symbol_var.get().strip()
        interval = self.interval_var.get().strip()
        start = self.start_var.get().strip()
        end = self.end_var.get().strip()
        use_sma = self.sma_var.get()
        ma_short = self.ma_short_var.get()
        ma_long = self.ma_long_var.get()
        use_boll = self.boll_var.get()
        boll_window = self.boll_window_var.get()
        boll_std = self.boll_std_var.get()
        tp_pct = self.tp_var.get()
        sl_pct = self.sl_var.get()
        show_log = self.log_var.get()

        # 데이터 로드
        try:
            df = yf.download(symbol, start=start, end=end, interval=interval, auto_adjust=True, progress=False)
            if df.empty:
                raise ValueError("데이터가 없습니다.")
        except Exception as e:
            messagebox.showerror("데이터 오류", str(e))
            return

        close = df["Close"].squeeze()
        if use_sma:
            df["sma_short"] = SMAIndicator(close, window=ma_short).sma_indicator()
            df["sma_long"] = SMAIndicator(close, window=ma_long).sma_indicator()
        if use_boll:
            bb = BollingerBands(close=close, window=boll_window, window_dev=boll_std)
            df["bb_high"] = bb.bollinger_hband()
            df["bb_low"] = bb.bollinger_lband()

        # 백테스트
        trades = []
        position = None
        entry_price = 0.0
        self.output.delete("1.0", tk.END)

        for i in range(1, len(df)):
            prev = df.iloc[i-1]
            curr = df.iloc[i]
            price = float(curr["Close"]) if not isinstance(curr["Close"], pd.Series) else float(curr["Close"].iloc[0])

            signal = None
            if use_sma:
                try:
                    ps = float(prev["sma_short"].iloc[0])
                    pl = float(prev["sma_long"].iloc[0])
                    cs = float(curr["sma_short"].iloc[0])
                    cl = float(curr["sma_long"].iloc[0])
                except Exception:
                    ps = pl = cs = cl = None
                if ps is not None and pl is not None and cs is not None and cl is not None:
                    if ps < pl and cs > cl:
                        signal = "BUY"
                    elif ps > pl and cs < cl:
                        signal = "SELL"

            if use_boll and signal is None:
                try:
                    bb_low = float(curr["bb_low"].iloc[0])
                    bb_high = float(curr["bb_high"].iloc[0])
                except Exception:
                    bb_low = bb_high = None
                if bb_low is not None and bb_high is not None:
                    if price < bb_low:
                        signal = "BUY"
                    elif price > bb_high:
                        signal = "SELL"

            if show_log:
                line = f"{curr.name} Close:{price:.2f}"
                if use_sma and cs is not None:
                    line += f" | SMA{ma_short}:{cs:.2f}, SMA{ma_long}:{cl:.2f}"
                if use_boll and bb_low is not None:
                    line += f" | BB_low:{bb_low:.2f}, BB_high:{bb_high:.2f}"
                line += f" -> {signal}\n"
                self.output.insert(tk.END, line)

            if signal == "BUY" and position is None:
                position = "LONG"
                entry_price = price
                trades.append({"type":"BUY","time":curr.name,"price":price})
                self.output.insert(tk.END, f"[BUY] {curr.name} at {price:.2f}\n")
                continue

            if position == "LONG":
                tp = entry_price * (1 + tp_pct/100)
                sl = entry_price * (1 - sl_pct/100)
                if price >= tp:
                    trades.append({"type":"SELL(TP)","time":curr.name,"price":price})
                    self.output.insert(tk.END, f"[TP] {curr.name} at {price:.2f}\n")
                    position = None
                elif price <= sl:
                    trades.append({"type":"SELL(SL)","time":curr.name,"price":price})
                    self.output.insert(tk.END, f"[SL] {curr.name} at {price:.2f}\n")
                    position = None

            if signal == "SELL" and position == "LONG":
                trades.append({"type":"SELL(sig)","time":curr.name,"price":price})
                self.output.insert(tk.END, f"[SELL(sig)] {curr.name} at {price:.2f}\n")
                position = None

        total = 0.0
        for j in range(0, len(trades), 2):
            if j+1 < len(trades):
                buy, sell = trades[j], trades[j+1]
                ret = (sell["price"] - buy["price"]) / buy["price"] * 100
                total += ret
        self.output.insert(tk.END, f"\n총 누적 수익률: {total:.2f}%")

if __name__ == "__main__":
    app = BacktesterGUI()
    app.mainloop()
