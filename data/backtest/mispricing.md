# Mispricing hypotheses: evaluation

Uses the app's own detectors (dashboard/mispricing.py) on every Superbet offer saved before tip-off. A game read
by the schedule (superbet_event_fetches) is rebuilt from superbet_prop_quotes, which hold only changes: at every
read, each line is its last quote so far. Older games come from the dashboard's superbet_props snapshots. The
detectors see only the player's games before that night and league numbers from the games before it; H5 sees
RotoWire's lineup as it was saved before each read (rotowire_lineups).

  a. Does the signal pay (decides the verdict): a signal is a side whose chance clears its after-tax break-even,
     counted once per game, player, bet and side, at its first read where it could be taken (the next read still
     had the same line and odds not worse; a signal at a game's last read can't be checked and isn't counted).
     Measured by the after-tax CLV (tracking.add_clv, valid closes only) and the after-tax ROI settled with ESPN.
  b. Does the mechanism work (descriptive): at each line's last quote before tip-off, by how much the signal's
     side won more often than its margin-free price, beyond the tilt of the same stat and side on every line
     offered in the same period (market_tilt), for a gap of at least MECHANISM_GAP_PP. H1b instead asks whether the combo's price moved
     toward its parts by the close in more than half of the cases (gap ≥ H1B_GAP_PP).

Verdicts follow the registry's rules on the nights after D (at least MIN_NIGHTS): admitted when the low end of the
99% range (nine hypotheses) of the CLV or ROI is above 0 with at least MIN_SIGNALS signals; rejected when a high
end is below 0, or the mean is ≤ 0 after REJECT_SIGNALS signals; no signals below one per NIGHTS_PER_SIGNAL nights;
otherwise wait. Ranges come from resampling whole nights. The nights up to D are shown for comparison with the
registry's exploration and never decide. The report never sets data/backtest/mispricing_status.json: that's done
by hand after reading it. Writes data/backtest/mispricing.md.

## Evaluation (nights after 2026-11-01): decides

### a. Does the signal pay (after tax)

| hypothesis | nights | signals | not takeable | unchecked | settled | won % | ROI after tax % | ROI low | ROI high | with a close | CLV after tax % | CLV low | CLV high | verdict | why |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| H1 | 0 | 0 | 0 | 0 | 0 | – | – | – | – | 0 | – | – | – | wait | 0 of the 10 nights a verdict needs |
| H2 | 0 | 0 | 0 | 0 | 0 | – | – | – | – | 0 | – | – | – | wait | 0 of the 10 nights a verdict needs |
| H5 | 0 | 0 | 0 | 0 | 0 | – | – | – | – | 0 | – | – | – | wait | 0 of the 10 nights a verdict needs |
| H6 | 0 | 0 | 0 | 0 | 0 | – | – | – | – | 0 | – | – | – | wait | 0 of the 10 nights a verdict needs |

### b. Does the mechanism work (last quote, settled)

| hypothesis | lines | gap ≥ 4 pp | nights | won % | price % | won − price pp | low | high | beyond the tilt pp | beyond low | beyond high |
|---|---|---|---|---|---|---|---|---|---|---|---|
| H2 | 0 | 0 | 0 | – | – | – | – | – | – | – | – |
| H5 | 0 | 0 | 0 | – | – | – | – | – | – | – | – |
| H6 | 0 | 0 | 0 | – | – | – | – | – | – | – | – |

Under's wins minus its price on all lines, pp: H2 {}; H5 {}; H6 {}

### H1b: did the combo's price move toward its parts by the close

| gap ≥ 3 pp | moved | toward the parts % | low | high | mean signed gap pp (all lines) |
|---|---|---|---|---|---|
| 0 | 0 | – | – | – | – |

## Exploration (nights up to 2026-11-01): for comparison only

### a. Does the signal pay (after tax)

| hypothesis | nights | signals | not takeable | unchecked | settled | won % | ROI after tax % | ROI low | ROI high | with a close | CLV after tax % | CLV low | CLV high | verdict | why |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| H1 | 13 | 0 | 0 | 0 | 0 | – | – | – | – | 0 | – | – | – | no signals | 0 signals on 13 nights: fewer than one per 5 nights |
| H2 | 13 | 97 | 26 | 57 | 94 | 48.9 | -20.1 | -40.4 | -1.3 | 0 | – | – | – | rejected | the high end of the 99% range of the ROI is below 0 |
| H5 | 13 | 462 | 27 | 436 | 462 | 50.0 | -18.5 | -40.7 | 4.8 | 0 | – | – | – | rejected | the mean ROI is ≤ 0 after 462 signals |
| H6 | 13 | 2 | 0 | 4 | 2 | 50.0 | 10.0 | -100.0 | 120.0 | 0 | – | – | – | no signals | 2 signals on 13 nights: fewer than one per 5 nights |

### b. Does the mechanism work (last quote, settled)

| hypothesis | lines | gap ≥ 4 pp | nights | won % | price % | won − price pp | low | high | beyond the tilt pp | beyond low | beyond high |
|---|---|---|---|---|---|---|---|---|---|---|---|
| H2 | 3306 | 1286 | 13 | 53.5 | 51.0 | 2.5 | -1.2 | 5.5 | 2.2 | -1.3 | 5.1 |
| H5 | 1265 | 1215 | 12 | 46.3 | 50.1 | -3.8 | -11.8 | 1.0 | -3.6 | -10.9 | 2.2 |
| H6 | 2010 | 131 | 13 | 48.9 | 44.4 | 4.4 | -1.9 | 10.4 | 3.4 | -2.5 | 9.0 |

Under's wins minus its price on all lines, pp: H2 {'3PM': 2.7, 'FGM': 2.1, 'FTM': 3.6}; H5 {'3PA': -1.5, '3PM': 2.7, 'ARP': 3.5, 'AST': 4.2, 'BLK': 5.6, 'FGA': 0.6, 'FGM': 2.1, 'FTA': 2.9, 'FTM': 3.6, 'PA': 3.9, 'PF': 0.8, 'PR': 1.9, 'PTS': 2.3, 'RA': 2.2, 'REB': 0.7, 'STL': -0.3, 'TO': -1.4}; H6 {'3PM': 2.7, 'BLK': 5.6, 'PF': 0.8, 'STL': -0.3, 'TO': -1.4}

### H1b: did the combo's price move toward its parts by the close

| gap ≥ 3 pp | moved | toward the parts % | low | high | mean signed gap pp (all lines) |
|---|---|---|---|---|---|
| 72 | 64 | 67.2 | 45.5 | 83.9 | 0.3 |
