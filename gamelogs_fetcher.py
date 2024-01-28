# This is a sample Python script.
import re
from random import randint
from time import sleep
import requests
from bs4 import BeautifulSoup
import pandas as pd

MINSLEEP = 0
MAXSLEEP = 0
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:20.0) Gecko/20100101 Firefox/20.0'}


def get_game_boxscores(game_id, home_or_away):
    url = f'https://www.espn.com/nba/boxscore?gameId={game_id}'
    sleep(randint(MINSLEEP, MAXSLEEP))
    page = requests.get(url, headers)
    soup = BeautifulSoup(page.text, 'html.parser')
    table_body = soup.find_all('table')
    if home_or_away == 'home': result_df = pd.read_html(str(table_body))[1]
    if home_or_away == 'away': result_df = pd.read_html(str(table_body))[2]
    return result_df


def teams_ids():
    url = 'https://www.espn.com/nba/teams'
    sleep(randint(MINSLEEP, MAXSLEEP))
    page = requests.get(url, headers)
    soup = BeautifulSoup(page.text, 'html.parser')
    team_links = soup.find_all('a', attrs={'href': re.compile("^/nba/team/stats/_/name/")})
    return [f'{link.get("href").split("/")[-2]}' for link in team_links]


# Press the green button in the gutter to run the script.
def player_ids_for_team(team_id):
    sleep(randint(MINSLEEP, MAXSLEEP))
    team_page = requests.get(f'https://www.espn.com/nba/team/roster/_/name/{team_id}', headers)
    soup = BeautifulSoup(team_page.text, 'html.parser')
    player_links = soup.find_all('a', attrs={'href': re.compile("^https://www.espn.com/nba/player/_/id/")})
    player_ids = {}
    player_ids = [f'{link.get("href").split("/")[-2]}' for link in player_links]
    # return dict.fromkeys(player_ids)
    player_ids = list(dict.fromkeys(player_ids))  # removes duplicates
    return player_ids


def player_gamelog_url(player_id):
    return f'https://www.espn.com/nba/player/gamelog/_/id/{player_id}'


