# chart-says-so

**English** | [中文](README.zh-CN.md)

> Every word on a chart has to be earned by the numbers on that chart.

An agent skill that checks a chart's words against its own data before the chart is published. It finds the claims in the title, subtitle, notes and alt text, tests each one against the plotted series, lints the text and the few drawing choices that make a shape lie, helps rewrite the words from the data, and ends with one gate: **SHIP**, **FIX** or **HOLD**.

Works with Claude Code, Codex, Cursor and any agent that reads `SKILL.md`. The helper script is plain Python 3 (standard library only).

## Why

Agents draw charts well and write chart text badly:

- "Doubled" over a line that rose 60%.
- "Record high" over seven data points, or over a line whose peak was two years ago.
- "Up 15%" on a share that moved from 20% to 35% (that is 15 points, or 75% relative).
- Bars whose axis starts at 1,000.
- A title that says "Line chart of weekly users", a subtitle that says "Hover for details", alt text that says "bar chart".

Readers trust the headline more than the bars. This skill catches the gap before anyone else does.

## Features

- **Claim check, English and Chinese.** Changes with a number (`rose 12%`, `下降了3个百分点`), multiples (`doubled`, `3x`, `翻倍`, `减半`), extremes (`highest`, `record`, `新高`) and plain directions. Year windows (`since 2020`, `from 2021 to 2024`, `2020年以来`) are honored.
- **Four verdicts.** HOLDS, STRETCH (right direction, overstated), WRONG (data says otherwise), UNCHECKED (needs a human or a series name).
- **Percent vs points.** On a percent axis, a "%" claim is tested both ways and flagged until the text says which one it means.
- **Chosen-start warning.** A rise measured from the series low (or a fall from the high) while earlier points exist.
- **17 lint codes** for chart words and scaffolding: chart-type titles, topic titles, reading instructions, repetition, heavy gridlines and 3D, legend instead of direct labels, missing unit, source or alt text, cut baselines on bars, twin axes, crowded pies, trend words on thin data, hype words.
- **One gate.** SHIP / FIX / HOLD, also as exit code 0 / 1 / 2 for CI.
- **Rewrite order.** Title as a finding, subtitle with unit and period, direct labels, event notes, source line, alt text with numbers.

## Install

```bash
git clone https://github.com/fangdididi/chart-says-so.git
```

| Agent | Where to put it |
|---|---|
| Claude Code | `~/.claude/skills/chart-says-so/` (or `.claude/skills/` in a project) |
| Codex | `~/.codex/skills/chart-says-so/` or reference `SKILL.md` from `AGENTS.md` |
| Cursor | `.cursor/skills/chart-says-so/` or add `SKILL.md` as a project rule |
| Any other agent | Point it at `SKILL.md` (English) or `SKILL.zh-CN.md` (Chinese) |

Then ask, for example: *"Check the chart in reports/q3.py before I put it in the deck."* or *"Write honest alt text for this chart."*

## Use the script directly

```bash
python3 scripts/chartcheck.py --blank > card.json     # starter card
python3 scripts/chartcheck.py card.json               # markdown report
python3 scripts/chartcheck.py card.json --json        # JSON result
python3 -m unittest discover -s tests                 # 17 tests
```

## Example

`examples/before.json`: column chart titled "Column chart of monthly sign-ups", subtitle "Sign-ups surged 120% since 2022. Hover a bar for details.", axis from 1,000, 3D bars, no source.

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

`examples/after.json`: "Monthly sign-ups doubled from 2022 to 2025", axis from zero, a note on the 2022 dip, a source line, alt text with the numbers. **Gate: SHIP.**

`examples/zh-share.json`: a Chinese chart where "占比上升了15%" is only true as percentage points. **Gate: FIX** with C13.

## File structure

```
chart-says-so/
├── SKILL.md              # skill instructions (English)
├── SKILL.zh-CN.md        # skill instructions (Chinese)
├── README.md
├── README.zh-CN.md
├── LICENSE
├── scripts/
│   └── chartcheck.py     # claim check + lint + gate, stdlib only
├── examples/
│   ├── before.json       # HOLD
│   ├── after.json        # SHIP
│   └── zh-share.json     # FIX (percent vs points)
└── tests/
    └── test_chartcheck.py
```

## Limits

The script reads simple sentence shapes and the numbers in the card. It does not look at images, and it cannot judge comparisons between series, rankings or claims backed by data outside the chart. The skill tells the agent to check those by hand and to list them in the report.

## License

MIT © fangdididi
