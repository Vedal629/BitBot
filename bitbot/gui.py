import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

from dotenv import load_dotenv

from .config import StrategyConfig
from .exchange import PaperExchangeClient, UpbitExchangeClient
from .strategy import StrategyEngine
from .trader import TradingRunner


class TradingGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        load_dotenv()
        self.title("BitBot Auto Trader")
        self.paper_exchange = PaperExchangeClient()
        self.runner: TradingRunner | None = None
        self._create_widgets()
        self._layout_widgets()

    def _create_widgets(self):
        self.frame_market = ttk.LabelFrame(self, text="Trade Settings", padding=10)
        self.symbol_var = tk.StringVar(value="KRW-BTC")
        self.order_amount_var = tk.DoubleVar(value=10000)
        self.interval_var = tk.IntVar(value=60)
        self.live_mode_var = tk.BooleanVar(value=False)

        self.frame_strategy = ttk.LabelFrame(self, text="Buy/Sell Conditions", padding=10)
        self.short_window_var = tk.IntVar(value=5)
        self.long_window_var = tk.IntVar(value=20)
        self.rsi_window_var = tk.IntVar(value=14)
        self.buy_below_sma_var = tk.DoubleVar(value=1.0)
        self.sell_above_sma_var = tk.DoubleVar(value=1.0)
        self.buy_rsi_var = tk.DoubleVar(value=30.0)
        self.sell_rsi_var = tk.DoubleVar(value=70.0)
        self.take_profit_var = tk.DoubleVar(value=3.0)
        self.stop_loss_var = tk.DoubleVar(value=2.0)

        self.start_button = ttk.Button(self, text="Start", command=self.start_trading)
        self.stop_button = ttk.Button(self, text="Stop", command=self.stop_trading, state=tk.DISABLED)
        self.run_once_button = ttk.Button(self, text="Run Once", command=self.run_once)
        self.output = scrolledtext.ScrolledText(self, width=96, height=24)

    def _layout_widgets(self):
        self.frame_market.grid(row=0, column=0, padx=10, pady=8, sticky="ew")
        market_rows = [
            ("Symbol", self.symbol_var),
            ("Order Amount (KRW)", self.order_amount_var),
            ("Interval (seconds)", self.interval_var),
        ]
        for row, (label, var) in enumerate(market_rows):
            ttk.Label(self.frame_market, text=label).grid(row=row, column=0, sticky="w", padx=(0, 8), pady=2)
            ttk.Entry(self.frame_market, textvariable=var, width=18).grid(row=row, column=1, sticky="w", pady=2)
        ttk.Checkbutton(self.frame_market, text="Live Trading", variable=self.live_mode_var).grid(row=0, column=2, sticky="w", padx=16)

        self.frame_strategy.grid(row=1, column=0, padx=10, pady=8, sticky="ew")
        strategy_rows = [
            ("Short SMA", self.short_window_var),
            ("Long SMA", self.long_window_var),
            ("RSI Window", self.rsi_window_var),
            ("Buy: below long SMA (%)", self.buy_below_sma_var),
            ("Sell: above long SMA (%)", self.sell_above_sma_var),
            ("Buy: RSI below", self.buy_rsi_var),
            ("Sell: RSI above", self.sell_rsi_var),
            ("Take Profit (%)", self.take_profit_var),
            ("Stop Loss (%)", self.stop_loss_var),
        ]
        for idx, (label, var) in enumerate(strategy_rows):
            row = idx // 3
            col = (idx % 3) * 2
            ttk.Label(self.frame_strategy, text=label).grid(row=row, column=col, sticky="w", padx=(0, 8), pady=2)
            ttk.Entry(self.frame_strategy, textvariable=var, width=10).grid(row=row, column=col + 1, sticky="w", pady=2)

        button_frame = ttk.Frame(self)
        button_frame.grid(row=2, column=0, padx=10, pady=8, sticky="ew")
        self.start_button.grid(in_=button_frame, row=0, column=0, padx=(0, 8))
        self.stop_button.grid(in_=button_frame, row=0, column=1, padx=(0, 8))
        self.run_once_button.grid(in_=button_frame, row=0, column=2)
        self.output.grid(row=3, column=0, padx=10, pady=(0, 10), sticky="nsew")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

    def build_config(self) -> StrategyConfig:
        return StrategyConfig(
            symbol=self.symbol_var.get().strip(),
            quote_asset="KRW",
            order_amount=float(self.order_amount_var.get()),
            interval_seconds=max(5, int(self.interval_var.get())),
            short_window=max(2, int(self.short_window_var.get())),
            long_window=max(3, int(self.long_window_var.get())),
            rsi_window=max(2, int(self.rsi_window_var.get())),
            buy_below_sma_pct=float(self.buy_below_sma_var.get()),
            sell_above_sma_pct=float(self.sell_above_sma_var.get()),
            buy_rsi_below=float(self.buy_rsi_var.get()),
            sell_rsi_above=float(self.sell_rsi_var.get()),
            take_profit_pct=float(self.take_profit_var.get()),
            stop_loss_pct=float(self.stop_loss_var.get()),
            max_position_pct=100.0,
            live_mode=bool(self.live_mode_var.get()),
        )

    def create_runner(self, config: StrategyConfig) -> TradingRunner:
        if config.live_mode:
            if not messagebox.askyesno("Live Trading Confirmation", "Real orders will be submitted. Continue?"):
                raise RuntimeError("Live trading cancelled.")
            exchange = UpbitExchangeClient()
        else:
            exchange = self.paper_exchange
        return TradingRunner(exchange=exchange, strategy=StrategyEngine(), log=self.log)

    def start_trading(self):
        try:
            config = self.build_config()
            self.runner = self.create_runner(config)
            self.runner.start(config)
            self.start_button.configure(state=tk.DISABLED)
            self.stop_button.configure(state=tk.NORMAL)
            self.run_once_button.configure(state=tk.DISABLED)
        except Exception as exc:
            messagebox.showerror("Start Error", str(exc))

    def stop_trading(self):
        if self.runner:
            self.runner.stop()
        self.start_button.configure(state=tk.NORMAL)
        self.stop_button.configure(state=tk.DISABLED)
        self.run_once_button.configure(state=tk.NORMAL)

    def run_once(self):
        try:
            config = self.build_config()
            runner = self.create_runner(config)
            runner.run_once(config)
        except Exception as exc:
            messagebox.showerror("Run Error", str(exc))

    def log(self, message: str):
        self.output.insert(tk.END, f"{message}\n")
        self.output.see(tk.END)


def main():
    app = TradingGUI()
    app.mainloop()
