# Closing line value of the saved lines

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

61 games read at most 10 min before tip-off, 10058 lines at their last fetch, 8263 at their first.

## Per star level (last fetch before tip-off)

| stars | lines | nights | CLV % | CLV % range | CLV % after tax | clv pp | moved toward side % | moved range |
|---|---|---|---|---|---|---|---|---|
| ★★★★☆ | 50 | 10 | -7.0 | -7.5 … -6.3 | -18.2 | 0.2 | 42.0 | 29 … 59 |
| ★★★☆☆ | 1646 | 10 | -7.5 | -7.7 … -7.3 | -18.6 | -0.0 | 34.3 | 27 … 41 |
| ★★☆☆☆ | 2629 | 10 | -7.7 | -7.8 … -7.6 | -18.8 | -0.1 | 33.3 | 28 … 37 |
| ★☆☆☆☆ | 4287 | 10 | -7.9 | -8.0 … -7.8 | -18.9 | -0.0 | 33.3 | 28 … 37 |
| ☆☆☆☆☆ | 1446 | 10 | -8.1 | -8.3 … -7.9 | -19.1 | -0.2 | 32.9 | 28 … 40 |
| all | 10058 | 10 | -7.8 | -7.8 … -7.7 | -18.9 | -0.1 | 33.4 | 28 … 37 |

## When the quote was taken (first fetch of every line)

| hours before tip-off | lines | nights | CLV % | CLV % range | CLV % after tax | clv pp | moved toward side % | moved range |
|---|---|---|---|---|---|---|---|---|
| (0, 1] | 542 | 10 | -7.9 | -8.3 … -7.7 | -19.0 | -0.1 | 27.7 | 14 … 46 |
| (1, 3] | 298 | 8 | -7.8 | -8.2 … -7.0 | -18.9 | -0.2 | 46.3 | 43 … 51 |
| (3, 6] | 1119 | 9 | -8.1 | -8.4 … -7.3 | -19.1 | -0.2 | 44.1 | 42 … 52 |
| (6, 12] | 2012 | 7 | -8.1 | -8.4 … -7.8 | -19.1 | -0.2 | 43.2 | 42 … 45 |
| (12, 48] | 4292 | 5 | -8.0 | -8.2 … -7.7 | -19.1 | -0.2 | 43.5 | 42 … 46 |
| all | 8263 | 10 | -8.0 | -8.2 … -7.8 | -19.1 | -0.2 | 42.6 | 41 … 44 |

## Fixed segments (last fetch)

| stats | lines | nights | CLV % | CLV % range | CLV % after tax | clv pp | moved toward side % | moved range |
|---|---|---|---|---|---|---|---|---|
| main stats | 4328 | 10 | -7.1 | -7.1 … -7.0 | -18.2 | -0.0 | 34.0 | 28 … 39 |
| side stats | 5730 | 10 | -8.4 | -8.5 … -8.3 | -19.4 | -0.1 | 33.0 | 28 … 37 |
| all | 10058 | 10 | -7.8 | -7.8 … -7.7 | -18.9 | -0.1 | 33.4 | 28 … 37 |

| side | lines | nights | CLV % | CLV % range | CLV % after tax | clv pp | moved toward side % | moved range |
|---|---|---|---|---|---|---|---|---|
| Under | 5937 | 10 | -7.7 | -7.8 … -7.6 | -18.8 | 0.0 | 35.3 | 30 … 40 |
| Over | 4121 | 10 | -8.0 | -8.1 … -7.8 | -19.0 | -0.1 | 30.7 | 26 … 35 |
| all | 10058 | 10 | -7.8 | -7.8 … -7.7 | -18.9 | -0.1 | 33.4 | 28 … 37 |

| player | lines | nights | CLV % | CLV % range | CLV % after tax | clv pp | moved toward side % | moved range |
|---|---|---|---|---|---|---|---|---|
| starter | 7415 | 10 | -7.8 | -7.8 … -7.7 | -18.9 | -0.1 | 33.1 | 28 … 38 |
| bench | 2643 | 10 | -7.8 | -7.9 … -7.7 | -18.9 | -0.0 | 34.2 | 30 … 37 |
| all | 10058 | 10 | -7.8 | -7.8 … -7.7 | -18.9 | -0.1 | 33.4 | 28 … 37 |

