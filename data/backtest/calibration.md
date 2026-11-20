# Calibration of the props model

The model's chance for a side is mapped to sigmoid(a·logit(market) + b·(logit(model) − logit(market)) + c·[Over] + d): a = weight of the bookmaker's margin-free chance, b = weight of the model's opinion beyond it, c = Over/Under bias, d = offset. Identity: a = b = 1, c = d = 0. Lines: Unibet 2022/23 29331, Superbet 2026/27 42020.

How to read b: it's how much of the model's disagreement with the price held up on past lines (b = 0.1 keeps a tenth of it). It calibrates the model's point chance only; it says nothing about whether the model's 95% range (edge low) is right, and a well-calibrated chance close to the price is not a betting edge.

## Held-out check

Coefficients fitted on the earlier lines of every source: a = 1.211, b = 0.177, c = 0.000, d = 0.000

### Unibet 2022/23: fitted on Nov 09 2022 – Jan 31 2023 (15568 lines), scored on Feb 01 2023 – May 08 2023 (13763 lines)

How well the chances predict the results (lower is better):

| chances | log loss | Brier |
|---|---|---|
| Market (margin-free price) | 0.6895 | 0.2482 |
| Uncalibrated model | 0.7025 | 0.2540 |
| Calibrated model | 0.6893 | 0.2481 |

