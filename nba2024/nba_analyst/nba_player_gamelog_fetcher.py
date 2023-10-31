from typing import List, Union
import re
import requests
from bs4 import BeautifulSoup
import pandas as pd
import random
import time
import logging
import json
import os

# Constants
MIN_SLEEP: int = 0
MAX_SLEEP: int = 0
BASE_URL: str = 'https://www.espn.com/nba'
SEASONS: List[str] = ['2023', '2022', '2021', '2020', '2019', '2018']  # Add more seasons as needed
SEASON_START_DATE = pd.to_datetime("2023-10-18").date()
TEAMS_JSON_FILE: str = os.path.join(os.path.dirname(__file__), '..', 'data', 'teams.json')  # JSON file containing team names
# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_page_soup(url: str) -> BeautifulSoup:
    time.sleep(random.randint(MIN_SLEEP, MAX_SLEEP))
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:20.0) Gecko/20100101 Firefox/20.0'}
    page = requests.get(url, headers=headers)
    return BeautifulSoup(page.text, 'html.parser')


def get_game_boxscores(game_id: str, home_or_away: str) -> Union[pd.DataFrame, None]:
    url = f'{BASE_URL}/boxscore?gameId={game_id}'
    soup = get_page_soup(url)
    table_body = soup.find_all('table')
    result_df = None

    if home_or_away == 'home':
        result_df = pd.read_html(str(table_body))[1]
    elif home_or_away == 'away':
        result_df = pd.read_html(str(table_body))[2]

    return result_df


def get_team_ids() -> List[str]:
    url = f'{BASE_URL}/teams'
    soup = get_page_soup(url)
    team_links = soup.find_all('a', attrs={'href': re.compile("^/nba/team/stats/_/name/")})
    return [link.get('href').split("/")[-2] for link in team_links]


def player_ids_for_team(team_id: str) -> List[str]:
    time.sleep(random.randint(MIN_SLEEP, MAX_SLEEP))
    url = f'{BASE_URL}/team/roster/_/name/{team_id}'
    soup = get_page_soup(url)
    player_links = soup.find_all('a', attrs={'href': re.compile("^https://www.espn.com/nba/player/_/id/")})
    player_ids = list(set([link.get('href').split("/")[-2] for link in player_links]))
    return player_ids


def retrieve_player_name(url: str) -> str:
    time.sleep(random.randint(0, 1))
    soup = get_page_soup(url)
    player_name = soup.find_all("h1", {"class": "PlayerHeader__Name"})[0].text.strip()
    return player_name


def scrap_player_gamelog(player_id: str, season_start_yyyy: str) -> pd.DataFrame:
    time.sleep(random.randint(MIN_SLEEP, MAX_SLEEP))
    url = f'{BASE_URL}/player/gamelog/_/id/{player_id}/type/nba/year/{int(season_start_yyyy) + 1}'
    espn_raw_data_tables = pd.read_html(url)

    # Filter out invalid gamelog columns
    gamelog_data_extracted_from_raw = pd.DataFrame()
    gamelog_data_extracted_from_raw = pd.concat([pd_table for pd_table in espn_raw_data_tables if 'Date' in pd_table.columns], ignore_index=True)

    # Data cleaning and transformation
    cleaned_gamelog = clean_and_transform_gamelog(gamelog_data_extracted_from_raw)
    return cleaned_gamelog


def player_gamelog(player_id: str) -> pd.DataFrame:
    gamelog = pd.DataFrame()
    for season in SEASONS:
        current_season_gamelog = scrap_player_gamelog(player_id, season)
        gamelog = pd.concat([gamelog, current_season_gamelog])

    gamelog['player_id'] = player_id
    gamelog['player_name'] = retrieve_player_name(f'{BASE_URL}/player/gamelog/_/id/{player_id}')

    return gamelog


def player_gamelog_for_season(player_id: str, season_start_yyyy: str = '2022') -> pd.DataFrame:
    current_season_gamelog = scrap_player_gamelog(player_id, season_start_yyyy)
    current_season_gamelog['player_id_ESPN'] = player_id
    current_season_gamelog['player_name_ESPN'] = retrieve_player_name(f'{BASE_URL}/player/gamelog/_/id/{player_id}')
    return current_season_gamelog


