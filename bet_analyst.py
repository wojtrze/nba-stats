from typing import List

import numpy as np
import pandas as pd
import csv
from bet_scrapper import all_today_bets, store_offers
from lineup_fetcher import players_unlikely_to_play
import datetime
pd.options.mode.chained_assignment = None  # default='warn'
threshold = {'PTS': 2.0,
             'ARP': 2.1,
             'REB': 1.35,
             'AST': 1.4,
             '3PM': 0.6
             }

UB_to_ESPN_player_name = {'J.Brown': 'JaylenBrown',
                          'D.Sabonis': 'DomantasSabonis',
                          'M.Beasley': 'MalikBeasley',
                          'B.Simmons': 'BenSimmons',
                          'J.Poeltl': 'JakobPoeltl',
                          'NicolasClaxton': 'NicClaxton',
                          'TroyBrown': 'TroyBrown Jr.',
                          'C.LeVert': 'CarisLeVert',
                          'CameronReddish': 'CamReddish'
                          }


class BetAssessment():
    temp_players_to_map = []
    gamelogs = pd.DataFrame()
    bets_resolved = pd.DataFrame()
    doubtful_players = players_unlikely_to_play()

    def __init__(self, bets):
        self.bets = bets
        with open('offers_resolved.csv', 'r') as file:
            self.bets_resolved = pd.read_csv(file)
            self.bets_resolved = self.bets_resolved.drop_duplicates(subset=['over_under', 'player_ESPN', 'closed_date', 'bet_type'])

        with open('2022-players-logs.csv', 'r') as file:
            self.gamelogs = pd.read_csv(file)

    def assess_bets_from_list(self, bets_list: List[dict]):
        for bet in bets_list:
            self.assess_bet_vs_player_gamelogs(bet)

    def assess_bet_vs_historical_player_bets(self, bet):
        pass

    def provide_stored_bet_results(self, b):
        error_count = 0
        positive_count = 0
        list_of_results = []
        all_players = pd.read_csv(f'2022-players-logs.csv')
        # b = stored_bets()  # .to_dict('records'), już nie pamiętam czemu
        # all_players = all_nba_players() # fixme coś nie działa, a w ogole trzeba to przemyśleć
        for index, row in b.iterrows():
            if row['player_ESPN'] not in UB_to_ESPN_player_name:
                player_gamelogs = all_players[all_players['player_name_ESPN'] == row['player_ESPN']]
            else:
                player_gamelogs = all_players[all_players['player_name_ESPN'] == UB_to_ESPN_player_name[row['player_ESPN']]]
            if player_gamelogs.empty:
                print(f"nie ma gamelogów gracza!!!!!!!!!!!!!!!!! {row['player_ESPN']}")
                continue
            player_gamelogs.drop_duplicates(subset=['Date'], inplace=True)

            bet_date = (datetime.datetime.fromisoformat(row['closed_date'].replace('Z', '')) - datetime.timedelta(hours=6)).strftime('%Y-%m-%d')
            bet_player = row['player_ESPN']
            bet_type = row['bet_type']
            bet_line = float(row['line'])
            player_df = player_gamelogs[player_gamelogs['Date'] == bet_date]
            if player_df.empty:
                print(f"no df for {bet_player} on {bet_date} found during bets analys!!!!!!!!!!!!!!!!! ")
                #print(player_gamelogs)
                error_count += 1
                continue
            else:
                positive_count += 1

            actual = 0
            player_df["ARP"] = float(player_df["PTS"]) + float(player_df["REB"]) + float(player_df["AST"])

            actual = player_df[bet_type].values[0]

            # in case it's series, not df
            if isinstance(actual, pd.Series):
                actual = float(actual.iloc[0])
            else:
                actual = float(actual)

            is_hit = False
            if row['over_under'] == "Over" and actual > bet_line:
                is_hit = True
            if row['over_under'] == "Under" and actual < bet_line:
                is_hit = True

            bet_result = row
            # extend with result data
            bet_result["diff"] = abs(actual - bet_line)
            bet_result["actual"] = actual
            bet_result["is_hit"] = is_hit

            list_of_results.append(bet_result)
            if is_hit:
                print(f"{bet_player} - {row['over_under']} {bet_line} {bet_type} - {is_hit=}")

        return pd.DataFrame(list_of_results)

    @staticmethod
    def assess_player_old_bets(player_ESPN):
        pass

    def assess_bet_vs_player_gamelogs(self, bet: dict) -> list:
        #ta funkcja powinna dołączać assessment do zakładu
        #powinna być czuła na datę zakładu
        reasons = []

        # handling of m
        if bet['player_ESPN'] not in UB_to_ESPN_player_name:
            gamelogs_df = self.gamelogs[self.gamelogs['player_name_ESPN'] == bet['player_ESPN']]
        else:
            # when player name is not found, check mapped names
            gamelogs_df = self.gamelogs[self.gamelogs['player_name_ESPN'] == UB_to_ESPN_player_name[bet['player_ESPN']]]


        if gamelogs_df.empty:
            #at thsi point we should have all gamelogs of player. If gamelog is empty, then #FIXME. something is wrong
            self.temp_players_to_map.append(bet['player_ESPN'])

        # prepare data for analysis
        gamelogs_df = gamelogs_df.drop_duplicates(subset=['Date'])
        gamelogs_df = gamelogs_df.sort_values(by='Date')
        # leave out first 5 games
        gamelogs_df = gamelogs_df.iloc[5:]
        type = bet['bet_type']
        gamelogs_df['AST'] = pd.to_numeric(gamelogs_df['AST'])
        gamelogs_df['REB'] = pd.to_numeric(gamelogs_df['REB'])
        gamelogs_df['PTS'] = pd.to_numeric(gamelogs_df['PTS'])
        gamelogs_df['3PM'] = pd.to_numeric(gamelogs_df['3PM'])
        gamelogs_df['ARP'] = gamelogs_df['AST'] + gamelogs_df['REB'] + gamelogs_df['PTS']

        # Convert the "Date" column to datetime
        gamelogs_df["Date"] = pd.to_datetime(gamelogs_df["Date"])

        # Calculate the current date and time
        current_date = pd.Timestamp.now()
        # Calculate the threshold date (30 days before the current date)
        # threshold_date = current_date - datetime.timedelta(days=30)
        # # trzeba #FIXME, możemy potrzebować więcej niż 30 dni np do oceny mediany, tu nie powinno być modyfikacji gamelogs_df. zaburza pozniejsze obliczenia
        # # Removes rows with a "Date" older than the threshold date
        # gamelogs_df = gamelogs_df[gamelogs_df["Date"] >= threshold_date]

        # leave games before bet closed date
        gamelogs_df = gamelogs_df[gamelogs_df["Date"] < datetime.datetime.strptime(bet['closed_date'], "%Y-%m-%dT%H:%M:%SZ")]

        # quantile-based reasons
        lower_bound = gamelogs_df[type].quantile(0.3)
        upper_bound = gamelogs_df[type].quantile(0.7)
        if bet['over_under'] == 'Over' and bet['line'] < lower_bound:
            reason = {"over_under": "Over",
                      "description": f"Line is {(lower_bound - bet['line']):.2f} below 30% quantile. vote for over",
                      "code": "quantiles"}
            reasons.append(reason)
        if bet['over_under'] == 'Under' and bet['line'] > upper_bound:
            reason = {"over_under": "Under",
                      "description": f"Line is {(bet['line'] - upper_bound):.2f} above 70% quantile. vote for under",
                      "code": "quantiles"}
            reasons.append(reason)

        # low odds reasons

        median = gamelogs_df[type].median()
        mean = gamelogs_df.sort_values(by=type, ascending=False).iloc[:-3].iloc[3:][type].mean()

        if bet['odds'] <= 1.73:
            reason = {"over_under": f"{bet['over_under']}",
                      "description": f"Bet odds is low: {bet['odds']=}. vote for {bet['over_under']}.",
                      "code": "low_odds"}
            reasons.append(reason)

        # median-based reasons

        median = gamelogs_df[type].median()
        mean = gamelogs_df.sort_values(by=type, ascending=False).iloc[:-3].iloc[3:][type].mean()

        if bet['over_under'] == 'Under' and (bet['line'] - median > threshold[type] or bet['line'] - mean > threshold[type]):
            reason = {"over_under": "Under",
                      "description": f"Betline is {bet['line'] - median:.2f} below median. vote for under.",
                      "code": "median"}
            reasons.append(reason)
        if bet['over_under'] == 'Over' and (median - bet['line'] > threshold[type] or mean - bet['line'] > threshold[type]):
            reason = {"over_under": "Over",
                      "description": f"Betline is {median - bet['line']:.2f} above median. vote for over.",
                      "code": "median"}
            reasons.append(reason)

        # last game-based reasons
        games_in_calculation = 8
        games_triggering = 6
        if bet['over_under'] == 'Over' and len(
                gamelogs_df.tail(games_in_calculation)[gamelogs_df.tail(games_in_calculation)[type] > bet['line']]) >= games_triggering:
            reason = {"over_under": "Over",
                      "description": f"Last {games_in_calculation} games {len(gamelogs_df.tail(games_in_calculation)[gamelogs_df.tail(games_in_calculation)[type] > bet['line']])} times over betline. vote for over.",
                      "code": "last_games"}
            reasons.append(reason)
        if bet['over_under'] == 'Under' and len(
                gamelogs_df.tail(games_in_calculation)[gamelogs_df.tail(games_in_calculation)[type] < bet['line']]) >= games_triggering:
            reason = {"over_under": "Under",
                      "description": f"Last {games_in_calculation} games {len(gamelogs_df.tail(games_in_calculation)[gamelogs_df.tail(games_in_calculation)[type] < bet['line']])} times under betline. vote for under.",
                      "code": "last_games"}
            reasons.append(reason)

        # TODO: lineup-based reasons
        game_doubtful_players = [d for d in self.doubtful_players if d['team'].upper() in [bet['home'].upper(), bet['away'].upper()]]

        reason = {"over_under": "Info",
                  "description": f"Game doubtful players: {game_doubtful_players}",
                  "code": "info"}
        reasons.append(reason)
        # bets_hits
        # fixme dodaj  ograniczenie daty do tych sprzed zamkniecia zakladu
        player_historical_bets = self.bets_resolved[self.bets_resolved['player_ESPN'] == bet['player_ESPN']]
        # if not player_historical_bets.empty:
        player_historical_bets = player_historical_bets[player_historical_bets['bet_type'] == bet['bet_type']]
        # Count the number of hits for 'Under' bets
        under_hits = len(
            player_historical_bets.loc[(player_historical_bets['over_under'] == 'Under') & (player_historical_bets['is_hit'] == True), :])

        # Count the number of hits for 'Over' bets
        over_hits = len(
            player_historical_bets.loc[(player_historical_bets['over_under'] == 'Over') & (player_historical_bets['is_hit'] == True), :])

        # Count the number of 'Under' bets
        under_all_count = len(player_historical_bets.loc[player_historical_bets['over_under'] == 'Under', :])

        # Count the number of 'Over' bets
        over_all_count = len(player_historical_bets.loc[player_historical_bets['over_under'] == 'Over', :])
        if under_all_count > 4:
            if under_hits / under_all_count > 0.65:
                reason = {"over_under": "Under",
                          "description": f"Player has {under_hits}/{under_all_count} under bets hit. vote for under.",
                          "code": "bets_hits"}
                reasons.append(reason)
        if over_all_count > 4:
            if over_hits / over_all_count > 0.65:
                reason = {"over_under": "Over",
                          "description": f"Player has {over_hits}/{over_all_count} over bets hit. vote for over.",
                          "code": "bets_hits"}
                reasons.append(reason)



