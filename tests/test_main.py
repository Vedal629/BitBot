import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

import yfinance as yf
import pandas as pd
from ta.volatility import BollingerBands

class BacktesterGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("비트코인 백테스트 GUI (볼린저 밴드 10% 전략)")
        self._create_widgets()
        self._layout_widgets()

    def _create_widgets(self):
        # 기본 설정 프레임
        self.frame_settings = ttk.LabelFrame(self, text="기본 설정", padding=10)
        self.symbol_var = tk.StringVar(value="BTC-USD")
        self.interval_var = tk.StringVar(value="1d")
        self.start_var = tk.StringVar(value="2023-01-01")
        self.end_var = tk.StringVar(value="2023-02-01")

        # 전략 설정 프레임
        self.frame_strategy = ttk.LabelFrame(self, text="전략 설정", padding=10)
        self.boll_window_var = tk.IntVar(value=20)
        self.boll_std_var = tk.DoubleVar(value=2.0)
        self.log_var = tk.BooleanVar(value=False)

        # 버튼 및 결과
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
        ttk.Label(self.frame_strategy, text="볼린저 밴드 기간").grid(row=0, column=0, sticky="e")
        ttk.Spinbox(self.frame_strategy, from_=5, to=200, textvariable=self.boll_window_var, width=5).grid(row=0, column=1)
        ttk.Label(self.frame_strategy, text="편차").grid(row=0, column=2, sticky="e")
        ttk.Spinbox(self.frame_strategy, from_=1.0, to=5.0, increment=0.1, textvariable=self.boll_std_var, width=5).grid(row=0, column=3)
        ttk.Checkbutton(self.frame_strategy, text="로그 표시", variable=self.log_var).grid(row=0, column=4, sticky="w")

        # 실행 버튼 및 출력
        self.run_button.grid(row=2, column=0, padx=10, pady=10, sticky="ew")
        self.output.grid(row=3, column=0, padx=10, pady=5)

        self.grid_columnconfigure(0, weight=1)
        self.frame_settings.grid_columnconfigure(1, weight=1)
        self.frame_strategy.grid_columnconfigure(3, weight=1)

    def backtest(self):
        # 입력값
        symbol = self.symbol_var.get().strip()
        interval = self.interval_var.get().strip()
        start = self.start_var.get().strip()
        end = self.end_var.get().strip()
        boll_window = self.boll_window_var.get()
        boll_std = self.boll_std_var.get()
        show_log = self.log_var.get()

        # 데이터 로드
        try:
            df = yf.download(symbol, start=start, end=end, interval=interval,
                             auto_adjust=True, progress=False)
            if df.empty:
                raise ValueError("데이터가 없습니다.")
        except Exception as e:
            messagebox.showerror("데이터 오류", str(e))
            return

        close = df['Close']
        bb = BollingerBands(close=close, window=boll_window, window_dev=boll_std)
        df['bb_high'] = bb.bollinger_hband()
        df['bb_low'] = bb.bollinger_lband()

        # 초기 자산 설정
        initial_cash = 100000  # 시작 현금 (원화 기준)
        cash = initial_cash
        coin = 0.0
        trades = []
        self.output.delete('1.0', tk.END)

        # 시뮬레이션
        for idx in df.index:
            price = df.at[idx, 'Close']
            low = df.at[idx, 'bb_low']
            high = df.at[idx, 'bb_high']

            if show_log:
                self.output.insert(tk.END, f"{idx.date()}  Close:{price:.2f}  BB_low:{low:.2f}  BB_high:{high:.2f}\n")

            # 밴드 하단 돌파: 보유 현금의 10% 매수
            if price < low and cash > 0:
                buy_amount = cash * 0.1
                buy_coin = buy_amount / price
                coin += buy_coin
                cash -= buy_amount
                trades.append((idx, 'BUY', price, buy_coin))
                self.output.insert(tk.END, f"[BUY] {idx.date()}  {buy_coin:.6f} BTC at {price:.2f}\n")

            # 밴드 상단 돌파: 보유 코인의 10% 매도
            elif price > high and coin > 0:
                sell_coin = coin * 0.1
                cash += sell_coin * price
                coin -= sell_coin
                trades.append((idx, 'SELL', price, sell_coin))
                self.output.insert(tk.END, f"[SELL] {idx.date()}  {sell_coin:.6f} BTC at {price:.2f}\n")

        # 최종 평가
        final_value = cash + coin * df['Close'].iloc[-1]
        ret_pct = (final_value - initial_cash) / initial_cash * 100
        self.output.insert(tk.END, f"\n최종 자산: {final_value:.2f} (수익률: {ret_pct:.2f}%)")

if __name__ == '__main__':
    app = BacktesterGUI()
    app.mainloop()
