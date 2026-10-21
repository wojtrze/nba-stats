# 2022/23 backtest of the props model

Unibet's 2022/23 player lines, each priced by `models.price_props` from the games before its date only. Main lines (the most balanced price per player, stat and game) of players with 5+ games. Pushes are left out; ROI is per unit at the line's odds; ci = 95% Wilson interval.

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
| Model pick (every line) | 29331 | 51.0 | 50.4 | 51.5 | -3.6 | 1.9 |
| Model pick, edge > 0 (🟢 or 🟡) | 20078 | 51.0 | 50.3 | 51.7 | -3.5 | 1.9 |
| Model pick, 🟢 only | 2181 | 52.1 | 50.0 | 54.2 | -1.9 | 1.9 |

### Model pick – by signal

| signal | bets | hit % | ci low % | ci high % | ROI % | avg odds |
|---|---|---|---|---|---|---|
| none | 9253 | 50.9 | 49.9 | 51.9 | -3.9 | 1.9 |
| 🟡 | 17897 | 50.9 | 50.1 | 51.6 | -3.7 | 1.9 |
| 🟢 | 2181 | 52.1 | 50.0 | 54.2 | -1.9 | 1.9 |

### Model pick – by edge (pp)

| edge bucket | bets | hit % | ci low % | ci high % | ROI % | avg odds |
|---|---|---|---|---|---|---|
| ≤ 0 | 9253 | 50.9 | 49.9 | 51.9 | -3.9 | 1.9 |
| 0–5 | 11345 | 50.6 | 49.7 | 51.5 | -4.3 | 1.9 |
| 5–10 | 5301 | 51.8 | 50.4 | 53.1 | -1.9 | 1.9 |
| 10+ | 3432 | 51.2 | 49.5 | 52.8 | -3.2 | 1.9 |

### Model pick – by bet type

| bet_type | bets | hit % | ci low % | ci high % | ROI % | avg odds |
|---|---|---|---|---|---|---|
| 3PM | 4860 | 50.6 | 49.2 | 52.0 | -4.0 | 1.9 |
| ARP | 6243 | 50.1 | 48.8 | 51.3 | -5.6 | 1.9 |
| AST | 4766 | 51.8 | 50.4 | 53.2 | -1.5 | 1.9 |
| PTS | 6817 | 50.5 | 49.3 | 51.7 | -4.7 | 1.9 |
| REB | 6645 | 52.0 | 50.8 | 53.2 | -1.9 | 1.9 |

### Model pick – by side

| best side | bets | hit % | ci low % | ci high % | ROI % | avg odds |
|---|---|---|---|---|---|---|
| Over | 13219 | 48.7 | 47.8 | 49.5 | -6.7 | 1.9 |
| Under | 16112 | 52.8 | 52.1 | 53.6 | -1.0 | 1.9 |

### Model pick – by month

| month | bets | hit % | ci low % | ci high % | ROI % | avg odds |
|---|---|---|---|---|---|---|
| 2022-11 | 3224 | 48.9 | 47.2 | 50.7 | -7.5 | 1.9 |
| 2022-12 | 5808 | 50.7 | 49.4 | 51.9 | -4.0 | 1.9 |
| 2023-01 | 6536 | 52.0 | 50.7 | 53.2 | -1.4 | 1.9 |
| 2023-02 | 4794 | 51.9 | 50.5 | 53.4 | -1.5 | 1.9 |
| 2023-03 | 5605 | 50.8 | 49.4 | 52.1 | -4.5 | 1.9 |
| 2023-04 | 2840 | 49.9 | 48.0 | 51.7 | -6.3 | 1.9 |
| 2023-05 | 524 | 54.4 | 50.1 | 58.6 | 2.6 | 1.9 |

### Calibration: model % vs how often the pick won

