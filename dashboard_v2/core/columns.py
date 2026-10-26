"""The columns the props tables show, kept here so their headers and tooltips (i18n.TERMS) can be tested."""

# the columns that decide a bet, in reading order: which line, the pick and its signal, why
PROPS_MAIN = ['name', 'game', 'tip-off', 'bet_type', 'line', 'bet', 'signal', 'lean', 'edge pp', 'best side',
              'pick odds', 'model %', 'proj avg', 'pick % L10', 'RotoWire', 'red flag']
# Props → More → Show every column
PROPS_MORE = ['edge low', 'break-even %', 'market %', 'line move', 'open line', 'adj avg', 'avg', 'avg L5', 'matchup',
              'spread', 'game total', 'percentile', 'pick %', 'games', 'min L5', 'raw model %', 'over_odds',
              'under_odds']
# Overview → best player lines
OVERVIEW_PROPS = ['name', 'bet_type', 'line', 'bet', 'signal', 'edge pp', 'pick odds', 'RotoWire']
