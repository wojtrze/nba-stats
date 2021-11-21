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

def all_nba_players():
    players = pd.DataFrame
    for team_id in ['bos', 'bkn', 'det']:
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
