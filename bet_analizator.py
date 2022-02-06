# game analysis
import re
from random import randint
from time import sleep
from pandasgui import show
from datetime import datetime, timedelta

# import link as link
import requests
from bet_fetcher import *
from bs4 import BeautifulSoup
import pandas as pd

home_8_rotation = [4066218, 4065648, 4066211, 2990992, 3917376, 3032979, 4066354, 4397008]
away_8_rotation = [3934719, 4433134, 3423, 2991230, 2578240, 4277843, 4431679, 3948153]

pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)
pd.set_option("expand_frame_repr", True)


# returns df with player gamelogs for home and away team
def game_players(home, away):
    home_df = pd.read_csv(f'team-{home}.csv')
    home_df['gametype'] = 'home'
    home_df['gameopp'] = away.upper()
    away_df = pd.read_csv(f'team-{away}.csv')
    away_df['gametype'] = 'away'
    away_df['gameopp'] = home.upper()
    return pd.concat([home_df, away_df])


def stored_bets():
    return pd.read_csv("bets.csv")


def all_nba_players():
    teams = [
        'bos',
        'bkn',
        'ny',
        'phi',
        'tor',
        'chi',
        'cle',
        'det',
        'ind',
        'mil',
        'den',
        'min',
        'okc',
        'por',
        'utah',
        'gs',
        'lac',
        'lal',
        'phx',
        'sac',
        'atl',
        'cha',
        'mia',
        'orl',
        'wsh',
        'dal',
        'hou',
        'mem',
        'no',
        'sa']

    players = pd.DataFrame()
    for team_id in teams:
        team_players = pd.read_csv(f'team-{team_id}.csv')
        players = pd.concat([players, team_players])
    # TODO data objects introduction
    return players


# selects only direct matchups (player against current opponent team)
def direct_matchups(plr_df):  # TODO -> dataframe - general type annotations
    return plr_df[plr_df['gameopp'] == plr_df['OPP']]


def add_columns(plr_df):
    plr_df['ARP'] = plr_df['AST'] + plr_df['REB'] + plr_df['PTS']
    plr_df['PTS36'] = plr_df['PTS'] / plr_df['MIN'] * 36
    plr_df['ARP36'] = plr_df['ARP'] / plr_df['MIN'] * 36
    plr_df['lost_ponints'] = 2 * ((plr_df['FGA'] - plr_df['3PA']) - (plr_df['FGM'] - plr_df['3PM'])) + (
            plr_df['FTA'] - plr_df['FTM']) + 3 * (plr_df['3PA'] - plr_df['3PM'])
    plr_df['plusminus'] = plr_df['PTS'] - plr_df['lost_ponints']
    return plr_df


# dataframe z grami georga, gdzie nie grałKawhi vs gdzie grał
# without_player(players_df, player_to_check, 'KawhiLeonard').describe(percentiles=[0.35, 0.5, 0.65])
# FIXME fetching all nba playes is needed here
def without_player(df, player, player_b):
    when_player_b_didnt_play = pd.DataFrame()
    player_games = df[df['player_name'] == player]
    player_b_games = df[df['player_name'] == player_b]
    delete_when_play_together = pd.concat([player_games, player_b_games]).drop_duplicates(subset=['Date'], keep=False)
    when_player_b_didnt_play = delete_when_play_together[delete_when_play_together['player_name'] == player]
    return when_player_b_didnt_play


# returns type:dict bet data concatenated with: over_rating, under_rating, over_count, under_count
# FIXME duplicated fields from debt and previous rating system
def percentile_analysis(bet, desc="description", weight=1, seasons=None, location_sensitive=False, direct=False, last_x=None):
    players = game_players(bet['home'], bet['away'])

    player_name_to_check = bet['name_ESPN']
    bet_date = bet['changed_date']
    player_df = players[(players['player_name'] == player_name_to_check)]
    player_df = player_df[player_df["Date"] < bet_date[:10]]
    player_df['ARP'] = player_df['AST'] + player_df['REB'] + player_df['PTS']
    if seasons is not None:
        player_df = player_df[player_df['season_id'].isin(seasons)]
    if location_sensitive:
        player_df = player_df[player_df['gametype'] == player_df['type']]
    if direct:
        player_df = player_df[player_df['gameopp'] == player_df['OPP']]
    if last_x is not None:
        player_df = player_df.sort_values(by='Date', ascending=False).head(last_x)

    stats = bet['bet_type']
    lower_bound = player_df[stats].quantile(0.17)
    median_line = player_df[stats].quantile(0.50)
    upper_bound = player_df[stats].quantile(0.83)
    is_in_percentiles = lower_bound <= bet['line'] <= upper_bound
    lower_offset = lower_bound - bet['line']
    upper_offset = bet['line'] - upper_bound
    min_diff = min([abs(bet['line'] - lower_bound), abs(bet['line'] - upper_bound)])
    if is_in_percentiles:
        min_diff = 0 - min_diff
    uptolow = upper_bound - lower_bound
    offset_to_range = min_diff / uptolow
    # TODO: print(f"betline {bet['line']} divides resultset to {} percent below")
    game = f"{bet['away']} @ {bet['home']}"
    under_rating = weight * upper_offset
    over_rating = weight * lower_offset
    over_line_count = player_df[(player_df[stats] > bet['line'])].shape[0]
    under_line_count = player_df[(player_df[stats] < bet['line'])].shape[0]

    # returns partial scoring dict (bet analysis for certain part of games, e.g. Last 5 games home/away, vs opponent, etc.)
    # returned partial scoring contains over/under_rtg, quantile range, bet_offset, bet data, over/under_count
    # this is the place where all parameters to be taken into analysis of Prediction(scoring) and PredAc Predicdtion Assessment Accuracy
    if type(bet) != dict:
        bet = bet.to_dict()
    rating = {"player": player_name_to_check, "game": game, "type": bet['bet_type'], "betline": bet['line'], "desc": desc, "over_rtg": over_rating, "under_rtg": under_rating,
              "q20": lower_bound, "median": median_line, "q80": upper_bound, "under": lower_offset, "over": upper_offset, "range": uptolow,
              "offset_to_range": offset_to_range, "seasons": seasons, "location": location_sensitive, "direct": direct,
              "last_x": last_x, "bet_date": bet_date, "over_count": over_line_count, "under_count": under_line_count, "date": bet['changed_date'][:10]}
    return bet | rating


