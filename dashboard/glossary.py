"""Column labels and tooltips shared by the dashboard's tables, so every number explains itself on hover."""
from typing import Dict, Optional

import pandas as pd
import streamlit as st

# box-score stats, as stored in the game logs
STAT_HELP = {
    'PTS': "Points", 'REB': "Rebounds (offensive + defensive)", 'AST': "Assists", '3PM': "Three-pointers made",
    '3PA': "Three-pointers attempted", 'PA': "Points + assists", 'PR': "Points + rebounds",
    'RA': "Rebounds + assists", 'ARP': "Points + rebounds + assists (PRA)", 'STL': "Steals", 'BLK': "Blocks",
    'TO': "Turnovers", 'FGM': "Field goals made (2s and 3s)", 'FGA': "Field goals attempted (2s and 3s)",
    'FTM': "Free throws made", 'FTA': "Free throws attempted", 'PF': "Personal fouls", 'MIN': "Minutes played",
    'OREB': "Offensive rebounds", 'DREB': "Defensive rebounds",
    'PLUS_MINUS': "Team's points minus opponent's points while the player was on court",
}

HELP = STAT_HELP | {
    # game log
    'Date': "Game date (US Eastern)", 'OPP': "Opponent", 'type': "Home or away",
    'Result': "Win/loss and final score from the player's team's point of view",
    'season_type': "pre = preseason, regular, playin, post = playoffs", 'starter': "Started the game",
    'rest_days': "Days since the player's previous game (1 = back-to-back)",

    # Today's props
    'game': "Away @ home", 'name': "Player", 'bet_type': "Stat the line is on (hover the stat names in the Player "
                                                         "page's game log for what each one means)",
    'RotoWire': "Tonight's role from RotoWire: starter (✔ = lineup confirmed), bench, or the injury tag with the "
                "chance to play (Out 0%, Ques 50%…). Empty when RotoWire doesn't list the game yet.",
    'line': "Bookmaker's line: Over wins above it, Under below it",
    'over_odds': "Superbet's decimal odds for Over. Implied chance = 1 / odds.",
    'under_odds': "Superbet's decimal odds for Under. Implied chance = 1 / odds.",
    'games': "Number of games behind the numbers in this row",
    'avg': "Player's average of this stat in the games shown (sidebar seasons and game types)",
    'adj avg': "avg plus the player's usual change when tonight's out teammates miss games, shrunk toward 0 "
               "when there are few such games. Equal to avg when nobody is out. Uses RotoWire's out list as input.",
    'avg L5': "Average over the player's last 5 games",
    'over %': "Share of games above the line", 'under %': "Share of games below the line",
    'over % L10': "Share of the last 10 games above the line", 'under % L10': "Share of the last 10 games below the line",
    'percentile': "Where the line sits in the player's results: share of games below it (50 = at the median, "
                  "80 = the player beat it only 20% of the time)",
    'in band': "Line is between the player's 30th and 70th percentile. Outside the band = the line looks unusually "
               "low or high for this player.",
    'best side': "The side (Over/Under) with the bigger edge: the one to consider betting",
    'pick odds': "Superbet's odds for the picked side",
    'source': "Where the name comes from", 
    'edge pp': "model % minus break-even %, in percentage points: how much more often the pick should win than "
               "the price needs. +5 = wins 5 pp more often than needed to break even.",
    'edge low': "The edge at the low end of the model's 95% range. Above 0 = positive even if the player's "
                "results so far were on the lucky side; few games make the range wide.",
    'break-even %': "Chance the pick must win to break even at Superbet's odds: 100 / odds (margin included)",
    'market %': "Superbet's chance for the pick with the bookmaker's margin removed, so Over + Under = 100%",
    'signal': "🟢 the edge stays positive even at the low end of the range; 🟡 positive edge, but the range "
              "reaches below break-even (too little data to be sure)",
    'min L5': "Average minutes over the last 5 games: falling minutes are a warning sign for Overs",
    'open line': "The line when daily_snapshot.py first saw it",
    'line move': "Current line minus the opening line: + = the line went up (the market expects more), − = down. "
                 "Empty without an earlier snapshot.",
    'proj avg': "adj avg × the game factors: Superbet's implied team total vs the team's usual points, and what "
                "the opponent allows to the player's position vs the league. Each counts half and at most ±8%.",
    'matchup': "soft / tough: the opponent allows at least 5% more / less of this stat to the player's position "
               "than the average NBA defense",
    'spread': "The player's team handicap on Superbet's main line: −8.5 = favoured by 8.5. 10+ either way = "
              "blowout risk, when starters sit the fourth quarter.",
    'game total': "Superbet's main total points line for the game",
    'odds move': "Current odds minus the first snapshot's for the same outcome and line: falling odds = money "
                 "came in on it",
    'line moves': "Superbet's main home handicap and total, first snapshot → now",

    # Games
    'start (PL)': "Tip-off, Polish time; ⏰ = within the next hour",
    'tip-off': "Tip-off, Polish time; ⏰ = within the next hour. Lines leave the page when the game starts.",
    'proj score': "Projected score, away – home",
    'proj winner': "Team the projection favours and by how many points",
    'proj total': "Projected combined points",
    'best bet': "The market outcome with the biggest model edge in this game",
    'best edge pp': "Model chance minus the chance implied by Superbet's odds (1/odds) for the best bet, in "
                    "percentage points",
    'market': "Moneyline = who wins (incl. overtime); Handicap = winner after adding the line to the team's score; "
              "Total / team totals = combined or one team's points (incl. overtime)",
    'team': "Team the outcome is about", 'side': "home/away for moneyline and handicap, over/under for totals",
    'odds': "Superbet's decimal odds", 'implied %': "Chance implied by the odds: 100 / odds (includes the "
                                                    "bookmaker's margin, so both sides add up to ~105%)",
    'model %': "Chance from the projection (team ratings from the scraped games + RotoWire absences), assuming results scatter around it like they did last season "
               "(margin ±14, total ±18, team total ±11.5 points)",
    'fair odds': "Odds that would match the model's chance: 100 / model %. Bet only when Superbet pays more.",
    'out': "Player RotoWire lists as out tonight", 'games missed': "Team games this player missed while on the "
                                                                   "team, which the change is based on",
    'team pts change': "How many more (+) or fewer (−) points the team scored without this player, shrunk by "
                       "sample size",
    'opp pts change': "How many more (+) or fewer (−) points opponents scored without this player, shrunk by "
                      "sample size",

    # Lineup lab scenario
    'Out': "Tick to mark the player out tonight and see how everyone else's estimate shifts",
    'role': "Starter / Bench in tonight's lineup, or Out",
    'usual': "Player's average of this stat for this team in the games shown",
    'exact match': "Average in team games where all five chosen starters played and everyone marked out missed – "
                   "the closest real-life match to tonight, but often only a few games",
    'exact games': "Number of exact-match games", 'estimate': "usual + the sum of each absence's with/without "
                                                              "change, shrunk by sample size",
    'change': "estimate − usual", 'usual MIN': "Usual minutes per game", 'exact MIN': "Minutes in exact-match games",
    'confidence': "How many games the estimate rests on: high = 10+, medium = 4–9, low = fewer",

    # Player page
    'split': "How the games are divided", 'value': "Group within the split",
    'median': "Middle value: half the games were above, half below",
    'last': "Most recent game against this opponent",
    'minutes': "Average minutes", 'shots': "Average field-goal attempts",

    # Teams
    'G': "Allowed to opponents' guards, per game", 'F': "Allowed to opponents' forwards, per game",
    'C': "Allowed to opponents' centers, per game",
    'G vs avg': "How much more (+) or less (−) this defense allows to guards than the average NBA defense (+ = soft matchup for guards' Overs)",
    'F vs avg': "How much more (+) or less (−) this defense allows to forwards than the average NBA defense (+ = soft matchup for forwards' Overs)",
    'C vs avg': "How much more (+) or less (−) this defense allows to centers than the average NBA defense (+ = soft matchup for centers' Overs)",
    'wins': "Wins", 'losses': "Losses", 'home': "Home record (wins-losses)", 'pts': "Points scored per game",
    'opp_pts': "Points allowed per game", 'pace': "Possessions per game (both teams averaged)",
    'off_rtg': "Offensive rating: points scored per 100 possessions",
    'def_rtg': "Defensive rating: points allowed per 100 possessions (lower is better)",
    'net_rtg': "Offensive minus defensive rating: points per 100 possessions better than opponents",

    # Rule backtest
    'rule': "Rule from bet_analyst.py", 'vote': "agrees = bets in the direction the rule voted; disagrees = the "
                                                "opposite direction",
    'bets': "Number of bets", 'hit %': "Share of bets that won",
    'ci low %': "Lower end of the 95% confidence interval of the hit rate",
    'ci high %': "Upper end of the 95% confidence interval of the hit rate",
    'ROI %': "Profit per 100 units staked when betting 1 unit on each bet", 'avg odds': "Average decimal odds",
    'agree': "Rules that voted for the bet's side", 'against': "Rules that voted against the bet's side",
    'net': "agree − against",
    'pattern': "Which rules voted: +rule = for the bet's side, −rule = against",
    'over_under': "Over or Under", 'odds_bin': "Odds range",

    # Data status
    'season': "Season (starts in the first year)", 'last game': "Date of the newest stored game",
    'checked through': "Every game up to this date is stored; the next update starts the day after",
    'pre': "Preseason games", 'regular': "Regular-season games", 'playin': "Play-in games",
    'post': "Playoff games", 'allstar': "All-Star games (kept out of the regular-season stats)",
    'file': "Snapshot file", 'rows': "Rows stored", 'snapshots': "Number of times it was fetched",
    'note': "Injury tag or role",
}

