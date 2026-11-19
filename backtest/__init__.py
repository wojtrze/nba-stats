"""Backtests of the dashboard's models on historical lines. Run from the repository root:

    python -m backtest.run
"""
import os
import sys

# the dashboard's model modules (models, metrics, tracking) live in dashboard/, as for daily_snapshot.py
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'dashboard'))

# the reports print ★, ≥ and Polish letters: a Windows console (cp1250) can't encode ★ and the script died after
# writing its file. Print UTF-8 instead, replacing what the console can't show (pytest's captured streams can't
# be reconfigured, so they're left as they are).
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding='utf-8', errors='replace')
    except (AttributeError, ValueError):
        pass
