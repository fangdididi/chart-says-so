# chart-says-so（图上说的，数据认不认）

[English](README.md) | **中文**

> 图表上的每一个字，都要由这张图上的数字来撑腰。

一个 agent skill：在图表发布之前，用图表自己的数据去核对图上的文字。它找出标题、副标题、注释和替代文字里的说法，逐条用画出来的序列检验；检查图表文字以及几种会让图形"说谎"的画法；按数据重写文字；最后给出一个结论：**SHIP（可以发）**、**FIX（改完再发）** 或 **HOLD（不能发）**。

适用于 Claude Code、Codex、Cursor 以及任何能读取 `SKILL.md` 的 agent。辅助脚本是纯 Python 3（只用标准库）。

## 为什么需要它

Agent 画图很在行，写图上的字却常出错：

- 线只涨了 60%，标题写"翻倍"。
- 只有 7 个点就写"历史新高"，或者峰值其实在两年前。
- 占比从 20% 升到 35%，写成"上升了 15%"（其实是 15 个百分点，相对增长 75%）。
- 柱状图纵轴从 1000 开始。
- 标题是"每周用户折线图"，副标题是"悬停查看详情"，替代文字只有"柱状图"。

读者信标题胜过信柱子。这个 skill 让你在别人发现之前先发现。

## 功能

- **中英文说法核对。** 带数字的变化（`rose 12%`、`下降了3个百分点`）、倍数（`doubled`、`3x`、`翻倍`、`减半`）、极值（`highest`、`record`、`新高`）以及只有方向的词。支持年份区间（`since 2020`、`from 2021 to 2024`、`2020年以来`）。
- **四种判定。** HOLDS 成立、STRETCH 夸大（方向对、幅度说大了）、WRONG 错误（数据不支持）、UNCHECKED 无法核对（需要人工或点明序列）。
- **百分比与百分点。** 在百分比轴上，"%"类说法两种读法都算，并在文字写清之前一直提醒。
- **起点挑选提醒。** 前面明明还有数据，却从最低点开始算涨幅（或从最高点算跌幅）。
- **17 个检查代码**，覆盖图表文字和装饰：写图表类型的标题、只有话题的标题、看图说明、重复、密网格和 3D、用图例代替直接标注、缺单位/来源/替代文字、柱状图截断基线、双纵轴、饼图太碎、少量数据配趋势词、夸张词。
- **一个结论。** SHIP / FIX / HOLD，同时作为退出码 0 / 1 / 2，可接入 CI。
- **重写顺序。** 标题写结论，副标题写单位和时间段，直接标注，事件注释，来源行，带数字的替代文字。

## 安装

```bash
git clone https://github.com/fangdididi/chart-says-so.git
```

| Agent | 放置位置 |
|---|---|
| Claude Code | `~/.claude/skills/chart-says-so/`（或项目内 `.claude/skills/`） |
| Codex | `~/.codex/skills/chart-says-so/`，或在 `AGENTS.md` 中引用 `SKILL.md` |
| Cursor | `.cursor/skills/chart-says-so/`，或把 `SKILL.md` 加为项目规则 |
| 其他 agent | 让它读取 `SKILL.md`（英文）或 `SKILL.zh-CN.md`（中文） |

然后这样说即可：*"放进 PPT 之前，帮我检查一下 reports/q3.py 里的图。"* 或 *"给这张图写一段老实的替代文字。"*

## 直接使用脚本

```bash
python3 scripts/chartcheck.py --blank > card.json     # 生成卡片模板
python3 scripts/chartcheck.py card.json               # markdown 报告
python3 scripts/chartcheck.py card.json --json        # JSON 结果
python3 -m unittest discover -s tests                 # 17 个测试
```

## 示例

`examples/before.json`：柱状图，标题"Column chart of monthly sign-ups"，副标题"Sign-ups surged 120% since 2022. Hover a bar for details."，纵轴从 1000 起，3D 柱子，没有来源。

```
**Gate: HOLD**

| # | Where    | Said        | Series   | Window    | Data              | Verdict |
|---|----------|-------------|----------|-----------|-------------------|---------|
| 1 | subtitle | surged 120% | Sign-ups | 2022→2025 | +109.1 % relative | STRETCH |

- [FIX]  C02 NAMES-THE-CHART
- [FIX]  C04 READING-INSTRUCTIONS
- [HOLD] C10 CUT-BASELINE: column chart with value axis starting at 1000
- [WARN] C14 CHOSEN-START: 'surged 120%' starts at the series low (2022→2025)
- ...
```

`examples/after.json`：标题改为"Monthly sign-ups doubled from 2022 to 2025"，纵轴从零起，给 2022 年回落加注释，补来源行，替代文字写出具体数字。**结论：SHIP。**

`examples/zh-share.json`：中文图表，"线上订单占比上升了15%"只有按百分点理解才成立。**结论：FIX**，触发 C13。

## 文件结构

```
chart-says-so/
├── SKILL.md              # skill 说明（英文）
├── SKILL.zh-CN.md        # skill 说明（中文）
├── README.md
├── README.zh-CN.md
├── LICENSE
├── scripts/
│   └── chartcheck.py     # 说法核对 + 检查 + 结论，仅标准库
├── examples/
│   ├── before.json       # HOLD
│   ├── after.json        # SHIP
│   └── zh-share.json     # FIX（百分比与百分点）
└── tests/
    └── test_chartcheck.py
```

## 局限

脚本只认简单句式，只看卡片里的数字。它不看图片，也判断不了序列之间的比较、排名，或依赖图外数据的说法。skill 会要求 agent 人工核对这些内容，并在报告里列出。

## 许可证

MIT © fangdididi
