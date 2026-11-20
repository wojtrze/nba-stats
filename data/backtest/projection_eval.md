# Projection accuracy: candidate proj avg against the results (exploratory)

Minutes: EWMA half-life 5 games in tonight's role, this season's games from the player's 3rd of it; rate: this season's, with last season's worth 5 games. *vs* = the candidate's MAE minus the reference's (below 0 = closer to the results), with the 95% range from resampling whole nights. Several candidates are tried on the same games, so treat a small gain as noise.

## A. Stored seasons' logs (2024-11-09 – 2026-11-18, 438 nights); reference: season mean

| stat | candidate | lines | MAE | bias | vs | low | high |
|---|---|---|---|---|---|---|---|
| PTS | season mean | 54770 | 4.779 | 0.190 | 0.000 | – | – |
| PTS | minutes (all games) × rate | 54770 | 4.661 | 0.085 | -0.117 | -0.132 | -0.104 |
| PTS | core: minutes in role × rate | 54770 | 4.597 | 0.085 | -0.181 | -0.199 | -0.165 |
| REB | season mean | 54770 | 1.952 | 0.047 | 0.000 | – | – |
| REB | minutes (all games) × rate | 54770 | 1.913 | -0.012 | -0.040 | -0.045 | -0.035 |
| REB | core: minutes in role × rate | 54770 | 1.890 | -0.012 | -0.062 | -0.069 | -0.056 |
| AST | season mean | 54770 | 1.382 | 0.054 | 0.000 | – | – |
| AST | minutes (all games) × rate | 54770 | 1.356 | 0.027 | -0.025 | -0.029 | -0.022 |
| AST | core: minutes in role × rate | 54770 | 1.342 | 0.027 | -0.040 | -0.044 | -0.036 |
| 3PM | season mean | 54770 | 0.910 | 0.020 | 0.000 | – | – |
| 3PM | minutes (all games) × rate | 54770 | 0.901 | 0.007 | -0.010 | -0.011 | -0.008 |
| 3PM | core: minutes in role × rate | 54770 | 0.895 | 0.007 | -0.015 | -0.017 | -0.013 |
| ARP | season mean | 54770 | 6.351 | 0.291 | 0.000 | – | – |
| ARP | minutes (all games) × rate | 54770 | 6.139 | 0.100 | -0.212 | -0.234 | -0.192 |
| ARP | core: minutes in role × rate | 54770 | 6.011 | 0.100 | -0.340 | -0.368 | -0.313 |
| all | season mean | 273850 | 3.075 | 0.121 | 0.000 | – | – |
| all | minutes (all games) × rate | 273850 | 2.994 | 0.041 | -0.081 | -0.089 | -0.073 |
| all | core: minutes in role × rate | 273850 | 2.947 | 0.041 | -0.128 | -0.138 | -0.118 |

## B. Superbet lines (2026-10-20 – 2026-11-18, 29 nights); reference: the current proj avg

*closer %* = closer to the result than the line; *within 10%*: as the Overview's Spot on counts it; *corr* = correlation of (projection − line) with (result − line).

