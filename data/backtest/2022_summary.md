# 2022/23 backtest of the props model

Unibet's 2022/23 player lines, each priced by `models.price_props` from the games before its date only. Main lines (the most balanced price per player, stat and game) of players with 5+ games. Pushes are left out; ROI is per unit at the line's odds; ci = 95% Wilson interval.

model %, edges and signals are calibrated (data/backtest/calibration.json) when the calibration exists; it's fitted on this same season, so these numbers are then in-sample. The honest check on games the fit never saw is data/backtest/calibration.md.

- raw rows: 541877, player games: 26891, players: 511, rows moved to the real team: 2395, player games with a position: 86%
- lines in the file: 39829, lines without a matching player: 9, lines where the player didn't play that game: 0, lines priced: 39820, main lines: 29388

## Variant: none

29331 lines, 151 dates.

### Strategies on the same lines

| strategy | bets | hit % | ci low % | ci high % | ROI % | avg odds |
|---|---|---|---|---|---|---|
| Always Under | 29331 | 52.2 | 51.6 | 52.7 | -2.7 | 1.9 |
| Always Over | 29331 | 47.8 | 47.3 | 48.4 | -8.9 | 1.9 |
| Bookmaker's favourite side | 29331 | 53.8 | 53.2 | 54.4 | -4.8 | 1.8 |
| Toward the season average | 29095 | 52.7 | 52.2 | 53.3 | -3.3 | 1.8 |
| Toward the last-5 average | 29331 | 50.6 | 50.0 | 51.1 | -6.3 | 1.9 |
| Toward proj avg | 29326 | 52.7 | 52.1 | 53.3 | -3.3 | 1.8 |
| Model pick (every line) | 29331 | 52.5 | 51.9 | 53.1 | -3.4 | 1.9 |
| Model pick, edge > 0 (🟢 or 🟡) | 258 | 53.1 | 47.0 | 59.1 | -2.1 | 1.9 |
| Model pick, 🟢 only | 0 | – | – | – | – | – |

### Model pick – by signal

| signal | bets | expected % | hit % | ci low % | ci high % | ROI % | avg odds |
|---|---|---|---|---|---|---|---|
| none | 29331 | 52.0 | 52.5 | 51.9 | 53.1 | -3.4 | 1.9 |

### Model pick – by edge (pp)

| edge bucket | bets | expected % | hit % | ci low % | ci high % | ROI % | avg odds |
|---|---|---|---|---|---|---|---|
| ≤ 0 | 29073 | 52.0 | 52.5 | 51.9 | 53.1 | -3.4 | 1.9 |
| 0–5 | 258 | 54.5 | 53.1 | 47.0 | 59.1 | -2.1 | 1.9 |

### Model pick – by bet type

| bet_type | bets | expected % | hit % | ci low % | ci high % | ROI % | avg odds |
|---|---|---|---|---|---|---|---|
| 3PM | 4860 | 54.4 | 54.3 | 52.9 | 55.7 | -4.3 | 1.8 |
| ARP | 6243 | 51.0 | 50.6 | 49.4 | 51.9 | -4.8 | 1.9 |
| AST | 4766 | 52.5 | 53.9 | 52.5 | 55.3 | -1.5 | 1.8 |
| PTS | 6817 | 50.9 | 50.8 | 49.6 | 52.0 | -4.5 | 1.9 |
| REB | 6645 | 52.1 | 53.6 | 52.4 | 54.8 | -1.5 | 1.8 |

### Model pick – by side

| best side | bets | expected % | hit % | ci low % | ci high % | ROI % | avg odds |
|---|---|---|---|---|---|---|---|
| Over | 10313 | 51.6 | 50.5 | 49.5 | 51.5 | -6.6 | 1.9 |
| Under | 19018 | 52.3 | 53.6 | 52.9 | 54.3 | -1.7 | 1.8 |

### Model pick – by month

| month | bets | expected % | hit % | ci low % | ci high % | ROI % | avg odds |
|---|---|---|---|---|---|---|---|
| 2022-11 | 3224 | 52.2 | 51.4 | 49.6 | 53.1 | -6.0 | 1.8 |
| 2022-12 | 5808 | 52.1 | 52.3 | 51.0 | 53.6 | -3.8 | 1.9 |
| 2023-01 | 6536 | 52.1 | 53.1 | 51.9 | 54.3 | -2.1 | 1.9 |
| 2023-02 | 4794 | 52.1 | 52.8 | 51.4 | 54.2 | -2.4 | 1.9 |
| 2023-03 | 5605 | 51.9 | 53.0 | 51.7 | 54.3 | -2.5 | 1.9 |
| 2023-04 | 2840 | 52.0 | 51.0 | 49.1 | 52.8 | -6.6 | 1.8 |
| 2023-05 | 524 | 51.8 | 53.6 | 49.3 | 57.9 | -0.6 | 1.9 |

### Calibration: model % vs how often the pick won

