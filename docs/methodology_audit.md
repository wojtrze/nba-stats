# Methodology audit

An audit of the code (branch `dev-2026-10-26`, `main` after PR #7) against the external methodology review of
the README. Each finding is classed as a confirmed defect, a documentation ambiguity, a methodological
limitation or a risk, with the code it's in. Fixes land one at a time, each with a regression test; this file
records which are done.

**What the project does and doesn't establish.** The safeguards described in the README (calibration, held-out
checks, red flags) don't show a profitable betting edge. On the held-out data, the calibrated model predicts
about as well as the margin-free price (log loss 0.6889 vs 0.6895 on 2022 Feb–May). No 🟢 threshold has
qualified on Superbet. The historical test uses Unibet's 2022/23 lines, while live operation uses Superbet,
and the features available differ between the two:
- 2022/23 has no game odds, so there is no implied-team-total factor;
- 2022/23 has no RotoWire, so absences are either none or an oracle;
- positions in 2022/23 are taken from 2024–26 logs.

## Data flow: source to settlement

```
ESPN JSON ─ espn_scraper ─────────────► data/<season>/player_gamelogs.csv, games.csv
RotoWire ─ lineup_fetcher ─ save_lineups_if_changed ─► rotowire_lineups.csv (fetched_at)
Superbet ─ superbet_fetcher.todays_offers
          └ daily_snapshot.save_superbet
              └ add_model_columns
                  ├ backtest.calibrate.refresh   (refits calibration.json when a new night settled)
                  ├ models.price_props + reasons.flag_props ─► superbet_props.csv  (pick, model_pct, edge_pp,
                  │                                             edge_low, signal, red_flag, raw_*, market_over_pct)
                  └ models.price_games ─────────────────────► superbet_game_odds.csv (model_pct, edge_pp, proj_*)

Dashboards: newest fetch ─ price_props / price_games (live, current RotoWire, current calibration) ─► pages
            bet slip ─ bets.kelly_stake(staking_chance) ─ bets.save_bets ─► my_bets.csv

Settlement / evaluation:
  tracking.settle_props / settle_games   first pre-tip snapshot = the bet, last = last observed pregame quote
  nightly.night_props                     last pre-tip snapshot; recomputes missing picks (marked recomputed)
  backtest.calibrate.superbet_lines       last pre-tip snapshot's raw_* → calibration fit
  backtest.run.settle                     2022/23 lines
```

A displayed prediction and a saved one can differ. The dashboard reprices the newest fetch with the current
RotoWire version and the current calibration, but the row in `superbet_props.csv` keeps what was computed at
fetch time. Before the step 1 fix, neither of them records the model version or the calibration it used.

## Findings

