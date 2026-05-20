import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import SMAIndicator

from .config import MarketSnapshot, Position, StrategyConfig, TradeDecision


class StrategyEngine:
    def build_snapshot(self, symbol: str, candles: pd.DataFrame, config: StrategyConfig) -> MarketSnapshot:
        close = candles["close"].squeeze()
        price = float(close.iloc[-1])

        sma_short = None
        sma_long = None
        rsi = None

        if len(close) >= config.short_window:
            sma_short = float(SMAIndicator(close, window=config.short_window).sma_indicator().iloc[-1])
        if len(close) >= config.long_window:
            sma_long = float(SMAIndicator(close, window=config.long_window).sma_indicator().iloc[-1])
        if len(close) >= config.rsi_window:
            rsi = float(RSIIndicator(close, window=config.rsi_window).rsi().iloc[-1])

        return MarketSnapshot(symbol=symbol, price=price, sma_short=sma_short, sma_long=sma_long, rsi=rsi)

    def decide(
        self,
        snapshot: MarketSnapshot,
        position: Position | None,
        config: StrategyConfig,
    ) -> TradeDecision:
        if position is None:
            buy_reasons = []
            if snapshot.sma_long is not None:
                buy_line = snapshot.sma_long * (1 - config.buy_below_sma_pct / 100)
                if snapshot.price <= buy_line:
                    buy_reasons.append(f"price <= long SMA - {config.buy_below_sma_pct:.2f}%")
            if snapshot.rsi is not None and snapshot.rsi <= config.buy_rsi_below:
                buy_reasons.append(f"RSI <= {config.buy_rsi_below:.2f}")
            if buy_reasons:
                return TradeDecision("BUY", " and ".join(buy_reasons))
            return TradeDecision("HOLD", "No buy condition matched.")

        pnl_pct = (snapshot.price - position.entry_price) / position.entry_price * 100
        if pnl_pct >= config.take_profit_pct:
            return TradeDecision("SELL", f"take profit reached: {pnl_pct:.2f}%")
        if pnl_pct <= -config.stop_loss_pct:
            return TradeDecision("SELL", f"stop loss reached: {pnl_pct:.2f}%")

        sell_reasons = []
        if snapshot.sma_long is not None:
            sell_line = snapshot.sma_long * (1 + config.sell_above_sma_pct / 100)
            if snapshot.price >= sell_line:
                sell_reasons.append(f"price >= long SMA + {config.sell_above_sma_pct:.2f}%")
        if snapshot.rsi is not None and snapshot.rsi >= config.sell_rsi_above:
            sell_reasons.append(f"RSI >= {config.sell_rsi_above:.2f}")
        if sell_reasons:
            return TradeDecision("SELL", " and ".join(sell_reasons))

        return TradeDecision("HOLD", f"Position open, PnL {pnl_pct:.2f}%.")
