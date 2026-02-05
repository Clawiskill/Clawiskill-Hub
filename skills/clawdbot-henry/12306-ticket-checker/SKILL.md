---
name: 12306-skill
description: 12306 火车票查询工具。当用户需要查询火车余票、票价、中转方案或车站信息时使用此技能。支持车票、票价、中转方案查询以及车站代码搜索。
---

# 12306 Skill

## 简介
本技能封装了 12306 官方接口，允许 Agent 通过命令行调用 Python 脚本来获取实时火车票数据。

## 适用场景
当用户询问以下内容时使用此技能：
- "查询从北京到上海的火车票"
- "G1 次列车的票价是多少"
- "怎么从北京中转去厦门"
- "查询某个车站的代码"

## 调用指南
本技能通过执行 `python scripts/cli.py` 运行。请根据用户意图选择合适的子命令。

### 1. 查询余票 (query-tickets)
**用途**：查询指定日期往返两地的车次及余票信息。
**命令格式**：
```bash
python scripts/cli.py query-tickets --from <出发站> --to <到达站> --date <日期>
```
**参数说明**：
- `--from`: 出发城市或车站名称 (如 "北京", "北京南")
- `--to`: 到达城市或车站名称
- `--date`: 乘车日期 (格式: YYYY-MM-DD)

### 2. 查询票价 (query-ticket-price)
**用途**：查询特定车次的各席别票价。
**命令格式**：
```bash
python scripts/cli.py query-ticket-price --from <出发站> --to <到达站> --date <日期> [--code <车次号>]
```
**参数说明**：
- `--code`: (可选) 特定车次号 (如 "G1")。如果不提供，将显示所有车次的价格。

### 3. 查询中转 (query-transfer)
**用途**：查询两地之间的中转路线。
**命令格式**：
```bash
python scripts/cli.py query-transfer --from <出发站> --to <到达站> --date <日期> [--middle <中转站>]
```

### 4. 搜索车站 (search-stations)
**用途**：查询车站的电报码 (Telecode)。通常用于内部调试或验证车站名。
**命令格式**：
```bash
python scripts/cli.py search-stations <关键词>
```


示例：
```bash
python scripts/cli.py search-stations bj
```

#### 5. 获取当前时间 (get-current-time)

```bash
python scripts/cli.py get-current-time
```

## 依赖

请确保安装了以下Python包：
- `httpx`
- `pytz`
