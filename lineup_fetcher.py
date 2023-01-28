import requests
from bs4 import BeautifulSoup


def players_unlikely_to_play():
    url = "https://www.rotowire.com/basketball/nba-lineups.php"
    page = requests.get(url)
    soup = BeautifulSoup(page.content, 'html.parser')

    li_75pct_elements = soup.find_all("li", class_="is-pct-play-75")
    li_50pct_elements = soup.find_all("li", class_="is-pct-play-50")
    li_25pct_elements = soup.find_all("li", class_="is-pct-play-25")
    li_0pct_elements = soup.find_all("li", class_="is-pct-play-0")

    players = []

    for element in li_75pct_elements:
        players.append({"name": element.find('a').get_text(),
                        "team": element.find_parent("div", class_="lineup__box").find("div", class_="lineup__abbr").get_text(),
                        "likelihood": 75})

    for element in li_50pct_elements:
        players.append({"name": element.find('a').get_text(),
                        "team": element.find_parent("div", class_="lineup__box").find("div", class_="lineup__abbr").get_text(),
                        "likelihood": 50})

    for element in li_25pct_elements:
        players.append({"name": element.find('a').get_text(),
                        "team": element.find_parent("div", class_="lineup__box").find("div", class_="lineup__abbr").get_text(),
                        "likelihood": 25})

    for element in li_0pct_elements:
        players.append({"name": element.find('a').get_text(),
                        "team": element.find_parent("div", class_="lineup__box").find("div", class_="lineup__abbr").get_text(),
                        "likelihood": 0})
    return players


if __name__ == "__main__":
    print(players_unlikely_to_play())
