# Calibration of the props model

The model's chance for a side is mapped to sigmoid(a·logit(market) + b·(logit(model) − logit(market)) + c·[Over] + d): a = weight of the bookmaker's margin-free chance, b = weight of the model's opinion beyond it, c = Over/Under bias, d = offset. Identity: a = b = 1, c = d = 0. Lines: Unibet 2022/23 29331, Superbet 2026/27 50484.

How to read b: it's how much of the model's disagreement with the price held up on past lines (b = 0.1 keeps a tenth of it). It calibrates the model's point chance only; it says nothing about whether the model's 95% range (edge low) is right, and a well-calibrated chance close to the price is not a betting edge.

## Held-out check

Coefficients fitted on the earlier lines of every source: a = 1.204, b = 0.158, c = 0.000, d = 0.000

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
| Calibrated pick, every line | 13763 | 52.7 | 51.8 | 53.5 | -4.0 | 1.8 |
| Calibrated pick, edge > 0 | 837 | 55.8 | 52.4 | 59.1 | -0.1 | 1.8 |

Signal efficiency: every line whose calibrated edge reaches the threshold (cumulative):

| edge ≥ pp | expected % | bets | hit % | ci low % | ci high % | ROI % | avg odds | break-even % | nights |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 56.6 | 837 | 55.8 | 52.4 | 59.1 | -0.1 | 1.8 | 55.7 | 73 |
| 1 | 56.9 | 268 | 54.5 | 48.5 | 60.3 | -1.1 | 1.8 | 55.0 | 51 |
| 2 | 57.5 | 99 | 51.5 | 41.8 | 61.1 | -6.6 | 1.8 | 54.8 | 31 |
| 3 | 58.2 | 27 | 48.1 | 30.7 | 66.0 | -13.5 | 1.8 | 54.5 | 11 |
| 4 | 59.1 | 7 | 57.1 | 25.0 | 84.2 | 4.7 | 1.8 | 54.7 | 3 |
| 5 | 67.0 | 1 | 0.0 | 0.0 | 79.3 | -100.0 | 1.6 | 61.7 | 1 |

Calibration on the unseen lines (both sides of every line):

| chance | rows | predicted % | won % |
|---|---|---|---|
| 15–20% | 1 | 17.0 | 0.0 |
| 20–25% | 3 | 22.3 | 66.7 |
| 25–30% | 16 | 28.6 | 25.0 |
| 30–35% | 166 | 33.5 | 34.3 |
| 35–40% | 1075 | 38.1 | 40.6 |
| 40–45% | 3152 | 42.8 | 45.2 |
| 45–50% | 9350 | 47.9 | 47.6 |
| 50–55% | 9350 | 52.1 | 52.4 |
| 55–60% | 3152 | 57.2 | 54.8 |
| 60–65% | 1075 | 61.9 | 59.4 |
| 65–70% | 166 | 66.5 | 65.7 |
| 70–75% | 16 | 71.4 | 75.0 |
| 75–80% | 3 | 77.7 | 33.3 |
| 80–85% | 1 | 83.0 | 100.0 |

### Superbet 2026/27: fitted on Oct 20 2026 – Nov 14 2026 (34798 lines), scored on Nov 15 2026 – Nov 25 2026 (15686 lines)

How well the chances predict the results (lower is better):

| chances | log loss | Brier |
|---|---|---|
| Market (margin-free price) | 0.6847 | 0.2458 |
| Uncalibrated model | 0.6897 | 0.2482 |
| Calibrated model | 0.6843 | 0.2456 |

