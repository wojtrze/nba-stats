import requests
from random import randint
from time import sleep
import json
import pandas as pd

NORMALIZED_TEAM_NAME = {
    "Boston Celtics": "bos",
    "Brooklyn Nets": "bkn",
    "New York Knicks": "ny",
    "Philadelphia 76ers": "phi",
    "Toronto Raptors": "tor",
    "Chicago Bulls": "chi",
    "Cleveland Cavaliers": "cle",
    "Detroit Pistons": "det",
    "Indiana Pacers": "ind",
    "Milwaukee Bucks": "mil",
    "Denver Nuggets": "den",
    "Minnesota Timberwolves": "min",
    "Oklahoma City Thunder": "okc",
    "Portland Trail Blazers": "por",
    "Utah Jazz": "utah",
    "Golden State Warriors": "gs",
    "Los Angeles Clippers": "lac",
    "Los Angeles Lakers": "lal",
    "Phoenix Suns": "phx",
    "Sacramento Kings": "sac",
    "Atlanta Hawks": "atl",
    "Charlotte Hornets": "cha",
    "Miami Heat": "mia",
    "Orlando Magic": "orl",
    "Washington Wizards": "wsh",
    "Dallas Mavericks": "dal",
    "Houston Rockets": "hou",
    "Memphis Grizzlies": "mem",
    "New Orleans Pelicans": "no",
    "San Antonio Spurs": "sa"
}

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:20.0) Gecko/20100101 Firefox/20.0'}


def todays_games_list():
    url = "https://pl.unibet-45.com/sportsbook-feeds/views/filter/basketball/nba/matches?includeParticipants=true&useCombined=true&ncid=1635861681"
    resp = requests.get(url)
    a = resp.json()
    events = a['layout']['sections'][1]['widgets'][0]['matches']['events']
    unibet_games_id_list = []
    for event in events:
        if event['event']['group'] != 'NBA':
            continue
        event_id = event['event']['id']
        unibet_games_id_list.append(event_id)
    return unibet_games_id_list


def all_today_bets():
    excluded_games = []  # in case you don't want game bets so be fetched
    result = []
    today_games = todays_games_list()
    for game_id in today_games:
        if game_id in excluded_games:
            continue
        result.extend(game_betoffer_list(event_id=game_id))
        print(f'game_id: {game_id} - {len(result)} total offers count')
    return result


def game_betoffer_list(event_id):
    label_to_bet_type = {
        "Points, rebounds & assists by the player - Including Overtime": "ARP",
        "Points scored by the player - Including Overtime": "PTS",
        "Assists by the player - Including Overtime": "AST",
        "3-point field goals made by the player - Including Overtime": "3PM",
        "Rebounds by the player - Including Overtime": "REB"
    }
    sleep(randint(1, 3))
    url = f"https://eu-offering.kambicdn.org/offering/v2018/ub/betoffer/event/{event_id}.json?lang=pl_PL&market=PL&ncid=1685181683"
    resp = requests.get(url, headers)
    game_bet_offers = resp.json()['betOffers']
    home = NORMALIZED_TEAM_NAME[resp.json()['events'][0]['homeName']]
    away = NORMALIZED_TEAM_NAME[resp.json()['events'][0]['awayName']]
    filtered_offers = []

    for bet_offer in game_bet_offers:
        if bet_offer['criterion']['englishLabel'] not in label_to_bet_type:
            continue

        bet_type = label_to_bet_type[bet_offer['criterion']['englishLabel']]
        if 'closed' in bet_offer:
            closed_date = bet_offer['closed']
        else:
            continue

        for bet_outcome in bet_offer['outcomes']:
            bet_outcome_id = bet_outcome['id']
            player_name = bet_outcome['participant']
            odds = bet_outcome['odds']
            line = bet_outcome['line']
            over_under = bet_outcome['englishLabel']
    
            offer_dict = {"player_ESPN": ''.join(player_name.split(',')[::-1]).strip(),
                          "bet_type": bet_type,
                          "odds": odds / 1000,
                          "line": line / 1000,
                          "over_under": over_under,
                          "home": home,
                          "away": away,
                          "bet_id": bet_outcome_id,
                          "closed_date": closed_date
                          }
            filtered_offers.append(offer_dict.copy())

    return filtered_offers


def store_offers(offers):
    df = pd.DataFrame(offers)
    pd.read_csv('offers.csv').append(df).drop_duplicates().to_csv('offers.csv', index=False)

if __name__ == '__main__':
    bets = all_today_bets()
    store_offers(bets)