LABELS = {
    'bet_type': "bet", 'best side': "pick", 'over_odds': "over odds", 'under_odds': "under odds", 'season_type': "game type",
    'PLUS_MINUS': "+/-", 'rest_days': "rest days", 'type': "home/away", 'off_rtg': "ORtg", 'def_rtg': "DRtg",
    'net_rtg': "net rtg", 'opp_pts': "opp pts", 'G': "guards", 'F': "forwards", 'C': "centers",
    'G vs avg': "guards vs NBA avg", 'F vs avg': "forwards vs NBA avg", 'C vs avg': "centers vs NBA avg",
    'over_under': "side", 'odds_bin': "odds", 'ARP': "PRA",
}


# --- where each number comes from ---
# A new data source only needs an entry here (icon, name, Streamlit colour, column tint) and its columns in
# COLUMN_SOURCE or a table's `sources`.
SOURCES = {
    'superbet': ('💰', "Superbet", 'orange', 'rgba(245, 158, 11, 0.12)'),
    'rotowire': ('📋', "RotoWire", 'blue', 'rgba(59, 130, 246, 0.12)'),
    'stats': ('📊', "Calculated from scraped NBA stats", 'green', 'rgba(16, 185, 129, 0.12)'),
}

# default source of a column; tables override it with `sources` where a name means something else
COLUMN_SOURCE = {
    'bet_type': 'superbet', 'line': 'superbet', 'over_odds': 'superbet', 'under_odds': 'superbet',
    'pick odds': 'superbet', 'odds': 'superbet', 'implied %': 'superbet', 'start (PL)': 'superbet', 'tip-off': 'superbet',
    'market %': 'superbet', 'break-even %': 'superbet', 'edge low': 'stats', 'open line': 'superbet',
    'line move': 'superbet', 'spread': 'superbet', 'game total': 'superbet', 'odds move': 'superbet',
    'line moves': 'superbet', 'proj avg': 'stats', 'matchup': 'stats',
    'RotoWire': 'rotowire', 'out': 'rotowire',
    'best side': 'stats', 'signal': 'stats', 'edge pp': 'stats', 'games': 'stats', 'avg': 'stats',
    'adj avg': 'stats', 'avg L5': 'stats', 'over %': 'stats', 'under %': 'stats', 'over % L10': 'stats',
    'under % L10': 'stats', 'percentile': 'stats', 'in band': 'stats', 'min L5': 'stats',
    'proj score': 'stats', 'proj winner': 'stats', 'proj total': 'stats', 'best bet': 'stats',
    'best edge pp': 'stats', 'model %': 'stats', 'raw model %': 'stats', 'fair odds': 'stats', 'games missed': 'stats',
    'team pts change': 'stats', 'opp pts change': 'stats',
}


