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
    side stats, Over vs Under. Nothing else is split, so no segment wins by chance among many.

Ranges are 95% from resampling whole nights. Writes data/backtest/clv.md.

4 games with a close, 0 lines at their last fetch, 0 at their first.
