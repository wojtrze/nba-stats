# Ranking a night's lines: the evidence behind the shortlist

No line clears Superbet's 12% stake tax (metrics.COST_PROFILES), so the dashboards' decision is 'don't bet' every
night. The question here is the relative one: among tonight's lines, are the ones the model ranks first better
than the rest? Two rank keys are compared, each choosing its own side of a line:

    ev            the side with the higher expected return (p × odds), ranked by it: what models.price_props shows
    disagreement  the side whose calibrated chance is furthest above the margin-free price, ranked by that gap

The calibration (a, b) is fitted on the earlier part of each source and the lines are scored on the later part
(2022/23: Nov–Jan / Feb–May; Superbet: all but the latest 30% of nights / those nights, as backtest/calibrate.py
splits them). Pushes are left out. 'won − price pp' is how much more often the chosen sides won than the
margin-free price said: 0 = the ranking knows nothing the price doesn't. ROI is per unit at the line's odds,
before and after the tax. The shortlist rows apply decisions.shortlist's rules (no 🔴, one line per game and one
per player). Writes data/backtest/shortlist.md.

Calibration fitted on the earlier lines: a = 1.224, b = 0.092, c = 0.000, d = 0.000

## Unibet 2022/23, key 'ev': 13763 unseen lines, 77 nights

| rank in the night | lines | nights | won % | ci low % | ci high % | price said % | won − price pp | ROI % | ROI after tax % |
|---|---|---|---|---|---|---|---|---|---|
| top 2% | 233 | 72 | 59.7 | 53.3 | 65.8 | 55.1 | 4.6 | 2.3 | -10.0 |
| 2–5% | 422 | 77 | 56.2 | 51.4 | 60.8 | 55.5 | 0.7 | -5.0 | -16.4 |
| 5–10% | 685 | 77 | 57.8 | 54.1 | 61.5 | 55.5 | 2.3 | -2.2 | -14.0 |
| 10–25% | 2071 | 77 | 57.7 | 55.5 | 59.8 | 54.7 | 3.0 | -0.7 | -12.6 |
| 25–50% | 3447 | 77 | 52.5 | 50.9 | 54.2 | 53.1 | -0.6 | -6.8 | -18.0 |
| bottom 50% | 6905 | 77 | 52.2 | 51.0 | 53.4 | 51.1 | 1.1 | -4.0 | -15.5 |