| # | Finding | Class | Where | Status |
|---|---|---|---|---|
| F1 | `daily_snapshot.py --reprice` rewrites the model columns of `superbet_props.csv` in place, so the recorded live predictions are lost. All 26,925 saved rows have `raw_*` values, although those columns only exist since commit 11017b5. No row records the model version or the calibration it was priced with. | Confirmed defect | `daily_snapshot.reprice_snapshots`, `add_model_columns` | fixed: rows carry `model_version`, `calibration_id`, `prediction_origin`; `--reprice` writes `superbet_props_replay.csv`; the live values were recovered from git into `superbet_props_recorded_legacy.csv` (24,423 recorded live, 2,502 Oct 20 replay) |
| F2 | The calibration is fitted on the saved `raw_*` chances, whichever model wrote them. Live rows, repriced rows and different model versions are pooled. A calibration has to be fitted on the same model it's applied to. | Confirmed defect | `backtest.calibrate.superbet_lines` | fixed: the fit uses only `nightly.MODEL_VERSION` chances (`nightly.priced_by`: recorded live, else that version's replay; 2022 lines tagged with `model_version`); `refresh` refits on a version change and waits for the new version's lines. Refit on current-version lines gave identical coefficients, because 11017b5 had repriced everything with this model |
| F3 | Without `calibration.json`, the raw model's chances are used silently (identity coefficients). Their overconfident edges then become 🟡 picks and Kelly stakes. | Confirmed defect | `models.load_calibration` | fixed: `models.calibration_status` (fitted / missing / version mismatch) is a column of `price_props`; unless fitted no 🟢/🟡, no bet, verdict Pass, no Kelly stake for props; warning on Props, Overview, Today's props and the slip |
| F4 | The 🟢 threshold is chosen on the held-out Superbet nights, and those same nights are its only validation. Today that's 2 nights (30% of 6). It's re-chosen after every settled night, which is repeated selection on the same outcomes. | Methodological limitation (overfitting) | `backtest.calibrate.choose_green_edge`, `refresh` | mitigated: 🟢 needs 50+ bets over 10+ held-out nights, ROI > 0 and the hit rate's 95% low end above the bets' break-even; the report states the selection policy and that the threshold is exploratory. A clean fix needs a later untouched period (P1 harness) |
| F5 | Game markets are never calibrated. A fixed +5 pp edge gives 🟢, and 23.8% of the saved game outcomes reach it. The bet slip sizes game bets with Kelly on the raw `model %`. | Confirmed defect (unvalidated signal) | `metrics.market_edges`, Games pages, `bets.staking_chance` | fixed: game outcomes get no 🟢/🟡, verdict Pass and no stake; the calibration report tracks the game model against the margin-free price (Oct 21–25, 580 outcomes: log loss 0.7011 vs 0.6719; old 🟢 expected 68.1%, won 55.3%). A game calibration follows at 300+ outcomes on 10+ nights |
| F6 | The "95% range" is p ± 1.96·√(p(1−p)/(n+11)): the sampling noise of a shrunk hit rate, not a prediction interval, and it leaves out the projection, the market prior and model error. It's then passed through the calibration, where b = 0.079 shrinks it almost to nothing. The docstring calls it a Beta posterior. | Documentation ambiguity + limitation | `metrics.prop_probability`, `models.price_props`, `bets.staking_chance` | open |
| F7 | There are two settlement implementations: `tracking._result` / `_profit` and `backtest.run.side_result`. When a game is stored but has no row for the player, it settles as `void`, even if the scraper skipped that player's line. A postponed game stays `pending` forever. No props or game lines are integer today, so pushes are rare, but the props model mixes conditional and unconditional chances on integer lines. | Confirmed (duplication), edge cases | `dashboard/tracking.py`, `backtest/run.py`, `metrics.prop_probability` | fixed: one implementation (`metrics.side_result` / `side_profit`) used by tracking, backtest and dashboard v2; the points check is `metrics.score_check` (both Data pages); missing row in an incomplete box score and a game still missing after later ones are stored → `unresolved`, counted on the pages. No settled line of the record changed. The props model's integer-line chances remain a limitation (no integer lines offered so far) |
| F8 | Settling by name (`name_ESPN` → id) takes the last match, with no check for two players sharing a name. | Limitation | `tracking.settle_props` | fixed: a name fallback is used only when it belongs to exactly one player; otherwise `unresolved` |
| F9 | CSV writes from both dashboards and the scheduled jobs have no lock and no atomic write. `_append` rewrites the whole file whenever a new column appears. | Confirmed defect (reproduced) | `daily_snapshot._append`, `bets.save_bets` | fixed: `safe_io.py` (lock file + atomic replace) for every data writer: snapshot appends and the column-adding rewrite, the RotoWire save-on-change, `my_bets.csv`, the run log, the scraper's game logs (`_drop_game` rewrote them in place), `checked_through`, the calibration, the backtest and ablation outputs. The Superbet cooldown was per process; it's now `data/superbet_contact.txt`, claimed under a lock. Reproduced with the old code: 4 processes × 40 appends → rows lost and stray header lines; 3 dashboards → one RotoWire change saved 3 times. Run log wording reconciled in the README |

## Existing tests and missing regression tests

| Concern | Existing tests | Missing |
|---|---|---|
| Lineage (F1) | `dashboard/test_snapshot.py::test_reprice_writes_a_replay_and_leaves_the_record_alone`, `test_lineage_names_the_model_and_the_calibration` | (was: repricing leaves `superbet_props.csv` unchanged; saved rows carry model version, calibration id and origin) |
| Calibration source (F2) | `test_superbet_lines_judges_the_last_fetch_before_tip_off`, `test_refresh_refits_only_after_a_new_night`, `test_lines_2022_only_of_the_current_model`, `test_refresh_refits_for_a_new_model_version_and_waits_for_its_lines`, `dashboard/test_nightly.py::test_priced_by_never_mixes_model_versions` | – |
| Calibration state (F3) | `test_load_calibration`, `test_calibration_status_and_warning`, `dashboard/test_models.py::test_no_valid_calibration_means_no_pick`, `dashboard/test_bets.py::test_no_stake_on_an_uncalibrated_prop`, `dashboard/test_reasons.py::test_verdict_is_pass_for_a_prop_without_valid_calibration` | – |
| 🟢 threshold (F4) | `backtest/test_backtest.py::test_choose_green_edge_needs_many_nights_and_a_clear_margin_over_break_even` | – |
| Game signal (F5) | `test_settle_games`, `dashboard/test_reasons.py::test_game_outcomes_red_only_for_flags`, `test_game_reasons_for_a_total`, `dashboard/test_bets.py::test_staking_chance_uses_the_low_end_for_props`, `backtest/test_backtest.py::test_game_lines_margin_free_chance_and_report` | – |
| Staking (F6) | `dashboard/test_bets.py::test_kelly_stake`, `test_staking_chance_uses_the_low_end_for_props` | (covered by F3/F5 tests) |
| Settlement (F7, F8) | `test_settle_props`, `test_side_result_push_and_profit`, `test_save_and_settle_my_bets`, `dashboard/test_tracking.py::test_side_result_and_profit`, `test_settle_props_statuses`, `test_settle_games_postponed_is_unresolved` | – |
| Persistence (F9) | `tests/test_safe_io.py` (4 concurrent writer processes, byte-exact appends, interrupted write, exclusive / reentrant / stale lock, shared Superbet cooldown, one RotoWire change saved once) | – |

