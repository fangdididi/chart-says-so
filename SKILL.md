---
name: chart-says-so
description: Check that every word on a chart is earned by its numbers before the chart ships. Turns a chart into a small card, tests each claim in the title, subtitle, notes and alt text against the plotted data (HOLDS / STRETCH / WRONG / UNCHECKED), lints the chart's words and scaffolding (C01-C17), rewrites the text from the data, and returns a gate of SHIP, FIX or HOLD. Use when an agent or person has made a chart for a report, deck, dashboard, post or README and is about to publish it.
---

# chart-says-so

**Language:** English | [中文](SKILL.zh-CN.md)

## What this is

A chart is two things glued together: marks drawn from data, and words written by someone. Agents are good at drawing the marks and careless with the words. The title says "doubled" when the line went up 60%. The subtitle says "record high" over seven data points. A bar chart starts its axis at 1,000 so a 9% gap looks like a cliff. The text explains how to hover. The alt text says "bar chart" and nothing else.

chart-says-so is a pre-publish check for that gap. It does three jobs, in this order:

1. **Truth.** Find every checkable claim in the chart's words and test it against the numbers on the chart itself.
2. **Words.** Cut the text a reader does not need (chart-type titles, reading instructions, repeated lines, hype) and add the text they do need (a takeaway title, a unit, a source, alt text with numbers).
3. **Drawing honesty.** Catch the few drawing choices that make the shape lie: a cut baseline on bars, twin value axes, a crowded pie, a start point picked at the series low.

It ends with one gate: **SHIP**, **FIX** or **HOLD**.

## The problem it solves

Wrong chart text is worse than no text, because readers trust the title more than the bars. Most chart guidance is about picking the right chart or making it pretty. This skill assumes the chart type is already chosen and asks a narrower question: *does the chart say anything its data does not show?*

## When to use it

- An agent just produced a chart (matplotlib, Vega-Lite, ECharts, Chart.js, Recharts, a spreadsheet, an SVG) for something that other people will read.
- You are reviewing a slide, report, dashboard tile, blog post or social image that has a chart with a headline on it.
- You are writing alt text or a caption for an existing chart.

Do **not** use it to choose a chart type, design a palette or build a dashboard layout. Do not use it on exploratory plots that only you will see.

## Step by step

### 1. Make the chart card

Write a JSON card that holds exactly what the reader will see. Start from `python3 scripts/chartcheck.py --blank`. Fields:

| Field | Meaning |
|---|---|
| `kind` | `line`, `area`, `bar`, `column`, `stacked`, `pie`, `donut`, `scatter`, `slope` |
| `title`, `subtitle` | The words as shown, not as intended |
| `y.unit`, `y.min`, `y.log` | Value-axis unit, where the axis starts, log scale or not |
| `series[].name`, `series[].points` | Each plotted series as `[x, y]` pairs, in the order drawn. Use the numbers the chart actually plots, after any filtering |
| `labels` | `legend` or `direct` (name at the line end / on the bar) |
| `value_labels` | `all`, `some` or `none` |
| `gridlines` | `none`, `light` or `dense` |
| `second_axis` | `true` if there is a second value axis |
| `decoration` | Anything with no data job: `3d`, `drop shadow`, `gradient`, `frame`, `icons` |
| `annotations[].text` | Notes placed on the chart |
| `source` | The source line as shown |
| `alt` | The alt text as shipped |

Read the values from the code or data that drew the chart, never from the picture. If you can only see an image, mark the card `"read_from": "image"` and say so in the report.

### 2. Run the check

```bash
python3 scripts/chartcheck.py card.json          # markdown report
python3 scripts/chartcheck.py card.json --json   # for further processing
```

Exit code: 0 SHIP, 1 FIX, 2 HOLD.

### 3. Read the claim verdicts

The script finds claims in English and Chinese: changes with a number (`rose 12%`, `下降了3个百分点`), multiples (`doubled`, `3x`, `翻倍`, `减半`), extremes (`highest`, `record`, `新高`), and bare directions (`grew`, `回落`). It uses a year window if the sentence names one (`since 2020`, `from 2021 to 2024`, `2020年以来`), otherwise first point to last point.

| Verdict | Meaning | What to do |
|---|---|---|
| HOLDS | Direction and size match within 5% (multiples within 10%) | Keep |
| STRETCH | Direction right, size or scope overstated | Rewrite with the real number, or soften ("up about 60%") |
| WRONG | Data moves the other way, or the "highest" point is not the latest | Rewrite; the chart cannot ship as is |
| UNCHECKED | No series named when there are several, window not in data, start value zero | Name the series or check by hand and note it |

