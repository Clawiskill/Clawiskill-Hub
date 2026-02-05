---
name: 12306-ticket-checker
description: Query real-time train tickets, prices, and transfer routes from China Railway 12306.
---

# 12306 Train Ticket Checker

A powerful tool to query train tickets, check prices, and find transfer routes using the official 12306 API.

## Features

*   **Query Tickets**: Check remaining tickets for direct trains.
*   **Query Prices**: Get ticket prices for different seat types.
*   **Smart Transfer**: Find transfer routes when direct tickets are sold out.
*   **Station Search**: Look up station codes (telecodes).

## Usage

This skill exposes a CLI script `scripts/cli.py` that you can run with Python.

### 1. Install Dependencies
```bash
uv pip install httpx pytz
```

### 2. Query Remaining Tickets
```bash
python3 scripts/cli.py query-tickets --from "Shanghai Hongqiao" --to "Beijing Nan" --date 2026-02-10
# or use Chinese station names directly:
python3 scripts/cli.py query-tickets --from 上海虹桥 --to 北京南 --date 2026-02-10
```

### 3. Query Ticket Prices
```bash
python3 scripts/cli.py query-ticket-price --from 杭州东 --to 厦门北 --date 2026-02-12
```

### 4. Find Transfer Routes
```bash
python3 scripts/cli.py query-transfer --from 杭州西 --to 晋城东 --date 2026-02-10
```

### 5. Search Station Codes
```bash
python3 scripts/cli.py search-stations "hangzhou"
```

## Notes

*   Ensure you have a valid Python environment.
*   The API connects directly to 12306.cn, so network latency may vary.
*   Date format must be `YYYY-MM-DD`.
