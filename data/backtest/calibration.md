# Calibration of the props model

The model's chance for a side is mapped to sigmoid(a·logit(market) + b·(logit(model) − logit(market)) + c·[Over] + d): a = weight of the bookmaker's margin-free chance, b = weight of the model's opinion beyond it, c = Over/Under bias, d = offset. Identity: a = b = 1, c = d = 0. Lines: Unibet 2022/23 29331, Superbet 2026/27 8222.

## Held-out check

Coefficients fitted on the earlier lines of every source: a = 1.225, b = 0.040, c = -0.067, d = 0.034

### Unibet 2022/23: fitted on Nov 09 2022 – Jan 31 2023 (15568 lines), scored on Feb 01 2023 – May 08 2023 (13763 lines)

How well the chances predict the results (lower is better):

| chances | log loss | Brier |
|---|---|---|
| Market (margin-free price) | 0.6895 | 0.2482 |
| Uncalibrated model | 0.7055 | 0.2552 |
| Calibrated model | 0.6888 | 0.2478 |

Betting the unseen lines (1 unit each, at the line's odds):

| strategy | bets | hit % | ci low % | ci high % | ROI % | avg odds |
|---|---|---|---|---|---|---|
| Always Under | 13763 | 53.4 | 52.6 | 54.2 | -0.6 | 1.9 |
| Always Over | 13763 | 46.6 | 45.8 | 47.4 | -11.4 | 1.9 |
| Calibrated pick, every line | 13763 | 53.9 | 53.1 | 54.7 | -2.3 | 1.8 |
| Calibrated pick, edge > 0 | 58 | 70.7 | 58.0 | 80.8 | 9.3 | 1.6 |

Signal efficiency: every line whose calibrated edge reaches the threshold (cumulative):

| edge ≥ pp | expected % | bets | hit % | ci low % | ci high % | ROI % | avg odds |
|---|---|---|---|---|---|---|---|
| 0 | 64.6 | 58 | 70.7 | 58.0 | 80.8 | 9.3 | 1.6 |
| 1 | – | 0 | – | – | – | – | – |
| 2 | – | 0 | – | – | – | – | – |
| 3 | – | 0 | – | – | – | – | – |
| 4 | – | 0 | – | – | – | – | – |
| 5 | – | 0 | – | – | – | – | – |

Calibration on the unseen lines (both sides of every line):

| chance | rows | predicted % | won % |
|---|---|---|---|
| 15–20% | 3 | 18.1 | 33.3 |
| 25–30% | 20 | 28.3 | 30.0 |
| 30–35% | 193 | 33.6 | 34.2 |
| 35–40% | 1105 | 38.1 | 42.4 |
| 40–45% | 2984 | 42.8 | 43.2 |
| 45–50% | 9458 | 47.9 | 48.1 |
| 50–55% | 9458 | 52.1 | 51.9 |
| 55–60% | 2984 | 57.2 | 56.8 |
| 60–65% | 1105 | 61.9 | 57.6 |
| 65–70% | 193 | 66.4 | 65.8 |
| 70–75% | 20 | 71.7 | 70.0 |
| 80–85% | 3 | 81.9 | 66.7 |

### Superbet 2026/27: fitted on Oct 20 2026 – Oct 23 2026 (5759 lines), scored on Oct 24 2026 – Oct 25 2026 (2463 lines)

How well the chances predict the results (lower is better):

| chances | log loss | Brier |
|---|---|---|
| Market (margin-free price) | 0.6877 | 0.2473 |
| Uncalibrated model | 0.6958 | 0.2509 |
| Calibrated model | 0.6887 | 0.2478 |

Betting the unseen lines (1 unit each, at the line's odds):

| strategy | bets | hit % | ci low % | ci high % | ROI % | avg odds |
|---|---|---|---|---|---|---|
| Always Under | 2463 | 48.2 | 46.2 | 50.1 | -12.1 | 1.8 |
| Always Over | 2463 | 51.8 | 49.9 | 53.8 | -3.3 | 1.9 |
| Calibrated pick, every line | 2463 | 51.4 | 49.5 | 53.4 | -9.5 | 1.8 |
| Calibrated pick, edge > 0 | 0 | – | – | – | – | – |

Signal efficiency: every line whose calibrated edge reaches the threshold (cumulative):

| edge ≥ pp | expected % | bets | hit % | ci low % | ci high % | ROI % | avg odds |
|---|---|---|---|---|---|---|---|
| 0 | – | 0 | – | – | – | – | – |
| 1 | – | 0 | – | – | – | – | – |
| 2 | – | 0 | – | – | – | – | – |
| 3 | – | 0 | – | – | – | – | – |
| 4 | – | 0 | – | – | – | – | – |
| 5 | – | 0 | – | – | – | – | – |

Calibration on the unseen lines (both sides of every line):

| chance | rows | predicted % | won % |
|---|---|---|---|
| 15–20% | 1 | 15.7 | 0.0 |
| 25–30% | 5 | 29.0 | 20.0 |
| 30–35% | 74 | 33.0 | 33.8 |
| 35–40% | 255 | 37.8 | 41.2 |
| 40–45% | 663 | 42.8 | 43.7 |
| 45–50% | 1465 | 47.8 | 51.0 |
| 50–55% | 1465 | 52.2 | 49.0 |
| 55–60% | 663 | 57.2 | 56.3 |
| 60–65% | 255 | 62.2 | 58.8 |
| 65–70% | 74 | 67.0 | 66.2 |
| 70–75% | 5 | 71.0 | 80.0 |
| 80–85% | 1 | 84.3 | 100.0 |

### 🟢 threshold

No 🟢: none of the thresholds +1, +2, +3, +4, +5 pp had 50+ picks that paid on the unseen Superbet lines. Lines with a positive edge get 🟡.

## Used by the dashboards (fitted on every line)

a = 1.093, b = 0.079, c = -0.103, d = 0.052 (75106 line sides); no 🟢; Superbet lines through 2026-10-25
