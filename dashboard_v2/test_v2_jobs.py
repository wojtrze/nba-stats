from core.jobs import summary_line


def test_summary_line_lists_every_snapshot_file():
    output = ["INFO fetching...", "rotowire_lineups: 176 rows", "superbet_props: 2178 rows",
              "superbet_game_odds: 1698 rows", ""]
    assert summary_line(output) == "rotowire_lineups: 176 rows, superbet_props: 2178 rows, superbet_game_odds: 1698 rows"
    assert summary_line(["x", "superbet_props: failed"]) == "superbet_props: failed"


def test_summary_line_otherwise_the_last_line():
    assert summary_line(["checking", "2026/27: added 7 games, 202 player lines.", ""]) == \
        "2026/27: added 7 games, 202 player lines."
    assert summary_line([]) == ''
