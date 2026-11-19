# H10: a regular ruled Out and his teammates' lines

1. History (Unibet 2022/23, data/backtest/2022_lines.csv, variant 'absences': every rotation player who didn't
     play is known to be out, an upper bound on the news). A line counts when a regular (news.MIN_MINUTES+ over
     his last 10 games) of the player's team sat that night; side = the direction of the line's lineup adj, its
     size = |lineup adj| / avg. Won − price (margin-free) and ROI after tax by game without him no. (1, 2–3, 4+:
     the lowest of the team's absent regulars) and size (10%+, 20%+), with 95% ranges from resampling nights.
  2. Superbet: the rule exactly as the window applies it (absence_window.out_tonight from the night's RotoWire
     versions, absence_window.signal_rows: each listed teammate line at its first scheduled read once Out was known,
     on the side of its change), counted and judged as backtest/mispricing_eval's signals: once per game, player,
     bet and side, only when the next read still had the same line and odds not worse, after-tax CLV and ROI with
     99% ranges, the registry's verdict. Plus won − price on the settled signals.

Nights up to D are recognition (descriptive: the rule was fixed before looking at them, D = the day it was
written); nights after D decide (at least 10). Writes data/backtest/absence_shift.md and absence_shift.json (what
the Overview's window says about the record). The status in mispricing_status.json is set by hand.

## Superbet: evaluation (nights after 2026-11-19) decides, recognition (up to 2026-11-19) describes

| period | nights | signals | not takeable | unchecked | settled | won % | ROI after tax % | ROI low | ROI high | with a close | CLV after tax % | CLV low | CLV high | verdict | why | won − price pp |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| recognition · all | 15 | 527 | 289 | 55 | 521 | 51.8 | -14.8 | -25.8 | -7.1 | 235 | -18.5 | -19.3 | -17.9 | rejected | the high end of the 99% range of the CLV is below 0 | 1.7 |
| recognition · first game | 15 | 344 | 193 | 20 | 342 | 54.7 | -10.4 | -24.0 | 3.5 | 159 | -18.2 | -18.6 | -17.8 | rejected | the high end of the 99% range of the CLV is below 0 | 4.5 |
| evaluation · all | 0 | 0 | 0 | 0 | 0 | – | – | – | – | 0 | – | – | – | wait | 0 of the 10 nights a verdict needs | – |
| evaluation · first game | 0 | 0 | 0 | 0 | 0 | – | – | – | – | 0 | – | – | – | wait | 0 of the 10 nights a verdict needs | – |

## History: Unibet 2022/23 (known absences, an upper bound)

A side needs about 8–11 pp over the price after tax.

| game without him | size ≥ % | lines | nights | won % | price % | won − price pp | low | high | ROI after tax % |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 10.0 | 3670 | 129 | 49.8 | 49.8 | 0.1 | -2.1 | 2.1 | -17.0 |
| 1 | 20.0 | 1589 | 124 | 49.9 | 49.8 | 0.1 | -3.5 | 3.8 | -17.0 |
| 2–3 | 10.0 | 1885 | 98 | 49.3 | 49.9 | -0.6 | -4.2 | 2.6 | -18.5 |
| 2–3 | 20.0 | 750 | 89 | 50.8 | 49.7 | 1.1 | -4.2 | 6.3 | -15.4 |
| 4+ | 10.0 | 834 | 66 | 45.2 | 49.8 | -4.6 | -9.0 | -0.3 | -25.2 |
| 4+ | 20.0 | 272 | 60 | 43.8 | 49.9 | -6.1 | -13.5 | 1.3 | -27.2 |
