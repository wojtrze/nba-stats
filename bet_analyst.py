from typing import List
from pandasgui import show
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
significant_diff = {'PTS': 3.5,
                    'ARP': 4.5,
                    'REB': 1.5,
                    'AST': 1.5,
                    '3PM': 0.7
                    }

UB_to_ESPN_player_name = {'J.Brown': 'JaylenBrown',
                          'D.Sabonis': 'DomantasSabonis',
                          'M.Beasley': 'MalikBeasley',
                          'B.Simmons': 'BenSimmons',
                          'J.Poeltl': 'JakobPoeltl',
                          'NicolasClaxton': 'NicClaxton',
                          'TroyBrown': 'TroyBrown Jr.',
                          'C.LeVert': 'CarisLeVert',
                          'CameronReddish': 'CamReddish',
                          'NikolaJokić': 'NikolaJokic',
                          'LukaDončić': 'LukaDoncic'
                          }


class BetAssessment():
    blad = 0
    dobrze = 0
    temp_players_to_map = []
    gamelogs = pd.DataFrame()
    bets_resolved = pd.DataFrame()
    doubtful_players = players_unlikely_to_play()
    player_gamelogs = pd.DataFrame()
    reasons = []

    def __init__(self, bets):
        self.bets = bets
        with open('offers_resolved.csv', 'r') as file:
            self.bets_resolved = pd.read_csv(file)
            self.bets_resolved = self.bets_resolved.drop_duplicates(subset=['over_under', 'player_ESPN', 'closed_date', 'bet_type'])

        with open('2022-players-logs.csv', 'r') as file:
            self.gamelogs = pd.read_csv(file)

    def assess_bets_from_list(self, bets_list: List[dict]):
        for bet in bets_list:
            reasons = self.assess_bet_vs_player_gamelogs(bet)
            # f powyzej musi zwracac dict reasons i załączać go do betu
            # at this point we have a dict of reasons for bet. We should create columns named as reason["code"] field (str), put there value of reason["over_under"] and then return it as a dataframe
            for reason in reasons:
                # Create a new column with the name of the "code" field
                bet[reason["code"]] = reason["over_under"]
        return bets_list

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

            bet_date = (datetime.datetime.fromisoformat(row['closed_date'].replace('Z', '')) - datetime.timedelta(hours=6)).strftime(
                '%Y-%m-%d')
            bet_player = row['player_ESPN']
            bet_type = row['bet_type']
            bet_line = float(row['line'])
            player_df = player_gamelogs[player_gamelogs['Date'] == bet_date]
            if player_df.empty:
                print(f"no df for {bet_player} on {bet_date} found during bets analys. Player didn't play that day?")
                continue

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

    def quantiles_rule(self, bet, lower_quantile, upper_quantile):
        bet_type = bet['bet_type']
        lower_bound = self.player_gamelogs[bet_type].quantile(lower_quantile)
        upper_bound = self.player_gamelogs[bet_type].quantile(upper_quantile)
        if bet['over_under'] == 'Over' and bet['line'] < lower_bound:
            reason = {"over_under": "Over",
                      "description": f"Line is {(lower_bound - bet['line']):.2f} below {lower_quantile} quantile. vote for over",
                      "code": f"quantiles_{str(lower_quantile).replace('.', '_')}_{str(upper_quantile).replace('.', '_')}"}
            self.reasons.append(reason)
        if bet['over_under'] == 'Under' and bet['line'] > upper_bound:
            reason = {"over_under": "Under",
                      "description": f"Line is {(bet['line'] - upper_bound):.2f} above {upper_quantile} quantile. vote for under",
                      "code": f"quantiles_{str(lower_quantile).replace('.', '_')}_{str(upper_quantile).replace('.', '_')}"}
            self.reasons.append(reason)

    def averages_rule(self, bet, number_of_games_for_average=4):
        # averages
        self.player_gamelogs['diff'] = self.player_gamelogs[bet['bet_type']] - bet['line']
        try:
            averages = self.player_gamelogs.sort_values(by=['Date'], ascending=False).groupby(
                np.arange(len(self.player_gamelogs)) // number_of_games_for_average).agg(
                {'Date': 'first', f"{bet['bet_type']}": 'mean', 'diff': 'mean'})
            reason = {"over_under": float(f"{averages.iloc[0]['diff']}"),
                      "description": f"Last {number_of_games_for_average} games average of player is {averages.iloc[0]['diff']} from betline.",
                      "code": f"avg_diff_{number_of_games_for_average}_games"}
            self.reasons.append(reason)

            if averages.iloc[0]["diff"] > significant_diff[bet['bet_type']]:
                reason = {"over_under": "Over",
                          "description": f"Last {number_of_games_for_average} games average of player is {averages.iloc[0]['diff']} over betline. vote for over.",
                          "code": f"averages_{number_of_games_for_average}_games"}
                self.reasons.append(reason)

            if averages.iloc[0]["diff"] < -significant_diff[bet['bet_type']]:
                reason = {"over_under": "Under",
                          "description": f"Last {number_of_games_for_average} games average of player is {averages.iloc[0]['diff']} under betline. vote for under.",
                          "code": f"averages_{number_of_games_for_average}_games"}
                self.reasons.append(reason)

        except Exception as e:
            print("An error occurred:", e)

    def best_hits_rule(self, bet):
        # bets_hits
        player_historical_bets = self.bets_resolved[self.bets_resolved['player_ESPN'] == bet['player_ESPN']]
        # restrict to bets before bet closed date
        player_historical_bets = player_historical_bets[player_historical_bets['closed_date'] < bet['closed_date']]
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
                self.reasons.append(reason)
        if over_all_count > 4:
            if over_hits / over_all_count > 0.65:
                reason = {"over_under": "Over",
                          "description": f"Player has {over_hits}/{over_all_count} over bets hit. vote for over.",
                          "code": "bets_hits"}
                self.reasons.append(reason)

    def median_rule(self, bet):
        # median-based reasons
        bet_type = bet['bet_type']
        median = self.player_gamelogs[bet_type].median()
        mean = self.player_gamelogs.sort_values(by=bet_type, ascending=False).iloc[:-3].iloc[3:][bet_type].mean()

        if bet['over_under'] == 'Under' and (bet['line'] - median > threshold[bet_type] or bet['line'] - mean > threshold[bet_type]):
            reason = {"over_under": "Under",
                      "description": f"Betline is {bet['line'] - median:.2f} below median. vote for under.",
                      "code": "median"}
            self.reasons.append(reason)
        if bet['over_under'] == 'Over' and (median - bet['line'] > threshold[bet_type] or mean - bet['line'] > threshold[bet_type]):
            reason = {"over_under": "Over",
                      "description": f"Betline is {median - bet['line']:.2f} above median. vote for over.",
                      "code": "median"}
            self.reasons.append(reason)

    def last_games_hits_rule(self, bet, games_in_calculation, games_triggering):
        # last game-based reasons
        bet_type = bet['bet_type']
        if bet['over_under'] == 'Over' and len(
                self.player_gamelogs.tail(games_in_calculation)[
                    self.player_gamelogs.tail(games_in_calculation)[bet_type] > bet['line']]) >= games_triggering:
            reason = {"over_under": "Over",
                      "description": f"Last {games_in_calculation} games {len(self.player_gamelogs.tail(games_in_calculation)[self.player_gamelogs.tail(games_in_calculation)[bet_type] > bet['line']])} times over betline. vote for over.",
                      "code": f"last_games_{games_triggering}_{games_in_calculation}"}
            self.reasons.append(reason)
        if bet['over_under'] == 'Under' and len(
                self.player_gamelogs.tail(games_in_calculation)[
                    self.player_gamelogs.tail(games_in_calculation)[bet_type] < bet['line']]) >= games_triggering:
            reason = {"over_under": "Under",
                      "description": f"Last {games_in_calculation} games {len(self.player_gamelogs.tail(games_in_calculation)[self.player_gamelogs.tail(games_in_calculation)[bet_type] < bet['line']])} times under betline. vote for under.",
                      "code": f"last_games_{games_triggering}_{games_in_calculation}"}
            self.reasons.append(reason)

    def assess_bet_vs_player_gamelogs(self, bet: dict) -> list:
        self.reasons = []
        # handling of mapped names
        if bet['player_ESPN'] not in UB_to_ESPN_player_name:
            self.player_gamelogs = self.gamelogs[self.gamelogs['player_name_ESPN'] == bet['player_ESPN']]
        else:
            # when player name is not found, check mapped names
            self.player_gamelogs = self.gamelogs[self.gamelogs['player_name_ESPN'] == UB_to_ESPN_player_name[bet['player_ESPN']]]

        if self.player_gamelogs.empty:
            self.temp_players_to_map.append(bet['player_ESPN'])

        # prepare data for analysis
        self.player_gamelogs = self.player_gamelogs.drop_duplicates(subset=['Date'])
        self.player_gamelogs = self.player_gamelogs.sort_values(by='Date')

        self.player_gamelogs['AST'] = pd.to_numeric(self.player_gamelogs['AST'])
        self.player_gamelogs['REB'] = pd.to_numeric(self.player_gamelogs['REB'])
        self.player_gamelogs['PTS'] = pd.to_numeric(self.player_gamelogs['PTS'])
        self.player_gamelogs['3PM'] = pd.to_numeric(self.player_gamelogs['3PM'])
        self.player_gamelogs['ARP'] = self.player_gamelogs['AST'] + self.player_gamelogs['REB'] + self.player_gamelogs['PTS']

        # Convert the "Date" column to datetime
        self.player_gamelogs["Date"] = pd.to_datetime(self.player_gamelogs["Date"])

        # leave games before bet closed date
        timezone_difference = datetime.timedelta(hours=30)
        self.player_gamelogs = self.player_gamelogs[
            self.player_gamelogs["Date"] < (datetime.datetime.strptime(bet['closed_date'], "%Y-%m-%dT%H:%M:%SZ") - timezone_difference)]

        if self.player_gamelogs.shape[0] < 4:
            return self.reasons

        if self.player_gamelogs["OPP"].iloc[-1] in [bet["home"].upper(), bet["away"].upper()]:
            self.blad += 1
        else:
            self.dobrze += 1

        # quantile-based reasons
        self.quantiles_rule(bet, lower_quantile=0.2, upper_quantile=0.8)
        self.quantiles_rule(bet, lower_quantile=0.3, upper_quantile=0.7)
        self.quantiles_rule(bet, lower_quantile=0.4, upper_quantile=0.6)
        bet_type = bet['bet_type']

        self.median_rule(bet)

        # TODO
        self.trend_rule(bet)

        self.last_games_hits_rule(bet, games_in_calculation=8, games_triggering=6)
        self.last_games_hits_rule(bet, games_in_calculation=5, games_triggering=4)
        self.last_games_hits_rule(bet, games_in_calculation=2, games_triggering=2)
        self.best_hits_rule(bet)
        self.averages_rule(bet, number_of_games_for_average=2)
        self.averages_rule(bet, number_of_games_for_average=5)

        # TODO: lineup-based reasons
        game_doubtful_players = [d for d in self.doubtful_players if d['team'].upper() in [bet['home'].upper(), bet['away'].upper()]]

        reason = {"over_under": "Info",
                  "description": f"Game doubtful players: {game_doubtful_players}",
                  "code": "info"}
        self.reasons.append(reason)

        # if len(reasons) > 3:
        if "averages_2_games" in str(self.reasons) :
            print(
                f"{bet['player_ESPN']} {bet['over_under']}, {bet['line']} {bet['bet_type']} ({bet['odds']}), {bet['away']}@{bet['home']}, {bet['closed_date']}")
            # print(*self.reasons.count(), sep='\n')
            print(self.player_gamelogs[['Date', 'MIN', 'type', 'OPP', bet_type, 'diff']].tail(6))
            averages = None
            print("\n")

        return self.reasons

    def trend_rule(self, bet, games_in_calculations=5):
        bet_type = bet['bet_type']
        # retrieve information what is the trend of selected player's statistics (for each bet type)
        bet_type = bet['bet_type']
        desired_stats = self.player_gamelogs[bet_type].tail(games_in_calculations)

        trend = desired_stats.diff().mean()
        reason = {"over_under": f"{trend}",
                  "description": f"Player's {bet_type} trend is {trend}",
                  "code": "trend"}
        self.reasons.append(reason)



