"""The columns the props tables show, kept here so their headers and tooltips (i18n.TERMS) can be tested."""

# the props table, in reading order: which line, the decision for its game, the evaluated side and its price after
# the stake tax. One side column only: no 'our pick', 'better side' and 'projection leans' next to each other
PROPS_MAIN = ['tier', 'name', 'game', 'tip-off', 'bet_type', 'line', 'decision', 'side', 'side odds', 'p win %',
              'break-even net %', 'edge net pp', 'ev net 100', 'proj avg', 'pick % L10', 'RotoWire', 'red flag']
# Props → More → Show every column
PROPS_MORE = ['p push %', 'line move', 'open line', 'adj avg', 'avg', 'avg L5', 'matchup', 'spread',
              'game total', 'percentile', 'pick %', 'games', 'min L5', 'raw model %', 'over_odds', 'under_odds']
# Overview: the offers to bet, only those of a 'Bet' decision (none while no threshold is recorded)
OVERVIEW_PROPS = ['name', 'game', 'bet_type', 'line', 'side', 'side odds', 'p win %', 'edge net pp', 'ev net 100',
                  'RotoWire']
# Overview: the night's best lines by expected return (decisions.shortlist), shown while no offer is 'Bet'
SHORTLIST = ['tier', 'name', 'game', 'tip-off', 'bet_type', 'line', 'side', 'side odds', 'p win %', 'side market %',
             'above price pp', 'ev net 100', 'wait']

# Games: one row per game, then the chosen game's bets and each team's absences
GAMES_SUMMARY = ['game', 'start (PL)', 'decision', 'players', 'proj winner', 'proj score', 'proj total', 'RotoWire']
GAMES_MARKETS = ['market', 'team', 'side', 'line', 'odds', 'odds move', 'market %', 'model %', 'fair odds',
                 'break-even net %', 'edge net pp', 'ev net 100', 'red flag']
GAMES_ABSENCES = ['out', 'games missed', 'team pts change', 'opp pts change']
# Results: every settled line, and the columns of the rates tables (metrics.grouped_rates, tracking.results_table /
# threshold_table) next to the group they're split by
RESULTS_ALL = ['game_date', 'name', 'game', 'bet_type', 'line', 'pre avg', 'pre avg L10', 'pre games', 'proj_avg',
               'actual', 'status', 'pre avg side', 'pre avg result', 'pick', 'result', 'over_odds', 'under_odds',
               'last line']
RESULTS_BY_TYPE = ['bet_type', 'lines', 'over %', 'line error', 'line − avg', 'toward avg hit %', 'toward avg ROI %',
                   'toward proj hit %']
RATE_COLUMNS = ['bets', 'expected %', 'hit %', 'ci low %', 'ci high %', 'ROI %', 'ROI % std', 'break-even %',
                'break-even % std', 'avg odds', 'avg odds vs last %', 'edge ≥ pp', 'signal', 'edge bucket', 'pick',
                'market']
