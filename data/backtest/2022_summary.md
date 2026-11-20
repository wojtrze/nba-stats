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
| Toward proj avg | 29331 | 51.7 | 51.1 | 52.2 | -5.0 | 1.9 |
| Model pick (every line) | 29331 | 52.0 | 51.5 | 52.6 | -3.8 | 1.9 |
| Model pick, edge > 0 (🟢 or 🟡) | 1052 | 52.7 | 49.6 | 55.7 | -2.8 | 1.9 |
| Model pick, 🟢 only | 0 | – | – | – | – | – |

### Model pick – by signal

| signal | bets | expected % | hit % | ci low % | ci high % | ROI % | ROI % std | break-even % | break-even % std | avg odds |
|---|---|---|---|---|---|---|---|---|---|---|
| none | 29331 | 52.1 | 52.0 | 51.5 | 52.6 | -3.8 | -15.4 | 54.1 | 61.5 | 1.9 |

### Model pick – by edge (pp)

| edge bucket | bets | expected % | hit % | ci low % | ci high % | ROI % | ROI % std | break-even % | break-even % std | avg odds |
|---|---|---|---|---|---|---|---|---|---|---|
| ≤ 0 | 28279 | 52.0 | 52.0 | 51.4 | 52.6 | -3.9 | -15.4 | 54.1 | 61.5 | 1.9 |
| 0–5 | 1052 | 55.0 | 52.7 | 49.6 | 55.7 | -2.8 | -14.5 | 54.2 | 61.6 | 1.9 |

### Model pick – by bet type

| bet_type | bets | expected % | hit % | ci low % | ci high % | ROI % | ROI % std | break-even % | break-even % std | avg odds |
|---|---|---|---|---|---|---|---|---|---|---|
| 3PM | 4860 | 54.1 | 53.6 | 52.2 | 55.0 | -4.7 | -16.2 | 56.2 | 63.9 | 1.8 |
| ARP | 6243 | 51.2 | 50.5 | 49.2 | 51.7 | -5.0 | -16.4 | 53.2 | 60.4 | 1.9 |
| AST | 4766 | 52.4 | 52.4 | 51.0 | 53.8 | -3.6 | -15.2 | 54.5 | 61.9 | 1.9 |
| PTS | 6817 | 51.2 | 51.3 | 50.1 | 52.5 | -3.5 | -15.1 | 53.2 | 60.4 | 1.9 |
| REB | 6645 | 52.2 | 52.8 | 51.6 | 54.0 | -2.6 | -14.3 | 54.2 | 61.6 | 1.9 |

### Model pick – by side

| best side | bets | expected % | hit % | ci low % | ci high % | ROI % | ROI % std | break-even % | break-even % std | avg odds |
|---|---|---|---|---|---|---|---|---|---|---|
| Over | 11217 | 51.5 | 49.8 | 48.9 | 50.8 | -7.2 | -18.3 | 53.7 | 61.0 | 1.9 |
| Under | 18114 | 52.5 | 53.4 | 52.7 | 54.1 | -1.8 | -13.6 | 54.4 | 61.8 | 1.9 |

### Model pick – by month

| month | bets | expected % | hit % | ci low % | ci high % | ROI % | ROI % std | break-even % | break-even % std | avg odds |
|---|---|---|---|---|---|---|---|---|---|---|
| 2022-11 | 3224 | 52.1 | 50.8 | 49.0 | 52.5 | -6.6 | -17.8 | 54.2 | 61.6 | 1.9 |
| 2022-12 | 5808 | 52.1 | 51.8 | 50.5 | 53.0 | -4.3 | -15.8 | 54.1 | 61.4 | 1.9 |
| 2023-01 | 6536 | 52.1 | 52.5 | 51.3 | 53.7 | -2.7 | -14.4 | 54.0 | 61.3 | 1.9 |
| 2023-02 | 4794 | 52.2 | 52.3 | 50.9 | 53.7 | -2.9 | -14.6 | 54.0 | 61.3 | 1.9 |
| 2023-03 | 5605 | 52.1 | 52.0 | 50.7 | 53.3 | -3.9 | -15.5 | 54.2 | 61.6 | 1.9 |
| 2023-04 | 2840 | 52.2 | 52.1 | 50.3 | 54.0 | -4.2 | -15.7 | 54.5 | 61.9 | 1.9 |
| 2023-05 | 524 | 52.2 | 53.1 | 48.8 | 57.3 | -1.7 | -13.5 | 54.5 | 61.9 | 1.9 |

### Calibration: model % vs how often the pick won