def update_gamelogs():
    # Load teams from the JSON file
    with open(TEAMS_JSON_FILE, 'r') as file:
        teams: List[str] = json.load(file)

    for team_id in teams:
        team_gamelogs: pd.DataFrame = pd.DataFrame()
        player_ids: List[str] = player_ids_for_team(team_id)

        for player_id in player_ids:
            current_players_gamelog: pd.DataFrame = player_gamelog_for_season(player_id, '2022')
            current_players_gamelog['team'] = team_id
            if not current_players_gamelog.empty:
                logger.info(current_players_gamelog[['OPP', 'MIN', 'REB', 'AST', 'FG%', 'PTS', '3PM', 'Date', 'player_name_ESPN']].head(5))

            team_gamelogs = pd.concat([team_gamelogs, current_players_gamelog])

        team_gamelogs_file: str = f'{team_id}-2023-players-logs.csv'
        team_gamelogs.to_csv(team_gamelogs_file, mode='a', header=True, index=False)


def clean_and_transform_gamelog(gamelog_df):
    # Remove rows containing unwanted keywords in 'Date' column
    unwanted_keywords = ['acquired', 'Finals', 'Play-In', 'Game', 'Conference', 'RISING', 'PRESEASON',
                         'january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september',
                         'october', 'november', 'december', 'from', 'LeBron', 'Canada Series']
    gamelog_df = gamelog_df[~gamelog_df['Date'].str.contains('|'.join(unwanted_keywords), na=False, case=False)]

    # Split 'FG' column into 'FGM' and 'FGA' columns
    gamelog_df.loc[:, ['FGM', 'FGA']] = gamelog_df['FG'].str.split('-', expand=True)
    gamelog_df = gamelog_df.drop('FG', axis=1)

    # Split '3PT' column into '3PM' and '3PA' columns
    gamelog_df[['3PM', '3PA']] = gamelog_df['3PT'].str.split('-', expand=True)
    gamelog_df = gamelog_df.drop('3PT', axis=1)

    # Split 'FT' column into 'FTM' and 'FTA' columns
    gamelog_df.loc[:, ['FTM', 'FTA']] = gamelog_df['FT'].str.split('-', expand=True)
    gamelog_df = gamelog_df.drop('FT', axis=1)

    # Determine 'type' (home or away) based on 'OPP' column
    gamelog_df.loc[:, 'type'] = 'home'
    gamelog_df.loc[gamelog_df['OPP'].str.contains('@', na=False), 'type'] = 'away'

    # Remove 'vs' and '@' from 'OPP' column
    gamelog_df.loc[:, 'OPP'] = gamelog_df['OPP'].str.replace('vs', '')
    gamelog_df.loc[:, 'OPP'] = gamelog_df['OPP'].str.replace('@', '')

    # Prepare dates
    gamelog_df.loc[:, 'Date'] = pd.to_datetime(gamelog_df['Date'], format="%a %m/%d")
    year = "2022"
    # Update the year based on month
    gamelog_df.loc[:, 'Date'] = gamelog_df.apply(
        lambda row: row['Date'].replace(year=int(year) + 1) if 1 <= row['Date'].month <= 6 else row['Date'].replace(year=int(year)),
        axis=1).dt.date

    # Convert columns to numeric
    numeric_columns = ['MIN', 'REB', 'AST', 'BLK', 'STL', 'PF', 'TO', 'PTS', 'FGM', 'FGA', '3PM', '3PA', 'FTM', 'FTA']
    gamelog_df.loc[:, numeric_columns] = gamelog_df.loc[:, numeric_columns].apply(pd.to_numeric, errors='coerce', downcast='integer')

    # Filter gamelog for the current season (adjust the start date as needed)
    gamelog_df = gamelog_df[gamelog_df['Date'] >= SEASON_START_DATE]

    return gamelog_df


if __name__ == '__main__':
    update_gamelogs()
