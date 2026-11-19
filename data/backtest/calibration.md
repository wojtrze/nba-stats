# Calibration of the props model

The model's chance for a side is mapped to sigmoid(a·logit(market) + b·(logit(model) − logit(market)) + c·[Over] + d): a = weight of the bookmaker's margin-free chance, b = weight of the model's opinion beyond it, c = Over/Under bias, d = offset. Identity: a = b = 1, c = d = 0. Lines: Unibet 2022/23 29331, Superbet 2026/27 41142.

How to read b: it's how much of the model's disagreement with the price held up on past lines (b = 0.1 keeps a tenth of it). It calibrates the model's point chance only; it says nothing about whether the model's 95% range (edge low) is right, and a well-calibrated chance close to the price is not a betting edge.

## Held-out check

Coefficients fitted on the earlier lines of every source: a = 1.187, b = 0.177, c = 0.000, d = 0.000

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
| Calibrated pick, every line | 13763 | 52.6 | 51.8 | 53.5 | -3.5 | 1.8 |
| Calibrated pick, edge > 0 | 1402 | 54.9 | 52.3 | 57.5 | -0.3 | 1.8 |

Signal efficiency: every line whose calibrated edge reaches the threshold (cumulative):

| edge ≥ pp | expected % | bets | hit % | ci low % | ci high % | ROI % | avg odds | break-even % | nights |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 56.4 | 1402 | 54.9 | 52.3 | 57.5 | -0.3 | 1.8 | 55.1 | 77 |
| 1 | 56.7 | 678 | 55.0 | 51.3 | 58.7 | 1.0 | 1.8 | 54.4 | 67 |
| 2 | 57.1 | 313 | 54.6 | 49.1 | 60.1 | 0.8 | 1.9 | 54.0 | 54 |
| 3 | 58.3 | 122 | 56.6 | 47.7 | 65.0 | 3.8 | 1.9 | 54.1 | 35 |
| 4 | 59.5 | 54 | 55.6 | 42.4 | 68.0 | 1.3 | 1.8 | 54.4 | 19 |
| 5 | 60.2 | 27 | 48.1 | 30.7 | 66.0 | -12.1 | 1.9 | 54.3 | 9 |

Calibration on the unseen lines (both sides of every line):

| chance | rows | predicted % | won % |
|---|---|---|---|
| 15–20% | 1 | 17.3 | 0.0 |
| 20–25% | 2 | 21.5 | 50.0 |
| 25–30% | 15 | 28.3 | 33.3 |
| 30–35% | 171 | 33.4 | 34.5 |
| 35–40% | 1093 | 38.1 | 41.3 |
| 40–45% | 3294 | 42.9 | 44.7 |
| 45–50% | 9187 | 47.8 | 48.2 |
| 50–55% | 9187 | 52.2 | 51.8 |
| 55–60% | 3294 | 57.1 | 55.3 |
| 60–65% | 1093 | 61.9 | 58.7 |
| 65–70% | 171 | 66.6 | 65.5 |
| 70–75% | 15 | 71.7 | 66.7 |
| 75–80% | 2 | 78.5 | 50.0 |
| 80–85% | 1 | 82.7 | 100.0 |

### Superbet 2026/27: fitted on Oct 20 2026 – Nov 09 2026 (28180 lines), scored on Nov 10 2026 – Nov 18 2026 (12962 lines)

How well the chances predict the results (lower is better):

| chances | log loss | Brier |
|---|---|---|
| Market (margin-free price) | 0.6843 | 0.2456 |
| Uncalibrated model | 0.6934 | 0.2500 |
| Calibrated model | 0.6841 | 0.2456 |

