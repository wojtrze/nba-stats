class Bet():
    def __init__(self, player_ESPN, bet_type, odds, line, over_under, home, away, bet_id, closed_date):
        self.player_ESPN = player_ESPN
        self.bet_type = bet_type
        self.odds = odds
        self.line = line
        self.over_under = over_under
        self.home = home
        self.away = away
        self.bet_id = bet_id
        self.closed_date = closed_date

    def analyse_bet_against_player_stats(self):
        # Compare bet to player stats
        pass

    def analyse_bet_against_historical_player_bets(self):
        # Compare bet to historical player bets
        pass