def scrap_gamelog_page(player_id, season_start_yyyy):
    sleep(randint(MINSLEEP, MAXSLEEP))
    players_gamelog_url = f"https://www.espn.com/nba/player/gamelog/_/id/{player_id}/type/nba/year/{int(season_start_yyyy) + 1}"
    pandas_html = pd.read_html(players_gamelog_url)

    # remove rubbish from each table
    filtered_gamelog = pd.DataFrame()
    for pd_table in pandas_html:
        # only tables that contain 'Date' are valid gamelog columns
        if 'Date' not in pd_table.columns:
            continue
        # add to the filter value, that error occurs (application exit )
        filt = (~pd_table['Date'].str.contains(
            'acquired|Finals|Play-In|Game|Conference|RISING|PRESEASON|january|february|march|april|may|june|july|august|september|october|november|december|from|LeBron|Canada Series',
            na=False, case=False))
        current_dataframe = pd_table[filt]
        filtered_gamelog = pd.concat([filtered_gamelog, current_dataframe])
    if len(filtered_gamelog) == 0:
        return filtered_gamelog

    # filtered_gamelog.reindex()
    filtered_gamelog[['FGM', 'FGA']] = filtered_gamelog['FG'].str.split('-', 1, expand=True)
    filtered_gamelog.drop('FG', axis=1, inplace=True)

    filtered_gamelog[['3PM', '3PA']] = filtered_gamelog['3PT'].str.split('-', 1, expand=True)
    filtered_gamelog.drop('3PT', axis=1, inplace=True)

    filtered_gamelog[['FTM', 'FTA']] = filtered_gamelog['FT'].str.split('-', 1, expand=True)
    filtered_gamelog.drop('FT', axis=1, inplace=True)

    filtered_gamelog['type'] = 'home'
    filtered_gamelog.loc[filtered_gamelog['OPP'].str.contains('@', na=False), 'type'] = 'away'

    filtered_gamelog['OPP'] = filtered_gamelog['OPP'].str.replace('vs', '')
    filtered_gamelog['OPP'] = filtered_gamelog['OPP'].str.replace('@', '')

    # prepare dates
    filtered_gamelog[['Day', 'mm-dd']] = filtered_gamelog['Date'].str.split(' ', 1, expand=True)
    filtered_gamelog.drop('Date', axis=1, inplace=True)
    filtered_gamelog.drop('Day', axis=1, inplace=True)
    filtered_gamelog[['mm', 'dd']] = filtered_gamelog['mm-dd'].str.split('/', 1, expand=True)
    filtered_gamelog['mm'] = pd.to_numeric(filtered_gamelog['mm'])
    filtered_gamelog.loc[filtered_gamelog['mm'] >= 9, 'yyyy'] = f'/{season_start_yyyy}'
    filtered_gamelog.loc[filtered_gamelog['mm'] < 9, 'yyyy'] = f'/{int(season_start_yyyy) + 1}'
    filtered_gamelog['Date'] = filtered_gamelog['mm-dd'] + filtered_gamelog['yyyy']
    filtered_gamelog['Date'] = pd.to_datetime(filtered_gamelog['Date'])
    filtered_gamelog.drop(['mm', 'mm-dd', 'dd', 'yyyy'], axis=1, inplace=True)

    # prepare stats
    filtered_gamelog['MIN'] = pd.to_numeric(filtered_gamelog['MIN'])
    filtered_gamelog['REB'] = pd.to_numeric(filtered_gamelog['REB'])
    filtered_gamelog['AST'] = pd.to_numeric(filtered_gamelog['AST'])
    filtered_gamelog['BLK'] = pd.to_numeric(filtered_gamelog['BLK'])
    filtered_gamelog['STL'] = pd.to_numeric(filtered_gamelog['STL'])
    filtered_gamelog['PF'] = pd.to_numeric(filtered_gamelog['PF'])
    filtered_gamelog['TO'] = pd.to_numeric(filtered_gamelog['TO'])
    filtered_gamelog['PTS'] = pd.to_numeric(filtered_gamelog['PTS'])
    filtered_gamelog['FGM'] = pd.to_numeric(filtered_gamelog['FGM'])
    filtered_gamelog['FGA'] = pd.to_numeric(filtered_gamelog['FGA'])
    filtered_gamelog['3PM'] = pd.to_numeric(filtered_gamelog['3PM'])
    filtered_gamelog['3PA'] = pd.to_numeric(filtered_gamelog['3PA'])
    filtered_gamelog['FTM'] = pd.to_numeric(filtered_gamelog['FTM'])
    filtered_gamelog['FTA'] = pd.to_numeric(filtered_gamelog['FTA'])
    filtered_gamelog['season_id'] = season_start_yyyy
    # print(f'Gamelog from {season_start_yyyy} fetched')
    season_start_date = "19/10/2022"
    filtered_gamelog = filtered_gamelog[filtered_gamelog['Date'] >= season_start_date]
    return filtered_gamelog


def retrieve_player_name(url):
    sleep(randint(0, 1))
    gamelog_response = requests.get(url, headers)
    bs_html = BeautifulSoup(gamelog_response.text, 'html.parser')
    player_name = bs_html.find_all("h1", {"class": "PlayerHeader__Name"})[0].text.strip()
    # player_status= bs_html.find_all("h1", {"class": "ml0"})[0].text.strip()

    return player_name