| bin | bets | model % | actual % |
|---|---|---|---|
| 20.0 | 1 | 21.9 | 100.0 |
| 30.0 | 217 | 38.5 | 41.0 |
| 40.0 | 9064 | 47.4 | 48.2 |
| 50.0 | 18281 | 53.5 | 54.0 |
| 60.0 | 1757 | 62.4 | 60.4 |
| 70.0 | 10 | 71.5 | 70.0 |
| 80.0 | 1 | 81.5 | 100.0 |

## Variant: absences

29331 lines, 151 dates.

### Strategies on the same lines

| strategy | bets | hit % | ci low % | ci high % | ROI % | avg odds |
|---|---|---|---|---|---|---|
| Always Under | 29331 | 52.2 | 51.6 | 52.7 | -2.7 | 1.9 |
| Always Over | 29331 | 47.8 | 47.3 | 48.4 | -8.9 | 1.9 |
| Bookmaker's favourite side | 29331 | 53.8 | 53.2 | 54.4 | -4.8 | 1.8 |
| Toward the season average | 29095 | 52.7 | 52.2 | 53.3 | -3.3 | 1.8 |
| Toward the last-5 average | 29331 | 50.6 | 50.0 | 51.1 | -6.3 | 1.9 |
| Toward proj avg | 29327 | 52.4 | 51.8 | 53.0 | -3.5 | 1.9 |
| Model pick (every line) | 29331 | 52.5 | 51.9 | 53.0 | -3.3 | 1.9 |
| Model pick, edge > 0 (🟢 or 🟡) | 244 | 52.9 | 46.6 | 59.0 | -2.1 | 1.9 |
| Model pick, 🟢 only | 0 | – | – | – | – | – |

### Model pick – by signal

| signal | bets | expected % | hit % | ci low % | ci high % | ROI % | avg odds |
|---|---|---|---|---|---|---|---|
| none | 29331 | 52.0 | 52.5 | 51.9 | 53.0 | -3.3 | 1.9 |

### Model pick – by edge (pp)

| edge bucket | bets | expected % | hit % | ci low % | ci high % | ROI % | avg odds |
|---|---|---|---|---|---|---|---|
| ≤ 0 | 29087 | 52.0 | 52.5 | 51.9 | 53.0 | -3.4 | 1.9 |
| 0–5 | 244 | 54.5 | 52.9 | 46.6 | 59.0 | -2.1 | 1.9 |

### Model pick – by bet type

| bet_type | bets | expected % | hit % | ci low % | ci high % | ROI % | avg odds |
|---|---|---|---|---|---|---|---|
| 3PM | 4860 | 54.3 | 54.0 | 52.6 | 55.4 | -4.8 | 1.8 |
| ARP | 6243 | 50.9 | 50.6 | 49.3 | 51.8 | -4.9 | 1.9 |
| AST | 4766 | 52.4 | 53.6 | 52.2 | 55.0 | -1.8 | 1.8 |
| PTS | 6817 | 50.9 | 51.2 | 50.0 | 52.3 | -3.9 | 1.9 |
| REB | 6645 | 52.1 | 53.7 | 52.5 | 54.9 | -1.3 | 1.9 |

### Model pick – by side

| best side | bets | expected % | hit % | ci low % | ci high % | ROI % | avg odds |
|---|---|---|---|---|---|---|---|
| Over | 10912 | 51.5 | 50.4 | 49.5 | 51.4 | -6.5 | 1.9 |
| Under | 18419 | 52.3 | 53.7 | 53.0 | 54.4 | -1.5 | 1.8 |

### Model pick – by month

| month | bets | expected % | hit % | ci low % | ci high % | ROI % | avg odds |
|---|---|---|---|---|---|---|---|
| 2022-11 | 3224 | 52.2 | 51.3 | 49.6 | 53.0 | -6.1 | 1.8 |
| 2022-12 | 5808 | 52.0 | 51.9 | 50.6 | 53.2 | -4.4 | 1.9 |
| 2023-01 | 6536 | 52.0 | 53.4 | 52.1 | 54.6 | -1.4 | 1.9 |
| 2023-02 | 4794 | 52.0 | 52.9 | 51.5 | 54.3 | -2.1 | 1.9 |
| 2023-03 | 5605 | 51.9 | 52.6 | 51.3 | 53.9 | -3.2 | 1.9 |
| 2023-04 | 2840 | 52.0 | 51.6 | 49.8 | 53.5 | -5.4 | 1.8 |
| 2023-05 | 524 | 51.8 | 54.0 | 49.7 | 58.2 | 0.2 | 1.9 |

### Calibration: model % vs how often the pick won

| bin | bets | model % | actual % |
|---|---|---|---|
| 20.0 | 1 | 21.9 | 100.0 |
| 30.0 | 233 | 38.4 | 39.9 |
| 40.0 | 9145 | 47.4 | 48.3 |
| 50.0 | 18202 | 53.5 | 54.0 |
| 60.0 | 1739 | 62.4 | 60.4 |
| 70.0 | 10 | 71.6 | 70.0 |
| 80.0 | 1 | 81.5 | 100.0 |
