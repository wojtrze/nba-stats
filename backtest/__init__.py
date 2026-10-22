"""Backtests of the dashboard's models on historical lines. Run from the repository root:

    python -m backtest.run
"""
import os
import sys

# the dashboard's model modules (models, metrics, tracking) live in dashboard/, as for daily_snapshot.py
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'dashboard'))
