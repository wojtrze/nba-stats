# Calibration of the props model

The model's chance for a side is mapped to sigmoid(a·logit(market) + b·(logit(model) − logit(market)) + c·[Over] + d): a = weight of the bookmaker's margin-free chance, b = weight of the model's opinion beyond it, c = Over/Under bias, d = offset. Identity: a = b = 1, c = d = 0. Lines: Unibet 2022/23 29331, Superbet 2026/27 12901.

How to read b: it's how much of the model's disagreement with the price held up on past lines (b = 0.1 keeps a tenth of it). It calibrates the model's point chance only; it says nothing about whether the model's 95% range (edge low) is right, and a well-calibrated chance close to the price is not a betting edge.

## Held-out check

Coefficients fitted on the earlier lines of every source: a = 1.226, b = 0.100, c = 0.000, d = 0.000

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
| Calibrated pick, every line | 13763 | 53.3 | 52.5 | 54.2 | -3.8 | 1.8 |
| Calibrated pick, edge > 0 | 305 | 57.0 | 51.4 | 62.5 | -0.7 | 1.8 |

Signal efficiency: every line whose calibrated edge reaches the threshold (cumulative):

| edge ≥ pp | expected % | bets | hit % | ci low % | ci high % | ROI % | avg odds | break-even % | nights |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 57.6 | 305 | 57.0 | 51.4 | 62.5 | -0.7 | 1.8 | 57.1 | 55 |
| 1 | 57.7 | 60 | 58.3 | 45.7 | 69.9 | 3.3 | 1.8 | 56.1 | 25 |
| 2 | 59.3 | 13 | 46.2 | 23.2 | 70.9 | -19.8 | 1.8 | 57.0 | 7 |
| 3 | 64.8 | 1 | 0.0 | 0.0 | 79.3 | -100.0 | 1.6 | 61.7 | 1 |
| 4 | – | 0 | – | – | – | – | – | – | 0 |
| 5 | – | 0 | – | – | – | – | – | – | 0 |

Calibration on the unseen lines (both sides of every line):

| chance | rows | predicted % | won % |
|---|---|---|---|
| 15–20% | 2 | 18.1 | 50.0 |
| 20–25% | 2 | 22.6 | 50.0 |
| 25–30% | 18 | 28.7 | 22.2 |
| 30–35% | 163 | 33.6 | 32.5 |
| 35–40% | 1085 | 38.1 | 41.8 |
| 40–45% | 3086 | 42.8 | 44.5 |
| 45–50% | 9407 | 47.9 | 47.6 |
| 50–55% | 9407 | 52.1 | 52.4 |
| 55–60% | 3086 | 57.2 | 55.5 |
| 60–65% | 1085 | 61.9 | 58.2 |
| 65–70% | 163 | 66.4 | 67.5 |
| 70–75% | 18 | 71.3 | 77.8 |
| 75–80% | 2 | 77.4 | 50.0 |
| 80–85% | 2 | 81.9 | 50.0 |

### Superbet 2026/27: fitted on Oct 20 2026 – Oct 26 2026 (9768 lines), scored on Oct 27 2026 – Oct 29 2026 (3133 lines)

How well the chances predict the results (lower is better):

| chances | log loss | Brier |
|---|---|---|
| Market (margin-free price) | 0.6849 | 0.2459 |
| Uncalibrated model | 0.6926 | 0.2495 |
| Calibrated model | 0.6842 | 0.2456 |

Betting the unseen lines (1 unit each, at the line's odds):

| strategy | bets | hit % | ci low % | ci high % | ROI % | avg odds |
|---|---|---|---|---|---|---|
| Always Under | 3133 | 51.2 | 49.5 | 53.0 | -6.3 | 1.9 |
| Always Over | 3133 | 48.8 | 47.0 | 50.5 | -9.6 | 1.9 |
| Calibrated pick, every line | 3133 | 55.4 | 53.6 | 57.1 | -3.2 | 1.8 |
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
| 15–20% | 3 | 18.2 | 0.0 |
| 20–25% | 9 | 23.2 | 11.1 |
| 25–30% | 8 | 28.4 | 37.5 |
| 30–35% | 69 | 33.0 | 40.6 |
| 35–40% | 314 | 38.0 | 43.9 |
| 40–45% | 879 | 42.9 | 37.9 |
| 45–50% | 1851 | 47.8 | 47.8 |
| 50–55% | 1851 | 52.2 | 52.2 |
| 55–60% | 879 | 57.1 | 62.1 |
| 60–65% | 314 | 62.0 | 56.1 |
| 65–70% | 69 | 67.0 | 59.4 |
| 70–75% | 8 | 71.6 | 62.5 |
| 75–80% | 9 | 76.8 | 88.9 |
| 80–85% | 3 | 81.8 | 100.0 |

### 🟢 threshold

No 🟢: none of the thresholds +1, +2, +3, +4, +5 pp had 50+ picks over 10+ unseen Superbet nights that won more often than break-even at the low end of the 95% range. Lines with a positive edge get 🟡 (an estimated edge, not a validated one).

Selection policy: one bet per line (its last fetch before tip-off), the calibrated pick's side, 1 unit at that fetch's odds. The threshold is chosen on the same held-out nights it's judged on, among 5 candidates, and re-chosen as nights settle: exploratory, not a proven betting advantage.

## Used by the dashboards (fitted on every line)

a = 1.140, b = 0.132, c = 0.000, d = 0.000 (84464 line sides); no 🟢; Superbet lines through 2026-10-29

## Game markets (not calibrated)

988 settled main-line outcomes on 9 nights (Oct 21 2026 – Oct 29 2026); a calibration is fitted from 300+ outcomes on 10+ nights. Until then game outcomes get no 🟢 / 🟡 and no stake: the model's edges are estimates for research.

How well the chances predict the results (lower is better; both sides of each market count, so the rows aren't independent):

| chances | log loss | Brier |
|---|---|---|
| Market (margin-free price) | 0.6730 | 0.2408 |
| Game model | 0.7248 | 0.2609 |

Betting every outcome whose model edge reached the threshold (1 unit at the saved odds):

| bets | n | nights | expected % | hit % | ci low % | ci high % | break-even % | ROI % |
|---|---|---|---|---|---|---|---|---|
| edge > 0 | 415 | 9 | 65.8 | 50.6 | 45.8 | 55.4 | 52.2 | -4.2 |
| edge ≥ +5 pp (the old 🟢) | 313 | 9 | 68.9 | 49.2 | 43.7 | 54.7 | 51.7 | -6.0 |

By market:

| market | outcomes | model log loss | market log loss |
|---|---|---|---|
| AWAY_TOTAL | 238 | 0.7662 | 0.6942 |
| HOME_TOTAL | 244 | 0.7219 | 0.6911 |
| ML | 136 | 0.6529 | 0.5595 |
| SPREAD | 98 | 0.8835 | 0.6810 |
| TOTAL | 272 | 0.6699 | 0.6921 |
