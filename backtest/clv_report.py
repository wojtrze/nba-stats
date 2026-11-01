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
    side stats, Over vs Under, starters vs bench (RotoWire's last lineup before tip-off). Nothing else is split
    for a decision, so no segment wins by chance among many; the per-stat table is descriptive only.
  - game markets (main lines): the model's side of each moneyline, spread and total at its first fetch.

Ranges are 95% from resampling whole nights. Writes data/backtest/clv.md.
"""
import logging
import os
from typing import Optional

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
STARTER, BENCH, UNKNOWN = 'starter', 'bench', 'not listed'


def _row(part: pd.DataFrame) -> dict:
    valid = part[part['clv %'].notna()]
    if valid.empty:
        return {'lines': 0}
    nights = valid['game_date'].values
    moved = 100 * (valid['clv pp'] > 0).astype(float)
    spread = lambda fmt, v: fmt % night_bootstrap(nights, v) if len(set(nights)) > 1 else '–'   # one night: none
    return {'lines': len(valid), 'nights': int(valid['game_date'].nunique()),
            'CLV %': valid['clv %'].mean(), 'CLV % range': spread("%.1f … %.1f", valid['clv %'].values),
            'CLV % after tax': valid['clv % std'].mean(), 'clv pp': valid['clv pp'].mean(),
            'moved toward side %': moved.mean(), 'moved range': spread("%.0f … %.0f", moved.values)}


def table(d: pd.DataFrame, by: pd.Series, name: str) -> pd.DataFrame:
    keys = list(by.cat.categories) if hasattr(by, 'cat') else list(by.dropna().unique())
    return pd.DataFrame([{name: str(k), **_row(d[by == k])} for k in keys] + [{name: 'all', **_row(d)}])


def roles(record: pd.DataFrame, rotowire: pd.DataFrame) -> pd.Series:
    """Each line's player as RotoWire's last lineup before the game's tip-off had him (rotowire with ESPN ids):
    STARTER, BENCH (in a listed game but not a starter, the doubtful included) or UNKNOWN (game not listed)."""
    from nightly import lineups_before_tip
    out = pd.Series(UNKNOWN, index=record.index)
    if rotowire.empty or record.empty:
        return out
    for (night, start), rows in record.groupby(['game_date', 'start_time']):
        lineups = lineups_before_tip(rotowire, night, start)
        if lineups.empty:
            continue
        listed = set(lineups['team'])
        starters = set(lineups.loc[lineups['role'] == 'starter', 'player_id_ESPN'].dropna())
        teams = rows['game'].str.lower().str.split(' @ ')
        in_game = teams.map(lambda t: bool(set(t) & listed))
        out[rows.index] = np.where(~in_game, UNKNOWN, np.where(rows['player_id'].isin(starters), STARTER, BENCH))
    return out


def game_section(snapshots: pd.DataFrame, quotes: pd.DataFrame, reads: pd.DataFrame, games) -> list:
    """The model's side of each main game line (the outcome with the bigger saved edge), at its first fetch."""
    from tracking import closing_games, settle_games
    closing = closing_games(quotes, reads)
    if snapshots.empty or closing.empty or 'edge_pp' not in snapshots:
        return []
    settled = settle_games(snapshots, games, closing=closing)
    settled = settled[settled['main'] & settled['edge_pp'].notna() & settled['clv %'].notna()]
    # one side per market and line: a spread's line is from its side, so home −x and away +x are one pair
    pair = settled['line'].where(~((settled['market'] == 'SPREAD') & (settled['side'] == 'away')),
                                 -settled['line']).fillna(0)
    best = settled.assign(pair=pair).sort_values('edge_pp', ascending=False, kind='stable') \
        .drop_duplicates(['game_date', 'game', 'market', 'pair'])
    if best.empty:
        return []
    return ["## Game markets (main lines, the model's side at its first fetch)", "",
            markdown(table(best, best['market'], 'market')), ""]


def report(snapshots: pd.DataFrame, quotes: pd.DataFrame, reads: pd.DataFrame, logs, games,
           rotowire: Optional[pd.DataFrame] = None, game_snapshots: Optional[pd.DataFrame] = None,
           game_quotes: Optional[pd.DataFrame] = None) -> str:
    from decisions import star_text
    from tracking import CLOSE_MAX_AGE_MIN, _open_and_close, closing_props, settle_props, settle_stars, PROP_KEY
    closing = closing_props(quotes, reads)
    text = ["# Closing line value of the saved lines", "", __doc__.split("\n\n", 2)[2].strip(), ""]
    games_part = game_section(game_snapshots if game_snapshots is not None else pd.DataFrame(),
                              game_quotes if game_quotes is not None else pd.DataFrame(), reads, games)
    if closing.empty:
        return "\n".join(text + ["No line has a close yet: the scheduled fetches haven't read a game near tip-off.",
                                 ""] + games_part)
    record = settle_stars(snapshots, logs, games, closing=closing)
    record = record[record['clv %'].notna()].copy()
    first = _open_and_close(snapshots, PROP_KEY)[0]
    first = first.assign(pick=first['eval_side'].where(first['eval_side'].isin(['Over', 'Under']), first['pick']))
    early = settle_props(snapshots, logs, games, bets=first, closing=closing)
    early = early[early['clv %'].notna()]
    valid = closing.loc[closing['close age min'] <= CLOSE_MAX_AGE_MIN, 'event_id'].nunique()
    text += [f"{valid} games read at most {CLOSE_MAX_AGE_MIN} min before tip-off, {len(record)} lines at their "
             f"last fetch, {len(early)} at their first.", ""]
    if record.empty:
        return "\n".join(text + games_part)
    role = roles(record, rotowire if rotowire is not None else pd.DataFrame())
    text += ["## Per star level (last fetch before tip-off)", "",
             markdown(table(record, record['stars'].map(star_text), 'stars')), "",
             "## When the quote was taken (first fetch of every line)", "",
             markdown(table(early, pd.cut(early['h before tip'], HOURS), 'hours before tip-off')), "",
             "## Fixed segments (last fetch)", "",
             markdown(table(record, record['bet_type'].isin(MAIN_STATS).map({True: 'main stats',
                                                                              False: 'side stats'}), 'stats')), "",
             markdown(table(record, record['pick'], 'side')), "",
             markdown(table(record, role, 'player')), "",
             "## Per stat (descriptive: too many groups to pick a winner from)", "",
             markdown(table(record, record['bet_type'], 'stat')), ""]
    return "\n".join(text + games_part)


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    from espn_scraper import CURRENT_SEASON, SEASONS
    from espn_scraper.storage import load_games, load_player_gamelogs, read_snapshot, snapshot_file
    from models import prepare_logs
    from name_resolver import NameResolver
    read = lambda name: read_snapshot(snapshot_file(CURRENT_SEASON, name)) \
        if os.path.exists(snapshot_file(CURRENT_SEASON, name)) else pd.DataFrame()
    logs = prepare_logs(load_player_gamelogs(sorted(SEASONS)))
    rotowire = read('rotowire_lineups')
    if len(rotowire):
        rotowire = NameResolver(logs).add_ids(rotowire)
    text = report(read('superbet_props'), read('superbet_prop_quotes'), read('superbet_event_fetches'), logs,
                  load_games(sorted(SEASONS)), rotowire=rotowire, game_snapshots=read('superbet_game_odds'),
                  game_quotes=read('superbet_game_quotes'))
    atomic_write_text(REPORT_FILE, text)
    print(f"Written to {REPORT_FILE}")


if __name__ == '__main__':
    main()
