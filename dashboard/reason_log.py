"""The reasons behind every evaluated offer, saved with the snapshot that priced it, so they can be measured later
(audit package E: preparing the measurement, not tuning anything).

One record per priced line's evaluated side and snapshot: the exact offer (event, player, stat, line, side, odds),
the cost profile, the versions (code, model, calibration, reason definitions, hypothesis statuses, reason_lift),
the estimate, the game's decision with its causes and notes and what it means for this line, the data times, every
reason as data (its i18n key, kind, group, direction, value, reference, n, as_of, source, the model impact, the
validation and, for a hypothesis about another offer, which offer it's about) and the hypothesis signals. No text:
the key and the numbers are what is measured; the words change with the templates.

origin says how the record came to be:
  recorded        written by the snapshot itself, from the very objects it priced and decided with
  reconstructed   rebuilt later from the saved fetch, with the same model version and calibration it was priced with
  counterfactual  rebuilt with another model version or calibration than the one that priced it
A record is never replaced: a later reconstruction is written beside the recorded one, never over it (the key
includes the origin), and writing the same snapshot again adds nothing (write() is idempotent).

The calibration, the hypothesis statuses and reason_lift.json behind a record are archived whole in
data/archive/<kind>/<id>.json the first time a record uses them: their files are overwritten by every refit, and
an id alone wouldn't say what was used.

Computing a record (offer_records) never writes; only write() does, called from daily_snapshot (never from a page:
Streamlit's reruns would log the same view again and again).

    data/<season>/reason_log/<fetched_at>.jsonl.gz    one gzipped JSON line per record
"""
import gzip
import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional

import numpy as np
import pandas as pd

SCHEMA_VERSION = 1
# bump when what a reason means changes (not its wording: the texts' fingerprint follows that)
REASONS_VERSION = 1
RECORDED, RECONSTRUCTED, COUNTERFACTUAL = 'recorded', 'reconstructed', 'counterfactual'
ORIGINS = (RECORDED, RECONSTRUCTED, COUNTERFACTUAL)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# the i18n keys whose wording the reasons and decisions use (their fingerprint is saved with every record)
TEXT_PREFIXES = ('reason.', 'warn.', 'flag.', 'mispricing.', 'decision.', 'game.', 'gameflag.', 'panel.validation.')
# what each record keeps of a reason (no text)
REASON_FIELDS = ('key', 'kind', 'group', 'supports', 'flag', 'used_by_model', 'impact_pp', 'validation', 'verified',
                 'feature', 'value', 'reference', 'n', 'as_of', 'source', 'about', 'this_offer')
SIGNAL_FIELDS = ('hypothesis', 'mechanism', 'status', 'bet_type', 'line', 'side', 'odds', 'p_ours', 'p_book',
                 'gap_pp', 'needed_pp', 'clears', 'n', 'as_of', 'profile')


def log_dir(season: Optional[int] = None) -> str:
    from espn_scraper import CURRENT_SEASON
    from espn_scraper.storage import snapshot_file
    return os.path.join(os.path.dirname(snapshot_file(season or CURRENT_SEASON, 'x')), 'reason_log')


ARCHIVE_DIR = os.path.join('data', 'archive')


def log_path(fetched_at: str, directory: Optional[str] = None) -> str:
    stamp = pd.Timestamp(fetched_at).strftime('%Y%m%dT%H%M%SZ')
    return os.path.join(directory or log_dir(), f"{stamp}.jsonl.gz")


# --- versions ---

def code_version(root: str = ROOT) -> Dict:
    """The git commit the code runs from and whether its Python files differ from it (dirty); None when git
    can't say."""
    def git(*args) -> Optional[str]:
        try:
            done = subprocess.run(['git', *args], cwd=root, capture_output=True, text=True, timeout=10)
            return done.stdout.strip() if done.returncode == 0 else None
        except (OSError, subprocess.SubprocessError):
            return None
    commit = git('rev-parse', 'HEAD')
    changed = git('status', '--porcelain', '--untracked-files=no', '--', '*.py')
    return {'commit': commit, 'dirty': None if changed is None else bool(changed)}


