# H3: Superbet's team totals against its player points lines

At every read of a game before tip-off (the schedule's reads rebuilt from the quote files, older games from the
dashboard's snapshots) the team's gap: Superbet's team total − the sum of its player PTS lines' medians − what the
team's other players usually score (RotoWire's out players left out, as of that read).

  a. The signal (decides): every PTS line of a team whose |gap| ≥ team_total.MIN_GAP, on the gap's side (Over when
     above 0), no profitability threshold. Counted and judged exactly as backtest/mispricing_eval's signals: once
     per game, player, bet and side at its first read where it could be taken (the next read still had the same
     line and odds not worse), after-tax CLV and ROI with 99% ranges from resampling whole nights, the registry's
     verdict.
  b. The mechanism (descriptive): at each PTS line's last read, the gap's side won − its margin-free price by
     |gap|, and per team the correlation of the gap with the players' points minus their lines and with the team's
     points minus its total (the team total should be right and the lines off, not the other way round).
  c. As a model input (descriptive, what backtest/ablation.py would ask of a new rung): on the settled PTS lines
     at their last read, the market's chance with an Over/Under bias against the same plus the line's shift (its
     share of the gap / its spread), fitted on the earlier 70% of the nights and scored on the rest; log loss minus
     the market's with a 95% range from resampling nights.

Nights up to D are recognition (the rule was written on D after looking at them); nights after D decide (at least
10). Writes data/backtest/team_total.md. The status in mispricing_status.json is set by hand.

Fixed with D: OFFSET 0 points, MIN_GAP 6, others over the team's last 10 games. A side needs about 8–11 pp over the price after tax.

## Recognition (nights up to 2026-11-20): describes

### a. The signal (after tax)

| nights | signals | not takeable | unchecked | settled | won % | ROI after tax % | ROI low | ROI high | with a close | CLV after tax % | CLV low | CLV high | verdict | why | won − price pp |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 30 | 1379 | 134 | 523 | 1326 | 51.6 | -16.2 | -20.1 | -11.2 | 365 | -18.6 | -19.1 | -17.9 | rejected | the high end of the 99% range of the CLV is below 0 | 1.3 |

### b. The gap's side at the last read, by |gap|

| |gap| points | lines | nights | won % | price % | won − price pp | low | high | ROI after tax % |
|---|---|---|---|---|---|---|---|---|
| [0, 3) | 719 | 28 | 49.7 | 50.1 | -0.4 | -2.9 | 2.3 | -19.0 |
| [3, 6) | 580 | 28 | 51.2 | 50.1 | 1.1 | -2.4 | 4.7 | -16.3 |
| [6, 10) | 627 | 29 | 51.2 | 49.9 | 1.3 | -2.1 | 4.7 | -16.0 |
| [10, 15) | 455 | 26 | 47.7 | 50.0 | -2.4 | -6.1 | 2.6 | -22.0 |
| [15, 1000) | 505 | 22 | 48.9 | 50.0 | -1.1 | -5.9 | 3.7 | -19.9 |

Per team at its last read:

| teams | nights | mean gap | sd gap | corr(gap, players − lines) | corr(gap, team − T) |
|---|---|---|---|---|---|
| 450 | 30 | -0.774 | 15.448 | 0.043 | 0.027 |

## c. As a model input (recognition nights, the later 30% scored)

| model | scored lines | vs market | low | high | shift coefficient |
|---|---|---|---|---|---|
| market + Over/Under bias | 892 | 0.0015 | -0.0001 | 0.0030 | – |
| + the team-total shift | 892 | 0.0023 | 0.0002 | 0.0050 | -0.1255 |
