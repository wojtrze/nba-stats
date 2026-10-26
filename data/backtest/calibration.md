# Calibration of the props model

The model's chance for a side is mapped to sigmoid(a·logit(market) + b·(logit(model) − logit(market)) + c·[Over] + d): a = weight of the bookmaker's margin-free chance, b = weight of the model's opinion beyond it, c = Over/Under bias, d = offset. Identity: a = b = 1, c = d = 0. Lines: Unibet 2022/23 29331, Superbet 2026/27 8222.

How to read b: it's how much of the model's disagreement with the price held up on past lines (b = 0.1 keeps a tenth of it). It calibrates the model's point chance only; it says nothing about whether the model's 95% range (edge low) is right, and a well-calibrated chance close to the price is not a betting edge.

## Held-out check

Coefficients fitted on the earlier lines of every source: a = 1.239, b = 0.064, c = 0.000, d = 0.000

### Unibet 2022/23: fitted on Nov 09 2022 – Jan 31 2023 (15568 lines), scored on Feb 01 2023 – May 08 2023 (13763 lines)

How well the chances predict the results (lower is better):

| chances | log loss | Brier |
|---|---|---|
| Market (margin-free price) | 0.6895 | 0.2482 |
| Uncalibrated model | 0.7051 | 0.2550 |
| Calibrated model | 0.6894 | 0.2481 |

Betting the unseen lines (1 unit each, at the line's odds):

| strategy | bets | hit % | ci low % | ci high % | ROI % | avg odds |
|---|---|---|---|---|---|---|
| Always Under | 13763 | 53.4 | 52.6 | 54.2 | -0.6 | 1.9 |
| Always Over | 13763 | 46.6 | 45.8 | 47.4 | -11.4 | 1.9 |
| Calibrated pick, every line | 13763 | 53.7 | 52.8 | 54.5 | -4.1 | 1.8 |
| Calibrated pick, edge > 0 | 41 | 65.9 | 50.5 | 78.4 | 7.0 | 1.7 |

Signal efficiency: every line whose calibrated edge reaches the threshold (cumulative):

| edge ≥ pp | expected % | bets | hit % | ci low % | ci high % | ROI % | avg odds | break-even % | nights |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 61.2 | 41 | 65.9 | 50.5 | 78.4 | 7.0 | 1.7 | 61.0 | 21 |
| 1 | 64.2 | 2 | 50.0 | 9.5 | 90.5 | -22.5 | 1.6 | 63.1 | 2 |
| 2 | – | 0 | – | – | – | – | – | – | 0 |
| 3 | – | 0 | – | – | – | – | – | – | 0 |
| 4 | – | 0 | – | – | – | – | – | – | 0 |
| 5 | – | 0 | – | – | – | – | – | – | 0 |

Calibration on the unseen lines (both sides of every line):

| chance | rows | predicted % | won % |
|---|---|---|---|
| 15–20% | 2 | 17.5 | 50.0 |
| 20–25% | 2 | 22.4 | 50.0 |
| 25–30% | 18 | 28.6 | 22.2 |
| 30–35% | 165 | 33.6 | 33.3 |
| 35–40% | 1073 | 38.0 | 42.3 |
| 40–45% | 3046 | 42.8 | 44.4 |
| 45–50% | 9457 | 48.0 | 47.7 |
| 50–55% | 9457 | 52.0 | 52.3 |
| 55–60% | 3046 | 57.2 | 55.6 |
| 60–65% | 1073 | 62.0 | 57.7 |
| 65–70% | 165 | 66.4 | 66.7 |
| 70–75% | 18 | 71.4 | 77.8 |
| 75–80% | 2 | 77.6 | 50.0 |
| 80–85% | 2 | 82.5 | 50.0 |

### Superbet 2026/27: fitted on Oct 20 2026 – Oct 23 2026 (5759 lines), scored on Oct 24 2026 – Oct 25 2026 (2463 lines)

How well the chances predict the results (lower is better):

| chances | log loss | Brier |
|---|---|---|
| Market (margin-free price) | 0.6877 | 0.2473 |
| Uncalibrated model | 0.6954 | 0.2507 |
| Calibrated model | 0.6876 | 0.2473 |

Betting the unseen lines (1 unit each, at the line's odds):

| strategy | bets | hit % | ci low % | ci high % | ROI % | avg odds |
|---|---|---|---|---|---|---|
| Always Under | 2463 | 48.2 | 46.2 | 50.1 | -12.1 | 1.8 |
| Always Over | 2463 | 51.8 | 49.9 | 53.8 | -3.3 | 1.9 |
| Calibrated pick, every line | 2463 | 54.9 | 52.9 | 56.8 | -4.7 | 1.7 |
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
| 15–20% | 1 | 16.0 | 0.0 |
| 25–30% | 6 | 29.2 | 0.0 |
| 30–35% | 75 | 33.1 | 36.0 |
| 35–40% | 263 | 37.9 | 41.8 |
| 40–45% | 657 | 42.9 | 42.9 |
| 45–50% | 1461 | 47.9 | 50.4 |
| 50–55% | 1461 | 52.1 | 49.6 |
| 55–60% | 657 | 57.1 | 57.1 |
| 60–65% | 263 | 62.1 | 58.2 |
| 65–70% | 75 | 66.9 | 64.0 |
| 70–75% | 6 | 70.8 | 100.0 |
| 80–85% | 1 | 84.0 | 100.0 |

### 🟢 threshold

No 🟢: none of the thresholds +1, +2, +3, +4, +5 pp had 50+ picks over 10+ unseen Superbet nights that won more often than break-even at the low end of the 95% range. Lines with a positive edge get 🟡 (an estimated edge, not a validated one).

Selection policy: one bet per line (its last fetch before tip-off), the calibrated pick's side, 1 unit at that fetch's odds. The threshold is chosen on the same held-out nights it's judged on, among 5 candidates, and re-chosen as nights settle: exploratory, not a proven betting advantage.

## Used by the dashboards (fitted on every line)

a = 1.116, b = 0.121, c = 0.000, d = 0.000 (75106 line sides); no 🟢; Superbet lines through 2026-10-25

## Game markets (not calibrated)

580 settled main-line outcomes on 5 nights (Oct 21 2026 – Oct 25 2026); a calibration is fitted from 300+ outcomes on 10+ nights. Until then game outcomes get no 🟢 / 🟡 and no stake: the model's edges are estimates for research.

How well the chances predict the results (lower is better; both sides of each market count, so the rows aren't independent):

| chances | log loss | Brier |
|---|---|---|
| Market (margin-free price) | 0.6719 | 0.2403 |
| Game model | 0.7011 | 0.2492 |

Betting every outcome whose model edge reached the threshold (1 unit at the saved odds):

| bets | n | nights | expected % | hit % | ci low % | ci high % | break-even % | ROI % |
|---|---|---|---|---|---|---|---|---|
| edge > 0 | 243 | 5 | 65.5 | 58.4 | 52.2 | 64.5 | 52.0 | 11.0 |
| edge ≥ +5 pp (the old 🟢) | 188 | 5 | 68.1 | 55.3 | 48.2 | 62.2 | 51.4 | 6.2 |

By market:

| market | outcomes | model log loss | market log loss |
|---|---|---|---|
| AWAY_TOTAL | 138 | 0.7734 | 0.6926 |
| HOME_TOTAL | 150 | 0.7081 | 0.6942 |
| ML | 80 | 0.5687 | 0.5496 |
| SPREAD | 54 | 0.7878 | 0.6696 |
| TOTAL | 158 | 0.6688 | 0.6955 |