def fingerprint(obj) -> str:
    """A short id of a JSON-able object's content."""
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:10]


def texts_fingerprint() -> str:
    """The wording of every reason, decision and validation template (both languages)."""
    import i18n
    return fingerprint({k: v for k, v in i18n.TEXTS.items() if k.startswith(TEXT_PREFIXES)})


def _read_json(path: str) -> Optional[Dict]:
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def artefacts() -> Dict[str, Dict]:
    """What the evaluation rests on besides the code, read now (at evaluation time): {'calibration' (with its
    🟢 threshold, i.e. the admission of recommendations), 'mispricing_status' (the hypotheses' admission),
    'reason_lift' (the context's test): {'id', 'content'}}. content None when the file is missing."""
    from mispricing import STATUS_FILE
    from models import CALIBRATION_FILE, calibration_id
    from reasons import LIFT_FILE
    # the calibration as models reads it (relative to the working directory, like the pricing that used it)
    calibration = _read_json(CALIBRATION_FILE)
    status, lift = _read_json(STATUS_FILE), _read_json(LIFT_FILE)
    return {'calibration': {'id': calibration_id(), 'content': calibration},
            'mispricing_status': {'id': fingerprint(status) if status else 'none', 'content': status},
            'reason_lift': {'id': fingerprint(lift) if lift else 'none', 'content': lift}}


def versions(arts: Dict[str, Dict], code: Optional[Dict] = None) -> Dict:
    """The versions saved with every record of one evaluation."""
    from models import MODEL_VERSION, calibration_status
    from reasons import lift_check
    code = code_version() if code is None else code
    lift = arts['reason_lift']['content']
    calibration = arts['calibration']['content'] or {}
    return {'schema': SCHEMA_VERSION, 'code': code.get('commit'), 'code_dirty': code.get('dirty'),
            'model': MODEL_VERSION, 'calibration': arts['calibration']['id'],
            'calibration_model': calibration.get('model_version'),
            'calibration_status': calibration_status(),
            'green_edge_pp': calibration.get('green_edge_pp'),
            'reasons': REASONS_VERSION, 'texts': texts_fingerprint(),
            'mispricing_status': arts['mispricing_status']['id'], 'reason_lift': arts['reason_lift']['id'],
            'reason_lift_problems': lift_check(lift) if lift else ['missing']}


def origin_for(priced_with: Dict, now: Dict) -> str:
    """RECONSTRUCTED when a rebuild uses the model version and calibration the saved line was priced with
    (nightly.LINEAGE_COLUMNS: model_version, calibration_id), COUNTERFACTUAL otherwise."""
    same = priced_with.get('model_version') == now.get('model') and priced_with.get('calibration_id') == now.get(
        'calibration')
    return RECONSTRUCTED if same else COUNTERFACTUAL


# --- records (computing only: nothing here writes) ---

def _plain(value):
    """value as JSON: numbers as float (6 significant digits) / int, times as ISO text, NaN as None; lists and dicts
    recursively."""
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    if value is None or value is pd.NaT:
        return None
    if isinstance(value, (pd.Timestamp, datetime)):
        stamp = pd.Timestamp(value)
        return (stamp.tz_convert('UTC') if stamp.tzinfo else stamp).isoformat()
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        # 6 significant digits: plenty to measure with, and a quarter smaller than full precision
        return None if np.isnan(value) else float(f"{float(value):.6g}")
    if isinstance(value, (str, int)):
        return value
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return str(value)


def reason_data(reason: Dict) -> Dict:
    return {k: _plain(reason.get(k)) for k in REASON_FIELDS if k in reason}


def signal_data(signal: Dict, bet_type: str, line: float) -> Dict:
    out = {k: _plain(signal.get(k)) for k in SIGNAL_FIELDS}
    out['this_offer'] = signal.get('bet_type') == bet_type and float(signal.get('line')) == float(line)
    return out


