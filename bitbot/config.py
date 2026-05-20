from dataclasses import dataclass


@dataclass(frozen=True)
class StrategyConfig:
    symbol: str
    quote_asset: str
    order_amount: float
    interval_seconds: int
    short_window: int
    long_window: int
    rsi_window: int
    buy_below_sma_pct: float
    sell_above_sma_pct: float
    buy_rsi_below: float
    sell_rsi_above: float
    take_profit_pct: float
    stop_loss_pct: float
    max_position_pct: float
    live_mode: bool


@dataclass
class Position:
    symbol: str
    volume: float
    entry_price: float


@dataclass(frozen=True)
class MarketSnapshot:
    symbol: str
    price: float
    sma_short: float | None
    sma_long: float | None
    rsi: float | None


@dataclass(frozen=True)
class TradeDecision:
    signal: str
    reason: str