if __name__ == '__main__':
    def fetch_and_analyze_today_games():
        # if you want to assess only todays offers:
        bets = all_today_bets()
        store_offers(bets)
        assessment = BetAssessment(bets)
        assessed_bets = assessment.assess_bets_from_list(bets)
        print(assessment.temp_players_to_map)
        todays_bets = pd.DataFrame(assessed_bets)
        show(todays_bets)


    def resolve_bets():
        # part A: resolves bets from 'offers.csv and saves them to 'offers_resolved.csv'
        b = pd.read_csv("offers.csv").drop_duplicates(subset=['player_ESPN', 'bet_type', 'over_under', 'closed_date', 'line'])
        ass = BetAssessment(b)
        bets_with_results_dict = ass.provide_stored_bet_results(b)
        bets_with_results_dict.to_csv("offers_resolved.csv", index=False)


    def analyze_all_bets(start_date):
        # if you want to assess  resolved offers:
        bets = pd.read_csv("offers_resolved.csv").to_dict("records")
        bets = [bet for bet in bets if bet['closed_date'] >= start_date]
        assessment = BetAssessment(bets)
        # for each of bets asess_bet function puts reasons for bet
        assessed_bets = assessment.assess_bets_from_list(bets)
        print(assessment.temp_players_to_map)
        dfx = pd.DataFrame(assessed_bets)

        dfx['trend'] = dfx['trend'].astype(float)
        dfx['avg_diff_2_games'] = dfx['avg_diff_2_games'].astype(float)
        dfx['avg_diff_5_games'] = dfx['avg_diff_5_games'].astype(float)

        dfx.to_csv("all_assessed_bets20230425.csv", index=False)

        bins = [-12, -9, -7, -5, -4, -3, -2, -1, -0.5, 0, 0.5, 1, 2, 3, 4, 5, 7, 12]
        dfx['trend_bins'] = pd.cut(dfx['trend'], bins=bins)
        dfx['avg_diff_2_games_bins'] = pd.cut(dfx['avg_diff_2_games'], bins=bins)
        dfx['avg_diff_5_games_bins'] = pd.cut(dfx['avg_diff_5_games'], bins=bins)
        show(dfx)


    # resolve_bets()
    # analyze_all_bets(start_date="2023-04-15")
    #
    #
    fetch_and_analyze_today_games()
