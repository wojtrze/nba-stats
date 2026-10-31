# What each part of the props model adds

Every model below is fitted (metrics.calibrate's form) on the earlier lines of a source and scored on its later lines; all of them on exactly the same lines. See backtest/ablation.py for the rungs.

## Unibet 2022/23

Fitted on Nov 09 2022 – Jan 31 2023 (15568 lines, 74 nights), scored on Feb 01 2023 – May 08 2023 (13763 lines, 77 nights). No lineup knowledge, so rung 6 equals rung 5; no game odds, so there's no rung 7.

How well each model predicts the unseen lines (lower is better; *vs market* = its log loss minus the market's per line side, with the 95% range from resampling whole nights; a range below 0 means it beat the price):

| model | log loss | Brier | vs market | range low | range high |
|---|---|---|---|---|---|
| 1. Market (margin-free price) | 0.6895 | 0.2482 | 0.0000 | 0.0000 | 0.0000 |
| 2. + Over/Under bias | 0.6890 | 0.2480 | -0.0004 | -0.0007 | -0.0001 |
| 3. Hit rate | 0.6889 | 0.2479 | -0.0005 | -0.0009 | -0.0001 |
| 4. Distribution around the average | 0.6888 | 0.2478 | -0.0007 | -0.0013 | -0.0001 |
| 5. Hit rate + distribution | 0.6889 | 0.2479 | -0.0006 | -0.0011 | -0.0001 |
| 6. + absences | 0.6889 | 0.2479 | -0.0006 | -0.0011 | -0.0001 |
| 8. + matchup = the full model | 0.6889 | 0.2479 | -0.0006 | -0.0011 | -0.0000 |

Betting its positive-edge picks on those lines (1 unit each at the line's odds; a separate question from the predictions above):

| model | bets | hit % | ci low % | ci high % | ROI % | avg odds | break-even % |
|---|---|---|---|---|---|---|---|
| 1. Market (margin-free price) | 0 | – | – | – | – | – | – |
| 2. + Over/Under bias | 0 | – | – | – | – | – | – |
| 3. Hit rate | 0 | – | – | – | – | – | – |
| 4. Distribution around the average | 284 | 54.6 | 48.8 | 60.3 | 0.4 | 1.9 | 54.0 |
| 5. Hit rate + distribution | 51 | 51.0 | 37.7 | 64.1 | -8.4 | 1.8 | 54.9 |
| 6. + absences | 51 | 51.0 | 37.7 | 64.1 | -8.4 | 1.8 | 54.9 |
| 8. + matchup = the full model | 78 | 51.3 | 40.4 | 62.1 | -6.8 | 1.8 | 54.4 |

## Unibet 2022/23 with every absence known (oracle, an upper bound)

Fitted on Nov 09 2022 – Jan 31 2023 (15568 lines, 74 nights), scored on Feb 01 2023 – May 08 2023 (13763 lines, 77 nights). Absences come from who actually didn't play: not available before a game.

How well each model predicts the unseen lines (lower is better; *vs market* = its log loss minus the market's per line side, with the 95% range from resampling whole nights; a range below 0 means it beat the price):

| model | log loss | Brier | vs market | range low | range high |
|---|---|---|---|---|---|
| 1. Market (margin-free price) | 0.6895 | 0.2482 | 0.0000 | 0.0000 | 0.0000 |
| 5. Hit rate + distribution | 0.6889 | 0.2479 | -0.0006 | -0.0011 | -0.0001 |
| 6. + absences | 0.6888 | 0.2478 | -0.0007 | -0.0011 | -0.0002 |
| 8. + matchup = the full model | 0.6888 | 0.2478 | -0.0006 | -0.0012 | -0.0001 |

Betting its positive-edge picks on those lines (1 unit each at the line's odds; a separate question from the predictions above):

| model | bets | hit % | ci low % | ci high % | ROI % | avg odds | break-even % |
|---|---|---|---|---|---|---|---|
| 1. Market (margin-free price) | 0 | – | – | – | – | – | – |
| 5. Hit rate + distribution | 51 | 51.0 | 37.7 | 64.1 | -8.4 | 1.8 | 54.9 |
| 6. + absences | 75 | 50.7 | 39.6 | 61.7 | -7.7 | 1.9 | 54.2 |
| 8. + matchup = the full model | 113 | 49.6 | 40.5 | 58.6 | -9.5 | 1.9 | 54.2 |

## Superbet 2026/27

Fitted on Oct 20 2026 – Oct 26 2026 (9171 lines, 7 nights), scored on Oct 27 2026 – Oct 29 2026 (2928 lines, 3 nights). Each line at its last fetch before tip-off, priced again with the current model.

Only 3 scored nights: the ranges are wide and the ranking can change as nights settle.

How well each model predicts the unseen lines (lower is better; *vs market* = its log loss minus the market's per line side, with the 95% range from resampling whole nights; a range below 0 means it beat the price):

| model | log loss | Brier | vs market | range low | range high |
|---|---|---|---|---|---|
| 1. Market (margin-free price) | 0.6851 | 0.2460 | 0.0000 | 0.0000 | 0.0000 |
| 2. + Over/Under bias | 0.6846 | 0.2458 | -0.0005 | -0.0015 | 0.0014 |
| 3. Hit rate | 0.6841 | 0.2455 | -0.0010 | -0.0027 | 0.0021 |
| 4. Distribution around the average | 0.6835 | 0.2452 | -0.0016 | -0.0035 | 0.0017 |
| 5. Hit rate + distribution | 0.6838 | 0.2454 | -0.0013 | -0.0031 | 0.0019 |
| 6. + absences | 0.6838 | 0.2454 | -0.0013 | -0.0031 | 0.0019 |
| 7. + implied team total | 0.6837 | 0.2453 | -0.0014 | -0.0033 | 0.0022 |
| 8. + matchup = the full model | 0.6842 | 0.2456 | -0.0009 | -0.0026 | 0.0022 |

Betting its positive-edge picks on those lines (1 unit each at the line's odds; a separate question from the predictions above):

| model | bets | hit % | ci low % | ci high % | ROI % | avg odds | break-even % |
|---|---|---|---|---|---|---|---|
| 1. Market (margin-free price) | 0 | – | – | – | – | – | – |
| 2. + Over/Under bias | 23 | 69.6 | 49.1 | 84.4 | -4.0 | 1.4 | 71.7 |
| 3. Hit rate | 90 | 52.2 | 42.0 | 62.2 | -21.0 | 1.5 | 65.4 |
| 4. Distribution around the average | 110 | 61.8 | 52.5 | 70.4 | -3.3 | 1.6 | 64.5 |
| 5. Hit rate + distribution | 109 | 56.0 | 46.6 | 64.9 | -13.7 | 1.6 | 64.7 |
| 6. + absences | 109 | 56.0 | 46.6 | 64.9 | -13.7 | 1.6 | 64.7 |
| 7. + implied team total | 130 | 54.6 | 46.0 | 62.9 | -14.4 | 1.6 | 63.6 |
| 8. + matchup = the full model | 87 | 62.1 | 51.6 | 71.5 | -6.0 | 1.5 | 66.3 |

## Calibration form: how to fit the Over/Under bias

The full model's chance calibrated four ways, each fitted on the earlier lines of both sources pooled (as the dashboards' calibration is) and scored on each source's later lines. The dashboards use the form in backtest/calibrate.py's FITTED (a and b: no side bias, no offset). A source with few scored nights gets a range from resampling only those nights, which understates how unsure it is.

| scored on | form | log loss | Brier | vs market | range low | range high | coefficients |
|---|---|---|---|---|---|---|---|
| 2022 | Current: shared side bias and offset | 0.6888 | 0.2479 | -0.0006 | -0.0013 | 0.0002 | m +1.220, model +0.092, over -0.039, one +0.020 |
| superbet | Current: shared side bias and offset | 0.6842 | 0.2456 | -0.0009 | -0.0020 | 0.0011 | m +1.220, model +0.092, over -0.039, one +0.020 |
| 2022 | No side bias (offset kept) | 0.6892 | 0.2481 | -0.0002 | -0.0009 | 0.0005 | m +1.228, model +0.107, one +0.000 |
| superbet | No side bias (offset kept) | 0.6844 | 0.2457 | -0.0007 | -0.0014 | 0.0005 | m +1.228, model +0.107, one +0.000 |
| 2022 | No side bias, no offset | 0.6892 | 0.2481 | -0.0002 | -0.0009 | 0.0005 | m +1.228, model +0.107 |
| superbet | No side bias, no offset | 0.6844 | 0.2457 | -0.0007 | -0.0014 | 0.0005 | m +1.228, model +0.107 |
| 2022 | Side bias and offset per bookmaker | 0.6891 | 0.2480 | -0.0004 | -0.0011 | 0.0003 | m +1.220, model +0.097, over -0.014, one +0.007, over_sb -0.066, one_sb +0.033 |
| superbet | Side bias and offset per bookmaker | 0.6841 | 0.2455 | -0.0010 | -0.0026 | 0.0020 | m +1.220, model +0.097, over -0.014, one +0.007, over_sb -0.066, one_sb +0.033 |
