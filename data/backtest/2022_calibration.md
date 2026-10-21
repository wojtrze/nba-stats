# Calibration of the props model on 2022/23

The model's chance for a side is mapped to sigmoid(a·logit(market) + b·(logit(model) − logit(market)) + c·[Over] + d): a = weight of the bookmaker's margin-free chance, b = weight of the model's opinion beyond it, c = Over/Under bias, d = offset. Identity: a = b = 1, c = d = 0.

## Held-out check: fitted on Nov 09 – Jan 31 (15568 lines), scored on Feb 01 – May 08 (13763 lines)

Coefficients fitted on the first part: a = 1.120, b = 0.076, c = -0.032, d = 0.016

### How well the chances predict the results (lower is better)

| chances | log loss | Brier |
|---|---|---|
| Market (margin-free price) | 0.6895 | 0.2482 |
| Uncalibrated model | 0.7055 | 0.2552 |
| Calibrated model | 0.6889 | 0.2479 |

### Betting the unseen lines (1 unit each, at the line's odds)

| strategy | bets | hit % | ci low % | ci high % | ROI % | avg odds |
|---|---|---|---|---|---|---|
| Always Under | 13763 | 53.4 | 52.6 | 54.2 | -0.6 | 1.9 |
| Uncalibrated model pick, edge > 0 | 9654 | 51.4 | 50.4 | 52.4 | -2.9 | 1.9 |
| Uncalibrated model pick, 🟢 | 1651 | 51.8 | 49.4 | 54.2 | -2.7 | 1.9 |
| Calibrated pick, edge > 0 | 91 | 52.7 | 42.6 | 62.7 | -4.5 | 1.8 |
| Calibrated pick, 🟢 | 14 | 21.4 | 7.6 | 47.6 | -60.6 | 1.9 |

### Calibration of the calibrated model on the unseen lines (both sides of every line)

| chance | rows | predicted % | won % |
|---|---|---|---|
| 15–20% | 1 | 18.3 | 0.0 |
| 20–25% | 2 | 21.8 | 50.0 |
| 25–30% | 10 | 29.3 | 30.0 |
| 30–35% | 89 | 33.6 | 27.0 |
| 35–40% | 859 | 38.2 | 40.0 |
| 40–45% | 3001 | 42.8 | 44.3 |
| 45–50% | 9801 | 48.0 | 47.8 |
| 50–55% | 9801 | 52.0 | 52.2 |
| 55–60% | 3001 | 57.2 | 55.7 |
| 60–65% | 859 | 61.8 | 60.0 |
| 65–70% | 89 | 66.4 | 73.0 |
| 70–75% | 10 | 70.7 | 70.0 |
| 75–80% | 2 | 78.2 | 50.0 |
| 80–85% | 1 | 81.7 | 100.0 |

## Coefficients used by the dashboards (fitted on the whole season)

a = 1.005, b = 0.079, c = -0.120, d = 0.060 (29331 lines, 58662 line sides)