| lines bet | lines | nights | won % | ci low % | ci high % | price said % | won − price pp | ROI % | ROI after tax % |
|---|---|---|---|---|---|---|---|---|---|
| shortlist, top 3 a night | 205 | 77 | 60.5 | 53.7 | 66.9 | 56.4 | 4.0 | 0.7 | -11.4 |
| shortlist, top 5 a night | 295 | 77 | 60.7 | 55.0 | 66.1 | 56.9 | 3.8 | 0.2 | -11.9 |
| shortlist, top 10 a night | 412 | 77 | 59.7 | 54.9 | 64.3 | 57.0 | 2.7 | -1.6 | -13.4 |
| every line (the key's side) | 13763 | 77 | 53.6 | 52.8 | 54.5 | 52.6 | 1.1 | -4.0 | -15.5 |

Star levels (decisions.STAR_BANDS; the 4★ − 1★ row's range is of that difference):

| stars | lines | nights | won % | ci low % | ci high % | price said % | won − price pp | ROI % | ROI after tax % |
|---|---|---|---|---|---|---|---|---|---|
| 4★ | 263.0 | 77.0 | 60.8 | 54.8 | 66.5 | 56.8 | 4.1 | 0.8 | -11.3 |
| 3★ | 2460.0 | 77.0 | 58.2 | 56.2 | 60.1 | 55.0 | 3.1 | -0.5 | -12.4 |
| 2★ | 4135.0 | 77.0 | 52.9 | 51.3 | 54.4 | 53.2 | -0.4 | -6.5 | -17.7 |
| 1★ | 6905.0 | 77.0 | 52.2 | 51.0 | 53.4 | 51.1 | 1.1 | -4.0 | -15.5 |
| 0★ | 0.0 | 0.0 | – | – | – | – | – | – | – |
| every line | 13763.0 | 77.0 | 53.6 | 52.8 | 54.5 | 52.6 | 1.1 | -4.0 | -15.5 |
| 4★ − 1★ | – | – | – | -2.5 | 8.0 | – | 3.0 | – | – |

## Unibet 2022/23, key 'disagreement': 13763 unseen lines, 77 nights

| rank in the night | lines | nights | won % | ci low % | ci high % | price said % | won − price pp | ROI % | ROI after tax % |
|---|---|---|---|---|---|---|---|---|---|
| top 2% | 233 | 72 | 56.7 | 50.2 | 62.9 | 57.8 | -1.2 | -7.7 | -18.8 |
| 2–5% | 422 | 77 | 63.3 | 58.6 | 67.7 | 57.0 | 6.3 | 4.3 | -8.2 |
| 5–10% | 685 | 77 | 56.1 | 52.3 | 59.7 | 55.9 | 0.2 | -5.8 | -17.1 |
| 10–25% | 2071 | 77 | 58.1 | 56.0 | 60.2 | 54.6 | 3.5 | 0.2 | -11.9 |
| 25–50% | 3447 | 77 | 52.2 | 50.5 | 53.9 | 52.9 | -0.7 | -7.1 | -18.3 |
| bottom 50% | 6905 | 77 | 52.1 | 50.9 | 53.2 | 51.0 | 1.1 | -3.9 | -15.4 |

| lines bet | lines | nights | won % | ci low % | ci high % | price said % | won − price pp | ROI % | ROI after tax % |
|---|---|---|---|---|---|---|---|---|---|
| shortlist, top 3 a night | 205 | 77 | 59.0 | 52.2 | 65.5 | 58.8 | 0.2 | -5.7 | -17.0 |
| shortlist, top 5 a night | 295 | 77 | 60.0 | 54.3 | 65.4 | 58.6 | 1.4 | -3.8 | -15.3 |
| shortlist, top 10 a night | 412 | 77 | 60.7 | 55.9 | 65.3 | 58.5 | 2.1 | -2.6 | -14.3 |
| every line (the key's side) | 13763 | 77 | 53.6 | 52.8 | 54.5 | 52.6 | 1.1 | -4.0 | -15.5 |

Star levels (decisions.STAR_BANDS; the 4★ − 1★ row's range is of that difference):

| stars | lines | nights | won % | ci low % | ci high % | price said % | won − price pp | ROI % | ROI after tax % |
|---|---|---|---|---|---|---|---|---|---|
| 4★ | 291.0 | 77.0 | 61.9 | 56.2 | 67.2 | 58.8 | 3.1 | -1.1 | -13.0 |
| 3★ | 2432.0 | 77.0 | 57.8 | 55.8 | 59.7 | 55.3 | 2.4 | -1.9 | -13.6 |
| 2★ | 4135.0 | 77.0 | 53.2 | 51.7 | 54.7 | 53.1 | 0.1 | -5.6 | -17.0 |
| 1★ | 6905.0 | 77.0 | 52.1 | 50.9 | 53.2 | 51.0 | 1.1 | -3.9 | -15.4 |
| 0★ | 0.0 | 0.0 | – | – | – | – | – | – | – |
| every line | 13763.0 | 77.0 | 53.6 | 52.8 | 54.5 | 52.6 | 1.1 | -4.0 | -15.5 |
| 4★ − 1★ | – | – | – | -2.8 | 6.7 | – | 2.0 | – | – |

## Superbet 2026/27, key 'ev': 5357 unseen lines, 4 nights

| rank in the night | lines | nights | won % | ci low % | ci high % | price said % | won − price pp | ROI % | ROI after tax % |
|---|---|---|---|---|---|---|---|---|---|
| top 2% | 106 | 4 | 65.1 | 55.6 | 73.5 | 60.6 | 4.5 | 0.4 | -11.7 |
| 2–5% | 161 | 4 | 64.0 | 56.3 | 71.0 | 60.0 | 4.0 | -1.7 | -13.5 |
| 5–10% | 268 | 4 | 63.1 | 57.1 | 68.6 | 57.5 | 5.5 | 1.3 | -10.8 |
| 10–25% | 804 | 4 | 59.7 | 56.3 | 63.0 | 55.7 | 4.0 | -0.5 | -12.4 |
| 25–50% | 1339 | 4 | 57.5 | 54.8 | 60.1 | 53.4 | 4.1 | -0.2 | -12.2 |
| bottom 50% | 2679 | 4 | 51.8 | 49.9 | 53.7 | 51.7 | 0.1 | -7.7 | -18.8 |

| lines bet | lines | nights | won % | ci low % | ci high % | price said % | won − price pp | ROI % | ROI after tax % |
|---|---|---|---|---|---|---|---|---|---|
| shortlist, top 3 a night | 12 | 4 | 50.0 | 25.4 | 74.6 | 63.5 | -13.5 | -26.6 | -35.4 |
| shortlist, top 5 a night | 18 | 4 | 61.1 | 38.6 | 79.7 | 62.7 | -1.6 | -8.8 | -19.7 |
| shortlist, top 10 a night | 30 | 4 | 63.3 | 45.5 | 78.1 | 61.5 | 1.8 | -4.5 | -15.9 |
| every line (the key's side) | 5357 | 4 | 55.6 | 54.3 | 56.9 | 53.4 | 2.2 | -4.0 | -15.5 |

Star levels (decisions.STAR_BANDS; the 4★ − 1★ row's range is of that difference):

| stars | lines | nights | won % | ci low % | ci high % | price said % | won − price pp | ROI % | ROI after tax % |
|---|---|---|---|---|---|---|---|---|---|
| 4★ | 31.0 | 4.0 | 61.3 | 43.8 | 76.3 | 61.3 | -0.0 | -7.4 | -18.5 |
| 3★ | 780.0 | 4.0 | 63.3 | 59.9 | 66.6 | 57.2 | 6.1 | 2.5 | -9.8 |
| 2★ | 1282.0 | 4.0 | 56.6 | 53.9 | 59.3 | 53.6 | 3.0 | -1.9 | -13.7 |
| 1★ | 2132.0 | 4.0 | 52.0 | 49.9 | 54.1 | 51.6 | 0.4 | -7.1 | -18.2 |
| 0★ | 1132.0 | 4.0 | 55.7 | 52.7 | 58.5 | 53.7 | 1.9 | -4.7 | -16.1 |
| every line | 5357.0 | 4.0 | 55.6 | 54.3 | 56.9 | 53.4 | 2.2 | -4.0 | -15.5 |
| 4★ − 1★ | – | – | – | -31.7 | 15.7 | – | -0.4 | – | – |

## Superbet 2026/27, key 'disagreement': 5357 unseen lines, 4 nights

| rank in the night | lines | nights | won % | ci low % | ci high % | price said % | won − price pp | ROI % | ROI after tax % |
|---|---|---|---|---|---|---|---|---|---|
| top 2% | 106 | 4 | 67.9 | 58.5 | 76.0 | 65.1 | 2.8 | -4.6 | -16.1 |
| 2–5% | 161 | 4 | 68.3 | 60.8 | 75.0 | 60.5 | 7.9 | 4.5 | -8.0 |
| 5–10% | 268 | 4 | 61.9 | 56.0 | 67.5 | 58.2 | 3.7 | -2.1 | -13.8 |
| 10–25% | 804 | 4 | 60.2 | 56.8 | 63.5 | 56.3 | 3.9 | -1.0 | -12.9 |
| 25–50% | 1339 | 4 | 57.8 | 55.1 | 60.4 | 53.5 | 4.3 | -0.4 | -12.4 |
| bottom 50% | 2679 | 4 | 51.3 | 49.4 | 53.1 | 51.1 | 0.1 | -7.2 | -18.4 |

| lines bet | lines | nights | won % | ci low % | ci high % | price said % | won − price pp | ROI % | ROI after tax % |
|---|---|---|---|---|---|---|---|---|---|
| shortlist, top 3 a night | 12 | 4 | 58.3 | 32.0 | 80.7 | 71.1 | -12.8 | -26.8 | -35.5 |
| shortlist, top 5 a night | 18 | 4 | 66.7 | 43.7 | 83.7 | 68.9 | -2.2 | -11.7 | -22.3 |
| shortlist, top 10 a night | 30 | 4 | 70.0 | 52.1 | 83.3 | 66.6 | 3.4 | -3.4 | -15.0 |
| every line (the key's side) | 5357 | 4 | 55.6 | 54.3 | 56.9 | 53.4 | 2.2 | -3.9 | -15.5 |

Star levels (decisions.STAR_BANDS; the 4★ − 1★ row's range is of that difference):

| stars | lines | nights | won % | ci low % | ci high % | price said % | won − price pp | ROI % | ROI after tax % |
|---|---|---|---|---|---|---|---|---|---|
| 4★ | 32.0 | 4.0 | 71.9 | 54.6 | 84.4 | 66.2 | 5.7 | 0.3 | -11.7 |
| 3★ | 764.0 | 4.0 | 63.5 | 60.0 | 66.8 | 58.1 | 5.3 | 0.9 | -11.2 |
| 2★ | 1284.0 | 4.0 | 57.6 | 54.9 | 60.3 | 53.9 | 3.7 | -1.3 | -13.1 |
| 1★ | 2145.0 | 4.0 | 51.3 | 49.2 | 53.4 | 51.1 | 0.2 | -6.9 | -18.0 |
| 0★ | 1132.0 | 4.0 | 55.7 | 52.7 | 58.5 | 53.7 | 1.9 | -4.7 | -16.1 |
| every line | 5357.0 | 4.0 | 55.6 | 54.3 | 56.9 | 53.4 | 2.2 | -3.9 | -15.5 |
| 4★ − 1★ | – | – | – | -15.4 | 19.8 | – | 5.5 | – | – |
