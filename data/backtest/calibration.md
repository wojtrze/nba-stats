# Calibration of the props model

The model's chance for a side is mapped to sigmoid(a·logit(market) + b·(logit(model) − logit(market)) + c·[Over] + d): a = weight of the bookmaker's margin-free chance, b = weight of the model's opinion beyond it, c = Over/Under bias, d = offset. Identity: a = b = 1, c = d = 0. Lines: Unibet 2022/23 29331, Superbet 2026/27 16021.

How to read b: it's how much of the model's disagreement with the price held up on past lines (b = 0.1 keeps a tenth of it). It calibrates the model's point chance only; it says nothing about whether the model's 95% range (edge low) is right, and a well-calibrated chance close to the price is not a betting edge.

## Held-out check

Coefficients fitted on the earlier lines of every source: a = 1.225, b = 0.114, c = 0.000, d = 0.000

### Unibet 2022/23: fitted on Nov 09 2022 – Jan 31 2023 (15568 lines), scored on Feb 01 2023 – May 08 2023 (13763 lines)

How well the chances predict the results (lower is better):

| chances | log loss | Brier |
|---|---|---|
| Market (margin-free price) | 0.6895 | 0.2482 |
| Uncalibrated model | 0.7051 | 0.2550 |
| Calibrated model | 0.6892 | 0.2480 |