def decision_data(decision: Dict) -> Dict:
    """A game decision without its offer row (the record has the offer): status, reason, values, notes,
    threshold, odds_at, lineup_at."""
    return _plain({'status': decision['status'], 'reason': decision['reason'], 'values': decision.get('values'),
                   'notes': [list(n) for n in decision.get('notes') or []], 'threshold': decision.get('threshold'),
                   'odds_at': decision.get('odds_at'), 'lineup_at': decision.get('lineup_at'),
                   'offer': None if decision.get('offer') is None else {
                       k: decision['offer'].get(k) for k in ('name', 'bet_type', 'line', 'side')}})


def offer_records(table: pd.DataFrame, decisions: Dict, scope: pd.DataFrame, every_game: pd.DataFrame,
                  lineups: pd.DataFrame, fetched_at: str, evaluated_at, version: Dict, origin: str,
                  profile: str, coef: Dict, lifts: Dict, statuses: Dict,
                  recorded: Optional[pd.DataFrame] = None, lineup_at=None) -> List[Dict]:
    """One record per priced line of `table` (models.price_props + reasons.flag_props, as decided in
    `decisions`: decisions.game_decisions), its reasons built as the props page builds them (reasons.offer_context,
    mispricing.offer_signals once per player and game, reasons.prop_reasons) from the same inputs.

    scope: the games the lines were priced from (with top_up); every_game: every stored game (for the history
    against the opponent); lineups: RotoWire's rows with player_id_ESPN (fetched_at when known); version:
    versions(); lifts: reasons.lift_status(); statuses: mispricing.hypothesis_status(); recorded: for a rebuild,
    the saved columns of the same lines (same index as table: what the snapshot recorded then, kept beside the
    rebuilt numbers, never in their place); lineup_at: when the lineups were fetched (default their fetched_at
    column; None = unknown, and the reasons that need it aren't made, as on a page without it)."""
    from decisions import offer_decision
    from mispricing import offer_signals
    from reasons import offer_context, prop_reasons
    if origin not in ORIGINS:
        raise ValueError(f"origin must be one of {ORIGINS}")
    names = scope.groupby('player_id_ESPN')['player_display_name'].last() if len(scope) else pd.Series(dtype=str)
    by_player = {pid: g.sort_values('Date') for pid, g in scope.groupby('player_id_ESPN')}
    if lineup_at is None and len(lineups) and 'fetched_at' in lineups:
        lineup_at = lineups['fetched_at'].max()
    signals_of = {}
    records = []
    for i, row in table.iterrows():
        if not row.get('side') or pd.isna(row.get('side odds')):
            continue
        pid = row['player_id']
        games = by_player.get(pid, scope.iloc[:0])
        opp = row.get('opp') or ''
        history = every_game[(every_game['player_id_ESPN'] == pid) & (every_game['OPP'].str.lower() == opp)] \
            if len(every_game) and opp else every_game.iloc[:0]
        if 'season_type' in scope and len(history):
            history = history[history['season_type'].isin(scope['season_type'].unique())]
        bet = offer_context(row, games, scope, lineups, names, fetched_at, lineup_at, coef=coef)
        if (pid, row['event_id']) not in signals_of:
            player_lines = table[(table['player_id'] == pid) & (table['event_id'] == row['event_id'])]
            signals_of[(pid, row['event_id'])] = offer_signals(player_lines, games, scope, fetched_at,
                                                               status=statuses, profile=profile)
        signals = signals_of[(pid, row['event_id'])]
        reasons = prop_reasons(bet, games, history, 'en', validation=lifts, signals=signals)
        game = decisions.get(row['event_id'])
        line = offer_decision(game, row) if game else None
        record = {
            'schema': SCHEMA_VERSION, 'origin': origin, 'snapshot_id': fetched_at,
            'evaluated_at': _plain(pd.Timestamp(evaluated_at)), 'cost_profile': profile, 'versions': version,
            'offer': _plain({'event_id': row['event_id'], 'player_id': pid, 'name': row['name'],
                             'stat': row['bet_type'], 'line': row['line'], 'side': row['side'],
                             'odds': row['side odds'], 'over_odds': row.get('over_odds'),
                             'under_odds': row.get('under_odds'), 'start_time': row.get('start_time'),
                             'home': row.get('home'), 'away': row.get('away')}),
            'estimate': _plain({'model_pct': bet.get('model %'), 'break_even_pct': bet.get('break-even %'),
                                'edge_pp': bet.get('edge pp'), 'ev_100': bet.get('ev'), 'avg': bet.get('avg'),
                                'proj_avg': bet.get('proj avg'), 'lineup_adj': bet.get('lineup adj'),
                                'market_over_pct': bet.get('market over %'), 'impacts': bet.get('impacts'),
                                'red_flag': row.get('red flag'), 'signal': row.get('signal')}),
            'decision': {'game': decision_data(game) if game else None,
                         'offer': _plain({k: line.get(k) for k in ('status', 'reason', 'line')}) if line else None},
            'data_times': _plain({'odds_at': fetched_at, 'lineup_at': lineup_at,
                                  'stats_through': bet.get('stats_through'), 'games': len(games)}),
            'reasons': [reason_data(r) for r in reasons],
            'hypotheses': [signal_data(s, row['bet_type'], row['line']) for s in signals],
        }
        if recorded is not None and i in recorded.index:
            record['recorded'] = _plain(recorded.loc[i].to_dict())
        records.append(record)
    return records