| bin | bets | model % | actual % |
|---|---|---|---|
| 20.0 | 2 | 27.3 | 0.0 |
| 30.0 | 192 | 38.5 | 41.1 |
| 40.0 | 4848 | 46.9 | 44.7 |
| 50.0 | 16411 | 54.8 | 51.2 |
| 60.0 | 6422 | 63.8 | 54.5 |
| 70.0 | 1280 | 73.6 | 54.8 |
| 80.0 | 159 | 83.2 | 59.7 |
| 90.0 | 17 | 91.5 | 35.3 |

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
| Model pick (every line) | 29331 | 51.0 | 50.4 | 51.6 | -3.6 | 1.9 |
| Model pick, edge > 0 (🟢 or 🟡) | 20443 | 51.0 | 50.4 | 51.7 | -3.4 | 1.9 |
| Model pick, 🟢 only | 2215 | 52.5 | 50.4 | 54.6 | -0.8 | 1.9 |

### Model pick – by signal

| signal | bets | hit % | ci low % | ci high % | ROI % | avg odds |
|---|---|---|---|---|---|---|
| none | 8888 | 50.9 | 49.8 | 51.9 | -4.0 | 1.9 |
| 🟡 | 18228 | 50.9 | 50.1 | 51.6 | -3.7 | 1.9 |
| 🟢 | 2215 | 52.5 | 50.4 | 54.6 | -0.8 | 1.9 |

### Model pick – by edge (pp)

| edge bucket | bets | hit % | ci low % | ci high % | ROI % | avg odds |
|---|---|---|---|---|---|---|
| ≤ 0 | 8888 | 50.9 | 49.8 | 51.9 | -4.0 | 1.9 |
| 0–5 | 11259 | 50.7 | 49.7 | 51.6 | -4.3 | 1.9 |
| 5–10 | 5588 | 51.4 | 50.1 | 52.7 | -2.6 | 1.9 |
| 10+ | 3596 | 51.7 | 50.1 | 53.3 | -1.9 | 1.9 |

### Model pick – by bet type

| bet_type | bets | hit % | ci low % | ci high % | ROI % | avg odds |
|---|---|---|---|---|---|---|
| 3PM | 4860 | 50.2 | 48.8 | 51.6 | -4.7 | 1.9 |
| ARP | 6243 | 49.9 | 48.7 | 51.2 | -5.8 | 1.9 |
| AST | 4766 | 51.9 | 50.5 | 53.3 | -1.2 | 1.9 |
| PTS | 6817 | 51.0 | 49.9 | 52.2 | -3.7 | 1.9 |
| REB | 6645 | 51.8 | 50.6 | 53.0 | -2.2 | 1.9 |

### Model pick – by side

| best side | bets | hit % | ci low % | ci high % | ROI % | avg odds |
|---|---|---|---|---|---|---|
| Over | 13752 | 48.8 | 47.9 | 49.6 | -6.7 | 1.9 |
| Under | 15579 | 53.0 | 52.2 | 53.7 | -0.9 | 1.9 |

### Model pick – by month

| month | bets | hit % | ci low % | ci high % | ROI % | avg odds |
|---|---|---|---|---|---|---|
| 2022-11 | 3224 | 48.9 | 47.2 | 50.6 | -7.6 | 1.9 |
| 2022-12 | 5808 | 50.5 | 49.2 | 51.8 | -4.2 | 1.9 |
| 2023-01 | 6536 | 51.5 | 50.3 | 52.7 | -2.3 | 1.9 |
| 2023-02 | 4794 | 52.3 | 50.9 | 53.7 | -0.9 | 1.9 |
| 2023-03 | 5605 | 51.0 | 49.7 | 52.3 | -3.9 | 1.9 |
| 2023-04 | 2840 | 50.0 | 48.2 | 51.8 | -6.1 | 1.9 |
| 2023-05 | 524 | 55.3 | 51.1 | 59.5 | 4.4 | 1.9 |

### Calibration: model % vs how often the pick won

| bin | bets | model % | actual % |
|---|---|---|---|
| 20.0 | 2 | 27.3 | 0.0 |
| 30.0 | 179 | 38.5 | 44.7 |
| 40.0 | 4680 | 47.0 | 44.7 |
| 50.0 | 16280 | 54.9 | 51.1 |
| 60.0 | 6810 | 63.8 | 54.5 |
| 70.0 | 1213 | 73.5 | 55.9 |
| 80.0 | 148 | 82.8 | 52.7 |
| 90.0 | 19 | 91.4 | 36.8 |
