# Admitting an edge threshold (5★)

The 🟢 threshold of backtest/calibrate.py is chosen on the same held-out nights it's judged on, so it doesn't
qualify. Here the two steps get separate nights:

  1. Choose, on the saved Superbet lines of nights up to D: the calibration is fitted there (calibrate.FITTED) and
     the threshold is the smallest candidate edge after tax (edge net pp) whose bets made money after the 12% stake
     tax over at least MIN_CHOOSE_BETS bets and MIN_CHOOSE_NIGHTS nights.
  2. Judge it on the nights after D, which neither step has seen (at least MIN_JUDGED_NIGHTS). The bets are what
     decisions.player_decision would offer: per game, the best line without 🔴 whose edge net pp clears the
     threshold. Admitted when the low end of the after-tax ROI's 95% range is above 0, or the mean after-tax CLV
     is above 0 with its low end above 0 (bets with a valid close, tracking.closing_props).

Ranges are 95% from resampling whole nights. D defaults to the last night that leaves MIN_JUDGED_NIGHTS after it.
The report never sets ADMITTED_THRESHOLD: that's done by hand after reading it. Writes
data/backtest/threshold_admission.md.

Superbet lines: 41977 over 30 nights. Chosen on nights up to Oct 29 2026, judged on the later ones.

**Result: none** (no candidate made money after tax on the nights it was chosen on).

## Choosing (nights up to D)

| edge net pp ≥ | bets | nights | won % | ROI after tax % | ROI low | ROI high |
|---|---|---|---|---|---|---|
| 0 | 0 | 0 | – | – | – | – |
| 1 | 0 | 0 | – | – | – | – |
| 2 | 0 | 0 | – | – | – | – |
| 3 | 0 | 0 | – | – | – | – |
| 5 | 0 | 0 | – | – | – | – |
| 8 | 0 | 0 | – | – | – | – |
