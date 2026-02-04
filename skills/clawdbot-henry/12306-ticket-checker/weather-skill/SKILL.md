---
name: weather-skill
description: 天气查询工具。当用户需要查询实时天气、温度、湿度或生活指数时使用此技能。支持城市名称或 Adcode 查询，可获取扩展数据（如体感温度、AQI）和未来3天预报。
---

# Weather Skill

## 简介
本技能封装了 uapis.cn 的天气查询接口，允许 Agent 通过命令行快速获取精准、实时的天气数据。

## 适用场景
当用户询问以下内容时使用此技能：
- "北京今天天气怎么样？"
- "出门需要带伞吗？"
- "查一下上海的气温"
- "深圳市的空气质量如何"

## 调用指南
本技能通过执行 `python scripts/cli.py` 运行。

### 1. 查询天气 (query-weather)
**用途**：查询指定城市的实时天气状况，包括温度、湿度、风向等。
**命令格式**：
```bash
python scripts/cli.py query-weather --city <城市名称> [--adcode <城市编码>] [--extended] [--forecast] [--indices]
```
**参数说明**：
- `--city`: 城市名称 (如 "北京", "上海市", "福田区")。优先使用 Adcode 查询，若无 Adcode 则必须提供 City。
- `--adcode`: (可选) 6位数字城市编码 (如 "110000")。比 City 更精准。
- `--extended`: (可选) 开启扩展字段（体感温度、能见度、气压、紫外线、AQI等）。
- `--forecast`: (可选) 开启未来3天天气预报。
- `--indices`: (可选) 开启生活指数（穿衣、洗车、感冒等建议）。

**示例**：
*   基础查询：
    ```bash
    python scripts/cli.py query-weather --city 北京
    ```
*   全量查询（含预报和生活指数）：
    ```bash
    python scripts/cli.py query-weather --city 深圳 --extended --forecast --indices
    ```
