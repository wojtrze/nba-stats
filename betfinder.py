from bet_fetcher import *
from bet_analizator import *
from espn_scraper import *
from superbet_fetcher import all_today_props


def check_bet(bet, season_start_yyyy = None):
    players = game_players(bet['home'], bet['away'])
    player_name_to_check = bet['name_ESPN']
    player_df = players[(players['player_name'] == player_name_to_check)].copy()
    player_df['ARP'] = player_df['AST'] + player_df['REB'] + player_df['PTS']
    player_df['PA'] = player_df['PTS'] + player_df['AST']
    player_df['PR'] = player_df['PTS'] + player_df['REB']
    if season_start_yyyy is not None:
        player_df = player_df[player_df['season_id'] == int(season_start_yyyy)]
    if player_df.empty:
        return f"{player_name_to_check:>16} {bet['bet_type']} betline: {bet['line']:<5} no gamelogs found"
    lower_bound = player_df[bet['bet_type']].quantile(0.30)
    upper_bound = player_df[bet['bet_type']].quantile(0.70)
    is_in_percentiles = lower_bound <= bet['line'] <= upper_bound
    return f"{player_name_to_check:>16} {bet['bet_type']} betline: {bet['line']:<5} is_in_percentiles:{is_in_percentiles} ({lower_bound:>4} - {upper_bound:>4}, {len(player_df)} games)"


if __name__ == '__main__':
    bets = all_today_props()
    print(f"{len(bets)} offers")
    checked = set()
    for bet in bets:
        # over and under share the same line, check it once
        key = (bet['name_ESPN'], bet['bet_type'], bet['line'])
        if key in checked:
            continue
        checked.add(key)
        print(check_bet(bet))
