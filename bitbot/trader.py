import threading
from collections.abc import Callable

from .config import StrategyConfig
from .exchange import ExchangeClient
from .strategy import StrategyEngine


LogFn = Callable[[str], None]


class TradingRunner:
    def __init__(self, exchange: ExchangeClient, strategy: StrategyEngine, log: LogFn):
        self.exchange = exchange
        self.strategy = strategy
        self.log = log
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self, config: StrategyConfig):
        if self.running:
            raise RuntimeError("Trading runner is already running.")
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, args=(config,), daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()

    def run_once(self, config: StrategyConfig):
        candles = self.exchange.get_ohlcv(config.symbol, interval="minute1", count=max(config.long_window, config.rsi_window) + 5)
        snapshot = self.strategy.build_snapshot(config.symbol, candles, config)
        position = self.exchange.get_position(config.symbol)
        decision = self.strategy.decide(snapshot, position, config)

        self.log(
            f"{config.symbol} price={snapshot.price:.2f}, "
            f"sma_long={snapshot.sma_long}, rsi={snapshot.rsi}, signal={decision.signal} ({decision.reason})"
        )

        if decision.signal == "BUY":
            if config.order_amount <= 0:
                self.log("BUY skipped: order amount must be positive.")
                return
            result = self.exchange.buy_market(config.symbol, config.order_amount)
            self.log(f"BUY submitted: {result}")
            return

        if decision.signal == "SELL":
            if position is None:
                self.log("SELL skipped: no position.")
                return
            result = self.exchange.sell_market(config.symbol, position.volume)
            self.log(f"SELL submitted: {result}")

    def _run_loop(self, config: StrategyConfig):
        mode = "LIVE" if config.live_mode else "PAPER"
        self.log(f"{mode} trading started for {config.symbol}.")
        while not self._stop_event.is_set():
            try:
                self.run_once(config)
            except Exception as exc:
                self.log(f"ERROR: {exc}")
            self._stop_event.wait(config.interval_seconds)
        self.log("Trading stopped.")
