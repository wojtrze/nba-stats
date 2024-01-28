from datetime import datetime, timedelta
import requests
import time
from typing import List, Union, Dict
from selenium.common import NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from fake_useragent import UserAgent
import logging
import driver_manager
from selenium.webdriver.common.by import By
from selenium import webdriver
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SUPERBET_URL = "https://superbet.pl/zaklady-bukmacherskie/koszykowka/usa/usa-nba/wszystko"


def get_bets_by_game_id(superbet_event_id) -> List[Dict[str, Union[str, int]]]:
    game_url = "https://production-superbet-offer-pl.freetls.fastly.net/matches/byId"
    params = {"matchIds": superbet_event_id}

    headers = {
        "authority": "production-superbet-offer-pl.freetls.fastly.net",
        "accept": "application/json, text/plain, */*",
        "accept-language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7",
        "if-none-match": 'W/"2b31c-bvT4nD83gAw8kznssTKh0vcVR04"',
        "origin": "https://superbet.pl",
        "referer": "https://superbet.pl/",
        "sec-ch-ua": '"Google Chrome";v="120", "Chromium";v="120", "Not?A_Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "cross-site",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    }
    headers["user-agent"] = UserAgent().random

    response = requests.get(game_url, params=params, headers=headers)

    if response.status_code == 200:
        bets_for_game = response.json()["data"][0]["odds"]
    else:
        logger.info(f"Failed to fetch data. Status code: {response.status_code}")
        raise Exception("sth wrong")
    return bets_for_game


def filter_data(data, bet_type):
    result = [item for item in data if all(item.get(key) in value for key, value in bet_type.items())]
    return result


def get_sb_games_info_from_page(url):
    driver_manager.install_chromedriver()
    games_info = []
    with webdriver.Chrome() as driver:
        driver.get(url)
        try:
            accept_button = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "onetrust-accept-btn-handler")))
            accept_button.click()
            logger.info("Clicked on 'Akceptuję wszystkie' button.")
        except NoSuchElementException:
            logger.info("'Akceptuję wszystkie' button not found on the page.")

        time.sleep(8)
        # driver.wait_until(lambda: driver.execute_script('return document.readyState === "complete"'))
        # WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'event-row-container')))

        game_elements = driver.find_elements(By.CLASS_NAME, 'event-row-container')
        logger.info(f"{len(game_elements)} game events were found on {url}")

        current_datetime = datetime.now()
        for game_element in game_elements:
            game_info = extract_game_info(current_datetime, game_element)
            player_props = extract_player_props_from_game(current_datetime, game_element)
            logger.info(f"{len(player_props)} props extracted for game {game_info['away']} at {game_info['home']}")
            game_info['odds']['player_props'] = player_props
            games_info.append(game_info)
            time.sleep(4)

    logger.info(f"{len(games_info)} game(s) extracted from superbet")

    # driver.quit()
    return games_info


def extract_game_info(current_datetime, game_element):
    adjusted_time = current_datetime - timedelta(hours=6)
    # TODO exception handling
    game_info = {"superbet_event_id": game_element.get_attribute("id").replace("event-", ""),
                 "event_time": game_element.find_element(By.CLASS_NAME, "event-time").text.strip(),
                 "home": game_element.find_element(By.XPATH, ".//*[@class='event-competitor__name e2e-event-team1-name']").text.strip(),
                 "away": game_element.find_element(By.XPATH, ".//*[@class='event-competitor__name e2e-event-team2-name']").text.strip(),
                 "odds": {
                     "game_winner": {
                         "home_win": game_element.find_elements(By.XPATH, ".//*[@class='odd-button__odd-value-new e2e-odd-current-value']")[0].text.strip(),
                         "away_win": game_element.find_elements(By.XPATH, ".//*[@class='odd-button__odd-value-new e2e-odd-current-value']")[1].text.strip(),
                         "access_time": adjusted_time.strftime("%Y-%m-%d %H:%M:%S"),
                     },
                     "total_teams_pts": {},
                     "player_props": []
                 }}
    return game_info


def extract_player_props_from_game(current_datetime, game_element):
    # weź wszystkie
    raw_props_for_game = get_bets_by_game_id(game_element.get_attribute("id").replace("event-", ""))
    bet_types = {
        "pts": {"bgdi": [200949]},
        "ast": {"bgdi": [200950]},
        "reb": {"bgdi": [200951]},
        "thr": {"bgdi": [200992]},
        "stl": {"bgdi": [200984]},
        "tov": {"bgdi": [200985]}
    }
    players_props_for_game = []
    for k, v in bet_types.items():
        props_for_bet_type = filter_data(raw_props_for_game, v)
        for prop in props_for_bet_type:
            prop['bet_type'] = k
        players_props_for_game = players_props_for_game + props_for_bet_type

    # utilize props
    return players_props_for_game


def create_props_dataframe(games_info):
    props_list = []
    for game_info in games_info:
        for player_prop in game_info['odds']['player_props']:
            prop_dict = {
                'player': player_prop['spc']['player'],
                'swish_player_id': player_prop['extra']['swish-player-id'],
                'odds': player_prop['ov'],
                'over_under': 'over' if player_prop['oo'] == 1 else 'under',
                'bet_line': player_prop['spc']['total'],
                'bet_type': player_prop['bet_type'],
                'home': game_info['home'],
                'away': game_info['away'],
                'event_time': game_info['event_time']
            }
            props_list.append(prop_dict)

    df = pd.DataFrame(props_list)
    return df


def main():
    games_info = get_sb_games_info_from_page(SUPERBET_URL)
    if len(games_info) == 0:
        print("games not found")
    else:
        print(f"{len(games_info)} games  found")

    a=create_props_dataframe(games_info)
    print(a)
    # wyciągnij dane z games info do dataframe


if __name__ == "__main__":
    main()

    bet = {
        "player_name": "Obi Toppin",
        "type": "pts",
        "condition": "36+",
        "odds": 1.72,
        "player_team": "NYK",
        "opponent_team": "BOS",
        "homegame": True,
        "analysis_data": {
            "injury_status": "OK",
            "sentiment": "5/10",
            "projected_matchup": "Jalen Brown",
            "unavailable_team_players": ["Julius Randle"]
        },
        "bet_resolution": {
            "is_hit": False,
            "actual": 34,
            "matchup": "Jalen Brown"
        }
    }
