from bet_fetcher import *
from bet_analizator import *
from gamelogs_fetcher import *


def check_bet(bet, season_start_yyyy = None):
    players = game_players(bet['home'], bet['away'])
    player_name_to_check = bet['name_ESPN']
    player_df = players[(players['player_name'] == player_name_to_check)] # tu może copy deep
    player_df['ARP'] = player_df['AST'] + player_df['REB'] + player_df['PTS']
    if season_start_yyyy is not None:
        player_df = player_df[player_df['season_id'] == 2021]
    describe_df = player_df.describe(percentiles=[0.35, 0.5, 0.65])
    lower_bound = player_df['ARP'].quantile(0.30)
    upper_bound = player_df['ARP'].quantile(0.70)
    is_in_percentiles = lower_bound <= bet['line'] <= upper_bound
    return f"{player_name_to_check:>16} betline: {bet['line']:<5} is_in_percentiles:{is_in_percentiles} ({lower_bound:>4} - {upper_bound:>4})"


if __name__ == '__main__':
    bets = all_today_bets()
    print(bets)
    for bet in bets:
        check_bet(bet)