def record_key(record: Dict) -> tuple:
    """What makes two records the same observation: the snapshot, how it came to be and with what (origin, model,
    calibration, reason definitions, cost profile), and the offer's side."""
    v, o = record['versions'], record['offer']
    return (record['snapshot_id'], record['origin'], v['model'], v['calibration'], v['reasons'],
            record['cost_profile'], o['event_id'], o['player_id'] if o['player_id'] is not None else o['name'],
            o['stat'], o['line'], o['side'])


# --- the one place that writes ---

def read(path: str) -> List[Dict]:
    if not os.path.exists(path):
        return []
    with gzip.open(path, 'rt', encoding='utf-8') as f:
        return [json.loads(line) for line in f if line.strip()]


def archive(arts: Dict[str, Dict], directory: str = ARCHIVE_DIR) -> int:
    """Each artefact's content under its id, once (an id already archived is left as it is). Returns how many were
    new."""
    from safe_io import atomic_write_text
    new = 0
    for kind, art in arts.items():
        if art['content'] is None:
            continue
        path = os.path.join(directory, kind, f"{art['id']}.json")
        if not os.path.exists(path):
            atomic_write_text(path, json.dumps(art['content'], indent=2, sort_keys=True))
            new += 1
    return new


def write(records: Iterable[Dict], arts: Optional[Dict[str, Dict]] = None, directory: Optional[str] = None,
          archive_dir: str = ARCHIVE_DIR) -> int:
    """Add the records to their snapshot's file, skipping any whose record_key is already there (writing the same
    snapshot again adds nothing; a reconstruction never replaces the recorded one), and archive `arts`. Returns
    the number of records added."""
    from safe_io import atomic_write, locked
    records = list(records)
    if arts:
        archive(arts, archive_dir)
    added = 0
    by_snapshot = {}
    for r in records:
        by_snapshot.setdefault(r['snapshot_id'], []).append(r)
    for snapshot, part in by_snapshot.items():
        path = log_path(snapshot, directory)
        with locked(path):
            saved = read(path)
            seen = {record_key(r) for r in saved}
            new = []
            for r in part:
                key = record_key(r)
                if key not in seen:
                    seen.add(key)
                    new.append(r)
            if not new:
                continue
            lines = [json.dumps(r, sort_keys=True, separators=(',', ':')) for r in saved + new]
            payload = gzip.compress(("\n".join(lines) + "\n").encode('utf-8'), mtime=0)
            atomic_write(path, lambda f: f.write(payload), mode='wb')
            added += len(new)
    return added


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
