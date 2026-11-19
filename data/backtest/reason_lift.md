# Context reasons against the props model on unseen lines

*vs model* = the log loss with the feature minus without it, per line side (below 0 = the feature helped), with the 95% range from resampling whole nights; *beta* = its weight fitted on the earlier lines (positive = more of it, more Over). See backtest/reason_lift.py.

## Unibet 2022/23

| feature | lines | nights | beta | vs model | range low | range high |
|---|---|---|---|---|---|---|
| hits_l10 | 13763 | 77 | -0.0919 | 0.0000 | -0.0003 | 0.0003 |
| minutes | 13392 | 77 | -0.0535 | -0.0002 | -0.0004 | 0.0000 |
| venue | 13763 | 77 | 0.0331 | -0.0000 | -0.0000 | 0.0000 |
| rest | 13763 | 77 | -0.0229 | 0.0002 | 0.0000 | 0.0005 |
| vs_opp | 7003 | 75 | -0.0111 | 0.0000 | -0.0001 | 0.0001 |
| volume | 8213 | 77 | -0.1573 | 0.0001 | -0.0002 | 0.0004 |

## Superbet 2026/27

| feature | lines | nights | beta | vs model | range low | range high |
|---|---|---|---|---|---|---|
| hits_l10 | 12552 | 9 | 0.1591 | 0.0008 | 0.0001 | 0.0016 |
| minutes | 12328 | 9 | -0.1184 | -0.0004 | -0.0022 | 0.0010 |
| venue | 12428 | 9 | -0.1401 | 0.0005 | -0.0003 | 0.0014 |
| rest | 12552 | 9 | 0.0408 | 0.0004 | 0.0000 | 0.0007 |
| vs_opp | 895 | 6 | 0.1225 | 0.0019 | -0.0034 | 0.0073 |
| volume | 3558 | 9 | -0.0947 | -0.0006 | -0.0009 | -0.0002 |

## Verdicts (what the panel shows)

| feature | status | why |
|---|---|---|
| hits_l10 | no_lift |  |
| minutes | no_lift |  |
| venue | no_lift |  |
| rest | no_lift |  |
| vs_opp | no_lift |  |
| volume | no_lift |  |
| role | untested | needs RotoWire's role as of each line |
| blowout | untested | needs the spread as of each line (2022/23 has no game odds) |