## P2: wording and side effects (Oct 26)

- "Closing line" → *last observed pregame quote*: `last line`, `last odds`, `line vs last`, `odds vs last %` (was `close line`, `clv line`, `clv odds %`, `avg CLV %`), with `h before tip` / `last h before tip` (`tracking.settle_props` / `settle_games`).
- Signals mean the same on every page (the `signal` tip and `GAME_SIGNAL_TIP` in `dashboard/glossary.py`): 🟢 = held up on 10+ unseen nights, 🟡 = a positive *estimated* edge, 🔴 = a reason to pass; game outcomes only 🔴.
- The calibration report says how to read b (how much of the model's disagreement held up; not interval coverage, not a betting edge).
- Legacy entry points are labelled in the README and in the files (`bet_fetcher.py`, `bet_scrapper.py`, `indicators_aggregation.py`, `bet_analyst.py`'s Unibet mode, `nba2024/`, `Untitled6.ipynb`).
- `bet_analyst` fetched RotoWire at import (a class attribute); `BetAssessment(bets, doubtful_players=...)` now takes the list, fetched only when a bet needs it (`tests/test_feeds.py::test_bet_assessment_needs_no_network_until_asked`).
- `safe_io.locked` on Windows: a writer waiting for a lock that was being deleted got PermissionError and crashed (the intermittent `test_appends_from_several_processes_all_land`); now treated as busy (0 failures in 15 stress runs, 2 in 8 before).

## Model contribution (step 7, `backtest/ablation.py`)

On identical lines, fitted on the earlier part and scored on the later part of each source, with night-resampled ranges (report: `data/backtest/ablation.md`):

- Unibet 2022/23 (77 unseen nights): the Over/Under bias beats the price by 0.0004 log loss (range −0.0007…−0.0001); the player's numbers add ~0.0002, inside the noise; absences (also the oracle) and the matchup add nothing measurable.
- Superbet 2026/27 (2 unseen nights): every fitted rung is worse than the price (+0.0034 ± 0.003), already at the side-bias rung.

Implication: no component earns more complexity yet. The next model changes should be judged on this ladder, and the side bias is the first suspect (it doesn't carry across periods or bookmakers).

**First change judged on it (Oct 26): the calibration no longer fits the Over/Under bias or the offset** (`backtest/calibrate.py` `FITTED = ['a', 'b']`). Fitted on both sources' earlier lines and scored on each one's later lines: shared bias 2022 −0.0007 / Superbet +0.0008 vs the price; no bias +0.0001 / −0.0002; bias per bookmaker −0.0003 / +0.0027. The bias belongs to Unibet 2022/23 and doesn't carry to Superbet, and Superbet's own is too noisy to fit yet. Refit: a = 1.120, b = 0.100; held-out Superbet log loss 0.6877 (= the price; was 0.6887). Raw chances are unchanged, so `MODEL_VERSION` stays; the new calibration has a new `calibration_id`.

**Candidate model changes on 2022/23** (`backtest/ideas.py`, report `data/backtest/ideas_2022.md`; exploratory: 8 candidates on the same 77 nights, calibrated a, b as the dashboards are; difference from the current model per line side, night-resampled range):

- Count distribution (negative binomial / Poisson with the player's own spread) for every stat: −0.0002 (−0.0002…−0.0001), on 3PM −0.0004 (−0.0006…−0.0002). Small but consistently better; the only candidate whose range is clearly below 0. For 3PM only or 3PM/AST/REB: −0.0001.
- Recency weighting (half-life 5 / 10 / 20 games): worse, +0.0002 to +0.0003. The season's equal weights are better.
- Distribution only (no hit rate): +0.0001, worse on 3PM (+0.0005).
- No candidate's positive-edge picks beat break-even in a way the interval supports.

Adopted (Oct 26) as model `2026-10-26-count` (`metrics.count_over` in `metrics.prop_probability`); the 2022 backtest rerun and the Superbet lines repriced (the replay keeps both versions), calibration refitted: a = 1.116, b = 0.121; held-out log loss 2022 0.6894 (price 0.6895, normal model 0.6896), Superbet 0.6876 (price 0.6877). Recency weighting dropped. The F6 docstring is corrected (the range is the hit rate's sampling noise, not a Beta posterior or a prediction interval), and on whole-number lines the distribution's P(over) + P(under) + P(push) = 1 (`test_prop_probability_whole_line_pushes`). Judge it on Superbet as nights settle (`python -m backtest.ablation --refresh`).

## Fix order

1. Lineage (F1)
2. Calibration fitted on one model version (F2)
3. Visible calibration state, no raw-model staking (F3)
4. A stricter 🟢 (F4)
5. No game signal without evidence (F5)
6. One settlement implementation plus edge cases (F7, F8)
7. Ablation harness on identical lines, then model changes only where it shows a gain
8. Persistence (F9)
9. README / UI wording (F6 and the P2 items)