def player_gamelog(player_id):
    gamelog = pd.DataFrame()
    # beginning of season, makes no sense to look here
    # current_season_gamelog_1 = scrap_gamelog_page(f"https://www.espn.com/nba/player/gamelog/_/id/{player_id}",
    #                                               season_start_yyyy='2020')
    # gamelog = pd.concat([gamelog, current_season_gamelog_1])
    current_season_gamelog_0 = scrap_gamelog_page(
        f"https://www.espn.com/nba/player/gamelog/_/id/{player_id}/type/nba/year/2022", season_start_yyyy='2021')
    gamelog = pd.concat([gamelog, current_season_gamelog_0])
    current_season_gamelog_1 = scrap_gamelog_page(
        f"https://www.espn.com/nba/player/gamelog/_/id/{player_id}/type/nba/year/2021", season_start_yyyy='2020')
    gamelog = pd.concat([gamelog, current_season_gamelog_1])
    current_season_gamelog_2 = scrap_gamelog_page(
        f"https://www.espn.com/nba/player/gamelog/_/id/{player_id}/type/nba/year/2020", season_start_yyyy='2019')
    gamelog = pd.concat([gamelog, current_season_gamelog_2])
    current_season_gamelog_3 = scrap_gamelog_page(
        f"https://www.espn.com/nba/player/gamelog/_/id/{player_id}/type/nba/year/2019", season_start_yyyy='2018')
    gamelog = pd.concat([gamelog, current_season_gamelog_3])
    current_season_gamelog_4 = scrap_gamelog_page(
        f"https://www.espn.com/nba/player/gamelog/_/id/{player_id}/type/nba/year/2018", season_start_yyyy='2017')
    gamelog = pd.concat([gamelog, current_season_gamelog_4])
    gamelog['player_id'] = player_id
    gamelog['player_name'] = retrieve_player_name(f"https://www.espn.com/nba/player/gamelog/_/id/{player_id}")
    gamelog.reindex()
    return gamelog


def player_gamelog_for_season(player_id, season_start_yyyy='2022'):
    gamelog = pd.DataFrame()
    current_season_gamelog = scrap_gamelog_page(player_id, season_start_yyyy)
    gamelog = current_season_gamelog
    gamelog['player_id_ESPN'] = player_id
    gamelog['player_name_ESPN'] = retrieve_player_name(f"https://www.espn.com/nba/player/gamelog/_/id/{player_id}")
    return gamelog


def roster_page_url(team_id):
    pass


def get_gamelog_with_soup(player_id):
    sleep(randint(MINSLEEP, MAXSLEEP))
    gamelog_response = requests.get(f"https://www.espn.com/nba/player/gamelog/_/id/{player_id}", headers)
    bs_html = BeautifulSoup(gamelog_response.text, 'html.parser')
    all_log_tables = bs_html.find_all("div", {"class": "mb5"})
    partial_log_table = all_log_tables[1]  # przykładowa
    table_rows = partial_log_table.find_all('tr', attrs={'class': 'mb5'})
    l = []
    for tr in table_rows:
        td = tr.find_all('td')
        row = [tr.text for tr in td]
        l.append(row)
    return pd.DataFrame(l)


def get_last_fetching_date(team_id):
    team_game_dates_df = pd.DataFrame()
    team_game_dates_df = pd.read_csv(f'team-{team_id}.csv')
    # team_game_dates_df['Date'] = pd.to_datetime(team_game_dates_df['Date'])
    # return team_game_dates_df['Date'].max()
    return "2023/10/18"


def update_gamelogs():
    for team_id in teams:
        team_gamelogs_df = pd.DataFrame()
        player_id_list = player_ids_for_team(team_id)
        # print(f'for team {team_id} scrapping data for players: {player_id_list}')
        for player_espn_id in player_id_list:
            # print(f'processing player: {player_espn_id} from {team_id}')
            current_players_gamelog = player_gamelog_for_season(player_espn_id, season_start_yyyy='2022')
            current_players_gamelog['team'] = team_id
            # filter out already updated for current season - maybe to try-except
            try:
                if current_players_gamelog.empty:
                    print("empty gamelog")
                    continue
                if not current_players_gamelog.empty:
                    print(current_players_gamelog[['OPP', 'MIN', 'REB', 'AST', 'FG%',
                                                   'PTS', '3PM', 'type', 'Date', 'player_name_ESPN']].head(5))
            except:
                print("coś nie tak")
                print(current_players_gamelog)
            team_gamelogs_df = pd.concat([team_gamelogs_df, current_players_gamelog])
        df = pd.DataFrame(team_gamelogs_df)
        team_gamelogs_file = f'2022-players-logs.csv'
        df.to_csv(team_gamelogs_file, mode='a', header=True, index=False)
        # pd.read_csv(team_gamelogs_file).append(df).drop_duplicates().to_csv(team_gamelogs_file, index=False)


if __name__ == '__main__':
    pd.set_option('display.max_columns', None)
    pd.set_option('display.max_rows', None)
    pd.set_option("expand_frame_repr", True)

    # teams = teams_ids()
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
        'mem'
        'no',
        'sa'
    ]

    print(teams)
    update_gamelogs()
