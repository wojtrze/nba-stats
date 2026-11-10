"""When the scheduled fetches run (fetch_loop.py): a pure function of the night's games and the clock.

- Hourly, on the hour, while any game is still to start: every game starting within HOURLY_HORIZON, with RotoWire.
- In each game's last hour, at LAST_HOUR minutes before its tip-off (T-60, T-40, T-20, T-10, T-5): the games of
  that tip-off, with RotoWire.
- An hourly slot within HOURLY_MERGE of a last-hour slot is folded into it (all games); slots within MERGE_GAP of
  each other become one, at the earliest time.
- Priced slots (a full snapshot with the model, read by the dashboards) are every PRICED_EVERY hours and each T-60;
  the others only record quotes (fetch_loop.save_quotes).
- A slot more than LATE past its time (the computer slept, the program started late) is skipped, not caught up.

Every one of these is a setting (Config, saved by fetch_loop.worker_settings and edited in the v2 Data center); the
constants below are the defaults.
"""
from dataclasses import asdict, dataclass, field, fields, replace
from datetime import datetime, timedelta
from typing import Dict, Iterable, List, Optional, Tuple

LAST_HOUR = (60, 40, 20, 10, 5)            # minutes before tip-off
HOURLY_HORIZON = timedelta(hours=24)
HOURLY_MERGE = timedelta(minutes=15)
MERGE_GAP = timedelta(minutes=3)
LATE = timedelta(minutes=3)
PRICED_EVERY = 2                           # hours (UTC hour divisible by it)
SLOT_LIMIT_MIN = 6                         # the watchdog's limit for one slot's run (fetch_loop.run_guarded)


