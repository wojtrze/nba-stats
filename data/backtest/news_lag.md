# H4 stage 1: RotoWire news and the speed of Superbet's lines

Events and reactions come from dashboard/news.py (the same code as the Overview's news window): a regular (20+
minutes over his last 10 games) ruled out, or back from Out, between two RotoWire versions at most 2 h apart, on a
game the schedule read before the news and at its slot. Only games read by the schedule count (the dashboard's
snapshots are too sparse to time a reaction).

  1. Speed (descriptive): how many teammate lines had moved or were withdrawn by our first read, how many moved
     only later and how many minutes after we saw the news, against the other team's lines between the same two
     reads (what moves without news), and how far the late moves went against the ~11 pp a side needs after tax.
  2. The signal (test a, decides): the side fixed in advance (2026-11-19) – a teammate's Over after an out, his
     Under after a return – on every teammate PTS / REB / AST / PRA line that still stood at our first read, taken
     at that read. Counted and judged exactly as backtest/mispricing_eval's signals: once per game, player, bet and
     side, only when the next read still had the same line and odds not worse, after-tax CLV and ROI with 99% ranges
     from resampling whole nights, the registry's verdict.

Nights up to D are the recognition nights (descriptive, they set nothing after the fact: the side and the signal
were fixed before looking at them); nights after D decide (at least 10). Writes data/backtest/news_lag.md and
news_lag.json (the summary the Overview's news window shows). The status in mispricing_status.json is set by hand.

## Evaluation (nights after 2026-11-19): decides

### Speed

| news | events | nights | lines | moved by our read | withdrawn by our read | moved later | never | reacted by our read % | other team moved % | late: median min | late: median pp |
|---|---|---|---|---|---|---|---|---|---|---|---|
| out | 0 | 0 | 0 | 0 | 0 | 0 | 0 | – | – | – | – |
| return | 0 | 0 | 0 | 0 | 0 | 0 | 0 | – | – | – | – |
| all | 0 | 0 | 0 | 0 | 0 | 0 | 0 | – | – | – | – |

A side needs about 11 pp after tax; *late: median pp* is how far the chance moved after our read on the lines that stood (same line).

### The signal (after tax)

| nights | signals | not takeable | unchecked | settled | won % | ROI after tax % | ROI low | ROI high | with a close | CLV after tax % | CLV low | CLV high | verdict | why |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 0 | 0 | 0 | 0 | – | – | – | – | 0 | – | – | – | wait | 0 of the 10 nights a verdict needs |

## Recognition (nights up to 2026-11-19): descriptive

### Speed

| news | events | nights | lines | moved by our read | withdrawn by our read | moved later | never | reacted by our read % | other team moved % | late: median min | late: median pp |
|---|---|---|---|---|---|---|---|---|---|---|---|
| out | 54 | 10 | 700 | 410 | 203 | 78 | 9 | 87.6 | 70.0 | 40.0 | 1.0 |
| return | 5 | 2 | 46 | 21 | 0 | 25 | 0 | 45.7 | 55.7 | 60.0 | 1.7 |
| all | 59 | 10 | 746 | 431 | 203 | 103 | 9 | 85.0 | 68.9 | 60.0 | 1.0 |

A side needs about 11 pp after tax; *late: median pp* is how far the chance moved after our read on the lines that stood (same line).

### The signal (after tax)

| nights | signals | not takeable | unchecked | settled | won % | ROI after tax % | ROI low | ROI high | with a close | CLV after tax % | CLV low | CLV high | verdict | why |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 15 | 52 | 49 | 6 | 48 | 39.6 | -34.0 | -80.9 | -7.2 | 24 | -18.8 | -19.4 | -18.0 | rejected | the high end of the 99% range of the CLV is below 0 |