| stat | candidate | lines | MAE | bias | vs | low | high | closer % | within 10% % | corr |
|---|---|---|---|---|---|---|---|---|---|---|
| PTS | current proj avg | 2849 | 5.233 | -0.364 | 0.000 | – | – | 45.349 | 18.147 | -0.006 |
| PTS | core, no absence change | 2849 | 5.247 | -0.342 | 0.014 | -0.003 | 0.030 | 45.033 | 18.041 | -0.018 |
| PTS | core + the full absence change | 2849 | 5.251 | -0.421 | 0.018 | 0.001 | 0.038 | 45.595 | 17.726 | -0.001 |
| PTS | current × pace | 2849 | 5.233 | -0.376 | 0.000 | -0.015 | 0.017 | 45.560 | 18.112 | 0.001 |
| PTS | current × pace × matchup | 2849 | 5.285 | -0.363 | 0.052 | 0.020 | 0.087 | 45.455 | 17.515 | -0.018 |
| PTS | current, actual starter flag (oracle) | 2849 | 5.230 | -0.377 | -0.003 | -0.024 | 0.022 | 45.349 | 18.147 | -0.001 |
| PTS | Superbet's line | 2849 | 5.002 | 0.104 | – | – | – | – | 18.814 | – |
| REB | current proj avg | 2674 | 2.075 | -0.122 | 0.000 | – | – | 50.561 | 30.965 | 0.042 |
| REB | core, no absence change | 2674 | 2.075 | -0.113 | 0.001 | -0.004 | 0.006 | 50.224 | 31.301 | 0.035 |
| REB | core + the full absence change | 2674 | 2.085 | -0.143 | 0.010 | 0.004 | 0.017 | 49.888 | 31.002 | 0.038 |
| REB | current × pace | 2674 | 2.076 | -0.125 | 0.001 | -0.006 | 0.007 | 50.112 | 30.479 | 0.049 |
| REB | current × pace × matchup | 2674 | 2.078 | -0.100 | 0.003 | -0.013 | 0.017 | 49.102 | 30.217 | 0.062 |
| REB | current, actual starter flag (oracle) | 2674 | 2.077 | -0.129 | 0.002 | -0.007 | 0.011 | 50.262 | 31.040 | 0.034 |
| REB | Superbet's line | 2674 | 2.029 | 0.049 | – | – | – | – | 32.162 | – |
| AST | current proj avg | 2096 | 1.701 | -0.064 | 0.000 | – | – | 50.143 | 37.166 | 0.059 |
| AST | core, no absence change | 2096 | 1.694 | -0.053 | -0.007 | -0.014 | 0.000 | 50.668 | 37.405 | 0.063 |
| AST | core + the full absence change | 2096 | 1.713 | -0.084 | 0.012 | 0.005 | 0.021 | 49.332 | 36.737 | 0.053 |
| AST | current × pace | 2096 | 1.700 | -0.066 | -0.001 | -0.004 | 0.003 | 49.952 | 37.166 | 0.067 |
| AST | current × pace × matchup | 2096 | 1.712 | -0.056 | 0.011 | -0.000 | 0.023 | 50.239 | 36.307 | 0.064 |
| AST | current, actual starter flag (oracle) | 2096 | 1.695 | -0.066 | -0.005 | -0.010 | -0.001 | 50.334 | 37.548 | 0.067 |
| AST | Superbet's line | 2096 | 1.667 | 0.103 | – | – | – | – | 38.454 | – |
| 3PM | current proj avg | 2229 | 1.167 | 0.007 | 0.000 | – | – | 54.195 | 49.933 | 0.119 |
| 3PM | core, no absence change | 2229 | 1.167 | 0.007 | 0.000 | -0.003 | 0.004 | 54.015 | 49.798 | 0.118 |
| 3PM | core + the full absence change | 2229 | 1.170 | -0.000 | 0.003 | -0.001 | 0.007 | 53.701 | 49.619 | 0.117 |
| 3PM | current × pace | 2229 | 1.167 | 0.005 | 0.001 | -0.002 | 0.003 | 54.598 | 49.574 | 0.120 |
| 3PM | current × pace × matchup | 2229 | 1.174 | 0.012 | 0.007 | 0.002 | 0.013 | 53.567 | 49.305 | 0.108 |
| 3PM | current, actual starter flag (oracle) | 2229 | 1.166 | 0.005 | -0.001 | -0.004 | 0.001 | 54.105 | 49.978 | 0.124 |
| 3PM | Superbet's line | 2229 | 1.178 | 0.112 | – | – | – | – | 52.445 | – |
| ARP | current proj avg | 2020 | 6.952 | -0.585 | 0.000 | – | – | 43.416 | 22.921 | -0.021 |
| ARP | core, no absence change | 2020 | 6.964 | -0.535 | 0.012 | -0.015 | 0.041 | 42.376 | 23.218 | -0.034 |
| ARP | core + the full absence change | 2020 | 6.977 | -0.695 | 0.025 | -0.006 | 0.063 | 42.277 | 22.376 | -0.015 |
| ARP | current × pace | 2020 | 6.957 | -0.619 | 0.005 | -0.026 | 0.038 | 43.218 | 22.970 | -0.012 |
| ARP | current × pace × matchup | 2020 | 7.077 | -0.594 | 0.125 | 0.056 | 0.201 | 42.475 | 21.881 | -0.032 |
| ARP | current, actual starter flag (oracle) | 2020 | 6.931 | -0.585 | -0.021 | -0.054 | 0.012 | 43.317 | 22.871 | -0.010 |
| ARP | Superbet's line | 2020 | 6.551 | -0.182 | – | – | – | – | 24.208 | – |
| all | current proj avg | 11868 | 3.427 | -0.224 | 0.000 | – | – | 48.702 | 31.176 | – |
| all | core, no absence change | 11868 | 3.431 | -0.207 | 0.004 | -0.004 | 0.014 | 48.433 | 31.294 | – |
| all | core + the full absence change | 11868 | 3.440 | -0.266 | 0.014 | 0.003 | 0.027 | 48.180 | 30.856 | – |
| all | current × pace | 11868 | 3.428 | -0.234 | 0.001 | -0.009 | 0.012 | 48.660 | 30.999 | – |
| all | current × pace × matchup | 11868 | 3.464 | -0.219 | 0.038 | 0.016 | 0.061 | 48.138 | 30.410 | – |
| all | current, actual starter flag (oracle) | 11868 | 3.421 | -0.230 | -0.005 | -0.016 | 0.005 | 48.635 | 31.261 | – |
| all | Superbet's line | 11868 | 3.289 | 0.044 | – | – | – | – | 32.524 | – |
