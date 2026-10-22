"""Rebuilding a box-score line from play-by-play. Run with: python -m pytest tests"""
from espn_scraper.play_by_play import missing_player, player_stats


def play(period, clock, text, actor=None, kind='Jump Shot', team='4', home=0, away=0, **extra):
    return {'period': {'number': period}, 'clock': {'displayValue': clock}, 'text': text, 'type': {'text': kind},
            'team': {'id': team}, 'homeScore': home, 'awayScore': away,
            'participants': [{'athlete': {'id': actor}}] if actor else [], **extra}


PLAYS = [
    play(1, '5:00', 'Lachlan Olbrich enters the game for Guerschon Yabusele', '9', 'Substitution'),
    play(1, '4:30', 'Lachlan Olbrich makes 25-foot running jump shot', '9', home=3,
         shootingPlay=True, scoringPlay=True, scoreValue=3, pointsAttempted=3),
    play(1, '4:00', "Jaylen Brown blocks Lachlan Olbrich 's layup", '9', 'Layup Shot',
         shootingPlay=True, scoringPlay=False, scoreValue=0, pointsAttempted=2, home=3),
    play(1, '3:50', 'Lachlan Olbrich offensive rebound', '9', 'Offensive Rebound', home=3),
    play(1, '3:40', 'Matas Buzelis makes layup (Lachlan Olbrich assists)', '1', 'Layup Shot', home=5,
         shootingPlay=True, scoringPlay=True, scoreValue=2, pointsAttempted=2),
    play(1, '3:00', 'Lachlan Olbrich blocks Jaylen Brown \'s layup', '2', 'Layup Shot', team='2', home=5,
         shootingPlay=True, scoringPlay=False, scoreValue=0, pointsAttempted=2),
    play(1, '2:00', 'Lachlan Olbrich bad pass (Jaylen Brown steals)', '9', 'Bad Pass\nTurnover', home=5),
    play(1, '1:00', 'Jaylen Brown makes jump shot', '2', team='2', home=5, away=2,
         shootingPlay=True, scoringPlay=True, scoreValue=2, pointsAttempted=2),
    play(1, '30.0', 'Guerschon Yabusele enters the game for Lachlan Olbrich', '1', 'Substitution', home=5, away=2),
    play(2, '12:00', 'Lachlan Olbrich personal foul', '9', 'Personal Foul', home=5, away=2),
    play(2, '11:00', 'Lachlan Olbrich makes free throw 1 of 1', '9', 'Free Throw - 1 of 1', home=6, away=2,
         shootingPlay=True, scoringPlay=True, scoreValue=1, pointsAttempted=1),
    play(2, '10:00', 'Isaac Okoro enters the game for Lachlan Olbrich', '3', 'Substitution', home=6, away=2),
]


def test_player_stats_from_play_by_play():
    s = player_stats(PLAYS, '9', 'Lachlan Olbrich', 'home')
    # on court 5:00-0:30 of Q1 (4.5 min) and from the start of Q2 to 10:00 (2 min)
    assert s['minutes'] == '6'
    assert s['points'] == '4'
    assert s['fieldGoalsMade-fieldGoalsAttempted'] == '1-2'          # the blocked layup counts as an attempt
    assert s['threePointFieldGoalsMade-threePointFieldGoalsAttempted'] == '1-1'   # 'pointsAttempted', not wording
    assert s['freeThrowsMade-freeThrowsAttempted'] == '1-1'
    assert (s['rebounds'], s['offensiveRebounds'], s['assists'], s['blocks']) == ('1', '1', '1', '1')
    assert (s['turnovers'], s['steals'], s['fouls']) == ('1', '0', '1')
    assert s['plusMinus'] == str(5 - 2 + 1)


def test_missing_player_found_by_short_name():
    found = missing_player(PLAYS, '4', 'Olbrich', known_ids={'1', '3'})
    assert found == {'id': '9', 'displayName': 'Lachlan Olbrich'}
    assert missing_player(PLAYS, '4', 'Nobody', known_ids=set()) is None