def betline_based_analysis():
    pass


def bet_result_based_analysis():
    pass


def form_tracking_analysis():
    pass


def this_season_analysis(bets):
    # returns list of bet+rating type:dict
    # TODO rename check_bet to percentile_scorings
    # TODO put each analysis in the way that allow exclude, compare. is list of dicts the best available solution?
    list_of_concatenated_bets_and_ratings = []
    for b in bets:
        list_of_concatenated_bets_and_ratings.append(percentile_analysis(b, desc="LG3", weight=1, seasons=[2021], last_x=3))  # ostatnie 4 mecze. priorytet 1.
        list_of_concatenated_bets_and_ratings.append(percentile_analysis(b, desc="LG14", weight=1, seasons=[2021], last_x=14))  # ostatnie 4 mecze. priorytet 1.
        list_of_concatenated_bets_and_ratings.append(percentile_analysis(b, desc="LG7-GLOC", weight=1, seasons=[2021], location_sensitive=True,
                                                                         last_x=7))  # ostatnie 4 gry home/away dla bieżącego zakładu. priorytet 2. pokazuje wypływ home/away. do porównania z LG8 i LG4 priorytet 2
        # list_of_concatenated_bets_and_ratings.append(betline_based_analysis())  # how many times he went over the line, how many under (in last period)
        # list_of_concatenated_bets_and_ratings.append(bet_result_based_analysis())  # how many times bet results for him were over, how many under
        # list_of_concatenated_bets_and_ratings.append(form_tracking_analysis())  # wykres arp i pts uśredniony z 8-dniowych okresów
        # list_of_analysis_dicts.append(check_bet(b, desc="LG20", weight=1, seasons=[2021], last_x=20)) # ostatnie 10 meczy, żeby porównać to  L4G, czy jest duża różnica. Jak nie ma różnicy, to szacowanie jest pewniejsze. priorytet 3
        list_of_concatenated_bets_and_ratings.append(percentile_analysis(b, desc="LG3OPP", weight=1, seasons=[2021], last_x=3, direct=True)) # ostatnie osiem meczy, żeby porównać to  L4G, czy jest duża różnica. Jak nie ma różnicy, to szacowanie jest pewniejsze. priorytet 3
        # list_of_analysis_dicts.append(check_bet(b, desc="LG12", weight=3, seasons=[2021], last_x=12)) # oczekiwania względem sezonu priorytet 4
    return list_of_concatenated_bets_and_ratings


def players_in_bets(bets):
    # players = game_players(bet['home'], bet['away'])
    players = pd.DataFrame()
    for bet in bets:
        player_glogs_for_panda = players_by_bet(bet)
        if bet["name_ESPN"] in players:
            continue
        players = pd.concat([players, player_glogs_for_panda])
    players = players.drop_duplicates(subset=["Date", "player_id"])
    return players[["player_name", "team", "OPP", "MIN", "ARP", "ARP36", "FG%", "FGA", "FGM", "PTS", "PTS36", "REB", "AST", "Date", "type"]]


def bets_scoring_df(bets):
    this_season_dict_list = this_season_analysis(bets)  # 4 analizy l5g, l5g loc, etc.
    partial_scores_df = pd.DataFrame(this_season_dict_list)
    scoring_df = partial_scores_df.groupby(['player', 'type'], as_index=False).agg(
        {'over_rtg': 'mean', 'under_rtg': 'mean', 'player': 'first', 'game': 'first', 'type': 'first', 'q20': 'mean', 'betline': 'first', 'q80': 'mean', 'under_count': 'sum',
         'over_count': 'sum', 'date': 'first'})
    return scoring_df


