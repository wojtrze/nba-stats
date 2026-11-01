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

## Superbet 2026/27, key 'ev': 4257 unseen lines, 3 nights

| rank in the night | lines | nights | won % | ci low % | ci high % | price said % | won − price pp | ROI % | ROI after tax % |
|---|---|---|---|---|---|---|---|---|---|
| top 2% | 84 | 3 | 61.9 | 51.2 | 71.6 | 61.3 | 0.6 | -6.2 | -17.5 |
| 2–5% | 128 | 3 | 64.1 | 55.5 | 71.9 | 60.1 | 3.9 | -2.3 | -14.1 |
| 5–10% | 213 | 3 | 62.0 | 55.3 | 68.2 | 57.6 | 4.4 | -0.7 | -12.6 |
| 10–25% | 639 | 3 | 59.9 | 56.1 | 63.7 | 55.5 | 4.4 | 0.1 | -11.9 |
| 25–50% | 1064 | 3 | 56.4 | 53.4 | 59.3 | 53.4 | 3.0 | -2.3 | -14.0 |
| bottom 50% | 2129 | 3 | 52.5 | 50.4 | 54.6 | 51.7 | 0.8 | -6.5 | -17.8 |

| lines bet | lines | nights | won % | ci low % | ci high % | price said % | won − price pp | ROI % | ROI after tax % |
|---|---|---|---|---|---|---|---|---|---|
| shortlist, top 3 a night | 9 | 3 | 44.4 | 18.9 | 73.3 | 64.9 | -20.5 | -37.7 | -45.1 |
| shortlist, top 5 a night | 13 | 3 | 61.5 | 35.5 | 82.3 | 63.7 | -2.2 | -9.8 | -20.6 |
| shortlist, top 10 a night | 23 | 3 | 65.2 | 44.9 | 81.2 | 62.2 | 3.0 | -2.7 | -14.4 |
| every line (the key's side) | 4257 | 3 | 55.6 | 54.1 | 57.1 | 53.4 | 2.2 | -4.1 | -15.6 |

## Superbet 2026/27, key 'disagreement': 4257 unseen lines, 3 nights

| rank in the night | lines | nights | won % | ci low % | ci high % | price said % | won − price pp | ROI % | ROI after tax % |
|---|---|---|---|---|---|---|---|---|---|
| top 2% | 84 | 3 | 67.9 | 57.3 | 76.9 | 65.3 | 2.6 | -5.2 | -16.6 |
| 2–5% | 128 | 3 | 68.8 | 60.3 | 76.1 | 60.5 | 8.2 | 5.1 | -7.5 |
| 5–10% | 213 | 3 | 61.5 | 54.8 | 67.8 | 58.4 | 3.1 | -3.1 | -14.7 |
| 10–25% | 639 | 3 | 60.7 | 56.9 | 64.4 | 56.3 | 4.5 | -0.2 | -12.2 |
| 25–50% | 1064 | 3 | 58.0 | 55.0 | 60.9 | 53.6 | 4.4 | -0.2 | -12.2 |
| bottom 50% | 2129 | 3 | 51.1 | 48.9 | 53.2 | 51.1 | -0.1 | -7.7 | -18.7 |

| lines bet | lines | nights | won % | ci low % | ci high % | price said % | won − price pp | ROI % | ROI after tax % |
|---|---|---|---|---|---|---|---|---|---|
| shortlist, top 3 a night | 9 | 3 | 66.7 | 35.4 | 87.9 | 70.7 | -4.0 | -15.0 | -25.2 |
| shortlist, top 5 a night | 13 | 3 | 69.2 | 42.4 | 87.3 | 69.4 | -0.1 | -9.9 | -20.7 |
| shortlist, top 10 a night | 23 | 3 | 73.9 | 53.5 | 87.5 | 67.0 | 6.9 | 1.0 | -11.1 |
| every line (the key's side) | 4257 | 3 | 55.6 | 54.1 | 57.1 | 53.4 | 2.2 | -4.0 | -15.5 |
