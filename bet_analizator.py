# game analysis
import re
from random import randint
from time import sleep
from pandasgui import show

# import link as link
import requests
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


def bet_result(bet):
    pass




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

    players = pd.DataFrame
    for team_id in teams:
        team_players = pd.read_csv(f'team-{team_id}.csv')
        players = pd.concat([players, team_players])
    return players


# selects only direct matchups (player against current opponent team)
def direct_matchups(plr_df):
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
def without_player(df, player, player_b):
    when_player_b_didnt_play = pd.DataFrame()
    player_games = df[df['player_name'] == player]
    player_b_games = df[df['player_name'] == player_b]
    delete_when_play_together = pd.concat([player_games, player_b_games]).drop_duplicates(subset=['Date'], keep=False)
    when_player_b_didnt_play = delete_when_play_together[delete_when_play_together['player_name'] == player]
    return when_player_b_didnt_play


# def assess_bet(bet):
#     return bet_assessment

def check_bet(bet, desc="description", weight=1, seasons=None, location_sensitive=False, direct=False, last_x=None):
    players = game_players(bet['home'], bet['away'])

    player_name_to_check = bet['name_ESPN']
    player_df = players[(players['player_name'] == player_name_to_check)]
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
    # over_under = todo
    uptolow = upper_bound - lower_bound
    offset_to_range = min_diff / uptolow
    # print(f"betline {bet['line']} divides resultset to {} percent below")
    game = f"{bet['away']} @ {bet['home']}"
    under_rating = weight*upper_offset
    over_rating = weight*lower_offset
    bet_date = bet['changed_date']
    over_line_count = player_df[(player_df[stats] > bet['line'])].shape[0]
    under_line_count = player_df[(player_df[stats] < bet['line'])].shape[0]
    # with player_df[(player_df[stats] > bet['line'])] as over_df:
    #     over_line_count = over_df.shape[0]
    # with player_df[(player_df[stats] < bet['line'])] as under_df:
    #     under_line_count = under_df.shape[0]
    return {"player": player_name_to_check, "game": game, "type": bet['bet_type'], "betline": bet['line'], "desc": desc, "over_rtg": over_rating, "under_rtg": under_rating,
            "q20": lower_bound, "median": median_line, "q80": upper_bound, "under": lower_offset, "over": upper_offset, "range": uptolow,
            "offset_to_range": offset_to_range, "seasons": seasons, "location": location_sensitive, "direct": direct,
            "last_x": last_x, "bet_date": bet_date, "over_count": over_line_count, "under_count": under_line_count}
    # return f"{player_name_to_check:<17} betline: {bet['line']:<4} is_in_percentiles:{is_in_percentiles} ({lower_bound:.2f} - {upper_bound:.2f}) *** {min_diff:.2f}"


def this_season_analysis(bets):
    list_of_dicts = []
    for b in bets:
        list_of_dicts.append(check_bet(b, desc="LG3", weight=0.35, seasons=[2021], last_x=3)) # ostatnie 4 mecze. priorytet 1.
        list_of_dicts.append(check_bet(b, desc="LG5", weight=0.20, seasons=[2021], last_x=5)) # ostatnie 4 mecze. priorytet 1.
        list_of_dicts.append(check_bet(b, desc="LG5-GLOC", weight=0.35, seasons=[2021], location_sensitive=True, last_x=5)) # ostatnie 4 gry home/away dla bieżącego zakładu. priorytet 2. pokazuje wypływ home/away. do porównania z LG8 i LG4 priorytet 2
        list_of_dicts.append(check_bet(b, desc="LG15", weight=0.10, seasons=[2021], last_x=15)) # ostatnie 10 meczy, żeby porównać to  L4G, czy jest duża różnica. Jak nie ma różnicy, to szacowanie jest pewniejsze. priorytet 3
        #list_of_dicts.append(check_bet(b, desc="LG10", weight=3, seasons=[2021], last_x=8)) # ostatnie osiem meczy, żeby porównać to  L4G, czy jest duża różnica. Jak nie ma różnicy, to szacowanie jest pewniejsze. priorytet 3
        #list_of_dicts.append(check_bet(b, desc="LG12", weight=3, seasons=[2021], last_x=12)) # oczekiwania względem sezonu priorytet 4
    # todo można wyciągać jakieś wnioski z porównań
    # LG4-LOC vs LG4 - if there's no difference => players plays the same no matter the location.
    #                   if there's a difference => rule in bet_assesment
    return list_of_dicts

def all_seasons_analysis(bets):
    list_of_dicts = []
    for b in bets:
        list_of_dicts.append(check_bet(b, desc="S2021", seasons=[2021]))
        list_of_dicts.append(check_bet(b, desc="S2020", seasons=[2020]))
        list_of_dicts.append(check_bet(b, desc="LS2", seasons=[2020, 2021], location_sensitive=False))
        list_of_dicts.append(check_bet(b, desc="LS2-GLOC", seasons=[2020, 2021], location_sensitive=True))
        list_of_dicts.append(check_bet(b, desc="LS2-OPP", seasons=[2020, 2021], direct=True))
    return list_of_dicts

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

#
# nba = game_players(home='sa', away='den')
# player_to_check = "DejounteMurray"
# nba = add_columns(nba)
# nba['OPP'] = nba['OPP'].str.lower()
# nba.drop(nba[nba['season_id'] == 2017].index, inplace=True)
# direct = direct_matchups(nba)
# home = nba[nba['gametype'] == 'home']
# home_direct = direct[direct['gametype'] == 'home']
# away = nba[nba['gametype'] == 'away']
# away_direct = direct[direct['gametype'] == 'away']
# hhaa = nba[nba['gametype'] == nba['type']]
#
#
#
#
#
# hhaa[(hhaa['player_name'] == player_to_check)].describe()
#
# h8 = direct[(direct['gametype'] == direct['type']) & (direct['gametype'] == 'home') & (
#     direct.player_id.isin(home_8_rotation))]  # home team 8 rotation for games played at home
#
# a8 = direct[(direct['gametype'] == direct['type']) & (direct['gametype'] == 'away') & (
#     direct.player_id.isin(away_8_rotation))]  # away team 8 rotation for games played away
#
#
#
#
# direct[direct['player_name'] == player_to_check].describe(percentiles=[0.35, 0.5, 0.65])
#
# # players_df[(players_df['player_name'] == player_to_check) & (players_df['gametype'] == players_df['type'])].describe(
# #     percentiles=[0.35, 0.5, 0.65])  # only home or away
# hhaa[(hhaa['player_name'] == player_to_check)]['ARP'].hist(density=True, histtype='step')
# direct_matchups(hhaa[(hhaa['player_name'] == player_to_check)])['ARP'].hist(density=True, histtype='step')
