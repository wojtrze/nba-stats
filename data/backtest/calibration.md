# Calibration of the props model

The model's chance for a side is mapped to sigmoid(a·logit(market) + b·(logit(model) − logit(market)) + c·[Over] + d): a = weight of the bookmaker's margin-free chance, b = weight of the model's opinion beyond it, c = Over/Under bias, d = offset. Identity: a = b = 1, c = d = 0. Lines: Unibet 2022/23 29331, Superbet 2026/27 28180.

How to read b: it's how much of the model's disagreement with the price held up on past lines (b = 0.1 keeps a tenth of it). It calibrates the model's point chance only; it says nothing about whether the model's 95% range (edge low) is right, and a well-calibrated chance close to the price is not a betting edge.

## Held-out check

Coefficients fitted on the earlier lines of every source: a = 1.200, b = 0.153, c = 0.000, d = 0.000

### Unibet 2022/23: fitted on Nov 09 2022 – Jan 31 2023 (15568 lines), scored on Feb 01 2023 – May 08 2023 (13763 lines)

How well the chances predict the results (lower is better):

| chances | log loss | Brier |
|---|---|---|
| Market (margin-free price) | 0.6895 | 0.2482 |
| Uncalibrated model | 0.7051 | 0.2550 |
| Calibrated model | 0.6891 | 0.2480 |

