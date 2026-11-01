# Calibration of the props model

The model's chance for a side is mapped to sigmoid(a·logit(market) + b·(logit(model) − logit(market)) + c·[Over] + d): a = weight of the bookmaker's margin-free chance, b = weight of the model's opinion beyond it, c = Over/Under bias, d = offset. Identity: a = b = 1, c = d = 0. Lines: Unibet 2022/23 29331, Superbet 2026/27 15837.

How to read b: it's how much of the model's disagreement with the price held up on past lines (b = 0.1 keeps a tenth of it). It calibrates the model's point chance only; it says nothing about whether the model's 95% range (edge low) is right, and a well-calibrated chance close to the price is not a betting edge.

## Held-out check

Coefficients fitted on the earlier lines of every source: a = 1.224, b = 0.092, c = 0.000, d = 0.000

### Unibet 2022/23: fitted on Nov 09 2022 – Jan 31 2023 (15568 lines), scored on Feb 01 2023 – May 08 2023 (13763 lines)

How well the chances predict the results (lower is better):

| chances | log loss | Brier |
|---|---|---|
| Market (margin-free price) | 0.6895 | 0.2482 |
| Uncalibrated model | 0.7051 | 0.2550 |
| Calibrated model | 0.6893 | 0.2481 |

Betting the unseen lines (1 unit each, at the line's odds):

| strategy | bets | hit % | ci low % | ci high % | ROI % | avg odds |
|---|---|---|---|---|---|---|
| Always Under | 13763 | 53.4 | 52.6 | 54.2 | -0.6 | 1.9 |
| Always Over | 13763 | 46.6 | 45.8 | 47.4 | -11.4 | 1.9 |
| Calibrated pick, every line | 13763 | 53.3 | 52.4 | 54.1 | -4.1 | 1.8 |
| Calibrated pick, edge > 0 | 190 | 57.9 | 50.8 | 64.7 | 0.5 | 1.8 |

Signal efficiency: every line whose calibrated edge reaches the threshold (cumulative):

| edge ≥ pp | expected % | bets | hit % | ci low % | ci high % | ROI % | avg odds | break-even % | nights |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 57.9 | 190 | 57.9 | 50.8 | 64.7 | 0.5 | 1.8 | 57.3 | 45 |
| 1 | 57.7 | 36 | 58.3 | 42.2 | 72.9 | 2.7 | 1.8 | 56.2 | 14 |
| 2 | 62.5 | 3 | 66.7 | 20.8 | 93.9 | 13.0 | 1.7 | 60.2 | 2 |
| 3 | – | 0 | – | – | – | – | – | – | 0 |
| 4 | – | 0 | – | – | – | – | – | – | 0 |
| 5 | – | 0 | – | – | – | – | – | – | 0 |

Calibration on the unseen lines (both sides of every line):

| chance | rows | predicted % | won % |
|---|---|---|---|
| 15–20% | 2 | 18.1 | 50.0 |
| 20–25% | 2 | 22.6 | 50.0 |
| 25–30% | 17 | 28.7 | 23.5 |
| 30–35% | 161 | 33.6 | 32.9 |
| 35–40% | 1075 | 38.1 | 41.7 |
| 40–45% | 3077 | 42.8 | 44.4 |
| 45–50% | 9429 | 47.9 | 47.7 |
| 50–55% | 9429 | 52.1 | 52.3 |
| 55–60% | 3077 | 57.2 | 55.6 |
| 60–65% | 1075 | 61.9 | 58.3 |
| 65–70% | 161 | 66.4 | 67.1 |
| 70–75% | 17 | 71.3 | 76.5 |
| 75–80% | 2 | 77.4 | 50.0 |
| 80–85% | 2 | 81.9 | 50.0 |

### Superbet 2026/27: fitted on Oct 20 2026 – Oct 27 2026 (10480 lines), scored on Oct 28 2026 – Oct 31 2026 (5357 lines)

How well the chances predict the results (lower is better):

| chances | log loss | Brier |
|---|---|---|
| Market (margin-free price) | 0.6837 | 0.2453 |
| Uncalibrated model | 0.6870 | 0.2468 |
| Calibrated model | 0.6824 | 0.2447 |

Betting the unseen lines (1 unit each, at the line's odds):

| strategy | bets | hit % | ci low % | ci high % | ROI % | avg odds |
|---|---|---|---|---|---|---|
| Always Under | 5357 | 54.2 | 52.8 | 55.5 | -1.1 | 1.9 |
| Always Over | 5357 | 45.8 | 44.5 | 47.2 | -15.0 | 1.9 |
| Calibrated pick, every line | 5357 | 55.6 | 54.3 | 57.0 | -2.9 | 1.8 |
| Calibrated pick, edge > 0 | 0 | – | – | – | – | – |

Signal efficiency: every line whose calibrated edge reaches the threshold (cumulative):

| edge ≥ pp | expected % | bets | hit % | ci low % | ci high % | ROI % | avg odds | break-even % | nights |
|---|---|---|---|---|---|---|---|---|---|
| 0 | – | 0 | – | – | – | – | – | – | 0 |
| 1 | – | 0 | – | – | – | – | – | – | 0 |
| 2 | – | 0 | – | – | – | – | – | – | 0 |
| 3 | – | 0 | – | – | – | – | – | – | 0 |
| 4 | – | 0 | – | – | – | – | – | – | 0 |
| 5 | – | 0 | – | – | – | – | – | – | 0 |

Calibration on the unseen lines (both sides of every line):

| chance | rows | predicted % | won % |
|---|---|---|---|
| 15–20% | 7 | 18.0 | 14.3 |
| 20–25% | 9 | 22.8 | 11.1 |
| 25–30% | 12 | 28.4 | 16.7 |
| 30–35% | 143 | 32.9 | 30.8 |
| 35–40% | 534 | 37.9 | 39.5 |
| 40–45% | 1424 | 42.9 | 40.3 |
| 45–50% | 3228 | 47.8 | 49.0 |
| 50–55% | 3228 | 52.2 | 51.0 |
| 55–60% | 1424 | 57.1 | 59.7 |
| 60–65% | 534 | 62.1 | 60.5 |
| 65–70% | 143 | 67.1 | 69.2 |
| 70–75% | 12 | 71.6 | 83.3 |
| 75–80% | 9 | 77.2 | 88.9 |
| 80–85% | 7 | 82.0 | 85.7 |

### 🟢 threshold

No 🟢: none of the thresholds +1, +2, +3, +4, +5 pp had 50+ picks over 10+ unseen Superbet nights that won more often than break-even at the low end of the 95% range. Lines with a positive edge get 🟡 (an estimated edge, not a validated one).

Selection policy: one bet per line (its last fetch before tip-off), the calibrated pick's side, 1 unit at that fetch's odds. The threshold is chosen on the same held-out nights it's judged on, among 5 candidates, and re-chosen as nights settle: exploratory, not a proven betting advantage.

## Used by the dashboards (fitted on every line)

a = 1.158, b = 0.144, c = 0.000, d = 0.000 (90336 line sides); no 🟢; Superbet lines through 2026-10-31

## Game markets (not calibrated)

1258 settled main-line outcomes on 11 nights (Oct 21 2026 – Oct 31 2026); a calibration is fitted from 300+ outcomes on 10+ nights. Until then game outcomes get no 🟢 / 🟡 and no stake: the model's edges are estimates for research.

How well the chances predict the results (lower is better; both sides of each market count, so the rows aren't independent):

| chances | log loss | Brier |
|---|---|---|
| Market (margin-free price) | 0.6732 | 0.2409 |
| Game model | 0.7160 | 0.2576 |

Betting every outcome whose model edge reached the threshold (1 unit at the saved odds):

| bets | n | nights | expected % | hit % | ci low % | ci high % | break-even % | ROI % |
|---|---|---|---|---|---|---|---|---|
| edge > 0 | 521 | 11 | 66.4 | 51.8 | 47.5 | 56.1 | 52.5 | -2.4 |
| edge ≥ +5 pp (the old 🟢) | 400 | 11 | 69.4 | 50.2 | 45.4 | 55.1 | 52.1 | -4.9 |

By market:

| market | outcomes | model log loss | market log loss |
|---|---|---|---|
| AWAY_TOTAL | 300 | 0.7453 | 0.6946 |
| HOME_TOTAL | 312 | 0.7197 | 0.6922 |
| ML | 170 | 0.6381 | 0.5595 |
| SPREAD | 134 | 0.7850 | 0.6813 |
| TOTAL | 342 | 0.6987 | 0.6903 |
