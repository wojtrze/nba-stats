# Mispricing hypotheses: evaluation

Uses the app's own detectors (dashboard/mispricing.py) on every Superbet offer saved before tip-off. A game read
by the schedule (superbet_event_fetches) is rebuilt from superbet_prop_quotes, which hold only changes: at every
read, each line is its last quote so far. Older games come from the dashboard's superbet_props snapshots. The
detectors see only the player's games before that night and league numbers from the games before it.

  a. Does the signal pay (decides the verdict): a signal is a side whose chance clears its after-tax break-even,
     counted once per game, player, bet and side, at its first read where it could be taken (the next read still
     had the same line and odds not worse; a signal at a game's last read can't be checked and isn't counted).
     Measured by the after-tax CLV (tracking.add_clv, valid closes only) and the after-tax ROI settled with ESPN.
  b. Does the mechanism work (descriptive): at each line's last quote before tip-off, by how much the signal's
     side won more often than its margin-free price, beyond the tilt of the same stat and side on all of the
     hypothesis's lines, for a gap of at least MECHANISM_GAP_PP. H1b instead asks whether the combo's price moved
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
| H6 | 0 | 0 | 0 | 0 | 0 | – | – | – | – | 0 | – | – | – | wait | 0 of the 10 nights a verdict needs |

### b. Does the mechanism work (last quote, settled)

| hypothesis | lines | gap ≥ 4 pp | nights | won % | price % | won − price pp | low | high | beyond the tilt pp | beyond low | beyond high |
|---|---|---|---|---|---|---|---|---|---|---|---|
| H2 | 0 | 0 | 0 | – | – | – | – | – | – | – | – |
| H6 | 0 | 0 | 0 | – | – | – | – | – | – | – | – |

Under's wins minus its price on all lines, pp: H2 {}; H6 {}

### H1b: did the combo's price move toward its parts by the close

| gap ≥ 3 pp | moved | toward the parts % | low | high | mean signed gap pp (all lines) |
|---|---|---|---|---|---|
| 0 | 0 | – | – | – | – |

## Exploration (nights up to 2026-11-01): for comparison only

### a. Does the signal pay (after tax)

| hypothesis | nights | signals | not takeable | unchecked | settled | won % | ROI after tax % | ROI low | ROI high | with a close | CLV after tax % | CLV low | CLV high | verdict | why |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| H1 | 12 | 0 | 0 | 0 | 0 | – | – | – | – | 0 | – | – | – | no signals | 0 signals on 12 nights: fewer than one per 5 nights |
| H2 | 12 | 94 | 26 | 56 | 92 | 50.0 | -18.3 | -36.7 | 1.9 | 0 | – | – | – | wait | neither range is clear of 0 yet |
| H6 | 12 | 2 | 0 | 4 | 2 | 50.0 | 10.0 | -100.0 | 120.0 | 0 | – | – | – | no signals | 2 signals on 12 nights: fewer than one per 5 nights |

### b. Does the mechanism work (last quote, settled)

| hypothesis | lines | gap ≥ 4 pp | nights | won % | price % | won − price pp | low | high | beyond the tilt pp | beyond low | beyond high |
|---|---|---|---|---|---|---|---|---|---|---|---|
| H2 | 3169 | 1236 | 12 | 53.8 | 51.0 | 2.8 | -0.9 | 5.5 | 2.5 | -1.0 | 4.9 |
| H6 | 1922 | 124 | 12 | 50.0 | 44.5 | 5.5 | -0.1 | 11.5 | 5.5 | 0.6 | 11.3 |

Under's wins minus its price on all lines, pp: H2 {'3PM': 3.0, 'FGM': 2.6, 'FTM': 4.1}; H6 {'3PM': 1.4, 'BLK': 12.6, 'PF': -2.4, 'STL': -1.8, 'TO': -2.3}

### H1b: did the combo's price move toward its parts by the close

| gap ≥ 3 pp | moved | toward the parts % | low | high | mean signed gap pp (all lines) |
|---|---|---|---|---|---|
| 61 | 54 | 68.5 | 44.0 | 85.5 | 0.3 |