Betting the unseen lines (1 unit each, at the line's odds):

| strategy | bets | hit % | ci low % | ci high % | ROI % | avg odds |
|---|---|---|---|---|---|---|
| Always Under | 13763 | 53.4 | 52.6 | 54.2 | -0.6 | 1.9 |
| Always Over | 13763 | 46.6 | 45.8 | 47.4 | -11.4 | 1.9 |
| Calibrated pick, every line | 13763 | 52.9 | 52.0 | 53.7 | -3.6 | 1.8 |
| Calibrated pick, edge > 0 | 1034 | 55.7 | 52.7 | 58.7 | 0.6 | 1.8 |

Signal efficiency: every line whose calibrated edge reaches the threshold (cumulative):

| edge ≥ pp | expected % | bets | hit % | ci low % | ci high % | ROI % | avg odds | break-even % | nights |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 56.5 | 1034 | 55.7 | 52.7 | 58.7 | 0.6 | 1.8 | 55.4 | 73 |
| 1 | 56.5 | 446 | 53.6 | 48.9 | 58.2 | -2.2 | 1.8 | 54.6 | 61 |
| 2 | 57.4 | 147 | 55.1 | 47.0 | 62.9 | 0.6 | 1.8 | 54.4 | 38 |
| 3 | 58.4 | 61 | 54.1 | 41.7 | 66.0 | -1.5 | 1.8 | 54.4 | 22 |
| 4 | 59.7 | 24 | 41.7 | 24.5 | 61.2 | -25.9 | 1.8 | 54.9 | 9 |
| 5 | 60.0 | 7 | 42.9 | 15.8 | 75.0 | -21.1 | 1.8 | 54.6 | 4 |

Calibration on the unseen lines (both sides of every line):

| chance | rows | predicted % | won % |
|---|---|---|---|
| 15–20% | 1 | 17.1 | 0.0 |
| 20–25% | 2 | 21.1 | 50.0 |
| 25–30% | 16 | 28.3 | 31.2 |
| 30–35% | 166 | 33.4 | 33.1 |
| 35–40% | 1094 | 38.1 | 41.7 |
| 40–45% | 3228 | 42.9 | 44.9 |
| 45–50% | 9256 | 47.9 | 48.3 |
| 50–55% | 9256 | 52.1 | 51.7 |
| 55–60% | 3228 | 57.1 | 55.1 |
| 60–65% | 1094 | 61.9 | 58.3 |
| 65–70% | 166 | 66.6 | 66.9 |
| 70–75% | 16 | 71.7 | 68.8 |
| 75–80% | 2 | 78.9 | 50.0 |
| 80–85% | 1 | 82.9 | 100.0 |

### Superbet 2026/27: fitted on Oct 20 2026 – Nov 02 2026 (19308 lines), scored on Nov 04 2026 – Nov 09 2026 (8872 lines)

How well the chances predict the results (lower is better):

| chances | log loss | Brier |
|---|---|---|
| Market (margin-free price) | 0.6848 | 0.2459 |
| Uncalibrated model | 0.6890 | 0.2479 |
| Calibrated model | 0.6838 | 0.2454 |

Betting the unseen lines (1 unit each, at the line's odds):

| strategy | bets | hit % | ci low % | ci high % | ROI % | avg odds |
|---|---|---|---|---|---|---|
| Always Under | 8872 | 53.0 | 52.0 | 54.1 | -3.1 | 1.9 |
| Always Over | 8872 | 47.0 | 45.9 | 48.0 | -12.7 | 1.9 |
| Calibrated pick, every line | 8872 | 53.9 | 52.8 | 54.9 | -4.8 | 1.8 |
| Calibrated pick, edge > 0 | 6 | 66.7 | 30.0 | 90.3 | 9.8 | 1.7 |

Signal efficiency: every line whose calibrated edge reaches the threshold (cumulative):

| edge ≥ pp | expected % | bets | hit % | ci low % | ci high % | ROI % | avg odds | break-even % | nights |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 59.5 | 6 | 66.7 | 30.0 | 90.3 | 9.8 | 1.7 | 59.2 | 5 |
| 1 | – | 0 | – | – | – | – | – | – | 0 |
| 2 | – | 0 | – | – | – | – | – | – | 0 |
| 3 | – | 0 | – | – | – | – | – | – | 0 |
| 4 | – | 0 | – | – | – | – | – | – | 0 |
| 5 | – | 0 | – | – | – | – | – | – | 0 |

Calibration on the unseen lines (both sides of every line):

| chance | rows | predicted % | won % |
|---|---|---|---|
| 10–15% | 1 | 14.3 | 0.0 |
| 15–20% | 7 | 17.6 | 14.3 |
| 20–25% | 13 | 22.0 | 15.4 |
| 25–30% | 35 | 28.0 | 28.6 |
| 30–35% | 285 | 33.0 | 33.0 |
| 35–40% | 927 | 37.8 | 38.4 |
| 40–45% | 2256 | 42.8 | 43.2 |
| 45–50% | 5348 | 47.8 | 48.4 |
| 50–55% | 5348 | 52.2 | 51.6 |
| 55–60% | 2256 | 57.2 | 56.8 |
| 60–65% | 927 | 62.2 | 61.6 |
| 65–70% | 285 | 67.0 | 67.0 |
| 70–75% | 35 | 72.0 | 71.4 |
| 75–80% | 13 | 78.0 | 84.6 |
| 80–85% | 7 | 82.4 | 85.7 |
| 85–90% | 1 | 85.7 | 100.0 |

### 🟢 threshold

No 🟢: none of the thresholds +1, +2, +3, +4, +5 pp had 50+ picks over 10+ unseen Superbet nights that won more often than break-even at the low end of the 95% range. Lines with a positive edge get 🟡 (an estimated edge, not a validated one).

Selection policy: one bet per line (its last fetch before tip-off), the calibrated pick's side, 1 unit at that fetch's odds. The threshold is chosen on the same held-out nights it's judged on, among 5 candidates, and re-chosen as nights settle: exploratory, not a proven betting advantage.

## Used by the dashboards (fitted on every line)

a = 1.139, b = 0.170, c = 0.000, d = 0.000 (115022 line sides); no 🟢; Superbet lines through 2026-11-09

## Game markets (not calibrated)

2268 settled main-line outcomes on 19 nights (Oct 21 2026 – Nov 09 2026); a calibration is fitted from 300+ outcomes on 10+ nights. Until then game outcomes get no 🟢 / 🟡 and no stake: the model's edges are estimates for research.

How well the chances predict the results (lower is better; both sides of each market count, so the rows aren't independent):

| chances | log loss | Brier |
|---|---|---|
| Market (margin-free price) | 0.6730 | 0.2408 |
| Game model | 0.7549 | 0.2727 |

Betting every outcome whose model edge reached the threshold (1 unit at the saved odds):

| bets | n | nights | expected % | hit % | ci low % | ci high % | break-even % | ROI % |
|---|---|---|---|---|---|---|---|---|
| edge > 0 | 960 | 19 | 65.7 | 49.8 | 46.6 | 52.9 | 52.5 | -6.4 |
| edge ≥ +5 pp (the old 🟢) | 710 | 18 | 69.3 | 47.3 | 43.7 | 51.0 | 52.2 | -10.9 |

By market:

| market | outcomes | model log loss | market log loss |
|---|---|---|---|
| AWAY_TOTAL | 532 | 0.7739 | 0.6971 |
| HOME_TOTAL | 558 | 0.7773 | 0.6884 |
| ML | 290 | 0.6854 | 0.5491 |
| SPREAD | 248 | 0.7830 | 0.6881 |
| TOTAL | 640 | 0.7401 | 0.6899 |