def source_legend(keys=tuple(SOURCES)) -> str:
    """Markdown legend of the sources, coloured like the column tints: put it in st.caption above a table."""
    return "  ".join(f"{SOURCES[k][0]} :{SOURCES[k][2]}-background[{SOURCES[k][1]}]" for k in keys)


def column_config(columns, formats: Optional[Dict[str, str]] = None, tips: Optional[Dict[str, str]] = None,
                  base: Optional[dict] = None, sources: Optional[Dict[str, Optional[str]]] = None) -> dict:
    """column_config for st.dataframe / st.data_editor: a tooltip and readable label for every known column,
    number formats from `formats` ({column: '%.1f'}), page-specific tooltips from `tips`. Columns with a source
    (COLUMN_SOURCE, overridden by `sources`; None = no source mark) get its icon in the label and its name in the
    tooltip. Entries in `base` (e.g. a CheckboxColumn) are kept as they are."""
    formats, tips, base, sources = formats or {}, tips or {}, dict(base or {}), sources or {}
    for col in columns:
        if col in base:
            continue
        text = tips.get(col, HELP.get(col))
        label = LABELS.get(col, col)
        source = sources.get(col, COLUMN_SOURCE.get(col))
        if source:
            icon, name = SOURCES[source][:2]
            label = f"{icon} {label}"
            text = f"Source: {name}. {text or ''}".strip()
        if col in formats:
            base[col] = st.column_config.NumberColumn(label, help=text, format=formats[col])
        else:
            base[col] = st.column_config.Column(label, help=text)
    return base


def tinted(df: pd.DataFrame, formats: Optional[Dict[str, str]] = None,
           sources: Optional[Dict[str, Optional[str]]] = None):
    """df as a Styler with each sourced column tinted in its source's colour (same columns as column_config).
    Number formats are applied here too, since a Styler's display values replace column_config formats."""
    formats, sources = formats or {}, sources or {}
    styler = df.style
    for col in df.columns:
        source = sources.get(col, COLUMN_SOURCE.get(col))
        if source:
            styler = styler.set_properties(subset=[col], **{'background-color': SOURCES[source][3]})
    printf = {c: (lambda f: lambda v: '–' if pd.isna(v) else f % v)(f) for c, f in formats.items() if c in df.columns}
    return styler.format(printf, na_rep='–')
