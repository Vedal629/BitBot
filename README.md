# BitBot

BitBot lets a user configure buy and sell conditions, then run those conditions
against Upbit market data in paper mode or live mode.

Paper mode is the default. Live trading requires API keys and an explicit
confirmation dialog before real orders are submitted.

## Run

```bash
pip install -r requirements.txt
python main.py
```

## Live Trading Setup

Create a `.env` file before using live trading.

```bash
UPBIT_ACCESS_KEY=your-access-key
UPBIT_SECRET_KEY=your-secret-key
```

## Supported Conditions

- Buy when price is below the long SMA by the configured percentage.
- Buy when RSI is below the configured value.
- Sell when price is above the long SMA by the configured percentage.
- Sell when RSI is above the configured value.
- Sell when take-profit or stop-loss is reached.

Use `Run Once` and paper mode first to confirm the conditions behave as expected.