Betting the unseen lines (1 unit each, at the line's odds):

| strategy | bets | hit % | ci low % | ci high % | ROI % | avg odds |
|---|---|---|---|---|---|---|
| Always Under | 12962 | 52.1 | 51.3 | 53.0 | -4.8 | 1.9 |
| Always Over | 12962 | 47.9 | 47.0 | 48.7 | -11.0 | 1.9 |
| Calibrated pick, every line | 12962 | 53.3 | 52.4 | 54.2 | -5.3 | 1.8 |
| Calibrated pick, edge > 0 | 72 | 43.1 | 32.3 | 54.6 | -27.8 | 1.7 |

Signal efficiency: every line whose calibrated edge reaches the threshold (cumulative):

| edge ≥ pp | expected % | bets | hit % | ci low % | ci high % | ROI % | avg odds | break-even % | nights |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 59.0 | 72 | 43.1 | 32.3 | 54.6 | -27.8 | 1.7 | 58.5 | 9 |
| 1 | 58.3 | 12 | 25.0 | 8.9 | 53.2 | -55.9 | 1.8 | 57.2 | 3 |
| 2 | – | 0 | – | – | – | – | – | – | 0 |
| 3 | – | 0 | – | – | – | – | – | – | 0 |
| 4 | – | 0 | – | – | – | – | – | – | 0 |
| 5 | – | 0 | – | – | – | – | – | – | 0 |

Calibration on the unseen lines (both sides of every line):

| chance | rows | predicted % | won % |
|---|---|---|---|
| 10–15% | 5 | 13.6 | 0.0 |
| 15–20% | 18 | 17.5 | 16.7 |
| 20–25% | 27 | 22.5 | 29.6 |
| 25–30% | 49 | 28.2 | 32.7 |
| 30–35% | 410 | 33.0 | 30.5 |
| 35–40% | 1426 | 37.9 | 37.5 |
| 40–45% | 3394 | 42.8 | 43.8 |
| 45–50% | 7633 | 47.8 | 48.9 |
| 50–55% | 7633 | 52.2 | 51.1 |
| 55–60% | 3394 | 57.2 | 56.2 |
| 60–65% | 1426 | 62.1 | 62.5 |
| 65–70% | 410 | 67.0 | 69.5 |
| 70–75% | 49 | 71.8 | 67.3 |
| 75–80% | 27 | 77.5 | 70.4 |
| 80–85% | 18 | 82.5 | 83.3 |
| 85–90% | 5 | 86.4 | 100.0 |

### 🟢 threshold

No 🟢: none of the thresholds +1, +2, +3, +4, +5 pp had 50+ picks over 10+ unseen Superbet nights that won more often than break-even at the low end of the 95% range. Lines with a positive edge get 🟡 (an estimated edge, not a validated one).

Selection policy: one bet per line (its last fetch before tip-off), the calibrated pick's side, 1 unit at that fetch's odds. The threshold is chosen on the same held-out nights it's judged on, among 5 candidates, and re-chosen as nights settle: exploratory, not a proven betting advantage.

## Used by the dashboards (fitted on every line)

a = 1.142, b = 0.161, c = 0.000, d = 0.000 (140946 line sides); no 🟢; Superbet lines through 2026-11-18

## Game markets (not calibrated)

3468 settled main-line outcomes on 28 nights (Oct 21 2026 – Nov 18 2026); a calibration is fitted from 300+ outcomes on 10+ nights. Until then game outcomes get no 🟢 / 🟡 and no stake: the model's edges are estimates for research.

How well the chances predict the results (lower is better; both sides of each market count, so the rows aren't independent):

| chances | log loss | Brier |
|---|---|---|
| Market (margin-free price) | 0.6768 | 0.2425 |
| Game model | 0.7362 | 0.2653 |

Betting every outcome whose model edge reached the threshold (1 unit at the saved odds):

| bets | n | nights | expected % | hit % | ci low % | ci high % | break-even % | ROI % |
|---|---|---|---|---|---|---|---|---|
| edge > 0 | 1472 | 28 | 66.5 | 52.4 | 49.9 | 55.0 | 52.6 | -1.2 |
| edge ≥ +5 pp (the old 🟢) | 1140 | 27 | 69.6 | 51.1 | 48.2 | 54.0 | 52.4 | -3.1 |

By market:

| market | outcomes | model log loss | market log loss |
|---|---|---|---|
| AWAY_TOTAL | 824 | 0.7330 | 0.6910 |
| HOME_TOTAL | 842 | 0.7529 | 0.6912 |
| ML | 426 | 0.6759 | 0.5742 |
| SPREAD | 382 | 0.7750 | 0.6906 |
| TOTAL | 994 | 0.7356 | 0.6915 |
