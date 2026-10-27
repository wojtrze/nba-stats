# Calibration of the props model

The model's chance for a side is mapped to sigmoid(a·logit(market) + b·(logit(model) − logit(market)) + c·[Over] + d): a = weight of the bookmaker's margin-free chance, b = weight of the model's opinion beyond it, c = Over/Under bias, d = offset. Identity: a = b = 1, c = d = 0. Lines: Unibet 2022/23 29331, Superbet 2026/27 9768.

How to read b: it's how much of the model's disagreement with the price held up on past lines (b = 0.1 keeps a tenth of it). It calibrates the model's point chance only; it says nothing about whether the model's 95% range (edge low) is right, and a well-calibrated chance close to the price is not a betting edge.

## Held-out check

Coefficients fitted on the earlier lines of every source: a = 1.219, b = 0.068, c = 0.000, d = 0.000

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
| Calibrated pick, every line | 13763 | 53.5 | 52.7 | 54.4 | -4.1 | 1.8 |
| Calibrated pick, edge > 0 | 41 | 58.5 | 43.4 | 72.2 | -2.7 | 1.7 |

Signal efficiency: every line whose calibrated edge reaches the threshold (cumulative):

| edge ≥ pp | expected % | bets | hit % | ci low % | ci high % | ROI % | avg odds | break-even % | nights |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 58.8 | 41 | 58.5 | 43.4 | 72.2 | -2.7 | 1.7 | 58.4 | 19 |
| 1 | 63.0 | 1 | 0.0 | 0.0 | 79.3 | -100.0 | 1.6 | 61.7 | 1 |
| 2 | – | 0 | – | – | – | – | – | – | 0 |
| 3 | – | 0 | – | – | – | – | – | – | 0 |
| 4 | – | 0 | – | – | – | – | – | – | 0 |
| 5 | – | 0 | – | – | – | – | – | – | 0 |

Calibration on the unseen lines (both sides of every line):

| chance | rows | predicted % | won % |
|---|---|---|---|
| 15–20% | 2 | 17.9 | 50.0 |
| 20–25% | 2 | 22.7 | 50.0 |
| 25–30% | 17 | 28.8 | 23.5 |
| 30–35% | 144 | 33.6 | 32.6 |
| 35–40% | 1046 | 38.1 | 42.0 |
| 40–45% | 3036 | 42.8 | 44.3 |
| 45–50% | 9516 | 48.0 | 47.8 |
| 50–55% | 9516 | 52.0 | 52.2 |
| 55–60% | 3036 | 57.2 | 55.7 |
| 60–65% | 1046 | 61.9 | 58.0 |
| 65–70% | 144 | 66.4 | 67.4 |
| 70–75% | 17 | 71.2 | 76.5 |
| 75–80% | 2 | 77.3 | 50.0 |
| 80–85% | 2 | 82.1 | 50.0 |

### Superbet 2026/27: fitted on Oct 20 2026 – Oct 24 2026 (7007 lines), scored on Oct 25 2026 – Oct 26 2026 (2761 lines)

How well the chances predict the results (lower is better):

| chances | log loss | Brier |
|---|---|---|
| Market (margin-free price) | 0.6839 | 0.2454 |
| Uncalibrated model | 0.6875 | 0.2471 |
| Calibrated model | 0.6828 | 0.2449 |

Betting the unseen lines (1 unit each, at the line's odds):

| strategy | bets | hit % | ci low % | ci high % | ROI % | avg odds |
|---|---|---|---|---|---|---|
| Always Under | 2761 | 52.5 | 50.7 | 54.4 | -4.2 | 1.8 |
| Always Over | 2761 | 47.5 | 45.6 | 49.3 | -11.9 | 1.9 |
| Calibrated pick, every line | 2761 | 56.4 | 54.6 | 58.3 | -1.9 | 1.7 |
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
| 15–20% | 4 | 17.5 | 0.0 |
| 20–25% | 1 | 20.2 | 0.0 |
| 25–30% | 9 | 29.1 | 22.2 |
| 30–35% | 78 | 33.3 | 33.3 |
| 35–40% | 276 | 37.9 | 40.2 |
| 40–45% | 725 | 42.9 | 40.1 |
| 45–50% | 1668 | 47.9 | 47.6 |
| 50–55% | 1668 | 52.1 | 52.4 |
| 55–60% | 725 | 57.1 | 59.9 |
| 60–65% | 276 | 62.1 | 59.8 |
| 65–70% | 78 | 66.7 | 66.7 |
| 70–75% | 9 | 70.9 | 77.8 |
| 75–80% | 1 | 79.8 | 100.0 |
| 80–85% | 4 | 82.5 | 100.0 |

### 🟢 threshold

No 🟢: none of the thresholds +1, +2, +3, +4, +5 pp had 50+ picks over 10+ unseen Superbet nights that won more often than break-even at the low end of the 95% range. Lines with a positive edge get 🟡 (an estimated edge, not a validated one).

Selection policy: one bet per line (its last fetch before tip-off), the calibrated pick's side, 1 unit at that fetch's odds. The threshold is chosen on the same held-out nights it's judged on, among 5 candidates, and re-chosen as nights settle: exploratory, not a proven betting advantage.

## Used by the dashboards (fitted on every line)

a = 1.135, b = 0.127, c = 0.000, d = 0.000 (78198 line sides); no 🟢; Superbet lines through 2026-10-26

## Game markets (not calibrated)

686 settled main-line outcomes on 6 nights (Oct 21 2026 – Oct 26 2026); a calibration is fitted from 300+ outcomes on 10+ nights. Until then game outcomes get no 🟢 / 🟡 and no stake: the model's edges are estimates for research.

How well the chances predict the results (lower is better; both sides of each market count, so the rows aren't independent):

| chances | log loss | Brier |
|---|---|---|
| Market (margin-free price) | 0.6758 | 0.2421 |
| Game model | 0.7211 | 0.2579 |

Betting every outcome whose model edge reached the threshold (1 unit at the saved odds):

| bets | n | nights | expected % | hit % | ci low % | ci high % | break-even % | ROI % |
|---|---|---|---|---|---|---|---|---|
| edge > 0 | 293 | 6 | 66.1 | 55.3 | 49.6 | 60.9 | 51.9 | 5.5 |
| edge ≥ +5 pp (the old 🟢) | 230 | 6 | 68.9 | 53.0 | 46.6 | 59.4 | 51.3 | 2.2 |

By market:

| market | outcomes | model log loss | market log loss |
|---|---|---|---|
| AWAY_TOTAL | 164 | 0.7593 | 0.6948 |
| HOME_TOTAL | 174 | 0.7093 | 0.6954 |
| ML | 98 | 0.6369 | 0.5720 |
| SPREAD | 68 | 0.9080 | 0.6721 |
| TOTAL | 182 | 0.6736 | 0.6972 |
