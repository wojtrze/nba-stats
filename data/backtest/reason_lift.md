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
| hits_l10 | 5147 | 4 | 0.2512 | -0.0022 | -0.0053 | -0.0001 |
| minutes | 3102 | 4 | -0.3470 | -0.0001 | -0.0120 | 0.0126 |
| venue | 4065 | 4 | -0.2709 | 0.0002 | -0.0013 | 0.0028 |
| rest | 5147 | 4 | 0.0566 | -0.0000 | -0.0006 | 0.0005 |
| vs_opp | 412 | 1 | 0.5487 | 0.0228 | – | – |
| volume | 891 | 0 | – | – | – | – |

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