Betting the unseen lines (1 unit each, at the line's odds):

| strategy | bets | hit % | ci low % | ci high % | ROI % | avg odds |
|---|---|---|---|---|---|---|
| Always Under | 13763 | 53.4 | 52.6 | 54.2 | -0.6 | 1.9 |
| Always Over | 13763 | 46.6 | 45.8 | 47.4 | -11.4 | 1.9 |
| Calibrated pick, every line | 13763 | 52.6 | 51.8 | 53.5 | -3.9 | 1.8 |
| Calibrated pick, edge > 0 | 1139 | 55.1 | 52.2 | 58.0 | -1.1 | 1.8 |

Signal efficiency: every line whose calibrated edge reaches the threshold (cumulative):

| edge ≥ pp | expected % | bets | hit % | ci low % | ci high % | ROI % | avg odds | break-even % | nights |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 56.8 | 1139 | 55.1 | 52.2 | 58.0 | -1.1 | 1.8 | 55.8 | 75 |
| 1 | 57.0 | 438 | 53.4 | 48.7 | 58.0 | -3.1 | 1.8 | 55.0 | 65 |
| 2 | 57.8 | 160 | 54.4 | 46.6 | 61.9 | -1.4 | 1.8 | 54.8 | 45 |
| 3 | 58.4 | 59 | 49.2 | 36.8 | 61.6 | -11.1 | 1.8 | 54.5 | 21 |
| 4 | 58.9 | 21 | 47.6 | 28.3 | 67.6 | -14.8 | 1.9 | 54.2 | 8 |
| 5 | 60.0 | 6 | 50.0 | 18.8 | 81.2 | -8.0 | 1.8 | 54.6 | 3 |

Calibration on the unseen lines (both sides of every line):

| chance | rows | predicted % | won % |
|---|---|---|---|
| 15–20% | 1 | 17.0 | 0.0 |
| 20–25% | 3 | 22.2 | 66.7 |
| 25–30% | 18 | 28.5 | 27.8 |
| 30–35% | 182 | 33.5 | 36.8 |
| 35–40% | 1096 | 38.1 | 40.3 |
| 40–45% | 3225 | 42.8 | 45.3 |
| 45–50% | 9238 | 47.9 | 47.8 |
| 50–55% | 9238 | 52.1 | 52.2 |
| 55–60% | 3225 | 57.2 | 54.7 |
| 60–65% | 1096 | 61.9 | 59.7 |
| 65–70% | 182 | 66.5 | 63.2 |
| 70–75% | 18 | 71.5 | 72.2 |
| 75–80% | 3 | 77.8 | 33.3 |
| 80–85% | 1 | 83.0 | 100.0 |

### Superbet 2026/27: fitted on Oct 20 2026 – Nov 10 2026 (29365 lines), scored on Nov 11 2026 – Nov 19 2026 (12655 lines)

How well the chances predict the results (lower is better):

| chances | log loss | Brier |
|---|---|---|
| Market (margin-free price) | 0.6856 | 0.2462 |
| Uncalibrated model | 0.6930 | 0.2498 |
| Calibrated model | 0.6857 | 0.2463 |

Betting the unseen lines (1 unit each, at the line's odds):

| strategy | bets | hit % | ci low % | ci high % | ROI % | avg odds |
|---|---|---|---|---|---|---|
| Always Under | 12655 | 51.2 | 50.3 | 52.1 | -6.4 | 1.9 |
| Always Over | 12655 | 48.8 | 47.9 | 49.7 | -9.1 | 1.9 |
| Calibrated pick, every line | 12655 | 53.4 | 52.5 | 54.3 | -6.0 | 1.8 |
| Calibrated pick, edge > 0 | 42 | 33.3 | 21.0 | 48.4 | -44.4 | 1.8 |

Signal efficiency: every line whose calibrated edge reaches the threshold (cumulative):

| edge ≥ pp | expected % | bets | hit % | ci low % | ci high % | ROI % | avg odds | break-even % | nights |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 58.0 | 42 | 33.3 | 21.0 | 48.4 | -44.4 | 1.8 | 57.4 | 7 |
| 1 | 58.5 | 7 | 14.3 | 2.6 | 51.3 | -77.4 | 1.7 | 57.4 | 1 |
| 2 | – | 0 | – | – | – | – | – | – | 0 |
| 3 | – | 0 | – | – | – | – | – | – | 0 |
| 4 | – | 0 | – | – | – | – | – | – | 0 |
| 5 | – | 0 | – | – | – | – | – | – | 0 |

Calibration on the unseen lines (both sides of every line):

| chance | rows | predicted % | won % |
|---|---|---|---|
| 10–15% | 4 | 13.9 | 0.0 |
| 15–20% | 15 | 17.5 | 33.3 |
| 20–25% | 30 | 22.6 | 36.7 |
| 25–30% | 49 | 28.3 | 32.7 |
| 30–35% | 426 | 33.0 | 32.6 |
| 35–40% | 1437 | 37.9 | 38.0 |
| 40–45% | 3288 | 42.8 | 44.8 |
| 45–50% | 7406 | 47.8 | 48.8 |
| 50–55% | 7406 | 52.2 | 51.2 |
| 55–60% | 3288 | 57.2 | 55.2 |
| 60–65% | 1437 | 62.1 | 62.0 |
| 65–70% | 426 | 67.0 | 67.4 |
| 70–75% | 49 | 71.7 | 67.3 |
| 75–80% | 30 | 77.4 | 63.3 |
| 80–85% | 15 | 82.5 | 66.7 |
| 85–90% | 4 | 86.1 | 100.0 |

### 🟢 threshold

No 🟢: none of the thresholds +1, +2, +3, +4, +5 pp had 50+ picks over 10+ unseen Superbet nights that won more often than break-even at the low end of the 95% range. Lines with a positive edge get 🟡 (an estimated edge, not a validated one).

Selection policy: one bet per line (its last fetch before tip-off), the calibrated pick's side, 1 unit at that fetch's odds. The threshold is chosen on the same held-out nights it's judged on, among 5 candidates, and re-chosen as nights settle: exploratory, not a proven betting advantage.

## Used by the dashboards (fitted on every line)

a = 1.138, b = 0.154, c = 0.000, d = 0.000 (142702 line sides); no 🟢; Superbet lines through 2026-11-19

## Game markets (not calibrated)

3546 settled main-line outcomes on 29 nights (Oct 21 2026 – Nov 19 2026); a calibration is fitted from 300+ outcomes on 10+ nights. Until then game outcomes get no 🟢 / 🟡 and no stake: the model's edges are estimates for research.

How well the chances predict the results (lower is better; both sides of each market count, so the rows aren't independent):

| chances | log loss | Brier |
|---|---|---|
| Market (margin-free price) | 0.6765 | 0.2423 |
| Game model | 0.7362 | 0.2653 |

Betting every outcome whose model edge reached the threshold (1 unit at the saved odds):

| bets | n | nights | expected % | hit % | ci low % | ci high % | break-even % | ROI % |
|---|---|---|---|---|---|---|---|---|
| edge > 0 | 1510 | 29 | 66.7 | 52.6 | 50.1 | 55.1 | 52.7 | -1.0 |
| edge ≥ +5 pp (the old 🟢) | 1174 | 28 | 69.8 | 51.3 | 48.4 | 54.1 | 52.4 | -3.0 |

By market:

| market | outcomes | model log loss | market log loss |
|---|---|---|---|
| AWAY_TOTAL | 840 | 0.7285 | 0.6907 |
| HOME_TOTAL | 862 | 0.7562 | 0.6920 |
| ML | 434 | 0.6689 | 0.5704 |
| SPREAD | 392 | 0.7815 | 0.6912 |
| TOTAL | 1018 | 0.7370 | 0.6913 |
