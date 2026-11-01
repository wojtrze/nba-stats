"""Does anything we rate beat the closing price? CLV of the saved lines, from the scheduled fetches' closes.

    python -m backtest.clv_report

The way to an edge after Superbet's 12% stake tax (docs/system_oceny_zakladow.md) is a price better than the
market's final one. fetch_loop reads every game 60, 40, 20, 10 and 5 minutes before tip-off, so each line has a
close (tracking.closing_props: valid when the game was read at most 10 minutes before tip-off). This report takes
every line as the record judges it (tracking.star_lines: its last fetch before tip-off with a price, at its saved
stars) and the first fetch of every line (the earliest price one could have taken), and asks:

  - CLV % per star level: the expected return at the closing margin-free price (above 0 = the side beat the close);
    after tax it has to clear 0 too, which takes a big move.
  - model_vs_move: how often the market moved toward the side the model rated (clv pp > 0). 50% = the model
    doesn't foresee moves; clearly more = betting early on its side gets better prices than the close.
  - the same by when the quote was taken (hours before tip-off) and for the segments fixed in advance: main vs
    side stats, Over vs Under. Nothing else is split, so no segment wins by chance among many.

Ranges are 95% from resampling whole nights. Writes data/backtest/clv.md.
"""
import logging
import os

import numpy as np
import pandas as pd

import backtest  # noqa: F401  (puts dashboard/ on the path)
from backtest.ablation import night_bootstrap
from backtest.run import OUT_DIR, markdown
from safe_io import atomic_write_text

log = logging.getLogger(__name__)

REPORT_FILE = os.path.join(OUT_DIR, 'clv.md')
MAIN_STATS = {'PTS', 'REB', 'AST', '3PM', 'PA', 'PR', 'RA', 'ARP'}
HOURS = [0, 1, 3, 6, 12, 48]


def _row(part: pd.DataFrame) -> dict:
    valid = part[part['clv %'].notna()]
    if valid.empty:
        return {'lines': 0}
    nights = valid['game_date'].values
    moved = 100 * (valid['clv pp'] > 0).astype(float)
    return {'lines': len(valid), 'nights': int(valid['game_date'].nunique()),
            'CLV %': valid['clv %'].mean(), 'CLV % range': "%.1f … %.1f" % night_bootstrap(nights, valid['clv %'].values),
            'CLV % after tax': valid['clv % std'].mean(), 'clv pp': valid['clv pp'].mean(),
            'moved toward side %': moved.mean(),
            'moved range': "%.0f … %.0f" % night_bootstrap(nights, moved.values)}


def table(d: pd.DataFrame, by: pd.Series, name: str) -> pd.DataFrame:
    keys = list(by.cat.categories) if hasattr(by, 'cat') else list(by.dropna().unique())
    return pd.DataFrame([{name: str(k), **_row(d[by == k])} for k in keys] + [{name: 'all', **_row(d)}])


def report(snapshots: pd.DataFrame, quotes: pd.DataFrame, reads: pd.DataFrame, logs, games) -> str:
    from decisions import star_text
    from tracking import _open_and_close, closing_props, settle_props, settle_stars, PROP_KEY
    closing = closing_props(quotes, reads)
    text = ["# Closing line value of the saved lines", "", __doc__.split("\n\n", 2)[2].strip(), ""]
    if closing.empty:
        return "\n".join(text + ["No line has a close yet: the scheduled fetches haven't read a game near tip-off."])
    record = settle_stars(snapshots, logs, games, closing=closing)
    record = record[record['clv %'].notna()].copy()
    first = _open_and_close(snapshots, PROP_KEY)[0]
    first = first.assign(pick=first['eval_side'].where(first['eval_side'].isin(['Over', 'Under']), first['pick']))
    early = settle_props(snapshots, logs, games, bets=first, closing=closing)
    early = early[early['clv %'].notna()]
    text += [f"{closing['event_id'].nunique()} games with a close, {len(record)} lines at their last fetch, "
             f"{len(early)} at their first.", ""]
    if record.empty:
        return "\n".join(text)
    text += ["## Per star level (last fetch before tip-off)", "",
             markdown(table(record, record['stars'].map(star_text), 'stars')), "",
             "## When the quote was taken (first fetch of every line)", "",
             markdown(table(early, pd.cut(early['h before tip'], HOURS), 'hours before tip-off')), "",
             "## Fixed segments (last fetch)", "",
             markdown(table(record, record['bet_type'].isin(MAIN_STATS).map({True: 'main stats',
                                                                              False: 'side stats'}), 'stats')), "",
             markdown(table(record, record['pick'], 'side')), ""]
    return "\n".join(text)


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    from espn_scraper import CURRENT_SEASON, SEASONS
    from espn_scraper.storage import load_games, load_player_gamelogs, read_snapshot, snapshot_file
    from models import prepare_logs
    read = lambda name: read_snapshot(snapshot_file(CURRENT_SEASON, name)) \
        if os.path.exists(snapshot_file(CURRENT_SEASON, name)) else pd.DataFrame()
    text = report(read('superbet_props'), read('superbet_prop_quotes'), read('superbet_event_fetches'),
                  prepare_logs(load_player_gamelogs(sorted(SEASONS))), load_games(sorted(SEASONS)))
    atomic_write_text(REPORT_FILE, text)
    print(f"Written to {REPORT_FILE}")


if __name__ == '__main__':
    main()