The script only reads simple sentence shapes. Read every title and note yourself as well and test any claim it missed (comparisons between series, rankings, "most", "only") by hand with the same four verdicts.

### 4. Work through the findings

| Code | Level | Finding |
|---|---|---|
| C01 NO-TITLE | fix | No title |
| C02 NAMES-THE-CHART | fix | Title says what the chart is ("Line chart of…") instead of what it shows |
| C03 TOPIC-TITLE | warn | Title is a topic with no finding |
| C04 READING-INSTRUCTIONS | fix | "Hover for details", "each dot is one week" |
| C05 SAID-TWICE | fix/warn | Subtitle repeats title; value on every mark plus gridlines |
| C06 HEAVY-SCAFFOLD | warn/fix | Dense gridlines, 3D, shadows, frames |
| C07 LEGEND-NOT-LABEL | warn | 2-6 lines identified by a legend instead of names at the line ends |
| C08 NO-UNIT | fix | Value axis without a unit |
| C09 NO-SOURCE | fix | No source line |
| C10 CUT-BASELINE | hold | Bar, column, area or stacked chart whose value axis does not start at zero |
| C11 TWIN-AXES | fix | Two value axes |
| C12 PIE-CROWD | fix/hold | More than 5 slices; percent slices that do not add to 100 |
| C13 PERCENT-VS-POINTS | fix | A "%" change on a percent axis; say "points" or "relative" |
| C14 CHOSEN-START | warn | A rise measured from the series low (or a fall from its high) while earlier points exist |
| C15 THIN-TREND | fix | "Surging", "plunging" on three points or fewer |
| C16 NO-ALT | fix | Missing alt text, or alt text with no finding and no numbers |
| C17 HYPE-WORD | warn | "Unprecedented", "stunning" and similar |

### 5. Rewrite from the data

Rewrite the words in this order, using only numbers present in the card:

1. **Title:** one sentence with the finding, a subject and a verb. "Sign-ups doubled from 2022 to 2025", not "Sign-ups over time".
2. **Subtitle:** what is counted, the unit and the period. Put the old topic title here.
3. **Labels:** name each line at its end; label only the points the title talks about.
4. **Notes:** one short note per event that explains a bend in the line. No reading instructions.
5. **Source line:** owner, dataset and date pulled.
6. **Alt text:** the title's finding plus the start, end and extreme values, in one or two sentences.

Then fix drawing honesty: bars and areas start at zero; split twin axes into two panels or index both to 100; fold small pie slices into "Other" or switch to sorted bars; if C14 fires, either show the earlier points or say the window in the title.

### 6. Re-run and report

Run the script again on the edited card until the gate is SHIP (warnings may remain if you can say why). Report:

- the gate before and after,
- each claim with its verdict and the number you used,
- the new title, subtitle, source line and alt text,
- anything checked by hand or left as a task for a human (for example, a number not in the plotted data).

## Examples

**Before** (`examples/before.json`): column chart titled "Column chart of monthly sign-ups", subtitle "Sign-ups surged 120% since 2022. Hover a bar for details.", value axis starting at 1,000, 3D bars, no source, alt "Bar chart of sign-ups".

Result: **HOLD**. The claim is STRETCH (data shows +109%, not +120%). C10 fires because the bars start at 1,000, and C02, C04, C06, C08, C09 and C16 also fire.

**After** (`examples/after.json`): title "Monthly sign-ups doubled from 2022 to 2025", subtitle with unit and period, axis from zero, one note on the 2022 dip, source line, alt text with 1,200 → 1,100 → 2,300. Result: **SHIP**, with a C14 warning that is answered by the note on the dip and the visible 2021 bar.

**Percent axis** (`examples/zh-share.json`): "线上订单占比上升了15%" on a share that went from 20% to 35%. That is +15 points but +75% relative, so the claim holds only as points. C13 asks for "15个百分点". The "历史新高" note over 7 points is a STRETCH; write "2019年以来最高".

## Tips

- Check the numbers the chart plots, not the raw table. Filtering, rounding, rolling averages and currency conversion all change the claim.
- A claim the data cannot reach (market share, "first ever", a number from elsewhere) is not wrong, but it does not belong on the chart unless the source line backs it. List it as a task.
- "Record" needs the full history. Over a short window, say "highest since 2019".
- Log axes and indexed lines (=100) need their own words in the subtitle: "log scale", "2020 = 100".
- A title can be true and still mislead through its window. If the earlier points tell a different story, show them.
- Keep warnings only when you can explain them in one line in the report.