Betting the unseen lines (1 unit each, at the line's odds):

| strategy | bets | hit % | ci low % | ci high % | ROI % | avg odds |
|---|---|---|---|---|---|---|
| Always Under | 15686 | 51.1 | 50.3 | 51.9 | -6.5 | 1.9 |
| Always Over | 15686 | 48.9 | 48.1 | 49.7 | -9.2 | 1.9 |
| Calibrated pick, every line | 15686 | 54.0 | 53.2 | 54.8 | -5.1 | 1.8 |
| Calibrated pick, edge > 0 | 24 | 54.2 | 35.1 | 72.1 | -10.5 | 1.7 |

Signal efficiency: every line whose calibrated edge reaches the threshold (cumulative):

| edge ≥ pp | expected % | bets | hit % | ci low % | ci high % | ROI % | avg odds | break-even % | nights |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 59.5 | 24 | 54.2 | 35.1 | 72.1 | -10.5 | 1.7 | 59.2 | 6 |
| 1 | 60.9 | 1 | 0.0 | 0.0 | 79.3 | -100.0 | 1.7 | 59.5 | 1 |
| 2 | – | 0 | – | – | – | – | – | – | 0 |
| 3 | – | 0 | – | – | – | – | – | – | 0 |
| 4 | – | 0 | – | – | – | – | – | – | 0 |
| 5 | – | 0 | – | – | – | – | – | – | 0 |

Calibration on the unseen lines (both sides of every line):

| chance | rows | predicted % | won % |
|---|---|---|---|
| 10–15% | 3 | 13.1 | 33.3 |
| 15–20% | 13 | 17.5 | 23.1 |
| 20–25% | 36 | 22.6 | 36.1 |
| 25–30% | 81 | 27.9 | 27.2 |
| 30–35% | 540 | 32.9 | 31.5 |
| 35–40% | 1848 | 37.8 | 39.3 |
| 40–45% | 3964 | 42.8 | 43.0 |
| 45–50% | 9201 | 47.8 | 47.9 |
| 50–55% | 9201 | 52.2 | 52.1 |
| 55–60% | 3964 | 57.2 | 57.0 |
| 60–65% | 1848 | 62.2 | 60.7 |
| 65–70% | 540 | 67.1 | 68.5 |
| 70–75% | 81 | 72.1 | 72.8 |
| 75–80% | 36 | 77.4 | 63.9 |
| 80–85% | 13 | 82.5 | 76.9 |
| 85–90% | 3 | 86.9 | 66.7 |

### 🟢 threshold

No 🟢: none of the thresholds +1, +2, +3, +4, +5 pp had 50+ picks over 10+ unseen Superbet nights that won more often than break-even at the low end of the 95% range. Lines with a positive edge get 🟡 (an estimated edge, not a validated one).

Selection policy: one bet per line (its last fetch before tip-off), the calibrated pick's side, 1 unit at that fetch's odds. The threshold is chosen on the same held-out nights it's judged on, among 5 candidates, and re-chosen as nights settle: exploratory, not a proven betting advantage.

## Used by the dashboards (fitted on every line)

a = 1.145, b = 0.165, c = 0.000, d = 0.000 (159630 line sides); no 🟢; Superbet lines through 2026-11-25

## Game markets (not calibrated)

4372 settled main-line outcomes on 35 nights (Oct 21 2026 – Nov 25 2026); a calibration is fitted from 300+ outcomes on 10+ nights. Until then game outcomes get no 🟢 / 🟡 and no stake: the model's edges are estimates for research.

How well the chances predict the results (lower is better; both sides of each market count, so the rows aren't independent):

| chances | log loss | Brier |
|---|---|---|
| Market (margin-free price) | 0.6759 | 0.2420 |
| Game model | 0.7439 | 0.2689 |

Betting every outcome whose model edge reached the threshold (1 unit at the saved odds):

| bets | n | nights | expected % | hit % | ci low % | ci high % | break-even % | ROI % |
|---|---|---|---|---|---|---|---|---|
| edge > 0 | 1887 | 35 | 67.0 | 51.4 | 49.1 | 53.7 | 52.6 | -3.3 |
| edge ≥ +5 pp (the old 🟢) | 1487 | 34 | 70.0 | 50.2 | 47.6 | 52.7 | 52.5 | -5.2 |

By market:

| market | outcomes | model log loss | market log loss |
|---|---|---|---|
| AWAY_TOTAL | 1032 | 0.7494 | 0.6888 |
| HOME_TOTAL | 1058 | 0.7353 | 0.6892 |
| ML | 522 | 0.6687 | 0.5771 |
| SPREAD | 476 | 0.7989 | 0.6898 |
| TOTAL | 1284 | 0.7566 | 0.6897 |