## Per stat (descriptive: too many groups to pick a winner from)

| stat | lines | nights | CLV % | CLV % range | CLV % after tax | clv pp | moved toward side % | moved range |
|---|---|---|---|---|---|---|---|---|
| AST | 534 | 10 | -7.0 | -7.2 … -6.7 | -18.2 | -0.0 | 35.0 | 28 … 41 |
| TO | 805 | 10 | -8.1 | -8.3 … -8.0 | -19.2 | -0.1 | 32.4 | 27 … 37 |
| PF | 795 | 10 | -7.9 | -8.1 … -7.7 | -19.0 | -0.0 | 34.6 | 26 … 41 |
| 3PM | 597 | 10 | -7.0 | -7.3 … -6.7 | -18.1 | 0.0 | 35.7 | 28 … 43 |
| PR | 535 | 10 | -7.0 | -7.2 … -6.8 | -18.2 | 0.0 | 32.9 | 28 … 39 |
| FTM | 800 | 10 | -7.9 | -8.0 … -7.7 | -18.9 | 0.0 | 33.6 | 30 … 37 |
| PTS | 637 | 10 | -7.1 | -7.2 … -7.0 | -18.3 | -0.1 | 33.6 | 29 … 38 |
| PA | 429 | 10 | -7.1 | -7.3 … -6.8 | -18.3 | -0.0 | 29.1 | 24 … 36 |
| ARP | 415 | 10 | -7.2 | -7.3 … -7.0 | -18.3 | -0.1 | 30.1 | 24 … 37 |
| RA | 489 | 10 | -7.1 | -7.4 … -6.8 | -18.2 | -0.0 | 33.9 | 27 … 40 |
| FTA | 790 | 10 | -8.8 | -8.9 … -8.7 | -19.7 | -0.0 | 31.8 | 28 … 35 |
| REB | 692 | 10 | -7.0 | -7.3 … -6.7 | -18.2 | -0.0 | 38.3 | 29 … 45 |
| 3PA | 730 | 10 | -8.9 | -9.1 … -8.6 | -19.8 | -0.1 | 33.6 | 29 … 38 |
| FGA | 719 | 10 | -8.9 | -9.1 … -8.6 | -19.8 | -0.1 | 32.5 | 27 … 38 |
| FGM | 760 | 10 | -8.3 | -8.5 … -8.0 | -19.3 | -0.3 | 30.3 | 25 … 36 |
| BLK | 103 | 9 | -7.6 | -8.0 … -7.2 | -18.7 | 0.2 | 40.8 | 25 … 56 |
| STL | 228 | 9 | -8.0 | -8.3 … -7.8 | -19.1 | -0.1 | 37.3 | 32 … 42 |
| all | 10058 | 10 | -7.8 | -7.8 … -7.7 | -18.9 | -0.1 | 33.4 | 28 … 37 |

## Game markets (main lines, the model's side at its first fetch)

| market | lines | nights | CLV % | CLV % range | CLV % after tax | clv pp | moved toward side % | moved range |
|---|---|---|---|---|---|---|---|---|
| ML | 57 | 10 | -5.2 | -8.0 … -2.7 | -16.6 | 0.5 | 50.9 | 35 … 66 |
| HOME_TOTAL | 129 | 10 | -5.9 | -7.0 … -5.1 | -17.2 | 0.2 | 51.9 | 40 … 58 |
| SPREAD | 118 | 10 | -3.3 | -7.1 … 0.0 | -14.9 | 1.0 | 56.8 | 38 … 70 |
| AWAY_TOTAL | 121 | 10 | -7.2 | -9.2 … -5.5 | -18.4 | -0.5 | 43.0 | 36 … 50 |
| TOTAL | 156 | 10 | -6.1 | -7.7 … -4.3 | -17.4 | -0.4 | 41.0 | 36 … 48 |
| all | 581 | 10 | -5.6 | -7.0 … -4.7 | -17.0 | 0.1 | 48.0 | 40 … 53 |