def players_by_bet(bet, seasons=None, location_sensitive=False, direct=False):
    players = game_players(bet['home'], bet['away'])
    player_name_to_check = bet['name_ESPN']
    player_df = players[(players['player_name'] == player_name_to_check)]
    player_df['ARP'] = player_df['AST'] + player_df['REB'] + player_df['PTS']

    player_df['ARP36'] = player_df['ARP'] / player_df['MIN'] * 36
    player_df['PTS36'] = player_df['PTS'] / player_df['MIN'] * 36
    if seasons is not None:
        player_df = player_df[player_df['season_id'].isin(seasons)]
    if location_sensitive:
        player_df = player_df[player_df['gametype'] == player_df['type']]
    return player_df


def check_scorings_accuracy(scoring_df):
    pass


def describe_with_insights_t(df):
    # produces describe table allowing to make some choices on betting
    # dataframes can be produced to show diff direct player vs global player stats
    df['games_count'] = df.count()  # coś to nie działa
    df_desc = df.describe(percentiles=[0.35, 0.5, 0.65])
    df_desc['deviation-to-mean'] = df_desc['std'] / df_desc['mean']
    df_desc['between_percentiles_BP'] = df_desc['65%'] - df_desc['35%']
    df_desc['percentiles_to_full_range_ratio'] = df_desc['between_percentiles_BP'] / df_desc['max'] - df_desc['min']
    df_desc = df_desc.T
    return df_desc


def player_desc_for_df(df, player_name):
    return df[df['player_name'] == player_name].describe(percentiles=[0.35, 0.5, 0.65])


def provide_stored_bet_results(b):
    list_of_results = []
    # b = stored_bets()  # .to_dict('records'), już nie pamiętam czemu
    # all_players = all_nba_players() # fixme coś nie działa, a w ogole trzeba to przemyśleć
    for index, row in b.iterrows():
        all_players = game_players(row['home'], row['away'])
        bet_analysis_dict = {}
        bet_date = row['changed_date'][:10]
        bet_player = row['name_ESPN']
        bet_type = row['bet_type']
        bet_line = row['line']
        dfn = all_players[(all_players['player_name'] == bet_player)]
        dfd = all_players[(all_players['Date'] == bet_date)]
        player_df = all_players[(all_players['player_name'] == bet_player) & (all_players['Date'] == bet_date)]
        if player_df.empty:
            bet_date = (datetime.strptime(bet_date, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')
            player_df = all_players[(all_players['player_name'] == bet_player) & (all_players['Date'] == bet_date)]
            if player_df.empty:
                # TODO: print(f"gamelog not found for {bet_player} on {bet_date} {row['away']}@{row['home']}")
                continue
            print(f"gamelog issue")
        # jakiś wyjątek, jak nie ma playera
        actual = 0
        if bet_type == "PTS":
            actual = player_df["PTS"]
        if bet_type == "ARP":
            actual = player_df["PTS"] + player_df["REB"] + player_df["AST"]
        actual = int(actual)
        if actual > bet_line:
            result = "over"
        else:
            result = "under"
        bet_result = row
        # extend with result data
        bet_result["diff"] = actual - bet_line
        bet_result["actual"] = actual
        bet_result["result"] = result
        # zrób scoring i załącz do betu ratingi, ovr/undr
        # bet_analysis_dict["ovr_rating"] = "na"
        # bet_analysis_dict["undr_rating"] ="na"
        # bet_analysis_dict["ovr_count"] ="na"
        # bet_analysis_dict["undr_count"] ="na"
        list_of_results.append(bet_result)

    return list_of_results


def provide_results_with_bet_scoring(list_of_results):
    # parametr wejściowy ma w sobie wyniki list_of_results, bo to one służą do porównania względem scoringówn
    # results and scoring important data
    # list_of_scorings = bets_scoring_df(bets) # scoring + over under ratings dla każdego zakładu
    list_of_results_with_scoring = this_season_analysis(list_of_results)
    # FIXME złączyć wyniki zakładów ze scoringiem  określonym w
    # for index, row in list_of_results.iterrows():
    #     scored_bet_wit_result = row
    #     this_season_analysis(bets)
    # list_of_results_with_scoring = list_of_scorings + list_of_results
    return list_of_results_with_scoring


if __name__ == '__main__':
    bets_df = stored_bets()  # FIXME
    bets = bets_df.to_dict('records')
    # bets = all_today_bets()
    # assessments = bets_scoring_df(bets)
    # assessments - scoring, data, itp. Trzeba pobrać wyniki po dacie i sprawdzić wynik
    # print(assessments)
    bets = stored_bets()
    # bets_scorings = this_season_analysis(bets)
    bets_results = provide_stored_bet_results(bets)
    scored_bets_results = provide_results_with_bet_scoring(bets_results)
    print(scored_bets_results)

    bets = stored_bets()
    scored_bets_results = provide_results_with_bet_scoring(provide_stored_bet_results(bets))
    show(pd.DataFrame(scored_bets_results))
