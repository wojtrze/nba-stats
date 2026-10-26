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
| 4. Distribution around the average | 0.6888 | 0.2479 | -0.0006 | -0.0012 | -0.0000 |
| 5. Hit rate + distribution | 0.6889 | 0.2479 | -0.0006 | -0.0011 | -0.0001 |
| 6. + absences | 0.6889 | 0.2479 | -0.0006 | -0.0011 | -0.0001 |
| 8. + matchup = the full model | 0.6889 | 0.2479 | -0.0006 | -0.0011 | -0.0000 |

Betting its positive-edge picks on those lines (1 unit each at the line's odds; a separate question from the predictions above):

| model | bets | hit % | ci low % | ci high % | ROI % | avg odds | break-even % |
|---|---|---|---|---|---|---|---|
| 1. Market (margin-free price) | 0 | – | – | – | – | – | – |
| 2. + Over/Under bias | 0 | – | – | – | – | – | – |
| 3. Hit rate | 0 | – | – | – | – | – | – |
| 4. Distribution around the average | 293 | 57.0 | 51.3 | 62.5 | 5.1 | 1.9 | 54.0 |
| 5. Hit rate + distribution | 67 | 55.2 | 43.4 | 66.5 | 0.4 | 1.8 | 54.5 |
| 6. + absences | 67 | 55.2 | 43.4 | 66.5 | 0.4 | 1.8 | 54.5 |
| 8. + matchup = the full model | 91 | 52.7 | 42.6 | 62.7 | -4.5 | 1.8 | 54.6 |

## Unibet 2022/23 with every absence known (oracle, an upper bound)

Fitted on Nov 09 2022 – Jan 31 2023 (15568 lines, 74 nights), scored on Feb 01 2023 – May 08 2023 (13763 lines, 77 nights). Absences come from who actually didn't play: not available before a game.

How well each model predicts the unseen lines (lower is better; *vs market* = its log loss minus the market's per line side, with the 95% range from resampling whole nights; a range below 0 means it beat the price):

| model | log loss | Brier | vs market | range low | range high |
|---|---|---|---|---|---|
| 1. Market (margin-free price) | 0.6895 | 0.2482 | 0.0000 | 0.0000 | 0.0000 |
| 5. Hit rate + distribution | 0.6889 | 0.2479 | -0.0006 | -0.0011 | -0.0001 |
| 6. + absences | 0.6888 | 0.2478 | -0.0007 | -0.0011 | -0.0002 |
| 8. + matchup = the full model | 0.6888 | 0.2479 | -0.0006 | -0.0011 | -0.0001 |

Betting its positive-edge picks on those lines (1 unit each at the line's odds; a separate question from the predictions above):

| model | bets | hit % | ci low % | ci high % | ROI % | avg odds | break-even % |
|---|---|---|---|---|---|---|---|
| 1. Market (margin-free price) | 0 | – | – | – | – | – | – |
| 5. Hit rate + distribution | 67 | 55.2 | 43.4 | 66.5 | 0.4 | 1.8 | 54.5 |
| 6. + absences | 105 | 51.4 | 42.0 | 60.8 | -5.9 | 1.9 | 54.1 |
| 8. + matchup = the full model | 153 | 48.4 | 40.6 | 56.2 | -11.4 | 1.8 | 54.3 |

## Superbet 2026/27

Fitted on Oct 20 2026 – Oct 23 2026 (5400 lines, 4 nights), scored on Oct 24 2026 – Oct 25 2026 (2350 lines, 2 nights). Each line at its last fetch before tip-off, priced again with the current model.

Only 2 scored nights: the ranges are wide and the ranking can change as nights settle.

How well each model predicts the unseen lines (lower is better; *vs market* = its log loss minus the market's per line side, with the 95% range from resampling whole nights; a range below 0 means it beat the price):

| model | log loss | Brier | vs market | range low | range high |
|---|---|---|---|---|---|
| 1. Market (margin-free price) | 0.6871 | 0.2470 | 0.0000 | 0.0000 | 0.0000 |
| 2. + Over/Under bias | 0.6907 | 0.2488 | 0.0036 | 0.0007 | 0.0063 |
| 3. Hit rate | 0.6904 | 0.2486 | 0.0033 | 0.0002 | 0.0061 |
| 4. Distribution around the average | 0.6907 | 0.2488 | 0.0035 | 0.0006 | 0.0063 |
| 5. Hit rate + distribution | 0.6905 | 0.2487 | 0.0034 | 0.0004 | 0.0062 |
| 6. + absences | 0.6905 | 0.2487 | 0.0034 | 0.0004 | 0.0062 |
| 7. + implied team total | 0.6905 | 0.2487 | 0.0033 | 0.0003 | 0.0061 |
| 8. + matchup = the full model | 0.6906 | 0.2487 | 0.0035 | 0.0006 | 0.0062 |

Betting its positive-edge picks on those lines (1 unit each at the line's odds; a separate question from the predictions above):

| model | bets | hit % | ci low % | ci high % | ROI % | avg odds | break-even % |
|---|---|---|---|---|---|---|---|
| 1. Market (margin-free price) | 0 | – | – | – | – | – | – |
| 2. + Over/Under bias | 242 | 60.3 | 54.1 | 66.3 | -6.8 | 1.5 | 64.8 |
| 3. Hit rate | 273 | 58.6 | 52.7 | 64.3 | -8.3 | 1.6 | 64.0 |
| 4. Distribution around the average | 245 | 59.6 | 53.3 | 65.5 | -7.8 | 1.6 | 64.6 |
| 5. Hit rate + distribution | 257 | 58.0 | 51.9 | 63.9 | -10.0 | 1.6 | 64.3 |
| 6. + absences | 257 | 58.0 | 51.9 | 63.9 | -10.0 | 1.6 | 64.3 |
| 7. + implied team total | 261 | 58.6 | 52.6 | 64.4 | -8.8 | 1.6 | 64.3 |
| 8. + matchup = the full model | 250 | 59.2 | 53.0 | 65.1 | -8.3 | 1.6 | 64.5 |

## Calibration form: how to fit the Over/Under bias

The full model's chance calibrated four ways, each fitted on the earlier lines of both sources pooled (as the dashboards' calibration is) and scored on each source's later lines. The dashboards use the form in backtest/calibrate.py's FITTED (a and b: no side bias, no offset). A source with few scored nights gets a range from resampling only those nights, which understates how unsure it is.

| scored on | form | log loss | Brier | vs market | range low | range high | coefficients |
|---|---|---|---|---|---|---|---|
| 2022 | Current: shared side bias and offset | 0.6888 | 0.2478 | -0.0007 | -0.0013 | -0.0000 | m +1.221, model +0.044, over -0.069, one +0.035 |
| superbet | Current: shared side bias and offset | 0.6879 | 0.2474 | 0.0008 | -0.0005 | 0.0019 | m +1.221, model +0.044, over -0.069, one +0.035 |
| 2022 | No side bias (offset kept) | 0.6895 | 0.2482 | 0.0001 | -0.0004 | 0.0006 | m +1.237, model +0.056, one +0.000 |
| superbet | No side bias (offset kept) | 0.6870 | 0.2470 | -0.0002 | -0.0002 | -0.0002 | m +1.237, model +0.056, one +0.000 |
| 2022 | No side bias, no offset | 0.6895 | 0.2482 | 0.0001 | -0.0004 | 0.0006 | m +1.237, model +0.056 |
| superbet | No side bias, no offset | 0.6870 | 0.2470 | -0.0002 | -0.0002 | -0.0002 | m +1.237, model +0.056 |
| 2022 | Side bias and offset per bookmaker | 0.6891 | 0.2480 | -0.0003 | -0.0009 | 0.0002 | m +1.222, model +0.054, over -0.031, one +0.015, over_sb -0.148, one_sb +0.074 |
| superbet | Side bias and offset per bookmaker | 0.6898 | 0.2484 | 0.0027 | -0.0006 | 0.0058 | m +1.222, model +0.054, over -0.031, one +0.015, over_sb -0.148, one_sb +0.074 |
