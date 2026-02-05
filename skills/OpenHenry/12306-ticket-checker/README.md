# Agent Skills Collection

本仓库包含了一系列 AI Agent 技能 (Skills)，旨在增强 AI 与现实世界的交互能力。

## 技能列表

| 技能名称 | 目录 | 描述 |
| :--- | :--- | :--- |
| **12306 Skill** | [12306-skill](./12306-skill) | 利用 12306 爬虫，支持余票查询、票价查询、中转方案及车站搜索。 |
| **Weather Skill** | [weather-skill](./weather-skill) | 封装 uapis.cn 天气接口，提供精准的实时天气、预报及生活指数查询。 |
| **Composition Scoring** | [composition-scoring-skill](./composition-scoring-skill) | 高中语文作文评分技能。依据标准规则进行打分、点评及硬性指标检测。 |

## 使用指南

### 1. 12306 Skill
详细使用说明请参考：[12306-skill/SKILL.md](./12306-skill/SKILL.md)

**核心功能：**
*   查询余票
*   查询票价
*   查询中转方案

### 2. Weather Skill
详细使用说明请参考：[weather-skill/SKILL.md](./weather-skill/SKILL.md)

**核心功能：**
*   查询实时天气
*   查询天气预报 (未来3天)
*   查询生活指数 (穿衣、紫外线等)

### 3. Composition Scoring Skill
详细使用说明请参考：[composition-scoring-skill/SKILL.md](./composition-scoring-skill/SKILL.md)

**核心功能：**
*   高中作文自动评分 (基础等级+发展等级)
*   生成改进建议
*   硬性指标检测 (字数、标题)

## 安装与配置

这些技能遵循标准的 Agent Skill 规范。

### 1. 准备工作

请根据需要使用的技能，分别安装依赖：

```bash
# 安装 12306-skill 依赖
cd 12306-skill
pip install -r requirements.txt

# 安装 weather-skill 依赖
cd ../weather-skill
pip install -r requirements.txt

# 安装 composition-scoring-skill 依赖 (仅需标准库)
cd ../composition-scoring-skill
# pip install -r requirements.txt
```

### 2. 部署 Skill

将对应的技能目录复制或链接到您的 Agent 技能目录下（例如 `~/.claude/skills/` 或项目根目录下的 `.claude/skills/`）。

Agent 启动时会自动加载 `SKILL.md` 并识别意图。

