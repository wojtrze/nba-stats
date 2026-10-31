# Calibration of the props model

The model's chance for a side is mapped to sigmoid(a·logit(market) + b·(logit(model) − logit(market)) + c·[Over] + d): a = weight of the bookmaker's margin-free chance, b = weight of the model's opinion beyond it, c = Over/Under bias, d = offset. Identity: a = b = 1, c = d = 0. Lines: Unibet 2022/23 29331, Superbet 2026/27 14737.

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

### Superbet 2026/27: fitted on Oct 20 2026 – Oct 27 2026 (10480 lines), scored on Oct 28 2026 – Oct 30 2026 (4257 lines)

How well the chances predict the results (lower is better):

| chances | log loss | Brier |
|---|---|---|
| Market (margin-free price) | 0.6828 | 0.2449 |
| Uncalibrated model | 0.6878 | 0.2472 |
| Calibrated model | 0.6815 | 0.2443 |

Betting the unseen lines (1 unit each, at the line's odds):

| strategy | bets | hit % | ci low % | ci high % | ROI % | avg odds |
|---|---|---|---|---|---|---|
| Always Under | 4257 | 53.2 | 51.7 | 54.7 | -2.8 | 1.9 |
| Always Over | 4257 | 46.8 | 45.3 | 48.3 | -13.5 | 1.9 |
| Calibrated pick, every line | 4257 | 55.6 | 54.1 | 57.1 | -3.2 | 1.8 |
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
| 15–20% | 4 | 17.8 | 0.0 |
| 20–25% | 9 | 22.8 | 11.1 |
| 25–30% | 10 | 28.2 | 20.0 |
| 30–35% | 123 | 32.9 | 31.7 |
| 35–40% | 423 | 37.9 | 39.5 |
| 40–45% | 1145 | 42.9 | 39.3 |
| 45–50% | 2543 | 47.8 | 48.9 |
| 50–55% | 2543 | 52.2 | 51.1 |
| 55–60% | 1145 | 57.1 | 60.7 |
| 60–65% | 423 | 62.1 | 60.5 |
| 65–70% | 123 | 67.1 | 68.3 |
| 70–75% | 10 | 71.8 | 80.0 |
| 75–80% | 9 | 77.2 | 88.9 |
| 80–85% | 4 | 82.2 | 100.0 |

### 🟢 threshold

No 🟢: none of the thresholds +1, +2, +3, +4, +5 pp had 50+ picks over 10+ unseen Superbet nights that won more often than break-even at the low end of the 95% range. Lines with a positive edge get 🟡 (an estimated edge, not a validated one).

Selection policy: one bet per line (its last fetch before tip-off), the calibrated pick's side, 1 unit at that fetch's odds. The threshold is chosen on the same held-out nights it's judged on, among 5 candidates, and re-chosen as nights settle: exploratory, not a proven betting advantage.

## Used by the dashboards (fitted on every line)

a = 1.163, b = 0.136, c = 0.000, d = 0.000 (88136 line sides); no 🟢; Superbet lines through 2026-10-30

## Game markets (not calibrated)

1160 settled main-line outcomes on 10 nights (Oct 21 2026 – Oct 30 2026); a calibration is fitted from 300+ outcomes on 10+ nights. Until then game outcomes get no 🟢 / 🟡 and no stake: the model's edges are estimates for research.

How well the chances predict the results (lower is better; both sides of each market count, so the rows aren't independent):

| chances | log loss | Brier |
|---|---|---|
| Market (margin-free price) | 0.6732 | 0.2409 |
| Game model | 0.7180 | 0.2580 |

Betting every outcome whose model edge reached the threshold (1 unit at the saved odds):

| bets | n | nights | expected % | hit % | ci low % | ci high % | break-even % | ROI % |
|---|---|---|---|---|---|---|---|---|
| edge > 0 | 479 | 10 | 66.5 | 52.2 | 47.7 | 56.6 | 52.6 | -1.7 |
| edge ≥ +5 pp (the old 🟢) | 371 | 10 | 69.5 | 50.7 | 45.6 | 55.7 | 52.1 | -4.0 |

By market:

| market | outcomes | model log loss | market log loss |
|---|---|---|---|
| AWAY_TOTAL | 276 | 0.7418 | 0.6928 |
| HOME_TOTAL | 290 | 0.7213 | 0.6909 |
| ML | 156 | 0.6537 | 0.5677 |
| SPREAD | 118 | 0.8113 | 0.6814 |
| TOTAL | 320 | 0.6912 | 0.6888 |
