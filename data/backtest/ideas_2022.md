# Candidate changes to the props model, on Unibet 2022/23 (exploratory)

Calibrated (a, b) on Nov 09 – Jan 31 2023 (15568 lines), scored on Feb 01 – May 08 2023 (13763 lines, 77 nights), every candidate on the same lines. Recency features rebuilt from the 2022/23 logs: 0 of 29331 lines with a game count different from the backtest's.

*vs current* = the candidate's log loss minus the current model's, per line side (below 0 = better), with the 95% range from resampling whole nights; *3PM* the same on 3PM lines only. Several candidates are tried on the same nights, so treat a small gain as noise.

| candidate | log loss | vs market | vs current | range low | range high | vs current, 3PM | 3PM low | 3PM high |
|---|---|---|---|---|---|---|---|---|
| Current model | 0.6893 | -0.0002 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| Distribution only (no hit rate) | 0.6893 | -0.0001 | 0.0001 | -0.0001 | 0.0003 | 0.0005 | 0.0002 | 0.0007 |
| Count distribution: 3PM | 0.6892 | -0.0003 | -0.0001 | -0.0001 | -0.0000 | -0.0003 | -0.0005 | -0.0002 |
| Count distribution: 3PM, AST, REB | 0.6892 | -0.0003 | -0.0001 | -0.0001 | -0.0000 | -0.0003 | -0.0005 | -0.0002 |
| Count distribution: every stat | 0.6891 | -0.0004 | -0.0002 | -0.0002 | -0.0001 | -0.0004 | -0.0006 | -0.0002 |
| Recency, half-life 5 games | 0.6896 | 0.0001 | 0.0003 | -0.0001 | 0.0008 | 0.0003 | -0.0003 | 0.0008 |
| Recency, half-life 10 games | 0.6895 | 0.0001 | 0.0003 | -0.0001 | 0.0006 | 0.0002 | -0.0003 | 0.0007 |
| Recency, half-life 20 games | 0.6894 | -0.0000 | 0.0002 | -0.0000 | 0.0004 | 0.0001 | -0.0001 | 0.0004 |

Betting each candidate's positive-edge picks on those lines (1 unit at the line's odds):

| candidate | bets | hit % | ci low % | ci high % | ROI % | avg odds |
|---|---|---|---|---|---|---|
| Current model | 89 | 53.9 | 43.6 | 63.9 | -2.3 | 1.8 |
| Distribution only (no hit rate) | 255 | 55.3 | 49.2 | 61.3 | 1.7 | 1.9 |
| Count distribution: 3PM | 78 | 53.8 | 42.9 | 64.5 | -2.2 | 1.8 |
| Count distribution: 3PM, AST, REB | 65 | 56.9 | 44.8 | 68.2 | 3.0 | 1.8 |
| Count distribution: every stat | 107 | 55.1 | 45.7 | 64.2 | 0.4 | 1.9 |
| Recency, half-life 5 games | 0 | – | – | – | – | – |
| Recency, half-life 10 games | 0 | – | – | – | – | – |
| Recency, half-life 20 games | 3 | 66.7 | 20.8 | 93.9 | 15.7 | 1.7 |
