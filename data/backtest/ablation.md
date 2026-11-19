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

Fitted on Oct 20 2026 – Nov 09 2026 (27205 lines, 20 nights), scored on Nov 10 2026 – Nov 18 2026 (12962 lines, 9 nights). Each line at its last fetch before tip-off, priced again with the current model.

Only 9 scored nights: the ranges are wide and the ranking can change as nights settle.

How well each model predicts the unseen lines (lower is better; *vs market* = its log loss minus the market's per line side, with the 95% range from resampling whole nights; a range below 0 means it beat the price):

| model | log loss | Brier | vs market | range low | range high |
|---|---|---|---|---|---|
| 1. Market (margin-free price) | 0.6843 | 0.2456 | 0.0000 | 0.0000 | 0.0000 |
| 2. + Over/Under bias | 0.6838 | 0.2454 | -0.0005 | -0.0027 | 0.0012 |
| 3. Hit rate | 0.6842 | 0.2456 | -0.0001 | -0.0027 | 0.0021 |
| 4. Distribution around the average | 0.6841 | 0.2455 | -0.0002 | -0.0029 | 0.0023 |
| 5. Hit rate + distribution | 0.6842 | 0.2456 | -0.0001 | -0.0027 | 0.0022 |
| 6. + absences | 0.6841 | 0.2455 | -0.0002 | -0.0028 | 0.0020 |
| 7. + implied team total | 0.6840 | 0.2455 | -0.0003 | -0.0029 | 0.0021 |
| 8. + matchup = the full model | 0.6839 | 0.2455 | -0.0004 | -0.0029 | 0.0019 |

Betting its positive-edge picks on those lines (1 unit each at the line's odds; a separate question from the predictions above):

| model | bets | hit % | ci low % | ci high % | ROI % | avg odds | break-even % |
|---|---|---|---|---|---|---|---|
| 1. Market (margin-free price) | 0 | – | – | – | – | – | – |
| 2. + Over/Under bias | 0 | – | – | – | – | – | – |
| 3. Hit rate | 1344 | 54.1 | 51.4 | 56.7 | -6.8 | 1.7 | 57.8 |
| 4. Distribution around the average | 1855 | 52.9 | 50.6 | 55.1 | -7.2 | 1.8 | 56.9 |
| 5. Hit rate + distribution | 1664 | 53.8 | 51.4 | 56.2 | -6.1 | 1.8 | 57.1 |
| 6. + absences | 1689 | 52.9 | 50.5 | 55.2 | -7.9 | 1.8 | 57.1 |
| 7. + implied team total | 1788 | 53.2 | 50.9 | 55.5 | -7.1 | 1.8 | 57.0 |
| 8. + matchup = the full model | 1482 | 53.6 | 51.1 | 56.2 | -6.8 | 1.8 | 57.4 |

## Calibration form: how to fit the Over/Under bias

The full model's chance calibrated four ways, each fitted on the earlier lines of both sources pooled (as the dashboards' calibration is) and scored on each source's later lines. The dashboards use the form in backtest/calibrate.py's FITTED (a and b: no side bias, no offset). A source with few scored nights gets a range from resampling only those nights, which understates how unsure it is.

| scored on | form | log loss | Brier | vs market | range low | range high | coefficients |
|---|---|---|---|---|---|---|---|
| 2022 | Current: shared side bias and offset | 0.6882 | 0.2476 | -0.0012 | -0.0024 | -0.0000 | m +1.171, model +0.140, over -0.109, one +0.055 |
| superbet | Current: shared side bias and offset | 0.6837 | 0.2454 | -0.0006 | -0.0025 | 0.0010 | m +1.171, model +0.140, over -0.109, one +0.055 |
| 2022 | No side bias (offset kept) | 0.6891 | 0.2480 | -0.0003 | -0.0014 | 0.0007 | m +1.190, model +0.182, one -0.000 |
| superbet | No side bias (offset kept) | 0.6841 | 0.2455 | -0.0002 | -0.0012 | 0.0009 | m +1.190, model +0.182, one -0.000 |
| 2022 | No side bias, no offset | 0.6891 | 0.2480 | -0.0003 | -0.0014 | 0.0007 | m +1.190, model +0.182 |
| superbet | No side bias, no offset | 0.6841 | 0.2455 | -0.0002 | -0.0012 | 0.0009 | m +1.190, model +0.182 |
| 2022 | Side bias and offset per bookmaker | 0.6890 | 0.2480 | -0.0004 | -0.0013 | 0.0005 | m +1.172, model +0.149, over -0.003, one +0.002, over_sb -0.164, one_sb +0.082 |
| superbet | Side bias and offset per bookmaker | 0.6838 | 0.2454 | -0.0005 | -0.0029 | 0.0017 | m +1.172, model +0.149, over -0.003, one +0.002, over_sb -0.164, one_sb +0.082 |
