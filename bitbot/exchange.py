import os
from abc import ABC, abstractmethod

import pyupbit

from .config import Position


class ExchangeClient(ABC):
    @abstractmethod
    def get_current_price(self, symbol: str) -> float:
        raise NotImplementedError

    @abstractmethod
    def get_ohlcv(self, symbol: str, interval: str, count: int):
        raise NotImplementedError

    @abstractmethod
    def get_position(self, symbol: str) -> Position | None:
        raise NotImplementedError

    @abstractmethod
    def buy_market(self, symbol: str, amount: float):
        raise NotImplementedError

    @abstractmethod
    def sell_market(self, symbol: str, volume: float):
        raise NotImplementedError


class UpbitExchangeClient(ExchangeClient):
    def __init__(self):
        access_key = os.getenv("UPBIT_ACCESS_KEY")
        secret_key = os.getenv("UPBIT_SECRET_KEY")
        if not access_key or not secret_key:
            raise ValueError("UPBIT_ACCESS_KEY and UPBIT_SECRET_KEY are required for live trading.")
        self.client = pyupbit.Upbit(access_key, secret_key)

    def get_current_price(self, symbol: str) -> float:
        price = pyupbit.get_current_price(symbol)
        if price is None:
            raise RuntimeError(f"Could not fetch current price for {symbol}.")
        return float(price)

    def get_ohlcv(self, symbol: str, interval: str, count: int):
        df = pyupbit.get_ohlcv(symbol, interval=interval, count=count)
        if df is None or df.empty:
            raise RuntimeError(f"Could not fetch candles for {symbol}.")
        return df

    def get_position(self, symbol: str) -> Position | None:
        base_asset = symbol.split("-")[-1]
        balances = self.client.get_balances()
        for balance in balances:
            if balance.get("currency") != base_asset:
                continue
            volume = float(balance.get("balance") or 0)
            if volume <= 0:
                return None
            avg_buy_price = float(balance.get("avg_buy_price") or 0)
            entry_price = avg_buy_price if avg_buy_price > 0 else self.get_current_price(symbol)
            return Position(symbol=symbol, volume=volume, entry_price=entry_price)
        return None

    def buy_market(self, symbol: str, amount: float):
        return self.client.buy_market_order(symbol, amount)

    def sell_market(self, symbol: str, volume: float):
        return self.client.sell_market_order(symbol, volume)


class PaperExchangeClient(ExchangeClient):
    def __init__(self, starting_cash: float = 1_000_000):
        self.cash = starting_cash
        self.positions: dict[str, Position] = {}

    def get_current_price(self, symbol: str) -> float:
        price = pyupbit.get_current_price(symbol)
        if price is None:
            raise RuntimeError(f"Could not fetch current price for {symbol}.")
        return float(price)

    def get_ohlcv(self, symbol: str, interval: str, count: int):
        df = pyupbit.get_ohlcv(symbol, interval=interval, count=count)
        if df is None or df.empty:
            raise RuntimeError(f"Could not fetch candles for {symbol}.")
        return df

    def get_position(self, symbol: str) -> Position | None:
        return self.positions.get(symbol)

    def buy_market(self, symbol: str, amount: float):
        if amount <= 0:
            raise ValueError("Order amount must be positive.")
        if amount > self.cash:
            raise ValueError("Paper account cash is not enough.")
        price = self.get_current_price(symbol)
        volume = amount / price
        self.cash -= amount
        current = self.positions.get(symbol)
        if current:
            total_cost = current.entry_price * current.volume + amount
            total_volume = current.volume + volume
            current.volume = total_volume
            current.entry_price = total_cost / total_volume
        else:
            self.positions[symbol] = Position(symbol=symbol, volume=volume, entry_price=price)
        return {"mode": "paper", "side": "buy", "symbol": symbol, "price": price, "volume": volume, "cash": self.cash}

    def sell_market(self, symbol: str, volume: float):
        current = self.positions.get(symbol)
        if current is None:
            raise ValueError("No paper position to sell.")
        sell_volume = min(volume, current.volume)
        price = self.get_current_price(symbol)
        self.cash += sell_volume * price
        current.volume -= sell_volume
        if current.volume <= 0:
            del self.positions[symbol]
        return {"mode": "paper", "side": "sell", "symbol": symbol, "price": price, "volume": sell_volume, "cash": self.cash}