@dataclass(frozen=True)
class Config:
    """The schedule's settings. hourly_every 0 = no hourly reads; priced_every 0 = a full snapshot only at T-60."""
    hourly_every: int = 1                  # hours between the all-games reads
    hourly_horizon: int = int(HOURLY_HORIZON.total_seconds() // 3600)   # hours ahead a game is read hourly
    last_hour: Tuple[int, ...] = LAST_HOUR  # minutes before tip-off
    priced_every: int = PRICED_EVERY        # hours between full priced snapshots (plus T-60)
    rotowire: bool = True                   # RotoWire's lineups with every read
    late: int = int(LATE.total_seconds() // 60)                       # minutes a slot may be late before it's skipped
    slot_limit: int = SLOT_LIMIT_MIN        # minutes one run may take before the watchdog gives up on it

    @property
    def horizon(self) -> timedelta:
        return timedelta(hours=self.hourly_horizon)

    @property
    def late_by(self) -> timedelta:
        return timedelta(minutes=self.late)

    def to_dict(self) -> Dict:
        return asdict(self) | {'last_hour': list(self.last_hour)}

    @classmethod
    def from_dict(cls, saved: Optional[Dict]) -> 'Config':
        """The saved settings over the defaults; unknown keys and values of the wrong kind are ignored."""
        cfg, known = cls(), {f.name for f in fields(cls)}
        values = {}
        for k, v in (saved or {}).items():
            if k not in known:
                continue
            try:
                if k == 'last_hour':
                    v = tuple(sorted({int(m) for m in v if 0 < int(m) <= 180}, reverse=True))
                elif k == 'rotowire':
                    v = bool(v)
                else:
                    v = int(v)
            except (TypeError, ValueError):
                continue
            values[k] = v
        cfg = replace(cfg, **values)
        problems = cfg.problems()
        return cls() if problems else cfg

    def problems(self) -> List[str]:
        """What makes these settings unusable (empty = fine)."""
        out = []
        if not 0 <= self.hourly_every <= 6:
            out.append('hourly_every')
        if not 1 <= self.hourly_horizon <= 48:
            out.append('hourly_horizon')
        if not 0 <= self.priced_every <= 12:
            out.append('priced_every')
        if not 1 <= self.late <= 30:
            out.append('late')
        if not 2 <= self.slot_limit <= 30:
            out.append('slot_limit')
        if not self.hourly_every and not self.last_hour:
            out.append('nothing scheduled')
        return out


DEFAULT = Config()


@dataclass(frozen=True)
class Slot:
    at: datetime
    kinds: Tuple[str, ...]                 # 'hourly', 'T-60', ...
    event_ids: frozenset = field(default_factory=frozenset)
    all_events: bool = False               # every game starting within HOURLY_HORIZON (not only event_ids)
    priced: bool = False
    rotowire: bool = True

    @property
    def kind(self) -> str:
        return '+'.join(self.kinds)


def _merge(a: Slot, b: Slot) -> Slot:
    return Slot(min(a.at, b.at), a.kinds + tuple(k for k in b.kinds if k not in a.kinds), a.event_ids | b.event_ids,
                a.all_events or b.all_events, a.priced or b.priced, a.rotowire or b.rotowire)


def _priced_hour(hour: datetime, cfg: Config) -> bool:
    return bool(cfg.priced_every) and hour.hour % cfg.priced_every == 0


def night_slots(events: Iterable[Tuple[int, datetime]], since: datetime, cfg: Config = DEFAULT) -> List[Slot]:
    """Every slot after `since` for the listed games (event_id, tip-off, UTC), in time order."""
    events = [(e, tip) for e, tip in events if tip > since]
    if not events:
        return []
    tips = sorted({tip for _, tip in events})
    last_hour = [Slot(tip - timedelta(minutes=m), (f'T-{m}',), frozenset(e for e, t in events if t == tip),
                      priced=m == 60, rotowire=cfg.rotowire)
                 for tip in tips for m in cfg.last_hour if tip - timedelta(minutes=m) > since]
    hourly = []
    hour = since.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    while cfg.hourly_every and hour < tips[-1]:
        ids = frozenset(e for e, t in events if hour < t <= hour + cfg.horizon)
        if ids and hour.hour % cfg.hourly_every == 0:
            hourly.append(Slot(hour, ('hourly',), ids, all_events=True, priced=_priced_hour(hour, cfg),
                               rotowire=cfg.rotowire))
        hour += timedelta(hours=1)
    # an hourly slot next to a last-hour slot is folded into the nearest one
    for h in hourly:
        near = [i for i, s in enumerate(last_hour) if abs(s.at - h.at) <= HOURLY_MERGE]
        if near:
            i = min(near, key=lambda i: abs(last_hour[i].at - h.at))
            last_hour[i] = _merge(last_hour[i], replace(h, at=last_hour[i].at))
        else:
            last_hour.append(h)
    merged: List[Slot] = []
    for slot in sorted(last_hour, key=lambda s: s.at):
        if merged and slot.at - merged[-1].at <= MERGE_GAP:
            merged[-1] = _merge(merged[-1], slot)
        else:
            merged.append(slot)
    return merged


def due(slots: List[Slot], now: datetime, done_through: Optional[datetime],
        late: timedelta = LATE) -> Tuple[Optional[Slot], List[Slot]]:
    """The slot to run now (None if none) and the slots skipped for being more than `late` behind. done_through is
    the time of the last slot already run (or skipped): nothing at or before it is due again."""
    pending = [s for s in slots if s.at <= now and (done_through is None or s.at > done_through)]
    skipped = [s for s in pending if now - s.at > late]
    on_time = [s for s in pending if now - s.at <= late]
    if len(on_time) > 1:                   # two at once (merged gaps can't, but be safe): one run covers both
        slot = on_time[0]
        for other in on_time[1:]:
            slot = _merge(slot, other)
        return replace(slot, at=on_time[-1].at), skipped
    return (on_time[0] if on_time else None), skipped


def next_at(slots: List[Slot], now: datetime) -> Optional[datetime]:
    later = [s.at for s in slots if s.at > now]
    return min(later) if later else None
