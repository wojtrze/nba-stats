"""Why the scheduled fetches stopped at night: the computer's power state now, and its sleeps from Windows' event log
(read only; nothing is changed in the system).

On 8-10.11 the PC slept at night although the fetches asked Windows to stay awake (fetch_loop._keep_awake): that
request only stops the idle timer, not a sleep chosen from the Start menu ("Application API"), the lid or the power
button, or a low battery. The Data center shows these so a missing night says why.
"""
import subprocess
import sys
from typing import Dict, List, Optional

import pandas as pd

# Kernel-Power 42's reason (the text after the last colon of its message) as a code the Data center words
# (i18n 'dc.reason.<code>'); None = not a new sleep. An unknown reason is kept as Windows wrote it.
REASONS = {
    'battery': 'battery',
    'application api': 'menu',
    'button or lid': 'lid',
    'system idle': 'idle',
    'hibernate from sleep - fixed timeout': None,       # the second step of a sleep already counted
}

# Kernel-Power 42 = going to sleep; Power-Troubleshooter 1 = woke up (Kernel-Power 107 is written right after 42)
_QUERY = ("Get-WinEvent -FilterHashtable @{{LogName='System'; Id=42,1; "
          "StartTime=[datetime]::Parse('{start}').ToLocalTime()}} -ErrorAction SilentlyContinue | "
          "Where-Object {{ $_.Id -eq 42 -or $_.ProviderName -like '*Power-Troubleshooter*' }} | ForEach-Object {{ "
          "$_.TimeCreated.ToUniversalTime().ToString('o') + '|' + $_.Id + '|' + "
          "(($_.Message -split \"`n\")[-1]).Trim() }}")


def parse_events(text: str) -> pd.DataFrame:
    """Lines 'time|id|last message line' (as _QUERY prints them: 42 sleep, 1 wake) as rows: at (UTC), event ('sleep', 'wake'),
    reason (a REASONS code; '' for a wake), oldest first. Sleeps that only continue an earlier one (sleep → hibernate)
    are left out, and so is the brief wake Windows logs at that step."""
    rows, hibernate = [], []
    for line in text.splitlines():
        parts = line.strip().split('|', 2)
        if len(parts) != 3:
            continue
        at, event_id, message = parts
        try:
            at = pd.Timestamp(at).tz_convert('UTC') if pd.Timestamp(at).tzinfo else pd.Timestamp(at, tz='UTC')
        except ValueError:
            continue
        if event_id == '1':
            rows.append({'at': at, 'event': 'wake', 'reason': ''})
        elif event_id == '42':
            raw = message.rsplit(':', 1)[-1].strip()
            reason = REASONS.get(raw.lower(), raw)
            if reason is not None:
                rows.append({'at': at, 'event': 'sleep', 'reason': reason})
            else:
                hibernate.append(at)
    near = lambda at: any(abs((at - h).total_seconds()) <= 60 for h in hibernate)
    rows = [r for r in rows if not (r['event'] == 'wake' and near(r['at']))]
    out = pd.DataFrame(rows, columns=['at', 'event', 'reason'])
    return out.sort_values('at', ignore_index=True)


def sleep_events(start) -> pd.DataFrame:
    """The computer's sleeps and wakes since `start` (UTC) from Windows' event log; empty elsewhere or on error."""
    if sys.platform != 'win32':
        return parse_events('')
    start = pd.Timestamp(start)
    start = start.tz_convert('UTC') if start.tzinfo else start.tz_localize('UTC')
    try:
        done = subprocess.run(['powershell', '-NoProfile', '-NonInteractive', '-Command',
                               _QUERY.format(start=f"{start:%Y-%m-%dT%H:%M:%S}Z")],
                              capture_output=True, text=True, timeout=20, encoding='utf-8', errors='replace')
    except (OSError, subprocess.SubprocessError):
        return parse_events('')
    return parse_events(done.stdout)


def power_status() -> Optional[Dict]:
    """{'on_battery': bool, 'percent': int or None} on Windows, None elsewhere or when unknown."""
    if sys.platform != 'win32':
        return None
    try:
        import ctypes
        from ctypes import wintypes

        class SystemPowerStatus(ctypes.Structure):
            _fields_ = [('ACLineStatus', wintypes.BYTE), ('BatteryFlag', wintypes.BYTE),
                        ('BatteryLifePercent', wintypes.BYTE), ('SystemStatusFlag', wintypes.BYTE),
                        ('BatteryLifeTime', wintypes.DWORD), ('BatteryFullLifeTime', wintypes.DWORD)]

        s = SystemPowerStatus()
        if not ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(s)):
            return None
        percent = s.BatteryLifePercent & 0xFF
        return {'on_battery': s.ACLineStatus == 0, 'percent': None if percent == 255 else percent}
    except Exception:                                    # noqa: BLE001  (informative only)
        return None


def sleeps_in(events: pd.DataFrame, gaps: List) -> List[Dict]:
    """For each gap (from, to) of the collection report, the first sleep inside it: {'from', 'to', 'sleep_at',
    'reason', 'wake_at'} (sleep_at None when the computer didn't sleep: the program wasn't running or was stuck)."""
    out = []
    for a, b in gaps:
        inside = events[(events['event'] == 'sleep') & (events['at'] >= a - pd.Timedelta(minutes=70))
                        & (events['at'] <= b)]
        if inside.empty:
            out.append({'from': a, 'to': b, 'sleep_at': None, 'reason': None, 'wake_at': None})
            continue
        first = inside.iloc[0]
        wake = events[(events['event'] == 'wake') & (events['at'] > first['at'])]
        out.append({'from': a, 'to': b, 'sleep_at': first['at'], 'reason': first['reason'],
                    'wake_at': wake['at'].iloc[0] if len(wake) else None})
    return out
