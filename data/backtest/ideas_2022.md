# Candidate changes to the props model, on Unibet 2022/23 (exploratory)

Calibrated (a, b) on Nov 09 – Jan 31 2023 (15568 lines), scored on Feb 01 – May 08 2023 (13763 lines, 77 nights), every candidate on the same lines. Recency features rebuilt from the 2022/23 logs: 0 of 29331 lines with a game count different from the backtest's.

*vs current* = the candidate's log loss minus the current model's, per line side (below 0 = better), with the 95% range from resampling whole nights; *3PM* the same on 3PM lines only. Several candidates are tried on the same nights, so treat a small gain as noise.

| candidate | log loss | vs market | vs current | range low | range high | vs current, 3PM | 3PM low | 3PM high |
|---|---|---|---|---|---|---|---|---|
| Current model | 0.6891 | -0.0004 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| Normal distribution (model 2026-10-26) | 0.6893 | -0.0002 | 0.0002 | 0.0001 | 0.0002 | 0.0004 | 0.0002 | 0.0006 |
| Distribution only (no hit rate) | 0.6890 | -0.0005 | -0.0002 | -0.0003 | 0.0000 | -0.0001 | -0.0003 | 0.0001 |
| Recency, half-life 5 games | 0.6896 | 0.0002 | 0.0005 | 0.0000 | 0.0010 | 0.0007 | 0.0000 | 0.0013 |
| Recency, half-life 10 games | 0.6895 | -0.0000 | 0.0004 | 0.0000 | 0.0007 | 0.0004 | -0.0001 | 0.0009 |
| Recency, half-life 20 games | 0.6893 | -0.0002 | 0.0002 | 0.0000 | 0.0004 | 0.0002 | -0.0001 | 0.0005 |

Betting each candidate's positive-edge picks on those lines (1 unit at the line's odds):

| candidate | bets | hit % | ci low % | ci high % | ROI % | avg odds |
|---|---|---|---|---|---|---|
| Current model | 107 | 55.1 | 45.7 | 64.2 | 0.4 | 1.9 |
| Normal distribution (model 2026-10-26) | 89 | 53.9 | 43.6 | 63.9 | -2.3 | 1.8 |
| Distribution only (no hit rate) | 382 | 55.8 | 50.7 | 60.7 | 3.1 | 1.9 |
| Recency, half-life 5 games | 0 | – | – | – | – | – |
| Recency, half-life 10 games | 0 | – | – | – | – | – |
| Recency, half-life 20 games | 9 | 55.6 | 26.7 | 81.1 | -1.3 | 1.8 |