# dodawanie reasonów zakończone, co dalej? todo

        #if len(reasons) > 3:
        if len(reasons) >= 4 and "last_games" in str(reasons):
        #if "last_games" in str(reasons):
            # if len(reasons) > 1 and "Over" in str(reasons) and "Under" in str(reasons) and bet['bet_type'] in ['ARP', 'REB', 'AST', 'PTS', '3PM']:
            # if len(reasons) > 3 and bet['bet_type'] in ['ARP', 'REB', 'AST', 'PTS', '3PM']:
            #print(bet)
            print(
                f"{bet['away']}@{bet['home']}, {bet['player_ESPN']}, {bet['over_under']}, {bet['line']}, {bet['bet_type']} ({bet['odds']}), {lower_bound=}, {upper_bound=}, {mean=}, {median=}")
            print(*reasons, sep='\n')
            gamelogs_df['diff'] = gamelogs_df[type] - bet['line']
            print(gamelogs_df[['Date', 'MIN', 'type', 'OPP', type, 'diff']].tail(9))
            srednie = gamelogs_df.sort_values(by=['Date'], ascending=False).groupby(np.arange(len(gamelogs_df)) // 5).agg({'Date':'first', f"{type}":'mean', 'diff': 'mean'})
            print (srednie)
            srednie= None
            print("\n")

        #at this point we have a dict of reasons for bet. We should create columns named as reason["code"] field (str), put there value of reason["over_under"] and then return it as a dataframe
        for reason in reasons:
            # Create a new column with the name of the "code" field
            bet[reason["code"]] = reason["over_under"]

        return bet

if __name__ == '__main__':

    # # part A: resolves bets from 'offers.csv and saves them to 'offers_resolved.csv'
    # b = pd.read_csv("offers.csv")
    # ass = BetAssessment(b)
    # bets_with_results_dict = ass.provide_stored_bet_results(b)
    # bets_with_results_dict.to_csv("offers_resolved.csv", index=False)

    # part B: fetches all today's bets for players, stores them in 'offers.csv'.

    # if you want to assess only todays offers:
    bets = all_today_bets()
    store_offers(bets)
    # if you want to assess  resolved offers:
    # bets = pd.read_csv("offers_resolved.csv").to_dict("records")
    #
    assessment = BetAssessment(bets)
    # # for each of bets asess_bet function puts reasons for bet
    sure_bets = assessment.assess_bets_from_list(bets)
    print(assessment.temp_players_to_map)

    # show in pndasgui
    # gui.show(sure_bets)