| bin | bets | model % | actual % |
|---|---|---|---|
| 20.0 | 1 | 22.7 | 100.0 |
| 30.0 | 238 | 38.4 | 40.8 |
| 40.0 | 9037 | 47.3 | 47.4 |
| 50.0 | 18147 | 53.6 | 53.6 |
| 60.0 | 1894 | 62.5 | 60.5 |
| 70.0 | 13 | 71.6 | 61.5 |
| 80.0 | 1 | 81.6 | 100.0 |

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
| Toward proj avg | 29331 | 51.5 | 51.0 | 52.1 | -5.1 | 1.9 |
| Model pick (every line) | 29331 | 52.0 | 51.5 | 52.6 | -3.8 | 1.9 |
| Model pick, edge > 0 (🟢 or 🟡) | 985 | 53.0 | 49.9 | 56.1 | -2.5 | 1.9 |
| Model pick, 🟢 only | 0 | – | – | – | – | – |

### Model pick – by signal

| signal | bets | expected % | hit % | ci low % | ci high % | ROI % | ROI % std | break-even % | break-even % std | avg odds |
|---|---|---|---|---|---|---|---|---|---|---|
| none | 29331 | 52.1 | 52.0 | 51.5 | 52.6 | -3.8 | -15.4 | 54.1 | 61.5 | 1.9 |

### Model pick – by edge (pp)

| edge bucket | bets | expected % | hit % | ci low % | ci high % | ROI % | ROI % std | break-even % | break-even % std | avg odds |
|---|---|---|---|---|---|---|---|---|---|---|
| ≤ 0 | 28346 | 52.0 | 52.0 | 51.4 | 52.6 | -3.9 | -15.4 | 54.1 | 61.5 | 1.9 |
| 0–5 | 985 | 55.1 | 53.0 | 49.9 | 56.1 | -2.5 | -14.2 | 54.3 | 61.7 | 1.9 |

### Model pick – by bet type

| bet_type | bets | expected % | hit % | ci low % | ci high % | ROI % | ROI % std | break-even % | break-even % std | avg odds |
|---|---|---|---|---|---|---|---|---|---|---|
| 3PM | 4860 | 54.2 | 53.4 | 52.0 | 54.8 | -5.1 | -16.5 | 56.3 | 63.9 | 1.8 |
| ARP | 6243 | 51.2 | 50.5 | 49.3 | 51.8 | -4.9 | -16.3 | 53.1 | 60.4 | 1.9 |
| AST | 4766 | 52.4 | 52.3 | 50.9 | 53.8 | -3.6 | -15.2 | 54.4 | 61.8 | 1.9 |
| PTS | 6817 | 51.2 | 51.5 | 50.3 | 52.7 | -3.2 | -14.8 | 53.1 | 60.4 | 1.9 |
| REB | 6645 | 52.2 | 52.8 | 51.6 | 54.0 | -2.6 | -14.3 | 54.2 | 61.6 | 1.9 |

### Model pick – by side

| best side | bets | expected % | hit % | ci low % | ci high % | ROI % | ROI % std | break-even % | break-even % std | avg odds |
|---|---|---|---|---|---|---|---|---|---|---|
| Over | 11489 | 51.5 | 49.9 | 48.9 | 50.8 | -7.1 | -18.2 | 53.7 | 61.0 | 1.9 |
| Under | 17842 | 52.5 | 53.4 | 52.7 | 54.2 | -1.7 | -13.5 | 54.4 | 61.8 | 1.9 |

### Model pick – by month

| month | bets | expected % | hit % | ci low % | ci high % | ROI % | ROI % std | break-even % | break-even % std | avg odds |
|---|---|---|---|---|---|---|---|---|---|---|
| 2022-11 | 3224 | 52.2 | 50.6 | 48.9 | 52.3 | -7.0 | -18.1 | 54.2 | 61.6 | 1.9 |
| 2022-12 | 5808 | 52.1 | 51.5 | 50.2 | 52.8 | -4.7 | -16.2 | 54.0 | 61.4 | 1.9 |
| 2023-01 | 6536 | 52.1 | 52.9 | 51.7 | 54.1 | -1.9 | -13.7 | 54.0 | 61.3 | 1.9 |
| 2023-02 | 4794 | 52.1 | 52.5 | 51.1 | 53.9 | -2.5 | -14.2 | 54.0 | 61.3 | 1.9 |
| 2023-03 | 5605 | 52.0 | 51.7 | 50.4 | 53.0 | -4.5 | -16.0 | 54.2 | 61.6 | 1.9 |
| 2023-04 | 2840 | 52.2 | 52.3 | 50.4 | 54.1 | -3.9 | -15.4 | 54.5 | 61.9 | 1.9 |
| 2023-05 | 524 | 52.1 | 52.9 | 48.6 | 57.1 | -1.9 | -13.7 | 54.4 | 61.8 | 1.9 |

### Calibration: model % vs how often the pick won

| bin | bets | model % | actual % |
|---|---|---|---|
| 20.0 | 1 | 22.7 | 100.0 |
| 30.0 | 243 | 38.4 | 37.9 |
| 40.0 | 9025 | 47.3 | 47.6 |
| 50.0 | 18177 | 53.6 | 53.6 |
| 60.0 | 1872 | 62.5 | 60.4 |
| 70.0 | 12 | 71.8 | 66.7 |
| 80.0 | 1 | 81.6 | 100.0 |