Betting the unseen lines (1 unit each, at the line's odds):

| strategy | bets | hit % | ci low % | ci high % | ROI % | avg odds |
|---|---|---|---|---|---|---|
| Always Under | 13763 | 53.4 | 52.6 | 54.2 | -0.6 | 1.9 |
| Always Over | 13763 | 46.6 | 45.8 | 47.4 | -11.4 | 1.9 |
| Calibrated pick, every line | 13763 | 53.1 | 52.3 | 53.9 | -4.0 | 1.8 |
| Calibrated pick, edge > 0 | 495 | 56.2 | 51.8 | 60.5 | -0.9 | 1.8 |

Signal efficiency: every line whose calibrated edge reaches the threshold (cumulative):

| edge ≥ pp | expected % | bets | hit % | ci low % | ci high % | ROI % | avg odds | break-even % | nights |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 57.2 | 495 | 56.2 | 51.8 | 60.5 | -0.9 | 1.8 | 56.5 | 64 |
| 1 | 57.1 | 106 | 57.5 | 48.0 | 66.5 | 3.1 | 1.8 | 55.4 | 33 |
| 2 | 58.3 | 33 | 51.5 | 35.2 | 67.5 | -8.6 | 1.8 | 55.7 | 12 |
| 3 | 60.3 | 7 | 42.9 | 15.8 | 75.0 | -25.4 | 1.8 | 57.1 | 5 |
| 4 | – | 0 | – | – | – | – | – | – | 0 |
| 5 | – | 0 | – | – | – | – | – | – | 0 |

Calibration on the unseen lines (both sides of every line):

| chance | rows | predicted % | won % |
|---|---|---|---|
| 15–20% | 2 | 18.2 | 50.0 |
| 20–25% | 2 | 22.7 | 50.0 |
| 25–30% | 17 | 28.5 | 23.5 |
| 30–35% | 166 | 33.5 | 34.3 |
| 35–40% | 1091 | 38.0 | 41.4 |
| 40–45% | 3124 | 42.8 | 44.7 |
| 45–50% | 9361 | 47.9 | 47.9 |
| 50–55% | 9361 | 52.1 | 52.1 |
| 55–60% | 3124 | 57.2 | 55.3 |
| 60–65% | 1091 | 62.0 | 58.6 |
| 65–70% | 166 | 66.5 | 65.7 |
| 70–75% | 17 | 71.5 | 76.5 |
| 75–80% | 2 | 77.3 | 50.0 |
| 80–85% | 2 | 81.8 | 50.0 |

### Superbet 2026/27: fitted on Oct 20 2026 – Oct 28 2026 (12380 lines), scored on Oct 29 2026 – Nov 01 2026 (3641 lines)

How well the chances predict the results (lower is better):

| chances | log loss | Brier |
|---|---|---|
| Market (margin-free price) | 0.6828 | 0.2449 |
| Uncalibrated model | 0.6864 | 0.2467 |
| Calibrated model | 0.6813 | 0.2442 |

Betting the unseen lines (1 unit each, at the line's odds):

| strategy | bets | hit % | ci low % | ci high % | ROI % | avg odds |
|---|---|---|---|---|---|---|
| Always Under | 3641 | 54.6 | 53.0 | 56.2 | -0.3 | 1.9 |
| Always Over | 3641 | 45.4 | 43.8 | 47.0 | -16.0 | 1.9 |
| Calibrated pick, every line | 3641 | 54.8 | 53.2 | 56.4 | -4.1 | 1.8 |
| Calibrated pick, edge > 0 | 1 | 0.0 | 0.0 | 79.3 | -100.0 | 1.4 |

Signal efficiency: every line whose calibrated edge reaches the threshold (cumulative):

| edge ≥ pp | expected % | bets | hit % | ci low % | ci high % | ROI % | avg odds | break-even % | nights |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 71.5 | 1 | 0.0 | 0.0 | 79.3 | -100.0 | 1.4 | 71.4 | 1 |
| 1 | – | 0 | – | – | – | – | – | – | 0 |
| 2 | – | 0 | – | – | – | – | – | – | 0 |
| 3 | – | 0 | – | – | – | – | – | – | 0 |
| 4 | – | 0 | – | – | – | – | – | – | 0 |
| 5 | – | 0 | – | – | – | – | – | – | 0 |

Calibration on the unseen lines (both sides of every line):

| chance | rows | predicted % | won % |
|---|---|---|---|
| 10–15% | 1 | 14.9 | 0.0 |
| 15–20% | 5 | 17.4 | 20.0 |
| 20–25% | 5 | 21.6 | 0.0 |
| 25–30% | 12 | 28.5 | 25.0 |
| 30–35% | 105 | 32.9 | 24.8 |
| 35–40% | 388 | 37.9 | 36.3 |
| 40–45% | 924 | 42.9 | 43.4 |
| 45–50% | 2201 | 47.8 | 49.9 |
| 50–55% | 2201 | 52.2 | 50.1 |
| 55–60% | 924 | 57.1 | 56.6 |
| 60–65% | 388 | 62.1 | 63.7 |
| 65–70% | 105 | 67.1 | 75.2 |
| 70–75% | 12 | 71.5 | 75.0 |
| 75–80% | 5 | 78.4 | 100.0 |
| 80–85% | 5 | 82.6 | 80.0 |
| 85–90% | 1 | 85.1 | 100.0 |

### 🟢 threshold

No 🟢: none of the thresholds +1, +2, +3, +4, +5 pp had 50+ picks over 10+ unseen Superbet nights that won more often than break-even at the low end of the 95% range. Lines with a positive edge get 🟡 (an estimated edge, not a validated one).

Selection policy: one bet per line (its last fetch before tip-off), the calibrated pick's side, 1 unit at that fetch's odds. The threshold is chosen on the same held-out nights it's judged on, among 5 candidates, and re-chosen as nights settle: exploratory, not a proven betting advantage.

## Used by the dashboards (fitted on every line)

a = 1.161, b = 0.146, c = 0.000, d = 0.000 (90704 line sides); no 🟢; Superbet lines through 2026-11-01

## Game markets (not calibrated)

1274 settled main-line outcomes on 12 nights (Oct 21 2026 – Nov 01 2026); a calibration is fitted from 300+ outcomes on 10+ nights. Until then game outcomes get no 🟢 / 🟡 and no stake: the model's edges are estimates for research.

How well the chances predict the results (lower is better; both sides of each market count, so the rows aren't independent):

| chances | log loss | Brier |
|---|---|---|
| Market (margin-free price) | 0.6731 | 0.2409 |
| Game model | 0.7196 | 0.2594 |

Betting every outcome whose model edge reached the threshold (1 unit at the saved odds):

| bets | n | nights | expected % | hit % | ci low % | ci high % | break-even % | ROI % |
|---|---|---|---|---|---|---|---|---|
| edge > 0 | 527 | 12 | 66.4 | 51.2 | 47.0 | 55.5 | 52.5 | -3.5 |
| edge ≥ +5 pp (the old 🟢) | 406 | 12 | 69.4 | 49.5 | 44.7 | 54.4 | 52.0 | -6.3 |

By market:

| market | outcomes | model log loss | market log loss |
|---|---|---|---|
| AWAY_TOTAL | 304 | 0.7456 | 0.6950 |
| HOME_TOTAL | 314 | 0.7233 | 0.6923 |
| ML | 172 | 0.6383 | 0.5572 |
| SPREAD | 138 | 0.7946 | 0.6813 |
| TOTAL | 346 | 0.7038 | 0.6908 |
