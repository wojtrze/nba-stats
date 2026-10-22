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
| Model pick (every line) | 29331 | 52.1 | 51.5 | 52.7 | -2.6 | 1.9 |
| Model pick, edge > 0 (🟢 or 🟡) | 1133 | 53.1 | 50.2 | 56.0 | 1.6 | 1.9 |
| Model pick, 🟢 only | 147 | 48.3 | 40.4 | 56.3 | -7.8 | 1.9 |

### Model pick – by signal

| signal | bets | hit % | ci low % | ci high % | ROI % | avg odds |
|---|---|---|---|---|---|---|
| none | 28198 | 52.0 | 51.5 | 52.6 | -2.8 | 1.9 |
| 🟡 | 986 | 53.9 | 50.7 | 56.9 | 2.9 | 1.9 |
| 🟢 | 147 | 48.3 | 40.4 | 56.3 | -7.8 | 1.9 |

### Model pick – by edge (pp)

| edge bucket | bets | hit % | ci low % | ci high % | ROI % | avg odds |
|---|---|---|---|---|---|---|
| ≤ 0 | 28198 | 52.0 | 51.5 | 52.6 | -2.8 | 1.9 |
| 0–5 | 1133 | 53.1 | 50.2 | 56.0 | 1.6 | 1.9 |

### Model pick – by bet type

| bet_type | bets | hit % | ci low % | ci high % | ROI % | avg odds |
|---|---|---|---|---|---|---|
| 3PM | 4860 | 53.7 | 52.3 | 55.1 | -1.3 | 1.9 |
| ARP | 6243 | 52.0 | 50.7 | 53.2 | -2.1 | 1.9 |
| AST | 4766 | 51.0 | 49.6 | 52.4 | -4.9 | 1.9 |
| PTS | 6817 | 51.8 | 50.6 | 53.0 | -2.5 | 1.9 |
| REB | 6645 | 52.1 | 50.9 | 53.3 | -2.5 | 1.9 |

### Model pick – by side

| best side | bets | hit % | ci low % | ci high % | ROI % | avg odds |
|---|---|---|---|---|---|---|
| Over | 324 | 46.9 | 41.5 | 52.4 | -0.6 | 2.1 |
| Under | 29007 | 52.1 | 51.6 | 52.7 | -2.6 | 1.9 |

### Model pick – by month

| month | bets | hit % | ci low % | ci high % | ROI % | avg odds |
|---|---|---|---|---|---|---|
| 2022-11 | 3224 | 51.9 | 50.1 | 53.6 | -3.2 | 1.9 |
| 2022-12 | 5808 | 50.6 | 49.3 | 51.9 | -5.2 | 1.9 |
| 2023-01 | 6536 | 51.1 | 49.9 | 52.3 | -4.1 | 1.9 |
| 2023-02 | 4794 | 53.8 | 52.4 | 55.2 | 1.2 | 1.9 |
| 2023-03 | 5605 | 53.0 | 51.7 | 54.3 | -1.4 | 1.9 |
| 2023-04 | 2840 | 52.2 | 50.3 | 54.0 | -3.4 | 1.9 |
| 2023-05 | 524 | 55.7 | 51.4 | 59.9 | 5.8 | 1.9 |

### Calibration: model % vs how often the pick won

| bin | bets | model % | actual % |
|---|---|---|---|
| 20.0 | 4 | 24.2 | 50.0 |
| 30.0 | 227 | 38.4 | 42.3 |
| 40.0 | 8167 | 47.2 | 47.1 |
| 50.0 | 19446 | 53.5 | 53.6 |
| 60.0 | 1486 | 62.3 | 61.6 |
| 70.0 | 1 | 70.0 | 0.0 |

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
| Model pick (every line) | 29331 | 52.1 | 51.5 | 52.6 | -2.6 | 1.9 |
| Model pick, edge > 0 (🟢 or 🟡) | 1049 | 51.1 | 48.1 | 54.1 | -2.0 | 1.9 |
| Model pick, 🟢 only | 134 | 48.5 | 40.2 | 56.9 | -6.8 | 1.9 |

### Model pick – by signal

| signal | bets | hit % | ci low % | ci high % | ROI % | avg odds |
|---|---|---|---|---|---|---|
| none | 28282 | 52.1 | 51.5 | 52.7 | -2.6 | 1.9 |
| 🟡 | 915 | 51.5 | 48.2 | 54.7 | -1.3 | 1.9 |
| 🟢 | 134 | 48.5 | 40.2 | 56.9 | -6.8 | 1.9 |

### Model pick – by edge (pp)

| edge bucket | bets | hit % | ci low % | ci high % | ROI % | avg odds |
|---|---|---|---|---|---|---|
| ≤ 0 | 28282 | 52.1 | 51.5 | 52.7 | -2.6 | 1.9 |
| 0–5 | 1049 | 51.1 | 48.1 | 54.1 | -2.0 | 1.9 |

### Model pick – by bet type

| bet_type | bets | hit % | ci low % | ci high % | ROI % | avg odds |
|---|---|---|---|---|---|---|
| 3PM | 4860 | 53.7 | 52.3 | 55.1 | -1.3 | 1.9 |
| ARP | 6243 | 51.9 | 50.7 | 53.2 | -2.1 | 1.9 |
| AST | 4766 | 51.0 | 49.5 | 52.4 | -4.8 | 1.9 |
| PTS | 6817 | 51.8 | 50.6 | 52.9 | -2.6 | 1.9 |
| REB | 6645 | 52.1 | 50.9 | 53.3 | -2.3 | 1.9 |

### Model pick – by side

| best side | bets | hit % | ci low % | ci high % | ROI % | avg odds |
|---|---|---|---|---|---|---|
| Over | 447 | 47.2 | 42.6 | 51.8 | -0.4 | 2.1 |
| Under | 28884 | 52.1 | 51.6 | 52.7 | -2.6 | 1.9 |

### Model pick – by month

| month | bets | hit % | ci low % | ci high % | ROI % | avg odds |
|---|---|---|---|---|---|---|
| 2022-11 | 3224 | 51.9 | 50.1 | 53.6 | -3.2 | 1.9 |
| 2022-12 | 5808 | 50.6 | 49.4 | 51.9 | -5.1 | 1.9 |
| 2023-01 | 6536 | 51.2 | 50.0 | 52.4 | -3.8 | 1.9 |
| 2023-02 | 4794 | 53.7 | 52.3 | 55.1 | 1.0 | 1.9 |
| 2023-03 | 5605 | 52.8 | 51.5 | 54.1 | -1.6 | 1.9 |
| 2023-04 | 2840 | 52.2 | 50.3 | 54.0 | -3.3 | 1.9 |
| 2023-05 | 524 | 56.1 | 51.8 | 60.3 | 6.5 | 1.9 |

### Calibration: model % vs how often the pick won

| bin | bets | model % | actual % |
|---|---|---|---|
| 20.0 | 4 | 24.2 | 50.0 |
| 30.0 | 245 | 38.4 | 42.0 |
| 40.0 | 8354 | 47.2 | 47.0 |
| 50.0 | 19267 | 53.4 | 53.7 |
| 60.0 | 1460 | 62.3 | 61.9 |
| 70.0 | 1 | 70.0 | 0.0 |
