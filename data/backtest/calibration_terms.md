# Extra calibration terms, held out

Each variant fitted on the fit part and scored on unseen nights (see backtest/calibration_terms.py). Δ = log loss minus the base's (negative is better); ranges are 95% from resampling whole nights. 4★ is approximate and small: read its won − price range, not just the mean.

## Superbet 2026/27

fit 2026-10-20…2026-11-14 (34798 lines), held out 2026-11-15…2026-11-25 (15686 lines); market log loss 0.6847

| variant | coefficients | held-out log loss | Δ vs base | Δ low | Δ high | 4★ lines | 4★ won % | 4★ price % | 4★ won − price | won − price low | won − price high | 4★ after tax % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| base a,b | a=+1.223 b=+0.206 | 0.6843 | 0 | 0 | 0 | 81 | 65.43 | 58.34 | 7.088 | -1.583 | 16.07 | -9.088 |
| +over | a=+1.200 b=+0.156 over=-0.080 | 0.6847 | 0.0004 | -0.0004 | 0.0013 | 81 | 69.14 | 57.93 | 11.21 | 4.959 | 17.57 | -3.852 |
| +small | a=+1.225 b=+0.196 small=-0.060 | 0.6842 | -0.0001 | -0.0004 | 0.0002 | 82 | 64.63 | 59.33 | 5.304 | -1.739 | 12.94 | -12.34 |
| +over+small | a=+1.198 b=+0.157 over=-0.086 small=+0.024 | 0.6848 | 0.0005 | -0.0003 | 0.0014 | 81 | 64.2 | 55.89 | 8.31 | 0.6232 | 17.17 | -6.926 |
| +b_main | a=+1.220 b=+0.269 b_main=-0.216 | 0.6843 | -0 | -0.0002 | 0.0001 | 81 | 59.26 | 56.78 | 2.48 | -4.224 | 9.653 | -15.56 |
| +all | a=+1.193 b=+0.225 over=-0.087 small=+0.030 b_main=-0.233 | 0.6848 | 0.0005 | -0.0004 | 0.0014 | 82 | 60.98 | 55.69 | 5.285 | -3.788 | 13.75 | -11.3 |

## Unibet 2022/23

fit 2022-11-09…2023-01-31 (15568 lines), held out 2023-02-01…2023-05-08 (13763 lines); market log loss 0.6895

| variant | coefficients | held-out log loss | Δ vs base | Δ low | Δ high | 4★ lines | 4★ won % | 4★ price % | 4★ won − price | won − price low | won − price high | 4★ after tax % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| base a,b | a=+1.130 b=+0.072 | 0.6893 | 0 | 0 | 0 | 269 | 59.48 | 55.9 | 3.579 | -1.569 | 8.681 | -12.24 |
| +over | a=+1.121 b=+0.057 over=-0.016 | 0.6889 | -0.0003 | -0.0005 | -0.0002 | 277 | 60.29 | 56.61 | 3.68 | -1.932 | 8.831 | -11.85 |
| +small | a=+1.128 b=+0.076 small=+0.082 | 0.6896 | 0.0003 | 0.0002 | 0.0005 | 303 | 48.84 | 55.47 | -6.627 | -11.16 | -2.167 | -27.62 |
| +over+small | a=+1.112 b=+0.053 over=-0.025 small=+0.106 | 0.6892 | -0.0001 | -0.0004 | 0.0001 | 307 | 50.49 | 56.03 | -5.541 | -10.33 | -0.6959 | -25.54 |
| +b_main | a=+1.127 b=+0.196 b_main=-0.235 | 0.6894 | 0.0002 | -0.0001 | 0.0005 | 302 | 54.64 | 51.54 | 3.092 | -1.984 | 8.325 | -12.41 |
| +all | a=+1.106 b=+0.187 over=-0.029 small=+0.117 b_main=-0.259 | 0.6894 | 0.0001 | -0.0004 | 0.0006 | 292 | 51.71 | 51 | 0.7114 | -4.792 | 5.987 | -14.99 |

## Verdict (Superbet held-out nights)

| variant | (a) log loss | (b) 4★ won − price | adopt |
|---|---|---|---|
| +over | fail | pass | no |
| +small | fail | fail | no |
| +over+small | fail | pass | no |
| +b_main | fail | fail | no |
| +all | fail | fail | no |

The live calibration is changed by hand only (calibrate.FITTED and features), never by this report.
