"""Running the scrapers from the Data center: each job is a subprocess whose output streams into the page, and
every run is logged to data/run_log.csv."""
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from typing import Dict, List

import pandas as pd
import streamlit as st

from core.data import clear_live, clear_stats
from loaders import RUN_LOG, RUN_LOG_COLUMNS, log_run as append_run, note_superbet_contact


def stats_command(season=None, since=None, until=None, game=None, rebuild=False) -> List[str]:
    """python -m espn_scraper with the chosen options (dates as YYYY-MM-DD)."""
    cmd = [sys.executable, '-m', 'espn_scraper']
    if game:
        return cmd + ['--game', str(game)]
    if season:
        cmd += ['--season', str(season)]
    if since:
        cmd += ['--since', str(since)]
    if until:
        cmd += ['--until', str(until)]
    if rebuild:
        cmd.append('--rebuild')
    return cmd


def snapshot_command(tomorrow: bool = False) -> List[str]:
    return [sys.executable, 'daily_snapshot.py'] + (['--tomorrow'] if tomorrow else [])


def summary_line(output: List[str]) -> str:
    """The run's last meaningful line ("2026/27: added 7 games, ..." for the scraper); for a snapshot every
    "<file>: N rows" line it printed, joined ("rotowire_lineups: 176 rows, superbet_props: 2178 rows, ...")."""
    lines = [line.strip() for line in output if line.strip()]
    counts = [line for line in lines if re.fullmatch(r'\w+: (\d+ rows|failed)', line)]
    if counts:
        return ', '.join(counts)[:200]
    return lines[-1][:200] if lines else ''


def run(job: str, cmd: List[str], label: str) -> int:
    """Run cmd, show its output live in a status box and log the run. Returns the exit code."""
    started, t0 = datetime.now(timezone.utc), time.monotonic()
    output: List[str] = []
    env = os.environ | {'PYTHONUNBUFFERED': '1', 'PYTHONIOENCODING': 'utf-8'}
    with st.status(label, expanded=True) as status:
        box = st.empty()
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                    encoding='utf-8', errors='replace', env=env)
            for line in proc.stdout:
                output.append(line.rstrip())
                box.code("\n".join(output[-25:]) or "(starting...)")
            code = proc.wait()
        except OSError as e:
            output.append(str(e))
            code = -1
        seconds = time.monotonic() - t0
        box.code("\n".join(output[-200:]) or "(no output)")
        if code == 0:
            status.update(label=f"{label}: done in {seconds:.0f} s", state='complete', expanded=False)
        else:
            status.update(label=f"{label}: failed (exit code {code})", state='error', expanded=True)
    log_run(started, job, cmd, code, seconds, summary_line(output))
    return code


def log_run(started: datetime, job: str, cmd: List[str], code: int, seconds: float, summary: str):
    append_run(started, job, ' '.join(['python'] + cmd[1:]), code, seconds, summary)


def recent_runs(n: int = 15) -> pd.DataFrame:
    if not os.path.exists(RUN_LOG):
        return pd.DataFrame(columns=RUN_LOG_COLUMNS)
    return pd.read_csv(RUN_LOG).tail(n).iloc[::-1]


def last_runs() -> Dict[str, Dict]:
    """The newest logged run of each job."""
    runs = recent_runs(500)
    return {job: part.iloc[0].to_dict() for job, part in runs.groupby('job')} if len(runs) else {}


def update_stats(**options) -> int:
    code = run('stats', stats_command(**options), "Updating stats from ESPN")
    if code == 0:
        clear_stats()
    return code


def save_snapshot(tomorrow: bool = False) -> int:
    """daily_snapshot.py, which fetches Superbet (and RotoWire) once: callers check data.superbet_wait() first."""
    note_superbet_contact()
    code = run('snapshot', snapshot_command(tomorrow), "Saving a RotoWire & Superbet snapshot"
               + (" (tomorrow's lineups)" if tomorrow else ""))
    clear_live()
    return code
