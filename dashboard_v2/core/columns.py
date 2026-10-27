"""The columns the props tables show, kept here so their headers and tooltips (i18n.TERMS) can be tested."""

# the columns that decide a bet, in reading order: which line, the pick and its signal, why
PROPS_MAIN = ['name', 'game', 'tip-off', 'bet_type', 'line', 'bet', 'signal', 'lean', 'edge pp', 'ev 100',
              'best side', 'pick odds', 'model %', 'proj avg', 'pick % L10', 'RotoWire', 'red flag']
# Props → More → Show every column
PROPS_MORE = ['edge low', 'break-even %', 'market %', 'line move', 'open line', 'adj avg', 'avg', 'avg L5', 'matchup',
              'spread', 'game total', 'percentile', 'pick %', 'games', 'min L5', 'raw model %', 'over_odds',
              'under_odds']
# Overview → best player lines
OVERVIEW_PROPS = ['name', 'bet_type', 'line', 'bet', 'signal', 'ev 100', 'model %', 'edge pp', 'pick odds',
                  'RotoWire']

# Games: one row per game, then the chosen game's bets and each team's absences
GAMES_SUMMARY = ['game', 'start (PL)', 'proj winner', 'proj score', 'proj total', 'best bet', 'signal', 'best edge pp',
                 'best odds', 'RotoWire']
GAMES_MARKETS = ['market', 'team', 'side', 'line', 'signal', 'edge pp', 'odds', 'odds move', 'implied %', 'model %',
                 'fair odds', 'red flag']
GAMES_ABSENCES = ['out', 'games missed', 'team pts change', 'opp pts change']
# Results: every settled line, and the columns of the rates tables (metrics.grouped_rates, tracking.results_table /
# threshold_table) next to the group they're split by
RESULTS_ALL = ['game_date', 'name', 'game', 'bet_type', 'line', 'pre avg', 'pre avg L10', 'pre games', 'proj_avg',
               'actual', 'status', 'pre avg side', 'pre avg result', 'pick', 'result', 'over_odds', 'under_odds',
               'last line']
RESULTS_BY_TYPE = ['bet_type', 'lines', 'over %', 'line error', 'line − avg', 'toward avg hit %', 'toward avg ROI %',
                   'toward proj hit %']
RATE_COLUMNS = ['bets', 'expected %', 'hit %', 'ci low %', 'ci high %', 'ROI %', 'avg odds', 'avg odds vs last %',
                'edge ≥ pp', 'signal', 'edge bucket', 'pick', 'market']
