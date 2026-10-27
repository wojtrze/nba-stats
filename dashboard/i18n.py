"""Plain-language words for dashboard v2, in English and Polish (no Streamlit, so it can be tested).

Written for someone who has finished school and knows almost nothing about betting: every number says what it is
and what a higher or a lower value means for the bet.

- TERMS: a table column's header (`label`) and tooltip (`tooltip`): what it is, what more / less of it means, an
  example. A key 'context:column' overrides a term on one kind of page (the game model's chance isn't the props
  model's).
- TEXTS: the pages' captions, buttons, verdicts and reasons; t(key, lang, **values) fills one in and raises on a
  missing key or language, so a gap shows up in the tests instead of on a page.
- VALUES: words shown inside cells (Over / Under / pass...), value(word, lang).
"""
import re
from dataclasses import dataclass
from typing import Dict, Optional

LANGS = ('en', 'pl')
DEFAULT = 'en'
LANGUAGE_NAMES = {'en': "🇬🇧 English", 'pl': "🇵🇱 Polski"}


def _w(en: str, pl: str) -> Dict[str, str]:
    return {'en': en, 'pl': pl}


@dataclass(frozen=True)
class Term:
    label: Dict[str, str]
    what: Dict[str, str]
    higher: Optional[Dict[str, str]] = None
    lower: Optional[Dict[str, str]] = None
    example: Optional[Dict[str, str]] = None


TERMS: Dict[str, Term] = {
    # --- which line ---
    'name': Term(_w("player", "zawodnik"), _w("The player the bet is about.", "Zawodnik, którego dotyczy zakład.")),
    'game': Term(_w("game", "mecz"), _w("The game: away team @ home team.", "Mecz: gość @ gospodarz.")),
    'tip-off': Term(_w("tip-off", "start"),
                    _w("When the game starts, Polish time. ⏰ = within the next hour. A line disappears from the list "
                       "when its game starts.",
                       "Kiedy zaczyna się mecz, czasu polskiego. ⏰ = w ciągu godziny. Linia znika z listy, gdy mecz "
                       "się zaczyna.")),
    'bet_type': Term(_w("stat", "statystyka"),
                     _w("What is counted: PTS points, REB rebounds, AST assists, 3PM three-pointers made; PA, PR, RA "
                        "and PRA add two or three of them up (P = points, R = rebounds, A = assists).",
                        "Co jest liczone: PTS punkty, REB zbiórki, AST asysty, 3PM celne rzuty za 3; PA, PR, RA i PRA "
                        "to suma dwóch lub trzech z nich (P = punkty, R = zbiórki, A = asysty).")),
    'line': Term(_w("line", "linia"),
                 _w("The number the bookmaker sets. **Over** wins if the player gets more than the line, **Under** "
                    "if he gets fewer. Lines end in .5, so there's no tie.",
                    "Liczba ustalona przez bukmachera. **Powyżej** wygrywa, gdy zawodnik zdobędzie więcej niż linia, "
                    "**Poniżej**, gdy mniej. Linie kończą się na ,5, więc nie ma remisu."),
                 _w("Harder for Over, easier for Under.", "Trudniej o Powyżej, łatwiej o Poniżej."),
                 _w("Easier for Over, harder for Under.", "Łatwiej o Powyżej, trudniej o Poniżej."),
                 _w("Line 20.5 points: 21 or more = Over wins, 20 or fewer = Under wins.",
                    "Linia 20.5 punktu: 21 lub więcej = wygrywa Powyżej, 20 lub mniej = wygrywa Poniżej.")),

    # --- the decision ---
    'bet': Term(_w("our pick", "nasz typ"),
                _w("**Over** or **Under** when our numbers say the odds pay more than the risk (a positive edge, "
                   "🟢 or 🟡). **pass** = don't bet: on most lines the odds are fair or too low.",
                   "**Powyżej** lub **Poniżej**, gdy nasze liczby mówią, że kurs płaci więcej niż wynosi ryzyko "
                   "(dodatnia przewaga, 🟢 lub 🟡). **odpuść** = nie graj: na większości linii kurs jest uczciwy "
                   "albo za niski.")),
    'signal': Term(_w("signal", "sygnał"),
                   _w("How much to trust the pick. 🟢 = the edge is big enough that such picks have actually won "
                      "money on 10+ evenings we didn't use to build the model (none so far). 🟡 = a positive "
                      "edge on paper, not yet proven. 🔴 = a warning: pass, whatever the numbers say. Empty = no "
                      "edge.",
                      "Na ile ufać typowi. 🟢 = przewaga jest na tyle duża, że takie typy rzeczywiście zarabiały "
                      "przez 10+ wieczorów, których nie użyliśmy do budowy modelu (na razie żaden). 🟡 = przewaga "
                      "na papierze, jeszcze nie potwierdzona. 🔴 = ostrzeżenie: odpuść, cokolwiek mówią liczby. "
                      "Puste = brak przewagi.")),
    'edge pp': Term(_w("edge (pp)", "przewaga (pp)"),
                    _w("Our chance that the pick wins **minus** the chance the odds need just to break even, in "
                       "percentage points (pp). It answers: do the odds pay enough for the risk?",
                       "Nasza szansa, że typ wygra, **minus** szansa potrzebna, żeby przy tym kursie wyjść na zero, "
                       "w punktach procentowych (pp). Odpowiada na pytanie: czy kurs płaci wystarczająco za ryzyko?"),
                    _w("Above 0: the odds pay more than the risk, a value bet. +3 = about 3 more wins per 100 such "
                       "bets than needed to break even. Around 0 = a fair price.",
                       "Więcej niż 0: kurs płaci więcej niż ryzyko, zakład z wartością. +3 = ok. 3 wygrane więcej na 100 "
                       "takich zakładów niż potrzeba, żeby wyjść na zero. Około 0 = uczciwy kurs."),
                    _w("Below 0: the odds pay too little. Betting such lines loses money over time, even if this "
                       "one wins tonight.",
                       "Mniej niż 0: kurs płaci za mało. Granie takich linii z czasem przynosi stratę, nawet jeśli ta "
                       "jedna dziś wejdzie."),
                    _w("Odds 1.90 need a 52.6% chance. Our chance 55% → edge 55 − 52.6 = +2.4 pp.",
                       "Kurs 1.90 wymaga 52.6% szans. Nasza szansa 55% → przewaga 55 − 52.6 = +2.4 pp.")),
    'best side': Term(_w("better side", "lepsza strona"),
                      _w("Over or Under, whichever has the bigger edge, even when both edges are negative. Only a "
                         "pick when the edge is positive (see 'our pick').",
                         "Powyżej lub Poniżej, zależnie od tego, gdzie przewaga jest większa, nawet gdy obie są "
                         "ujemne. To typ tylko przy dodatniej przewadze (zob. 'nasz typ').")),
    'pick odds': Term(_w("odds", "kurs"),
                      _w("Superbet's decimal odds for the better side: what a winning bet pays back per 1 staked, "
                         "stake included.",
                         "Kurs dziesiętny Superbetu na lepszą stronę: ile zwraca wygrany zakład za każdą 1 zł "
                         "stawki, razem ze stawką."),
                      _w("Pays more if it wins, but the bookmaker thinks it's less likely.",
                         "Więcej wypłaca przy wygranej, ale bukmacher uważa ją za mniej prawdopodobną."),
                      _w("Pays less, the bookmaker thinks it's more likely.",
                         "Mniej wypłaca, bukmacher uważa ją za bardziej prawdopodobną."),
                      _w("10 at 1.90 returns 19 if it wins: 9 profit.", "10 zł po kursie 1.90 to 19 zł przy wygranej: "
                                                                        "9 zł zysku.")),
    'model %': Term(_w("our chance %", "nasza szansa %"),
                    _w("How often we expect the better side to win, from the player's games, tonight's lineups and "
                       "the game, corrected by how such chances turned out on past lines. The correction pulls it "
                       "close to the bookmaker's chance, because our own opinion proved to be worth little beyond "
                       "the odds.",
                       "Jak często spodziewamy się wygranej lepszej strony, na podstawie meczów zawodnika, dzisiejszych "
                       "składów i meczu, poprawione o to, jak takie szanse sprawdzały się na dawnych liniach. "
                       "Poprawka ściąga ją blisko szansy bukmachera, bo nasza własna opinia okazała się warta "
                       "niewiele ponad kurs."),
                    _w("More likely to win. Compare it with 'needed to win %': only above it is the bet worth it.",
                       "Większa szansa wygranej. Porównaj z 'potrzebna skuteczność %': opłaca się tylko powyżej niej."),
                    _w("Less likely to win.", "Mniejsza szansa wygranej."),
                    _w("Our chance 55%, odds 1.90 need 52.6% → worth it (edge +2.4 pp).",
                       "Nasza szansa 55%, kurs 1.90 wymaga 52.6% → opłaca się (przewaga +2.4 pp).")),
    'break-even %': Term(_w("needed to win %", "potrzebna skuteczność %"),
                         _w("How often a bet at these odds must win just to break even: 100 ÷ odds. It includes the "
                            "bookmaker's margin.",
                            "Jak często zakład po tym kursie musi wygrywać, żeby wyjść na zero: 100 ÷ kurs. Zawiera "
                            "marżę bukmachera."),
                         _w("The bet must win more often to pay off (lower odds).",
                            "Zakład musi wygrywać częściej, żeby się opłacał (niższy kurs)."),
                         _w("Wins less often are enough (higher odds).",
                            "Wystarczy rzadziej wygrywać (wyższy kurs)."),
                         _w("Odds 1.90 → 100 ÷ 1.90 = 52.6%.", "Kurs 1.90 → 100 ÷ 1.90 = 52.6%.")),
    'market %': Term(_w("bookmaker's chance %", "szansa wg bukmachera %"),
                     _w("The chance Superbet's odds give the side, with the bookmaker's margin taken out, so Over "
                        "and Under add up to 100%. The market's own forecast, which is hard to beat.",
                        "Szansa, jaką kursy Superbetu dają tej stronie, po odjęciu marży bukmachera, tak że Powyżej i "
                        "Poniżej sumują się do 100%. Prognoza samego rynku, trudna do pobicia."),
                     _w("The bookmaker thinks the side is more likely.", "Bukmacher uważa tę stronę za bardziej "
                                                                         "prawdopodobną."),
                     _w("The bookmaker thinks it's less likely.", "Bukmacher uważa ją za mniej prawdopodobną."),
                     _w("Over 1.85, Under 1.95 → 51.3% Over, 48.7% Under.",
                        "Powyżej 1.85, Poniżej 1.95 → 51.3% Powyżej, 48.7% Poniżej.")),
    'edge low': Term(_w("edge, cautious (pp)", "przewaga ostrożnie (pp)"),
                     _w("The edge if the player's record so far was partly luck: the low end of its range. Few games "
                        "make the range wide.",
                        "Przewaga przy założeniu, że dotychczasowe wyniki zawodnika były częściowo szczęściem: dolny "
                        "kraniec jej przedziału. Mało meczów = szeroki przedział."),
                     _w("Above 0: the edge holds even on a cautious reading.",
                        "Więcej niż 0: przewaga trzyma się nawet przy ostrożnym odczycie."),
                     _w("Below 0: the edge may be luck.", "Mniej niż 0: przewaga może być przypadkiem.")),
    'lean': Term(_w("projection leans", "projekcja wskazuje"),
                 _w("Which way 'expected tonight' points when it is at least 10% away from the line. Information "
                    "only: on its own it hasn't beaten Superbet's odds.",
                    "W którą stronę wskazuje 'oczekiwane dziś', gdy różni się od linii o co najmniej 10%. Tylko "
                    "informacja: samo w sobie nie pokonało kursów Superbetu.")),
    'red flag': Term(_w("warning", "ostrzeżenie"),
                     _w("A reason to pass whatever the numbers say: too few games, preseason only, may not play, "
                        "minutes swinging, the line moving against the pick.",
                        "Powód, żeby odpuścić, cokolwiek mówią liczby: za mało meczów, tylko przedsezon, może nie "
                        "zagrać, wahające się minuty, linia ruszyła przeciw typowi.")),
    'RotoWire': Term(_w("tonight's role", "rola dziś"),
                     _w("From RotoWire: starter (✔ = lineup confirmed), bench, or the injury tag with the chance to "
                        "play (Out 0%, Doubt 25%, Ques 50%, Prob 75%). Empty = RotoWire doesn't list the game yet.",
                        "Z RotoWire: w pierwszej piątce (✔ = skład potwierdzony), rezerwa albo oznaczenie kontuzji z "
                        "szansą gry (Out 0%, Doubt 25%, Ques 50%, Prob 75%). Puste = RotoWire jeszcze nie podaje "
                        "tego meczu.")),

    # --- the player's numbers ---
    'proj avg': Term(_w("expected tonight", "oczekiwane dziś"),
                     _w("What we expect the player to get tonight: his average, adjusted for teammates who are out, "
                        "how many points his team is expected to score, and how much the opponent allows to his "
                        "position.",
                        "Ile spodziewamy się, że zawodnik zdobędzie dziś: jego średnia, poprawiona o nieobecnych "
                        "kolegów z drużyny, o to, ile punktów ma zdobyć jego drużyna, i o to, ile rywal pozwala "
                        "zdobywać na jego pozycji."),
                     _w("Above the line: points to Over.", "Wyżej niż linia: wskazuje na Powyżej."),
                     _w("Below the line: points to Under.", "Niżej niż linia: wskazuje na Poniżej."),
                     _w("Expected 23.4, line 20.5 → leans Over.", "Oczekiwane 23.4, linia 20.5 → skłania do "
                                                                  "Powyżej.")),
    'pick % L10': Term(_w("won, last 10 %", "trafione w ost. 10 %"),
                       _w("How often the better side would have won in the player's last 10 games.",
                          "Jak często lepsza strona wygrałaby w ostatnich 10 meczach zawodnika."),
                       _w("The side has been hitting lately.", "Ta strona ostatnio wchodzi."),
                       _w("It has been missing lately.", "Ostatnio nie wchodzi."),
                       _w("7 of 10 = 70%. Compare it with 'needed to win %'; 10 games is a small sample.",
                          "7 z 10 = 70%. Porównaj z 'potrzebna skuteczność %'; 10 meczów to mała próba.")),
    'pick %': Term(_w("won, all games %", "trafione, wszystkie mecze %"),
                   _w("How often the better side would have won in all the games shown.",
                      "Jak często lepsza strona wygrałaby we wszystkich pokazanych meczach."),
                   _w("It usually hits.", "Zwykle wchodzi."), _w("It usually misses.", "Zwykle nie wchodzi.")),
    'avg': Term(_w("average", "średnia"),
                _w("The player's average of this stat in the games shown (the seasons and game types in Scope).",
                   "Średnia zawodnika w tej statystyce w pokazanych meczach (sezony i rodzaje meczów z Zakresu)."),
                _w("Above the line: Over has usually won.", "Wyżej niż linia: zwykle wygrywało Powyżej."),
                _w("Below the line: Under has usually won.", "Niżej niż linia: zwykle wygrywało Poniżej.")),
    'adj avg': Term(_w("avg with absences", "średnia z nieobecnymi"),
                    _w("The average plus the player's usual change when tonight's out teammates miss games "
                       "(RotoWire). Equal to the average when nobody is out.",
                       "Średnia plus zwykła zmiana u zawodnika, gdy dzisiejsi nieobecni koledzy nie grają "
                       "(RotoWire). Równa średniej, gdy nikogo nie brakuje."),
                    _w("He usually gets more without them.", "Bez nich zwykle zdobywa więcej."),
                    _w("He usually gets less without them.", "Bez nich zwykle zdobywa mniej.")),
    'avg L5': Term(_w("avg last 5", "średnia z 5"),
                   _w("Average over the player's last 5 games.", "Średnia z ostatnich 5 meczów zawodnika."),
                   _w("Hot lately (5 games can be luck).", "Ostatnio w formie (5 meczów to może być przypadek)."),
                   _w("Cold lately.", "Ostatnio słabiej.")),
    'games': Term(_w("games", "mecze"),
                  _w("How many of the player's games the numbers come from.", "Z ilu meczów zawodnika pochodzą "
                                                                              "liczby."),
                  _w("More reliable numbers.", "Liczby bardziej wiarygodne."),
                  _w("Less reliable: under 8 games is a warning.", "Mniej wiarygodne: poniżej 8 meczów to "
                                                                   "ostrzeżenie.")),
    'min L5': Term(_w("minutes, last 5", "minuty, ost. 5"),
                   _w("Average minutes played over the last 5 games.", "Średnio rozegrane minuty w ostatnich 5 "
                                                                       "meczach."),
                   _w("A bigger role: more chances to score.", "Większa rola: więcej okazji do zdobyczy."),
                   _w("Falling minutes are a warning for Over.", "Spadające minuty to ostrzeżenie dla Powyżej.")),
    'percentile': Term(_w("line percentile", "percentyl linii"),
                       _w("Where the line sits among the player's results: the share of his games below it.",
                          "Gdzie wypada linia wśród wyników zawodnika: odsetek jego meczów poniżej niej."),
                       _w("A high line for him: he rarely went over it (80 = only 20% of games above).",
                          "Wysoka linia jak na niego: rzadko ją przekraczał (80 = tylko 20% meczów powyżej)."),
                       _w("A low line for him: he usually went over it.", "Niska linia jak na niego: zwykle ją "
                                                                          "przekraczał.")),
    'matchup': Term(_w("matchup", "rywal"),
                    _w("soft / tough: tonight's opponent allows at least 5% more / less of this stat to the player's "
                       "position than the average NBA defense. Soft helps Over, tough helps Under.",
                       "soft / tough (łatwy / trudny): dzisiejszy rywal pozwala na co najmniej 5% więcej / mniej tej "
                       "statystyki na pozycji zawodnika niż przeciętna obrona NBA. Łatwy pomaga Powyżej, trudny "
                       "Poniżej.")),
    'spread': Term(_w("handicap", "handicap"),
                   _w("The player's team handicap on Superbet: −8.5 = favoured to win by 8.5.",
                      "Handicap drużyny zawodnika w Superbecie: −8.5 = faworyt, ma wygrać o 8.5."),
                   _w("A big + : his team is the clear underdog.", "Duży + : jego drużyna to wyraźny słabszy."),
                   _w("A big − : his team is the clear favourite. ±10 or more = blowout risk: starters may sit "
                      "the fourth quarter.",
                      "Duży − : jego drużyna to wyraźny faworyt. ±10 lub więcej = ryzyko pogromu: podstawowi mogą "
                      "nie grać w czwartej kwarcie.")),
    'game total': Term(_w("game total", "suma punktów meczu"),
                       _w("Superbet's line for both teams' points together.", "Linia Superbetu na łączne punkty obu "
                                                                              "drużyn."),
                       _w("A high-scoring game expected: helps Overs.", "Oczekiwany mecz z dużą liczbą punktów: "
                                                                         "pomaga Powyżej."),
                       _w("A low-scoring game expected: helps Unders.", "Oczekiwany mecz z małą liczbą punktów: "
                                                                         "pomaga Poniżej.")),
    'line move': Term(_w("line move", "ruch linii"),
                      _w("The line now minus the line when we first saw it.",
                         "Linia teraz minus linia, gdy zobaczyliśmy ją po raz pierwszy."),
                      _w("The line went up: the market expects more. It agrees with Over and is a warning for "
                         "Under.",
                         "Linia poszła w górę: rynek oczekuje więcej. Zgadza się z Powyżej, to ostrzeżenie dla "
                         "Poniżej."),
                      _w("The line went down: the market expects less. It agrees with Under and is a warning for "
                         "Over.",
                         "Linia poszła w dół: rynek oczekuje mniej. Zgadza się z Poniżej, to ostrzeżenie dla "
                         "Powyżej.")),
    'open line': Term(_w("first line", "pierwsza linia"),
                      _w("The line when our snapshots first saw it.", "Linia, gdy nasze zapisy zobaczyły ją po raz "
                                                                      "pierwszy.")),
    'raw model %': Term(_w("our chance, before correction %", "nasza szansa przed poprawką %"),
                        _w("Our model's own chance before it is corrected by past results. It was overconfident, "
                           "so the corrected 'our chance %' is the one to use.",
                           "Własna szansa modelu, zanim zostanie poprawiona o dawne wyniki. Była zbyt pewna siebie, "
                           "więc należy używać poprawionej 'nasza szansa %'."),
                        _w("The model likes the side more.", "Model bardziej lubi tę stronę."),
                        _w("The model likes it less.", "Model mniej ją lubi.")),
    'over_odds': Term(_w("Over odds", "kurs Powyżej"),
                      _w("Superbet's decimal odds for Over.", "Kurs dziesiętny Superbetu na Powyżej."),
                      _w("Pays more; the bookmaker thinks Over is less likely.",
                         "Płaci więcej; bukmacher uważa Powyżej za mniej prawdopodobne."),
                      _w("Pays less; the bookmaker thinks Over is more likely.",
                         "Płaci mniej; bukmacher uważa Powyżej za bardziej prawdopodobne.")),
    'under_odds': Term(_w("Under odds", "kurs Poniżej"),
                       _w("Superbet's decimal odds for Under.", "Kurs dziesiętny Superbetu na Poniżej."),
                       _w("Pays more; the bookmaker thinks Under is less likely.",
                          "Płaci więcej; bukmacher uważa Poniżej za mniej prawdopodobne."),
                       _w("Pays less; the bookmaker thinks Under is more likely.",
                          "Płaci mniej; bukmacher uważa Poniżej za bardziej prawdopodobne.")),

    # --- results: how lines and picks turned out (Results page, the night view) ---
    'bets': Term(_w("bets", "zakłady"), _w("How many bets were won or lost (pushes and voids left out).",
                                           "Ile zakładów wygrano lub przegrano (zwroty i unieważnione pominięte)."),
                 _w("More bets: the rates below them are more reliable.", "Więcej zakładów: wskaźniki obok są "
                                                                          "bardziej wiarygodne."),
                 _w("Few bets: the rates can be luck.", "Mało zakładów: wskaźniki mogą być przypadkiem.")),
    'lines': Term(_w("lines", "linie"), _w("How many lines were won or lost (pushes and voids left out).",
                                           "Ile linii rozstrzygnięto (zwroty i unieważnione pominięte)."),
                  _w("More lines: more reliable.", "Więcej linii: bardziej wiarygodne."),
                  _w("Few lines: can be luck.", "Mało linii: może być przypadek.")),
    'hit %': Term(_w("won %", "wygrane %"), _w("How often the bets won.", "Jak często zakłady wygrywały."),
                  _w("Won more often. It pays only if it's above the needed-to-win % of the odds (about 52.5% at "
                     "1.90).", "Wygrywały częściej. Opłaca się tylko powyżej skuteczności wymaganej przez kursy "
                               "(ok. 52.5% przy 1.90)."),
                  _w("Won less often.", "Wygrywały rzadziej."),
                  _w("56 of 100 won = 56%.", "56 ze 100 wygranych = 56%.")),
    'ci low %': Term(_w("won %, low end", "wygrane %, dolna granica"),
                     _w("The low end of the 95% range of 'won %': with this many bets, the true rate is very "
                        "likely above it.", "Dolna granica 95% przedziału dla 'wygrane %': przy tej liczbie zakładów "
                                            "prawdziwa skuteczność jest najpewniej wyższa."),
                     _w("Above break-even (about 52.5%): the result is unlikely to be just luck.",
                        "Powyżej progu opłacalności (ok. 52.5%): wynik raczej nie jest tylko przypadkiem."),
                     _w("Below break-even: the bets may not really be winning, it could be luck.",
                        "Poniżej progu: zakłady mogą wcale nie być zyskowne, to może być przypadek.")),
    'ci high %': Term(_w("won %, high end", "wygrane %, górna granica"),
                      _w("The high end of the 95% range of 'won %'. Few bets make the range wide.",
                         "Górna granica 95% przedziału dla 'wygrane %'. Mało zakładów = szeroki przedział.")),
    'ROI %': Term(_w("profit per 100 %", "zysk na 100 %"),
                  _w("Profit for every 100 staked, betting the same amount on each.",
                     "Zysk na każde 100 zł postawione, przy równej stawce na każdy zakład."),
                  _w("Above 0 = made money: +5 means 105 back for every 100 staked.",
                     "Więcej niż 0 = zarobek: +5 znaczy 105 zł zwrotu na każde 100 zł stawek."),
                  _w("Below 0 = lost money. Betting at random loses about −5 (the bookmaker's margin).",
                     "Mniej niż 0 = strata. Losowe granie traci ok. −5 (marża bukmachera).")),
    'avg odds': Term(_w("avg odds", "średni kurs"), _w("The average odds of these bets.",
                                                       "Średni kurs tych zakładów."),
                     _w("Riskier bets that pay more.", "Bardziej ryzykowne zakłady, które więcej płacą."),
                     _w("Safer bets that pay less.", "Bezpieczniejsze zakłady, które mniej płacą.")),
    'expected %': Term(_w("expected %", "oczekiwane %"),
                       _w("How often our model expected these picks to win (its average chance). If the model is "
                          "honest, 'won %' lands close to it.",
                          "Jak często model spodziewał się wygranej tych typów (jego średnia szansa). Jeśli model jest "
                          "rzetelny, 'wygrane %' wypada blisko tej liczby."),
                       _w("The model was more confident.", "Model był bardziej pewny."),
                       _w("The model was less confident.", "Model był mniej pewny.")),
    'edge ≥ pp': Term(_w("edge at least (pp)", "przewaga co najmniej (pp)"),
                      _w("Every pick whose edge reached this many points (0 = any positive edge), so the rows "
                         "overlap.", "Każdy typ, którego przewaga osiągnęła tyle punktów (0 = dowolna dodatnia), więc "
                                     "wiersze się nakładają."),
                      _w("Only picks with a bigger edge: fewer bets.", "Tylko typy z większą przewagą: mniej "
                                                                       "zakładów."),
                      _w("More picks, smaller edges.", "Więcej typów, mniejsze przewagi.")),
    'avg odds vs last %': Term(_w("odds vs last quote %", "kurs wobec ostatniego %"),
                               _w("The bet's odds compared with the last odds our snapshots saw before tip-off, in %.",
                                  "Kurs zakładu w porównaniu z ostatnim kursem zapisanym przed startem, w %."),
                               _w("Above 0: we got a better price than the market settled on, an early sign of a "
                                  "real edge.", "Więcej niż 0: dostaliśmy lepszy kurs niż ostateczny rynkowy, "
                                                "wczesny znak prawdziwej przewagi."),
                               _w("Below 0: the market moved against us.", "Mniej niż 0: rynek ruszył przeciw "
                                                                           "nam.")),
    'odds vs last %': Term(_w("odds vs last quote %", "kurs wobec ostatniego %"),
                           _w("The bet's odds compared with the last odds before tip-off, in %.",
                              "Kurs zakładu w porównaniu z ostatnim kursem przed startem, w %."),
                           _w("A better price than the market's last.", "Lepszy kurs niż ostatni rynkowy."),
                           _w("A worse price.", "Gorszy kurs.")),
    'over %': Term(_w("went over %", "powyżej linii %"), _w("How often the result went over the line.",
                                                            "Jak często wynik był powyżej linii."),
                   _w("Overs won more: the lines were set too low.", "Częściej wygrywało Powyżej: linie były za "
                                                                      "niskie."),
                   _w("Unders won more: the lines were set too high.", "Częściej wygrywało Poniżej: linie były za "
                                                                        "wysokie.")),
    'under %': Term(_w("went under %", "poniżej linii %"), _w("How often betting Under won.",
                                                             "Jak często wygrywało Poniżej."),
                    _w("Unders won more.", "Częściej wygrywało Poniżej."),
                    _w("Unders won less.", "Rzadziej wygrywało Poniżej.")),
    'over ROI %': Term(_w("Over: profit per 100 %", "Powyżej: zysk na 100 %"),
                       _w("Profit per 100 staked betting every Over.", "Zysk na 100 zł, grając każde Powyżej."),
                       _w("Overs made money.", "Powyżej zarabiało."), _w("Overs lost money.", "Powyżej traciło.")),
    'under ROI %': Term(_w("Under: profit per 100 %", "Poniżej: zysk na 100 %"),
                        _w("Profit per 100 staked betting every Under.", "Zysk na 100 zł, grając każde Poniżej."),
                        _w("Unders made money.", "Poniżej zarabiało."), _w("Unders lost money.", "Poniżej traciło.")),
    'side to bet': Term(_w("better side", "lepsza strona"),
                        _w("The side (Over / Under) that won more often in this group.",
                           "Strona (Powyżej / Poniżej), która w tej grupie wygrywała częściej.")),
    'best side %': Term(_w("better side won %", "lepsza strona wygrała %"),
                        _w("How often the better side won in this group.", "Jak często lepsza strona wygrywała w tej "
                                                                           "grupie."),
                        _w("A clearer pattern; check its low end is above break-even.",
                           "Wyraźniejszy wzorzec; sprawdź, czy dolna granica jest powyżej progu."),
                        _w("Close to 50%: no pattern.", "Blisko 50%: brak wzorca.")),
    'best side ROI %': Term(_w("better side: profit per 100 %", "lepsza strona: zysk na 100 %"),
                            _w("Profit per 100 staked on the better side.", "Zysk na 100 zł na lepszej stronie."),
                            _w("It made money.", "Zarabiała."), _w("It lost money.", "Traciła.")),
    'our picks': Term(_w("our picks", "nasze typy"), _w("How many of our picks the group has.",
                                                        "Ile naszych typów jest w grupie.")),
    'our hit %': Term(_w("our picks won %", "nasze typy wygrane %"), _w("How often our picks won.",
                                                                        "Jak często nasze typy wygrywały."),
                      _w("Our picks did better.", "Nasze typy radziły sobie lepiej."),
                      _w("Our picks did worse.", "Nasze typy radziły sobie gorzej.")),
    'our ROI %': Term(_w("our picks: profit per 100 %", "nasze typy: zysk na 100 %"),
                      _w("Profit per 100 staked on our picks.", "Zysk na 100 zł na naszych typach."),
                      _w("Our picks made money.", "Nasze typy zarabiały."), _w("They lost money.", "Traciły.")),
    'venue': Term(_w("home/away", "dom/wyjazd"), _w("The player's team at home or away.",
                                                    "Drużyna zawodnika u siebie czy na wyjeździe.")),
    'position': Term(_w("position", "pozycja"), _w("G = guards, F = forwards, C = centers.",
                                                   "G = obrońcy, F = skrzydłowi, C = środkowi.")),
    'team': Term(_w("team", "drużyna"), _w("The player's team.", "Drużyna zawodnika.")),
    'night': Term(_w("night", "wieczór"), _w("The game date (US time).", "Data meczu (czas USA).")),
    'game_date': Term(_w("date", "data"), _w("The game date (US time).", "Data meczu (czas USA).")),
    'actual': Term(_w("result", "wynik"), _w("What the player actually got.", "Ile zawodnik faktycznie zdobył.")),
    'proj_avg': Term(_w("expected", "oczekiwane"),
                     _w("What we expected the player to get, at our last fetch before tip-off.",
                        "Ile oczekiwaliśmy, że zawodnik zdobędzie, przy ostatnim pobraniu przed startem."),
                     _w("Above the line pointed to Over.", "Wyżej niż linia wskazywało na Powyżej."),
                     _w("Below the line pointed to Under.", "Niżej niż linia wskazywało na Poniżej.")),
    'model_pct': Term(_w("our chance %", "nasza szansa %"), _w("Our chance for the pick then.",
                                                                 "Nasza szansa dla typu w tamtym momencie."),
                      _w("We were more confident.", "Byliśmy bardziej pewni."),
                      _w("We were less confident.", "Byliśmy mniej pewni.")),
    'proj error': Term(_w("miss vs expected", "błąd oczekiwanego"), _w("result − expected.", "wynik − oczekiwane."),
                       _w("The player got more than we expected.", "Zawodnik zdobył więcej, niż oczekiwaliśmy."),
                       _w("He got less than we expected.", "Zdobył mniej, niż oczekiwaliśmy.")),
    'closer than line': Term(_w("we were closer", "byliśmy bliżej"),
                             _w("✔ = our 'expected' was closer to the result than Superbet's line.",
                                "✔ = nasze 'oczekiwane' było bliżej wyniku niż linia Superbetu.")),
    'pick at open': Term(_w("our pick at first", "nasz typ na początku"),
                         _w("Our pick when we first saw the line.", "Nasz typ, gdy zobaczyliśmy linię po raz "
                                                                    "pierwszy.")),
    'red_flag': Term(_w("warning", "ostrzeżenie"), _w("The warnings at the fetch.", "Ostrzeżenia w chwili pobrania.")),
    'recomputed': Term(_w("recomputed", "przeliczone"),
                       _w("✔ = this fetch was saved before our numbers were (before Oct 21): the pick and the "
                          "expectation were recomputed from the games before that night.",
                          "✔ = to pobranie zapisano, zanim zapisywaliśmy nasze liczby (przed 21.10): typ i "
                          "oczekiwanie przeliczono z meczów sprzed tamtego wieczoru.")),
    'result': Term(_w("result", "rezultat"), _w("How the pick did: win, loss, push (a tie on a whole line: the stake "
                                                "comes back) or void (the player didn't play).",
                                                "Jak poszedł typ: wygrana, przegrana, zwrot (remis na pełnej linii: "
                                                "stawka wraca) lub nieważny (zawodnik nie zagrał).")),
    'status': Term(_w("status", "status"), _w("settled; pending (the game isn't in our stats yet); void (didn't play); "
                                              "unresolved (can't be settled from our stats).",
                                              "rozliczony; oczekuje (meczu nie ma jeszcze w statystykach); nieważny "
                                              "(nie zagrał); nierozstrzygnięty (nie da się rozliczyć z naszych "
                                              "danych).")),
    'pre avg': Term(_w("avg before", "średnia przed"), _w("The player's average before that game.",
                                                          "Średnia zawodnika przed tym meczem."),
                    _w("Above the line pointed to Over.", "Wyżej niż linia wskazywała na Powyżej."),
                    _w("Below the line pointed to Under.", "Niżej niż linia wskazywała na Poniżej.")),
    'pre avg L10': Term(_w("avg before, last 10", "średnia przed, ost. 10"), _w("Average of the 10 games before.",
                                                                               "Średnia z 10 meczów przed.")),
    'pre games': Term(_w("games before", "mecze przed"), _w("Games behind the average before.",
                                                            "Z ilu meczów jest średnia przed."),
                      _w("A more reliable average.", "Bardziej wiarygodna średnia."),
                      _w("A shaky average.", "Niepewna średnia.")),
    'pre avg side': Term(_w("average points to", "średnia wskazuje"), _w("The side the average before pointed to.",
                                                                         "Strona, na którą wskazywała średnia "
                                                                         "przed.")),
    'pre avg result': Term(_w("that side's result", "wynik tej strony"), _w("How that side did.",
                                                                            "Jak poszła ta strona.")),
    'last line': Term(_w("last line", "ostatnia linia"), _w("The line at our last snapshot before tip-off.",
                                                            "Linia z ostatniego zapisu przed startem.")),
    'line error': Term(_w("result − line", "wynik − linia"), _w("Average of result − line.",
                                                                "Średnia z wynik − linia."),
                       _w("Players beat the lines: Overs did well.", "Zawodnicy przebijali linie: Powyżej wypadało "
                                                                     "dobrze."),
                       _w("Players fell short: Unders did well.", "Zawodnicy nie dochodzili: Poniżej wypadało "
                                                                  "dobrze.")),
    'line − avg': Term(_w("line − avg", "linia − średnia"),
                       _w("How far the lines sat from the players' averages before the game, on average.",
                          "Jak daleko linie były od średnich zawodników przed meczem, przeciętnie."),
                       _w("Lines above the averages.", "Linie powyżej średnich."),
                       _w("Lines below the averages.", "Linie poniżej średnich.")),
    'toward avg hit %': Term(_w("toward avg: won %", "w stronę średniej: wygrane %"),
                             _w("How often the side the average before pointed to won.",
                                "Jak często wygrywała strona, na którą wskazywała średnia przed."),
                             _w("Following the average worked.", "Podążanie za średnią działało."),
                             _w("It didn't work.", "Nie działało.")),
    'toward avg ROI %': Term(_w("toward avg: profit per 100 %", "w stronę średniej: zysk na 100 %"),
                             _w("Its profit per 100 staked.", "Jej zysk na 100 zł."),
                             _w("Made money.", "Zarabiało."), _w("Lost money.", "Traciło.")),
    'toward proj hit %': Term(_w("toward expected: won %", "w stronę oczekiwanego: wygrane %"),
                              _w("The same toward our 'expected' (newer snapshots only).",
                                 "To samo w stronę naszego 'oczekiwanego' (tylko nowsze zapisy)."),
                              _w("Our expectation pointed the right way more often.",
                                 "Nasze oczekiwanie częściej wskazywało dobrze."),
                              _w("It pointed the wrong way more often.", "Częściej wskazywało źle.")),
    'edge bucket': Term(_w("edge (pp)", "przewaga (pp)"), _w("Picks grouped by their edge.",
                                                             "Typy pogrupowane według przewagi.")),
    'results:pick': Term(_w("our pick then", "nasz typ wtedy"), _w("Our pick when the snapshot was saved.",
                                                                    "Nasz typ w chwili zapisu.")),
    'results:signal': Term(_w("signal then", "sygnał wtedy"), _w("The signal the pick had then (none = no edge).",
                                                                 "Sygnał typu w tamtej chwili (none = brak "
                                                                 "przewagi).")),
    'proj score': Term(_w("expected score", "oczekiwany wynik"), _w("Our expected score, away – home.",
                                                                    "Nasz oczekiwany wynik, gość – gospodarz.")),
    'score': Term(_w("score", "wynik"), _w("The final score, away – home.", "Wynik końcowy, gość – gospodarz.")),
    'proj winner': Term(_w("expected winner", "oczekiwany zwycięzca"), _w("The team we expect to win, and by how "
                                                                          "much.", "Drużyna, która według nas wygra, "
                                                                                   "i o ile.")),
    'winner': Term(_w("winner", "zwycięzca"), _w("Who actually won.", "Kto faktycznie wygrał.")),
    'called': Term(_w("called it", "trafione"), _w("✔ = our expected winner won.", "✔ = nasz oczekiwany zwycięzca "
                                                                                   "wygrał.")),
    'total error': Term(_w("total miss", "błąd sumy"), _w("Actual total points − our expected total.",
                                                          "Faktyczna suma punktów − nasza oczekiwana suma."),
                        _w("A higher-scoring game than we expected.", "Mecz z większą liczbą punktów, niż "
                                                                     "oczekiwaliśmy."),
                        _w("A lower-scoring game than we expected.", "Mecz z mniejszą liczbą punktów, niż "
                                                                     "oczekiwaliśmy.")),
    'best bet': Term(_w("biggest edge", "największa przewaga"), _w("The game bet with our biggest edge (an estimate: "
                                                                   "the game model isn't calibrated).",
                                                                   "Zakład w meczu z naszą największą przewagą "
                                                                   "(szacunek: model meczów nie jest "
                                                                   "skalibrowany).")),
    'best result': Term(_w("its result", "jego wynik"), _w("How that bet did.", "Jak poszedł ten zakład.")),

    # --- game markets (Overview's biggest game edges; the Games page) ---
    'start (PL)': Term(_w("tip-off", "start"), _w("Tip-off, Polish time; ⏰ = within the next hour.",
                                                  "Start meczu, czasu polskiego; ⏰ = w ciągu godziny.")),
    'proj total': Term(_w("expected total", "oczekiwana suma"), _w("Our expected points of both teams together.",
                                                                   "Nasza oczekiwana suma punktów obu drużyn."),
                       _w("A higher-scoring game expected.", "Oczekiwany mecz z większą liczbą punktów."),
                       _w("A lower-scoring game expected.", "Oczekiwany mecz z mniejszą liczbą punktów.")),
    'best edge pp': Term(_w("biggest edge (pp), estimate", "największa przewaga (pp), szacunek"),
                         _w("The biggest edge among this game's bets. The game model isn't calibrated and was "
                            "overconfident, so it's an estimate for research.",
                            "Największa przewaga wśród zakładów w tym meczu. Model meczów nie jest skalibrowany i był "
                            "zbyt pewny siebie, więc to szacunek do analizy."),
                         _w("The model disagrees with the odds more.", "Model bardziej nie zgadza się z kursem."),
                         _w("The model agrees with the odds.", "Model zgadza się z kursem.")),
    'best odds': Term(_w("its odds", "jego kurs"), _w("Superbet's odds for the bet with the biggest edge.",
                                                      "Kurs Superbetu na zakład z największą przewagą.")),
    'market': Term(_w("bet type", "rodzaj zakładu"),
                   _w("Winner (incl. overtime); handicap = the winner after adding the line to the team's score; "
                      "total / team total = points of both teams or one team (incl. overtime).",
                      "Zwycięzca (z dogrywką); handicap = zwycięzca po dodaniu linii do wyniku drużyny; suma / suma "
                      "drużyny = punkty obu drużyn lub jednej (z dogrywką).")),
    'side': Term(_w("side", "strona"), _w("home / away for the winner and handicap, over / under for totals.",
                                          "gospodarz / gość przy zwycięzcy i handicapie, powyżej / poniżej przy "
                                          "sumach.")),
    'odds move': Term(_w("odds move", "ruch kursu"), _w("Odds now minus at the first snapshot.",
                                                        "Kurs teraz minus kurs z pierwszego zapisu."),
                      _w("Odds rose: less money came in on it.", "Kurs wzrósł: mniej pieniędzy wpłynęło na ten "
                                                                 "wynik."),
                      _w("Odds fell: money came in on it.", "Kurs spadł: na ten wynik wpłynęły pieniądze.")),
    'implied %': Term(_w("odds' chance %", "szansa z kursu %"),
                      _w("The chance the odds imply: 100 ÷ odds (margin included, so both sides add up to ~105%).",
                         "Szansa wynikająca z kursu: 100 ÷ kurs (z marżą, więc obie strony sumują się do ok. 105%)."),
                      _w("The bookmaker thinks it's more likely.", "Bukmacher uważa to za bardziej prawdopodobne."),
                      _w("The bookmaker thinks it's less likely.", "Bukmacher uważa to za mniej prawdopodobne.")),
    'fair odds': Term(_w("our fair odds", "nasz uczciwy kurs"), _w("Odds that would match our chance: 100 ÷ our "
                                                                   "chance. Only odds above it would pay.",
                                                                   "Kurs zgodny z naszą szansą: 100 ÷ nasza szansa. "
                                                                   "Opłacałby się tylko kurs wyższy."),
                      _w("We think it's less likely.", "Uważamy to za mniej prawdopodobne."),
                      _w("We think it's more likely.", "Uważamy to za bardziej prawdopodobne.")),
    'out': Term(_w("out", "nie zagra"), _w("A player RotoWire lists as out tonight.",
                                           "Zawodnik, który według RotoWire dziś nie zagra.")),
    'games missed': Term(_w("games missed", "opuszczone mecze"),
                         _w("Team games this player missed while on the team, which the change is based on.",
                            "Mecze drużyny, które zawodnik opuścił, będąc w niej; na nich opiera się zmiana."),
                         _w("A more reliable change.", "Bardziej wiarygodna zmiana."),
                         _w("A shaky change.", "Niepewna zmiana.")),
    'team pts change': Term(_w("team points change", "zmiana punktów drużyny"),
                            _w("How many more (+) or fewer (−) points the team scored without this player.",
                               "Ile punktów więcej (+) lub mniej (−) drużyna zdobywała bez tego zawodnika."),
                            _w("The team scored more without him.", "Bez niego drużyna zdobywała więcej."),
                            _w("The team scored less without him.", "Bez niego drużyna zdobywała mniej.")),
    'opp pts change': Term(_w("opponents' points change", "zmiana punktów rywali"),
                           _w("How many more (+) or fewer (−) points opponents scored without this player.",
                              "Ile punktów więcej (+) lub mniej (−) rywale zdobywali bez tego zawodnika."),
                           _w("Opponents scored more without him (his defense mattered).",
                              "Bez niego rywale zdobywali więcej (jego obrona miała znaczenie)."),
                           _w("Opponents scored less without him.", "Bez niego rywale zdobywali mniej.")),
    'games:model %': Term(_w("model's chance %", "szansa z modelu %"),
                          _w("The game model's chance, from team ratings, pace, home court and who's out. Not "
                             "calibrated against results: it was overconfident.",
                             "Szansa z modelu meczów: ratingi drużyn, tempo, atut własnej hali i nieobecni. Nie "
                             "skalibrowana na wynikach: była zbyt pewna siebie."),
                          _w("The model thinks it's more likely.", "Model uważa to za bardziej prawdopodobne."),
                          _w("The model thinks it's less likely.", "Model uważa to za mniej prawdopodobne.")),
    'games:signal': Term(_w("signal", "sygnał"),
                         _w("🔴 = a reason to pass whatever the numbers say (see warning). Game bets never get 🟢 / "
                            "🟡: their model isn't calibrated, so its edge is an estimate for research.",
                            "🔴 = powód, żeby odpuścić, cokolwiek mówią liczby (zob. ostrzeżenie). Zakłady na mecze "
                            "nigdy nie dostają 🟢 / 🟡: ich model nie jest skalibrowany, więc przewaga to szacunek do "
                            "analizy.")),
    'games:red flag': Term(_w("warning", "ostrzeżenie"),
                           _w("A reason to pass: early season, no RotoWire lineup yet, or an edge too big to be true.",
                              "Powód, żeby odpuścić: początek sezonu, brak składu z RotoWire albo przewaga zbyt duża, "
                              "żeby była prawdziwa.")),
    'games:RotoWire': Term(_w("lineups", "składy"), _w("✔ = RotoWire lists this game's lineups, so who's out is in the "
                                                       "projection.", "✔ = RotoWire podaje składy na ten mecz, więc "
                                                                      "nieobecni są w prognozie.")),
    'games:line': Term(_w("line", "linia"), _w("Handicap: the team's handicap (+1.5 = still wins the bet if it loses "
                                               "by 1). Totals: the points line. Empty for the winner.",
                                               "Handicap: handicap drużyny (+1.5 = zakład wygrywa nawet przy porażce "
                                               "o 1). Sumy: linia punktów. Puste przy zwycięzcy.")),
    'games:team': Term(_w("team", "drużyna"), _w("The team the bet is about.", "Drużyna, której dotyczy zakład.")),

    'odds': Term(_w("odds", "kurs"),
                 _w("Superbet's decimal odds: what a winning bet pays back per 1 staked, stake included.",
                    "Kurs dziesiętny Superbetu: ile zwraca wygrany zakład za każdą 1 zł stawki, razem ze stawką."),
                 _w("Pays more if it wins, but the bookmaker thinks it's less likely.",
                    "Więcej wypłaca przy wygranej, ale bukmacher uważa ją za mniej prawdopodobną."),
                 _w("Pays less, the bookmaker thinks it's more likely.",
                    "Mniej wypłaca, bukmacher uważa ją za bardziej prawdopodobną.")),
    'games:bet': Term(_w("bet", "zakład"),
                      _w("The game outcome: the winner, a handicap or a points total.",
                         "Wynik meczu, którego dotyczy zakład: zwycięzca, handicap albo suma punktów.")),
    'games:edge pp': Term(_w("edge (pp), estimate", "przewaga (pp), szacunek"),
                          _w("The game model's chance minus the chance the odds need to break even, in percentage "
                             "points. The game model isn't calibrated against results yet and was overconfident, so "
                             "this is an estimate for research, not a reason to bet.",
                             "Szansa z modelu meczów minus szansa potrzebna, żeby przy tym kursie wyjść na zero, w "
                             "punktach procentowych. Model meczów nie jest jeszcze skalibrowany na wynikach i był "
                             "zbyt pewny siebie, więc to szacunek do analizy, a nie powód do gry."),
                          _w("The model likes the outcome more than the odds do.",
                             "Model lubi ten wynik bardziej niż kurs."),
                          _w("The model likes it less than the odds do.", "Model lubi go mniej niż kurs.")),
}

# the numbers a pick is decided on: their tooltips must say what more and what less means
DECISION_TERMS = ['edge pp', 'model %', 'pick odds', 'break-even %', 'market %', 'proj avg', 'pick % L10', 'line',
                  'edge low', 'avg', 'games', 'percentile', 'line move', 'min L5', 'spread', 'game total']

_HEADINGS = {'higher': _w("↑ Higher", "↑ Gdy więcej"), 'lower': _w("↓ Lower", "↓ Gdy mniej"),
             'example': _w("Example", "Przykład")}


def term(column: str, context: Optional[str] = None) -> Optional[Term]:
    return TERMS.get(f"{context}:{column}") if context and f"{context}:{column}" in TERMS else TERMS.get(column)


def label(column: str, lang: str, context: Optional[str] = None) -> str:
    """The column's header in `lang` (the column name when there's no term for it)."""
    found = term(column, context)
    return found.label[lang] if found else column


def tooltip(column: str, lang: str, context: Optional[str] = None) -> Optional[str]:
    """What it is, what more / less of it means, an example: Markdown for a header tooltip. None without a term."""
    found = term(column, context)
    if not found:
        return None
    parts = [found.what[lang]]
    for part in ('higher', 'lower'):
        text = getattr(found, part)
        if text:
            parts.append(f"**{_HEADINGS[part][lang]}:** {text[lang]}")
    if found.example:
        parts.append(f"*{_HEADINGS['example'][lang]}:* {found.example[lang]}")
    return "\n\n".join(parts)


# --- words inside cells ---

VALUES = {'win': _w("win", "wygrana"), 'loss': _w("loss", "przegrana"), 'push': _w("push", "zwrot"),
          'void': _w("void", "nieważny"), 'settled': _w("settled", "rozliczony"), 'pending': _w("pending", "oczekuje"),
          'unresolved': _w("unresolved", "nierozstrzygnięty"), 'none': _w("none", "brak"),
          'home': _w("home", "gospodarz"), 'away': _w("away", "gość"), 'over': _w("over", "powyżej"),
          'under': _w("under", "poniżej"),
          'Over': _w("Over", "Powyżej"), 'Under': _w("Under", "Poniżej"), 'pass': _w("pass", "odpuść"),
          '': _w("", ""), 'starter': _w("starter", "pierwsza piątka"), 'bench': _w("bench", "rezerwa"),
          'soft': _w("soft", "łatwy"), 'tough': _w("tough", "trudny"), 'average': _w("average", "przeciętny")}


def value(word, lang: str):
    """A cell's word in `lang` (anything without a translation stays as it is)."""
    if not isinstance(word, str):
        return word
    if word.startswith('starter'):
        return VALUES['starter'][lang] + word[len('starter'):]
    return VALUES[word][lang] if word in VALUES else word


# --- the pages' texts ---

TEXTS: Dict[str, Dict[str, str]] = {
    # navigation and the language switch
    'nav.tonight': _w("Tonight", "Dziś"), 'nav.research': _w("Research", "Analiza"),
    'nav.review': _w("Review", "Wyniki"), 'nav.data': _w("Data", "Dane"),
    'nav.overview': _w("Overview", "Przegląd"), 'nav.props': _w("Props", "Zakłady na zawodników"),
    'nav.games': _w("Games", "Mecze"), 'nav.help': _w("How to read this", "Jak to czytać"),
    'nav.player': _w("Player history", "Historia zawodnika"), 'nav.team': _w("Team history", "Historia drużyny"),
    'nav.lineup': _w("Lineup lab", "Laboratorium składów"), 'nav.results': _w("Results", "Wyniki"),
    'nav.backtest': _w("Backtest 2022/23", "Test wsteczny 2022/23"), 'nav.data_center': _w("Data center",
                                                                                          "Centrum danych"),
    'language': _w("Language", "Język"),
    'source': _w("Source: {name}", "Źródło: {name}"),
    'legend.green': _w("🟢 = an edge of +{edge:g} pp or more: picks like that have won money on 10+ evenings the model "
                       "never saw.", "🟢 = przewaga +{edge:g} pp lub więcej: takie typy zarabiały przez 10+ "
                                     "wieczorów, których model nie widział."),
    'legend.no_green': _w("No 🟢 for now: no edge size has proven itself on 10+ unseen evenings yet.",
                          "Na razie brak 🟢: żadna wielkość przewagi nie sprawdziła się jeszcze przez 10+ "
                          "nieznanych modelowi wieczorów."),
    'legend.rest': _w("🟡 = a positive edge on paper, not yet proven. 🔴 = a warning: pass, whatever the numbers say "
                      "(listed last).", "🟡 = dodatnia przewaga na papierze, jeszcze niepotwierdzona. 🔴 = "
                                        "ostrzeżenie: odpuść, cokolwiek mówią liczby (na końcu listy)."),

    # Props page
    'props.title': _w("Props", "Zakłady na zawodników"),
    'props.purpose': _w("Superbet's player lines for the next 36 hours, compared with each player's games and "
                        "tonight's lineups. Pick a row to see why to bet or pass.",
                        "Linie Superbetu na zawodników na najbliższe 36 godzin, porównane z meczami każdego "
                        "zawodnika i dzisiejszymi składami. Wybierz wiersz, żeby zobaczyć, czy grać i dlaczego."),
    'props.how_to_choose': _w("**How to choose:** look for a 🟢 or 🟡 signal and a positive **edge**, check there is "
                              "no **warning**, then open the row and read the reasons for and against. Hover any "
                              "header for what it means; **How to read this** in the menu explains it all.",
                              "**Jak wybierać:** szukaj sygnału 🟢 lub 🟡 i dodatniej **przewagi**, sprawdź, czy "
                              "nie ma **ostrzeżenia**, potem otwórz wiersz i przeczytaj powody za i przeciw. "
                              "Najedź na nagłówek, żeby zobaczyć, co znaczy; **Jak to czytać** w menu wyjaśnia "
                              "wszystko."),
    'props.filter.games': _w("Games", "Mecze"), 'props.filter.all_games': _w("All games", "Wszystkie mecze"),
    'props.filter.types': _w("Stats", "Statystyki"),
    'props.filter.types_help': _w("PA = points + assists, PR = points + rebounds, RA = rebounds + assists, PRA = all "
                                  "three", "PA = punkty + asysty, PR = punkty + zbiórki, RA = zbiórki + asysty, PRA "
                                           "= wszystkie trzy"),
    'props.filter.signal': _w("Signal", "Sygnał"),
    'props.signal.all': _w("All", "Wszystkie"), 'props.signal.positive': _w("🟢🟡 Positive edge", "🟢🟡 Dodatnia "
                                                                                                "przewaga"),
    'props.signal.sure': _w("🟢 Proven", "🟢 Potwierdzone"),
    'props.filter.red_only_all': _w("🔴 lines are only in All.", "Linie 🔴 są tylko w Wszystkie."),
    'props.more': _w("More", "Więcej"),
    'props.hide_out': _w("Hide players RotoWire lists as out", "Ukryj zawodników, którzy wg RotoWire nie zagrają"),
    'props.min_games': _w("Min games", "Min. meczów"),
    'props.min_games_help': _w("Hide players with fewer games behind their numbers",
                               "Ukryj zawodników z mniejszą liczbą meczów"),
    'props.every_column': _w("Show every column", "Pokaż wszystkie kolumny"),
    'props.sort': _w("Sort by", "Sortuj"), 'props.sort.tip': _w("Tip-off, then edge", "Start, potem przewaga"),
    'props.sort.edge': _w("Edge only", "Tylko przewaga"),
    'props.kpi.shown': _w("Lines shown", "Pokazane linie"),
    'props.kpi.shown_help': _w("Lines that pass the filters, of every line Superbet offers",
                               "Linie spełniające filtry, spośród wszystkich linii Superbetu"),
    'props.kpi.green': _w("🟢 Proven", "🟢 Potwierdzone"),
    'props.kpi.green_help': _w("Picks whose edge is big enough that such picks have actually won money on unseen "
                               "evenings", "Typy z przewagą na tyle dużą, że takie typy rzeczywiście zarabiały w "
                                           "wieczory spoza budowy modelu"),
    'props.kpi.yellow': _w("🟡 Positive edge", "🟡 Dodatnia przewaga"),
    'props.kpi.yellow_help': _w("The odds pay more than the risk on paper; not yet proven",
                                "Kurs na papierze płaci więcej niż ryzyko; jeszcze nie potwierdzone"),
    'props.kpi.games': _w("Games", "Mecze"),
    'props.kpi.red': _w("🔴 Warnings", "🔴 Ostrzeżenia"),
    'props.kpi.red_help': _w("Lines with a reason to pass whatever the numbers say", "Linie z powodem, żeby "
                                                                                     "odpuścić, cokolwiek mówią "
                                                                                     "liczby"),
    'props.order.tip': _w("Earliest tip-off first; within a game 🟢 first, then the biggest edge",
                          "Najpierw najwcześniejszy start; w meczu najpierw 🟢, potem największa przewaga"),
    'props.order.edge': _w("🟢 first, then the biggest edge", "Najpierw 🟢, potem największa przewaga"),
    'props.order.rest': _w(", 🔴 last. ⏰ = starts within the hour; a line leaves the list when its game starts. "
                           "Hover a header for what it means; pick a row for the details. Most lines are a **pass**: "
                           "our numbers rarely disagree with the bookmaker enough to beat its margin.",
                           ", 🔴 na końcu. ⏰ = start w ciągu godziny; linia znika, gdy zaczyna się mecz. Najedź na "
                           "nagłówek, żeby zobaczyć, co znaczy; wybierz wiersz po szczegóły. Większość linii to "
                           "**odpuść**: nasze liczby rzadko różnią się od bukmachera na tyle, żeby pokonać jego "
                           "marżę."),
    'props.pick_row': _w("Pick a row in the table to see the reasons to bet or pass, the teammates' effect and the "
                         "history.", "Wybierz wiersz w tabeli, żeby zobaczyć powody za i przeciw, wpływ kolegów z "
                                     "drużyny i historię."),
    'props.no_logs': _w("No game logs for {name}: the Superbet name didn't match an ESPN player. Add it to OVERRIDES "
                        "in name_resolver.py.", "Brak meczów dla {name}: nazwa z Superbetu nie pasuje do zawodnika "
                                                "ESPN. Dodaj ją do OVERRIDES w name_resolver.py."),
    'props.no_odds': _w("Superbet has no odds for this line.", "Superbet nie ma kursów na tę linię."),
    'props.no_props': _w("**Superbet has no player props right now.** In preseason it only offers game markets; props "
                         "appear with the regular season. If games are on tonight, fetch the offers again in the Data "
                         "center. Meanwhile, check any line by hand below.",
                         "**Superbet nie ma teraz zakładów na zawodników.** W przedsezonie oferuje tylko zakłady na "
                         "mecze; zakłady na zawodników pojawiają się w sezonie zasadniczym. Jeśli dziś są mecze, "
                         "pobierz oferty ponownie w Centrum danych. W międzyczasie sprawdź dowolną linię ręcznie "
                         "poniżej."),
    'props.checker': _w("Line checker", "Sprawdzanie linii"),
    'props.checker_any': _w("Line checker: any player, any line", "Sprawdzanie linii: dowolny zawodnik, dowolna "
                                                                  "linia"),
    'banner.none': _w("📋 RotoWire doesn't list tonight's lineups (yet), so the averages aren't adjusted for absences. "
                      "Lineup lab can still show each player's numbers without a teammate.",
                      "📋 RotoWire (jeszcze) nie podaje dzisiejszych składów, więc średnie nie uwzględniają "
                      "nieobecnych. Laboratorium składów nadal pokaże liczby zawodnika bez danego kolegi."),
    'banner.some': _w("📋 Adjusted with RotoWire's lineups for {known} of {total} games ({confirmed} confirmed). Not "
                      "listed yet: {missing}.", "📋 Poprawione o składy z RotoWire dla {known} z {total} meczów "
                                                "({confirmed} potwierdzonych). Jeszcze bez składów: {missing}."),
    'banner.all': _w("📋 Every game adjusted with RotoWire's lineups ({confirmed} of {total} confirmed).",
                     "📋 Każdy mecz poprawiony o składy z RotoWire ({confirmed} z {total} potwierdzonych)."),

    # the selected line
    'detail.pass_title': _w("{name} · pass (better side {side}, edge {edge:+.1f} pp)",
                            "{name} · odpuść (lepsza strona {side}, przewaga {edge:+.1f} pp)"),
    'detail.not_listed': _w("not on RotoWire yet", "jeszcze nie ma w RotoWire"),
    'detail.tab.verdict': _w("Verdict", "Werdykt"),
    'detail.tab.mates': _w("Teammates (with / without)", "Koledzy (z / bez)"),
    'detail.tab.history': _w("History", "Historia"), 'detail.tab.move': _w("Line movement", "Ruch linii"),
    'detail.built': _w("**How 'expected tonight' was built**", "**Jak powstało 'oczekiwane dziś'**"),
    'detail.kpi.avg': _w("Average", "Średnia"), 'detail.kpi.avg_help': _w("{games} {games|game|games|games} in the scope",
                                                                          "{games} {games|mecz|mecze|meczów} w zakresie"),
    'detail.kpi.out': _w("+ teammates out", "+ nieobecni koledzy"),
    'detail.kpi.out_help': _w("The player's usual change when RotoWire's out players miss games",
                              "Zwykła zmiana u zawodnika, gdy nieobecni wg RotoWire nie grają"),
    'detail.kpi.game': _w("+ game & matchup", "+ mecz i rywal"),
    'detail.kpi.game_help': _w("How many points Superbet expects his team to score vs its usual (×{pace:.2f}) and what "
                               "the opponent allows to his position (×{matchup:.2f}, {word})",
                               "Ile punktów Superbet oczekuje od jego drużyny wobec zwykłej liczby (×{pace:.2f}) i "
                               "ile rywal pozwala zdobywać na jego pozycji (×{matchup:.2f}, {word})"),
    'detail.kpi.line': _w("Line", "Linia"), 'detail.kpi.line_delta': _w("{gap:+.1f} vs expected",
                                                                         "{gap:+.1f} wobec oczekiwanego"),
    'detail.open_player': _w("Open in Player history", "Otwórz w Historii zawodnika"),
    'detail.open_lineup': _w("Open {team} in Lineup lab", "Otwórz {team} w Laboratorium składów"),
    'detail.unknown': _w("unknown", "nieznany"),

    'mates.no_team': _w("The player's team isn't known from the stored games.",
                        "Drużyna zawodnika nie jest znana z zapisanych meczów."),
    'mates.every_season': _w("Use every stored season", "Użyj wszystkich zapisanych sezonów"),
    'mates.every_season_help': _w("Early in the season the current season has too few games without anyone; earlier "
                                  "seasons only count while both were on the team",
                                  "Na początku sezonu jest za mało meczów bez danego zawodnika; wcześniejsze sezony "
                                  "liczą się tylko wtedy, gdy obaj grali w drużynie"),
    'mates.not_listed': _w("📋 RotoWire doesn't list this team tonight, so nobody is marked out.",
                           "📋 RotoWire nie podaje dziś tej drużyny, więc nikt nie jest oznaczony jako nieobecny."),
    'mates.out': _w("📋 Out tonight (outlined): {names}. Their changes are already in the average above ({adj:+.1f}).",
                    "📋 Dziś nie zagrają (obramowani): {names}. Ich wpływ jest już w średniej powyżej ({adj:+.1f})."),
    'mates.none': _w("No teammate missed a game this player played, so there's nothing to compare yet.",
                     "Żaden kolega nie opuścił meczu, w którym grał ten zawodnik, więc nie ma jeszcze czego "
                     "porównać."),
    'mates.chart': _w("{name}'s {stat} when each teammate doesn't play", "{stat} zawodnika {name}, gdy dany kolega "
                                                                         "nie gra"),
    'mates.hover': _w("{mate} out: {without:.1f} in {n_without:.0f} games<br>playing: {with_:.1f} in {n_with:.0f} games",
                      "{mate} nie gra: {without:.1f} w {n_without:.0f} meczach<br>gra: {with_:.1f} w {n_with:.0f} "
                      "meczach"),
    'mates.col.teammate': _w("teammate", "kolega"), 'mates.col.out': _w("out tonight", "dziś nie gra"),
    'mates.col.change': _w("change", "zmiana"),
    'mates.col.change_help': _w("{stat} without the teammate minus with him. + = the player gets more when the "
                                "teammate is out.", "{stat} bez kolegi minus z nim. + = zawodnik zdobywa więcej, gdy "
                                                    "kolegi nie ma."),
    'mates.col.with': _w("{stat} with", "{stat} z nim"), 'mates.col.without': _w("{stat} without", "{stat} bez niego"),
    'mates.col.n_with': _w("games with", "mecze z nim"), 'mates.col.n_without': _w("games without", "mecze bez niego"),
    'mates.reliability': _w("Few games without a teammate make a change unreliable: 3 games is a hint, 10+ is evidence. "
                            "Only games inside the teammate's time on the team count.",
                            "Mało meczów bez kolegi to niepewna zmiana: 3 mecze to wskazówka, 10+ to dowód. Liczą się "
                            "tylko mecze z okresu, gdy kolega był w drużynie."),
    'history.none': _w("No games in the scope.", "Brak meczów w zakresie."),
    'history.chart': _w("Last {n} games vs the line", "Ostatnie {n} meczów wobec linii"),
    'history.dist': _w("Every game in the scope", "Wszystkie mecze w zakresie"),
    'history.splits': _w("**Splits**", "**Podziały**"),
    'history.vs_opp': _w("**Against {opp}** (every stored season): {avg:.1f} avg in {n} games, over {line:g} in {over}",
                         "**Przeciw {opp}** (wszystkie zapisane sezony): średnio {avg:.1f} w {n} meczach, powyżej "
                         "{line:g} w {over}"),
    'move.none': _w("No snapshots saved yet, so there's no history of this line.",
                    "Brak zapisanych ofert, więc nie ma historii tej linii."),
    'move.not_saved': _w("This line isn't in any saved snapshot yet.", "Tej linii nie ma jeszcze w żadnym zapisie."),
    'move.time': _w("time", "czas"),
    'move.now': _w("Now: line {line:g}, over {over:.2f} / under {under:.2f}. A line moving with the pick (up for an "
                   "Over) means the market agrees.", "Teraz: linia {line:g}, Powyżej {over:.2f} / Poniżej "
                                                      "{under:.2f}. Linia ruszająca w stronę typu (w górę przy "
                                                      "Powyżej) znaczy, że rynek się zgadza."),
    'checker.player': _w("Player", "Zawodnik"), 'checker.pick': _w("Type a name...", "Wpisz nazwisko..."),
    'checker.stat': _w("Stat", "Statystyka"), 'checker.line': _w("Line", "Linia"),
    'checker.games': _w("Games", "Mecze"), 'checker.all': _w("Over / Under (all)", "Powyżej / Poniżej (wszystkie)"),
    'checker.last10': _w("Over / Under (last 10)", "Powyżej / Poniżej (ost. 10)"),
    'checker.band': _w("Middle 40% of results", "Środkowe 40% wyników"),
    'checker.band_help': _w("The 30th to 70th percentile of the player's results. A line outside it looks unusually "
                            "low or high for him.", "Od 30. do 70. percentyla wyników zawodnika. Linia poza tym "
                                                    "przedziałem jest jak na niego nietypowo niska lub wysoka."),
    'checker.inside': _w("line inside", "linia w środku"), 'checker.outside': _w("line outside", "linia poza"),

    # the verdict panel (components.reasons_panel)
    'panel.for': _w("For", "Za"), 'panel.against': _w("Against", "Przeciw"), 'panel.nothing': _w("nothing", "nic"),
    'panel.pass_reasons': _w("Reasons to pass", "Powody, żeby odpuścić"),
    'panel.chart': _w("Last {n} games: {stat} (green = over the line)", "Ostatnie {n} meczów: {stat} (zielone = "
                                                                       "powyżej linii)"),
    'panel.line': _w("line {line:g}", "linia {line:g}"),
    'verdict.Bet': _w("Bet", "Graj"), 'verdict.Lean': _w("Lean", "Rozważ"), 'verdict.Pass': _w("Pass", "Odpuść"),
    'verdict.game': _w("The game model isn't calibrated against results yet: its edge is an estimate for research, "
                       "not a betting signal", "Model meczów nie jest jeszcze skalibrowany na wynikach: jego "
                                               "przewaga to szacunek do analizy, nie sygnał do gry"),
    'verdict.no_calibration': _w("No valid calibration: the model's chance isn't a betting signal (research only)",
                                 "Brak aktualnej kalibracji: szansa modelu nie jest sygnałem do gry (tylko do "
                                 "analizy)"),
    'verdict.no_value': _w("The odds don't pay enough for the chance", "Kurs nie płaci wystarczająco za tę szansę"),
    'verdict.strong': _w("A proven edge (🟢), and {pros} {pros|reason|reasons|reasons} for vs {cons} against",
                         "Potwierdzona przewaga (🟢) i {pros} {pros|powód|powody|powodów} za wobec {cons} przeciw"),
    'verdict.lean_unproven': _w("Positive edge, {pros} {pros|reason|reasons|reasons} for vs {cons} against, but not a proven one (🟡)",
                                "Dodatnia przewaga, {pros} {pros|powód|powody|powodów} za wobec {cons} przeciw, ale niepotwierdzona (🟡)"),
    'verdict.lean': _w("{pros} {pros|reason|reasons|reasons} for vs {cons} against", "{pros} {pros|powód|powody|powodów} za wobec {cons} przeciw"),
    'verdict.more_against': _w("Positive edge, but more reasons against ({cons}) than for ({pros})",
                               "Dodatnia przewaga, ale więcej powodów przeciw ({cons}) niż za ({pros})"),

    # reasons for and against a prop (reasons.prop_reasons)
    'reason.model': _w("Model: {side} wins {model:.0f}% of the time; odds {odds:.2f} need {be:.0f}% (edge {edge:+.1f} "
                       "pp, {low:+.1f} at the low end of the range)",
                       "Model: {side} wygrywa w {model:.0f}% przypadków; kurs {odds:.2f} wymaga {be:.0f}% (przewaga "
                       "{edge:+.1f} pp, {low:+.1f} przy ostrożnym odczycie)"),
    'reason.hits': _w("{side} in {hits} of {label} ({rate:.0f}%; needs {be:.0f}%)",
                      "{side} w {hits} z {label} ({rate:.0f}%; potrzeba {be:.0f}%)"),
    'reason.last_games': _w("the last {n} games", "ostatnich {n} meczów"),
    'reason.all_games': _w("all {n} games", "wszystkich {n} meczów"),
    'reason.expected': _w("Expected {proj:.1f} {stat} tonight vs the line {line:g} ({diff:+.1f}); average {avg:.1f}, "
                          "median {median:.1f}", "Oczekiwane dziś {proj:.1f} {stat} wobec linii {line:g} "
                                                 "({diff:+.1f}); średnia {avg:.1f}, mediana {median:.1f}"),
    'reason.minutes_up': _w("Minutes up lately: {recent:.1f} per game in the last 5 vs {usual:.1f}",
                            "Ostatnio więcej minut: {recent:.1f} na mecz w ostatnich 5 wobec {usual:.1f}"),
    'reason.minutes_down': _w("Minutes down lately: {recent:.1f} per game in the last 5 vs {usual:.1f}",
                              "Ostatnio mniej minut: {recent:.1f} na mecz w ostatnich 5 wobec {usual:.1f}"),
    'reason.teammates': _w("{names} out: {name} usually gets {adj:+.1f} {stat} without them",
                           "{names} nie zagra: {name} zwykle ma {adj:+.1f} {stat} bez nich"),
    'reason.home': _w("At home: {value:.1f} in {n} home games ({avg:.1f} overall)",
                      "U siebie: {value:.1f} w {n} meczach u siebie ({avg:.1f} ogółem)"),
    'reason.away': _w("Away: {value:.1f} in {n} away games ({avg:.1f} overall)",
                      "Na wyjeździe: {value:.1f} w {n} meczach wyjazdowych ({avg:.1f} ogółem)"),
    'reason.b2b': _w("Second night of a back-to-back", "Drugi mecz dzień po dniu"),
    'reason.b2b_detail': _w(": {value:.1f} in {n} such games ({avg:.1f} overall)",
                            ": {value:.1f} w {n} takich meczach ({avg:.1f} ogółem)"),
    'reason.matchup': _w("{opp} allow {value:.1f} {stat} per game to {position}, {diff:.1f} {more} than average (rank "
                         "{rank} of {teams}, 1 = allows the most): {word} matchup",
                         "{opp} pozwalają {position} na {value:.1f} {stat} na mecz, o {diff:.1f} {more} niż przeciętnie "
                         "(miejsce {rank} z {teams}, 1 = pozwala najwięcej): {word} rywal"),
    'reason.more': _w("more", "więcej"), 'reason.fewer': _w("fewer", "mniej"),
    'reason.position.G': _w("guards", "obrońcom"), 'reason.position.F': _w("forwards", "skrzydłowym"),
    'reason.position.C': _w("centers", "środkowym"), 'reason.position.': _w("this position", "tej pozycji"),
    'reason.vs_opp': _w("Against {opp}: {avg:.1f} {stat} in {n} games (all stored seasons)",
                        "Przeciw {opp}: {avg:.1f} {stat} w {n} meczach (wszystkie zapisane sezony)"),
    'reason.implied_higher': _w("Superbet expects {team} to score {implied:.0f} (usually {usual:.0f}): a "
                                "higher-scoring game than usual", "Superbet oczekuje, że {team} zdobędzie "
                                                                  "{implied:.0f} (zwykle {usual:.0f}): mecz z większą "
                                                                  "liczbą punktów niż zwykle"),
    'reason.implied_lower': _w("Superbet expects {team} to score {implied:.0f} (usually {usual:.0f}): a "
                               "lower-scoring game than usual", "Superbet oczekuje, że {team} zdobędzie "
                                                                "{implied:.0f} (zwykle {usual:.0f}): mecz z mniejszą "
                                                                "liczbą punktów niż zwykle"),
    'reason.blowout_favoured': _w("{team} favoured by {spread:g}: in a blowout starters sit out the fourth quarter",
                                  "{team} faworytem o {spread:g}: przy pogromie podstawowi siedzą w czwartej "
                                  "kwarcie"),
    'reason.blowout_underdogs': _w("{team} underdogs by {spread:g}: in a blowout starters sit out the fourth quarter",
                                   "{team} słabszy o {spread:g}: przy pogromie podstawowi siedzą w czwartej "
                                   "kwarcie"),
    'reason.line_up_with': _w("The line moved up {move:g} since the first snapshot (the market moved your way)",
                              "Linia wzrosła o {move:g} od pierwszego zapisu (rynek poszedł w twoją stronę)"),
    'reason.line_up_against': _w("The line moved up {move:g} since the first snapshot (the market moved against you)",
                                 "Linia wzrosła o {move:g} od pierwszego zapisu (rynek poszedł przeciw tobie)"),
    'reason.line_down_with': _w("The line moved down {move:g} since the first snapshot (the market moved your way)",
                                "Linia spadła o {move:g} od pierwszego zapisu (rynek poszedł w twoją stronę)"),
    'reason.line_down_against': _w("The line moved down {move:g} since the first snapshot (the market moved against "
                                   "you)", "Linia spadła o {move:g} od pierwszego zapisu (rynek poszedł przeciw "
                                           "tobie)"),

    # warnings (reasons.prop_flags)
    'flag.few_games': _w("Only {n} {n|game|games|games} in the sample: too few to trust the numbers",
                         "Tylko {n} {n|mecz|mecze|meczów} w próbie: za mało, żeby ufać liczbom"),
    'flag.preseason': _w("Every game is preseason: minutes and roles change in the regular season",
                         "Wszystkie mecze to przedsezon: minuty i role zmieniają się w sezonie zasadniczym"),
    'flag.may_not_play': _w("RotoWire: {status}: may sit or play limited minutes",
                            "RotoWire: {status}: może nie zagrać albo zagrać mało minut"),
    'flag.minutes': _w("Minutes swing a lot ({low:.0f}–{high:.0f}): the role isn't settled",
                       "Minuty bardzo się wahają ({low:.0f}–{high:.0f}): rola nie jest ustalona"),
    'flag.line_against': _w("The line moved {move:g} against the pick: the market may know something (injury, "
                            "minutes)", "Linia ruszyła o {move:g} przeciw typowi: rynek może coś wiedzieć "
                                        "(kontuzja, minuty)"),

    # game outcomes (core/labels.py) and their reasons (reasons.game_reasons)
    'market.ML': _w("Winner", "Zwycięzca"), 'market.SPREAD': _w("Handicap", "Handicap"),
    'market.TOTAL': _w("Total", "Suma"), 'market.HOME_TOTAL': _w("Home team total", "Suma gospodarza"),
    'market.AWAY_TOTAL': _w("Away team total", "Suma gościa"),
    'winner': _w("{team} by {margin:.1f}", "{team} o {margin:.1f}"),
    'game.model': _w("Model: {model:.0f}% vs {implied:.0f}% implied by odds {odds:.2f} (edge {edge:+.1f} pp)",
                     "Model: {model:.0f}% wobec {implied:.0f}% z kursu {odds:.2f} (przewaga {edge:+.1f} pp)"),
    'game.wins_by': _w("wins by {margin:.1f}", "wygrywa o {margin:.1f}"),
    'game.loses_by': _w("loses by {margin:.1f}", "przegrywa o {margin:.1f}"),
    'game.projection': _w("Projection: {team} {what}", "Prognoza: {team} {what}"),
    'game.covering': _w(", covering {line:+g} by {gap:.1f}", ", pokrywa {line:+g} o {gap:.1f}"),
    'game.missing': _w(", missing {line:+g} by {gap:.1f}", ", nie pokrywa {line:+g} o {gap:.1f}"),
    'game.net': _w("Net rating {team} {net:+.1f} vs {opp} {opp_net:+.1f} points per 100 possessions",
                   "Bilans {team} {net:+.1f} wobec {opp} {opp_net:+.1f} punktu na 100 posiadań"),
    'game.home_court': _w("Home court: {home} +{points:g} points", "Atut własnej hali: {home} +{points:g} pkt"),
    'game.absence_margin': _w("{team} without {name}: {swing:+.1f} point margin per game ({n} games missed)",
                              "{team} bez {name}: {swing:+.1f} pkt różnicy na mecz ({n} {n|mecz|mecze|meczów} "
                              "bez niego)"),
    'game.projected_total': _w("Projected {expected:.1f} points vs the line {line:g} ({gap:+.1f})",
                               "Prognoza {expected:.1f} pkt wobec linii {line:g} ({gap:+.1f})"),
    'game.pace_faster': _w("Pace {pace:.1f} possessions vs league {league:.1f}: a faster game than average",
                           "Tempo {pace:.1f} posiadań wobec ligi {league:.1f}: mecz szybszy niż przeciętnie"),
    'game.pace_slower': _w("Pace {pace:.1f} possessions vs league {league:.1f}: a slower game than average",
                           "Tempo {pace:.1f} posiadań wobec ligi {league:.1f}: mecz wolniejszy niż przeciętnie"),
    'game.attack': _w("{team} offense {off:.1f} vs {opp} defense {defense:.1f} (league {league:.1f}): {attack:+.1f} "
                      "per 100 possessions", "Atak {team} {off:.1f} wobec obrony {opp} {defense:.1f} (liga "
                                             "{league:.1f}): {attack:+.1f} na 100 posiadań"),
    'game.absence_points': _w("{team} without {name}: {change:+.1f} points ({n} games missed)",
                              "{team} bez {name}: {change:+.1f} pkt ({n} {n|mecz|mecze|meczów} bez niego)"),
    'gameflag.early': _w("Early season: the ratings are still mostly last season's, which don't know about summer "
                         "trades", "Początek sezonu: ratingi to wciąż głównie zeszły sezon, który nie zna letnich "
                                   "transferów"),
    'gameflag.no_lineup': _w("RotoWire doesn't list this game yet: absences aren't in the projection",
                             "RotoWire jeszcze nie podaje tego meczu: nieobecnych nie ma w prognozie"),
    'gameflag.big_edge': _w("Edge over 15 pp: more likely the model is missing something (a trade, rest) than the "
                            "market being that wrong", "Przewaga ponad 15 pp: bardziej prawdopodobne, że model "
                                                       "czegoś nie wie (transfer, odpoczynek), niż że rynek tak "
                                                       "bardzo się myli"),

    # Games page
    'games.title': _w("Games", "Mecze"),
    'games.purpose': _w("Superbet's bets on the games (winner, handicap, points totals) next to our team model: "
                        "attack and defense ratings, pace, home court and who RotoWire lists as out. The game model "
                        "isn't calibrated, so its edges are estimates for research, not bets.",
                        "Zakłady Superbetu na mecze (zwycięzca, handicap, sumy punktów) obok naszego modelu drużyn: "
                        "ratingi ataku i obrony, tempo, atut własnej hali i nieobecni wg RotoWire. Model meczów nie "
                        "jest skalibrowany, więc jego przewagi to szacunki do analizy, nie do gry."),
    'games.settings': _w("Model settings", "Ustawienia modelu"),
    'games.prior': _w("Prior weight (games)", "Waga zeszłego sezonu (mecze)"),
    'games.prior_help': _w("This season counts n / (n + this) against last season's ratings",
                           "Ten sezon liczy się jako n / (n + ta liczba) wobec ratingów z zeszłego sezonu"),
    'games.regress': _w("Pull last season toward the average", "Przyciągnij zeszły sezon do średniej"),
    'games.regress_help': _w("Rosters change over the summer; 0 = use last season's ratings as they were",
                             "Składy zmieniają się latem; 0 = użyj ratingów z zeszłego sezonu bez zmian"),
    'games.home_court': _w("Home court (points)", "Atut własnej hali (pkt)"),
    'games.home_court_help': _w("Points the home team gains from playing at home",
                                "Ile punktów gospodarz zyskuje, grając u siebie"),
    'games.shrink': _w("Absence shrink", "Ostrożność przy nieobecnych"),
    'games.shrink_help': _w("Each absence's effect is weighted by n / (n + this), n = games missed",
                            "Wpływ każdej nieobecności waży n / (n + ta liczba), n = opuszczone mecze"),
    'games.out_max': _w("Count as out", "Licz jako nieobecnego"),
    'games.out_max_value': _w("≤ {pct}% to play", "≤ {pct}% szans gry"),
    'games.out_max_help': _w("RotoWire players with at most this chance to play are treated as out",
                             "Zawodnicy z RotoWire z co najwyżej taką szansą gry są traktowani jako nieobecni"),
    'games.every_line': _w("Every line", "Wszystkie linie"),
    'games.every_line_help': _w("Otherwise only Superbet's main line of each bet type",
                                "Inaczej tylko główna linia Superbetu w każdym rodzaju zakładu"),
    'games.none': _w("**Superbet has no NBA games in the next 36 hours**, or none could be priced. Fetch the offers "
                     "again in the Data center.", "**Superbet nie ma meczów NBA w najbliższych 36 godzinach** albo "
                                                  "nie udało się ich wycenić. Pobierz oferty ponownie w Centrum "
                                                  "danych."),
    'games.ratings': _w("Ratings: {current} ({n_current} games) blended with {prior} ({n_prior} games). Superbet's "
                        "margin is about 2–3 pp per side, so small edges are noise.",
                        "Ratingi: {current} ({n_current} {n_current|mecz|mecze|meczów}) połączone z {prior} "
                        "({n_prior} {n_prior|mecz|mecze|meczów}). Marża Superbetu to ok. 2–3 pp na stronę, więc "
                        "małe przewagi to szum."),
    'games.pick_game': _w("Pick a game for its bets; showing the first one.",
                          "Wybierz mecz, żeby zobaczyć jego zakłady; pokazuję pierwszy."),
    'games.kpi.winner': _w("Expected winner", "Oczekiwany zwycięzca"),
    'games.kpi.winner_help': _w("Home margin {margin:+.1f}", "Przewaga gospodarza {margin:+.1f}"),
    'games.kpi.total': _w("Expected total", "Oczekiwana suma"),
    'games.kpi.points': _w("{team} points", "Punkty {team}"),
    'games.kpi.points_help': _w("Pace × (own attack rating + opponent's defense rating − league average) / 100, ± half "
                                "the home-court edge, + the effect of missing players",
                                "Tempo × (rating ataku + rating obrony rywala − średnia ligi) / 100, ± połowa atutu "
                                "hali, + wpływ nieobecnych"),
    'games.opening': _w("First lines (first snapshot): {home} handicap {spread:+g}, total {total:g}",
                        "Pierwsze linie (pierwszy zapis): handicap {home} {spread:+g}, suma {total:g}"),
    'games.tab.markets': _w("Bets", "Zakłady"), 'games.tab.teams': _w("Teams & absences", "Drużyny i nieobecni"),
    'games.best_shown': _w("The bet with the biggest edge is shown; pick a row for another.",
                           "Pokazany jest zakład z największą przewagą; wybierz wiersz, żeby zobaczyć inny."),
    'games.away': _w("Away", "Gość"), 'games.home': _w("Home", "Gospodarz"),
    'games.team_line': _w("**{side}: {team}** · attack {off:.1f}, defense {defense:.1f}, pace {pace:.1f}",
                          "**{side}: {team}** · atak {off:.1f}, obrona {defense:.1f}, tempo {pace:.1f}"),
    'games.not_listed': _w("📋 Not on RotoWire's page (yet).", "📋 (Jeszcze) nie ma na stronie RotoWire."),
    'games.lineup': _w("📋 {status} lineup: {players}", "📋 skład {status}: {players}"),
    'games.open_lineup': _w("Open {team} in Lineup lab", "Otwórz {team} w Laboratorium składów"),

    # Results page
    'results.title': _w("Results", "Wyniki"),
    'results.purpose': _w("Every line we saved, settled against the real results: were Superbet's lines off from the "
                          "players' averages, and did our picks win?",
                          "Każda zapisana linia rozliczona z prawdziwymi wynikami: czy linie Superbetu odbiegały od "
                          "średnich zawodników i czy nasze typy wygrywały?"),
    'results.tab.night': _w("🌙 Previous night", "🌙 Poprzedni wieczór"),
    'results.tab.saved': _w("All saved nights", "Wszystkie zapisane wieczory"),
    'results.update': _w("Update the stats in the Data center", "Zaktualizuj statystyki w Centrum danych"),
    'results.no_lines': _w("**No saved lines yet.** Fetch Superbet's lines before the games (Data center → Fetch & "
                           "save; every fetch is saved), then update the stats the next morning to settle them.",
                           "**Brak zapisanych linii.** Pobierz linie Superbetu przed meczami (Centrum danych → "
                           "Pobierz i zapisz; każde pobranie jest zapisywane), a następnego ranka zaktualizuj "
                           "statystyki, żeby je rozliczyć."),
    'results.dates': _w("Game dates", "Daty meczów"), 'results.types': _w("Stats", "Statystyki"),
    'results.types_help': _w("None picked = all", "Nic nie wybrane = wszystkie"),
    'results.min_games': _w("Min games before the line", "Min. meczów przed linią"),
    'results.min_games_help': _w("Leave out lines on players with fewer games before the game: their average says "
                                 "little", "Pomiń linie zawodników z mniejszą liczbą meczów przed meczem: ich "
                                           "średnia niewiele mówi"),
    'results.kpi.settled': _w("Settled lines", "Rozliczone linie"),
    'results.kpi.settled_note': _w("{pending} pending, {void} void, {unresolved} unresolved",
                                   "{pending} oczekuje, {void} nieważnych, {unresolved} nierozstrzygniętych"),
    'results.kpi.settled_help': _w("pending = the game isn't in our stats yet; void = the player didn't play; "
                                   "unresolved = can't be settled from our stats (player not identified, incomplete "
                                   "box score, or the game still missing while later ones are stored)",
                                   "oczekuje = meczu nie ma jeszcze w statystykach; nieważny = zawodnik nie zagrał; "
                                   "nierozstrzygnięty = nie da się rozliczyć z naszych danych (nieznany zawodnik, "
                                   "niepełne statystyki meczu albo brak meczu, choć późniejsze już są)"),
    'results.kpi.over': _w("Went over", "Powyżej linii"),
    'results.kpi.over_help': _w("How often the result went over the line. Far from 50% = the lines were set too low "
                                "or too high.", "Jak często wynik był powyżej linii. Daleko od 50% = linie były za "
                                                "niskie lub za wysokie."),
    'results.kpi.error': _w("Average result − line", "Średnio wynik − linia"),
    'results.kpi.error_help': _w("+ = players beat the lines on average", "+ = zawodnicy średnio przebijali linie"),
    'results.kpi.toward': _w("Toward the average: won", "W stronę średniej: wygrane"),
    'results.kpi.toward_help': _w("Betting the side the player's average before the game pointed to",
                                  "Granie strony, na którą wskazywała średnia zawodnika przed meczem"),
    'results.kpi.toward_roi': _w("Toward the average: profit per 100", "W stronę średniej: zysk na 100"),
    'results.kpi.toward_roi_help': _w("At the first odds of that side, the same stake on every line",
                                      "Po pierwszym kursie tej strony, równa stawka na każdą linię"),
    'results.tab.avg': _w("Lines vs averages", "Linie a średnie"),
    'results.tab.picks': _w("Our picks", "Nasze typy"),
    'results.tab.games': _w("Game bets", "Zakłady na mecze"),
    'results.tab.all': _w("All settled lines", "Wszystkie rozliczone linie"),
    'results.nothing': _w("Nothing settled in this selection yet: update the stats after the games (Data center).",
                          "W tym wyborze nic nie jest jeszcze rozliczone: zaktualizuj statystyki po meczach "
                          "(Centrum danych)."),
    'results.gap_chart': _w("Betting toward the average, by how far the line was from it",
                            "Granie w stronę średniej, wg odległości linii od niej"),
    'results.gap_hover': _w("%{x}: won %{y:.0f}%, profit per 100 %{customdata:+.1f}",
                            "%{x}: wygrane %{y:.0f}%, zysk na 100 %{customdata:+.1f}"),
    'results.gap_caption': _w("Each bar: lines grouped by how far the line was from the player's average before the "
                              "game, and how often the side toward the average won (number of lines in brackets). "
                              "Green = made money at the odds.",
                              "Każdy słupek: linie pogrupowane wg odległości od średniej zawodnika przed meczem i to, "
                              "jak często wygrywała strona w stronę średniej (liczba linii w nawiasie). Zielony = "
                              "zarabiało przy tych kursach."),
    'results.error_chart': _w("Result − line, per stat", "Wynik − linia, wg statystyki"),
    'results.error_caption': _w("Boxes above 0 = players beat Superbet's lines in that stat (Overs did well); the "
                                "dashed line in a box = its average.",
                                "Pudełka powyżej 0 = zawodnicy przebijali linie Superbetu w tej statystyce (Powyżej "
                                "wypadało dobrze); przerywana linia w pudełku = jego średnia."),
    'results.by_type': _w("**By stat**", "**Wg statystyki**"),
    'results.avg_caption': _w("The average before the game uses the Scope's seasons and game types and only games "
                              "before the line's game, so it's what you could have known when betting.",
                              "Średnia przed meczem używa sezonów i rodzajów meczów z Zakresu i tylko meczów sprzed "
                              "meczu z linią, więc to wiedza dostępna w chwili gry."),
    'results.no_picks': _w("No settled picks yet. Each fetch saves our pick with each line; older fetches have odds "
                           "but no pick, so they only count under Lines vs averages.",
                           "Brak rozliczonych typów. Każde pobranie zapisuje nasz typ przy każdej linii; starsze "
                           "pobrania mają kursy bez typu, więc liczą się tylko w Liniach a średnich."),
    'results.kpi.picks': _w("Picks settled", "Rozliczone typy"), 'results.kpi.hit': _w("Won", "Wygrane"),
    'results.kpi.profit': _w("Profit (1 unit each)", "Zysk (po 1 jednostce)"),
    'results.kpi.roi': _w("Profit per 100", "Zysk na 100"),
    'results.kpi.vs_last': _w("Odds vs last quote", "Kurs wobec ostatniego"),
    'results.kpi.vs_last_help': _w("Our odds vs the last odds before tip-off: getting better prices than the market's "
                                   "last is an early sign of a real edge",
                                   "Nasze kursy wobec ostatnich przed startem: lepsze ceny niż ostatnie rynkowe to "
                                   "wczesny znak prawdziwej przewagi"),
    'results.efficiency': _w("**Does a bigger edge win more?**", "**Czy większa przewaga częściej wygrywa?**"),
    'results.no_edge_yet': _w("No settled pick has had a positive edge yet.",
                              "Żaden rozliczony typ nie miał jeszcze dodatniej przewagi."),
    'results.curve': _w("Total profit, 1 unit per pick", "Łączny zysk, 1 jednostka na typ"),
    'results.curve_x': _w("picks", "typy"), 'results.curve_y': _w("units", "jednostki"),
    'results.calibration': _w("Our chance vs how often it won", "Nasza szansa a jak często wygrywało"),
    'results.calibration_ideal': _w("perfectly honest", "idealnie rzetelny"),
    'results.calibration_x': _w("our chance %", "nasza szansa %"), 'results.calibration_y': _w("won %", "wygrane %"),
    'results.calibration_caption': _w("Dots on the dotted line = our chances were honest: picks we gave 60% won about "
                                      "60% of the time. Dots below it = we were too confident.",
                                      "Kropki na linii przerywanej = nasze szanse były rzetelne: typy z szansą 60% "
                                      "wygrywały w ok. 60% przypadków. Kropki poniżej = byliśmy zbyt pewni."),
    'results.by_signal': _w("**By signal**", "**Wg sygnału**"), 'results.by_edge': _w("**By edge (pp)**",
                                                                                     "**Wg przewagi (pp)**"),
    'results.by_stat': _w("**By stat**", "**Wg statystyki**"), 'results.by_side': _w("**By side**",
                                                                                      "**Wg strony**"),
    'results.by_market': _w("**By bet type**", "**Wg rodzaju zakładu**"),
    'results.no_games': _w("No settled game bets yet (main lines only).",
                           "Brak rozliczonych zakładów na mecze (tylko główne linie)."),
    'results.kpi.games': _w("Settled", "Rozliczone"),
    'results.download': _w("Download CSV", "Pobierz CSV"),

    # the night view (night_view.py)
    'night.none': _w("No saved Superbet lines for a night that has started yet.",
                     "Brak zapisanych linii Superbetu z wieczoru, który już się zaczął."),
    'night.label': _w("{night} · {games} games · {lines} lines", "{night} · {games} {games|mecz|mecze|meczów} · {lines} "
                                                                 "{lines|linia|linie|linii}"),
    'night.pending_label': _w(" · results pending", " · wyniki w drodze"),
    'night.pick': _w("Nights (US dates)", "Wieczory (daty USA)"),
    'night.pick_help': _w("One night, or several to look at a period. Each line is judged by our last fetch before its "
                          "tip-off.", "Jeden wieczór albo kilka, żeby zobaczyć okres. Każda linia jest oceniana wg "
                                      "naszego ostatniego pobrania przed startem."),
    'night.pending': _w("{nights}: the games aren't in our stats yet, so those lines can't be settled. Update the "
                        "stats.", "{nights}: meczów nie ma jeszcze w statystykach, więc tych linii nie da się "
                                  "rozliczyć. Zaktualizuj statystyki."),
    'night.recomputed': _w("{n} lines were fetched before our picks and expectations were saved with each fetch (Oct "
                           "21): they are recomputed from the games before their night and the lineups and odds "
                           "saved before tip-off (✔ in the recomputed column).",
                           "{n} {n|linia została pobrana|linie zostały pobrane|linii zostało pobranych}, zanim "
                           "zapisywaliśmy typy i oczekiwania przy każdym pobraniu (21.10): przeliczono je z meczów "
                           "sprzed ich wieczoru oraz składów i kursów zapisanych przed startem (✔ w kolumnie "
                           "przeliczone)."),
    'night.kpi.settled': _w("Lines settled", "Rozliczone linie"),
    'night.kpi.settled_help': _w("Lines whose player played; void = didn't play; unresolved = can't be settled from "
                                 "our stats", "Linie, w których zawodnik zagrał; nieważny = nie zagrał; "
                                              "nierozstrzygnięty = nie da się rozliczyć"),
    'night.kpi.settled_note': _w("of {lines}, {void} void", "z {lines}, nieważnych: {void}"),
    'night.kpi.unresolved_note': _w(", {n} unresolved", ", nierozstrzygniętych: {n}"),
    'night.kpi.picks': _w("Our picks: won", "Nasze typy: wygrane"),
    'night.kpi.picks_help': _w("Every line's pick at our last fetch before tip-off",
                               "Typ każdej linii z ostatniego pobrania przed startem"),
    'night.kpi.roi': _w("profit per 100 {roi:+.1f}", "zysk na 100 {roi:+.1f}"),
    'night.kpi.edge': _w("🟢🟡 picks: won", "Typy 🟢🟡: wygrane"),
    'night.kpi.edge_help': _w("Picks with a positive edge", "Typy z dodatnią przewagą"),
    'night.kpi.n_picks': _w("{n} picks", "{n} {n|typ|typy|typów}"),
    'night.kpi.red': _w("🔴 picks: won", "Typy 🔴: wygrane"),
    'night.kpi.red_help': _w("Picks with a warning", "Typy z ostrzeżeniem"),
    'night.kpi.closer': _w("We beat the line", "Byliśmy bliżej niż linia"),
    'night.kpi.closer_help': _w("How often our expectation was closer to the result than Superbet's line",
                                "Jak często nasze oczekiwanie było bliżej wyniku niż linia Superbetu"),
    'night.kpi.closer_note': _w("typical miss {proj:.1f} vs line {line:.1f}", "typowy błąd {proj:.1f} wobec linii "
                                                                             "{line:.1f}"),
    'night.tab.props': _w("Player lines", "Linie zawodników"), 'night.tab.groups': _w("Where bets won",
                                                                                      "Gdzie zakłady wygrywały"),
    'night.tab.games': _w("Games", "Mecze"),
    'night.no_props': _w("No player lines were saved for these nights.",
                         "Dla tych wieczorów nie zapisano linii zawodników."),
    'night.stat': _w("Stat", "Statystyka"),
    'night.scatter': _w("{stat}: expected vs result (green = pick won)", "{stat}: oczekiwane a wynik (zielone = typ "
                                                                         "wygrał)"),
    'night.scatter_hover': _w("%{customdata[0]} (%{customdata[4]}): expected %{x:.1f}, got %{y}<br>line "
                              "%{customdata[1]}, pick %{customdata[2]} → %{customdata[3]}",
                              "%{customdata[0]} (%{customdata[4]}): oczekiwane %{x:.1f}, było %{y}<br>linia "
                              "%{customdata[1]}, typ %{customdata[2]} → %{customdata[3]}"),
    'night.x': _w("expected", "oczekiwane"), 'night.y': _w("result", "wynik"),
    'night.by_signal': _w("Our picks by signal", "Nasze typy wg sygnału"),
    'night.by_stat': _w("Our picks by stat", "Nasze typy wg statystyki"),
    'night.every_line': _w("**Every line**", "**Każda linia**"),
    'night.games': _w("Games", "Mecze"), 'night.all_games': _w("All games", "Wszystkie mecze"),
    'night.stats': _w("Stats", "Statystyki"), 'night.all': _w("All", "Wszystkie"),
    'night.result': _w("Result", "Rezultat"), 'night.signal': _w("Signal", "Sygnał"),
    'night.groups_caption': _w("Every settled line, grouped. For each group: how often betting Over and betting Under "
                               "won and paid at the lines' odds, and how our picks did. The groups where a bet was most "
                               "likely to win come first; the dashed line is break-even (about {be}%). One night is a "
                               "small sample: check the range and look at several nights before trusting a pattern.",
                               "Każda rozliczona linia, w grupach. Dla każdej grupy: jak często wygrywało i "
                               "zarabiało Powyżej i Poniżej oraz jak poszły nasze typy. Najpierw grupy, w których "
                               "zakład najczęściej wygrywał; przerywana linia to próg opłacalności (ok. {be}%). Jeden "
                               "wieczór to mała próba: sprawdź przedział i kilka wieczorów, zanim zaufasz "
                               "wzorcowi."),
    'night.group_by': _w("Group by", "Grupuj wg"),
    'night.group_by_help': _w("One axis (e.g. Stat) or several (e.g. Position + Stat)",
                              "Jedna oś (np. Statystyka) albo kilka (np. Pozycja + Statystyka)"),
    'night.min_lines': _w("Min lines", "Min. linii"),
    'night.min_lines_help': _w("Leave out groups with fewer settled lines", "Pomiń grupy z mniejszą liczbą linii"),
    'night.pick_axis': _w("Pick at least one axis to group by.", "Wybierz co najmniej jedną oś grupowania."),
    'night.no_group': _w("No group has that many lines; lower Min lines.",
                         "Żadna grupa nie ma tylu linii; zmniejsz Min. linii."),
    'night.group_text': _w("{side} {pct:.0f}% · {n} lines", "{side} {pct:.0f}% · {n} {n|linia|linie|linii}"),
    'night.group_hover': _w("%{y}: %{x:.1f}% won · profit per 100 %{customdata[0]:+.1f} · %{customdata[1]} lines",
                            "%{y}: %{x:.1f}% wygranych · zysk na 100 %{customdata[0]:+.1f} · %{customdata[1]} linii"),
    'night.groups_chart': _w("How often the better side won (blue = Over, orange = Under; whiskers = 95% range; dashed "
                             "= break-even)", "Jak często wygrywała lepsza strona (niebieski = Powyżej, pomarańczowy = "
                                              "Poniżej; wąsy = 95% przedział; przerywana = próg)"),
    'night.won_axis': _w("won %", "wygrane %"),
    'night.axis.bet_type': _w("Stat", "Statystyka"), 'night.axis.position': _w("Position", "Pozycja"),
    'night.axis.venue': _w("Home / away", "Dom / wyjazd"), 'night.axis.pick': _w("Our pick (Over / Under)",
                                                                                 "Nasz typ (Powyżej / Poniżej)"),
    'night.axis.signal': _w("Signal", "Sygnał"), 'night.axis.team': _w("Team", "Drużyna"),
    'night.axis.game': _w("Game", "Mecz"),
    'night.no_games': _w("No game odds were saved for these nights.", "Dla tych wieczorów nie zapisano kursów na "
                                                                      "mecze."),
    'night.kpi.called': _w("Winners called", "Trafieni zwycięzcy"),
    'night.kpi.called_value': _w("{n} of {total}", "{n} z {total}"),
    'night.kpi.called_help': _w("Our expected winner won", "Nasz oczekiwany zwycięzca wygrał"),
    'night.kpi.total': _w("Total points: average miss", "Suma punktów: średni błąd"),
    'night.kpi.total_help': _w("Average distance between the actual and our expected total",
                               "Średnia odległość między faktyczną a oczekiwaną sumą"),
    'night.kpi.best': _w("Biggest-edge bets won", "Wygrane zakłady z największą przewagą"),
    'night.kpi.best_help': _w("The game bet with our biggest edge, per game (an estimate: not calibrated)",
                              "Zakład z naszą największą przewagą w każdym meczu (szacunek: nieskalibrowany)"),
    'night.score_pending': _w("pending", "w drodze"),
    'night.games_recomputed': _w("Expected scores weren't saved with these fetches (they are from Oct 22 on), so "
                                 "they're recomputed as the dashboard would have made them: ratings from the games "
                                 "before that night and the RotoWire lineups saved before tip-off.",
                                 "Oczekiwanych wyników nie zapisywano przy tych pobraniach (są od 22.10), więc "
                                 "przeliczono je tak, jak zrobiłby to dashboard: ratingi z meczów sprzed tamtego "
                                 "wieczoru i składy RotoWire zapisane przed startem."),

    # How to read this (views/help.py)
    'help.title': _w("How to read this", "Jak to czytać"),
    'help.purpose': _w("What the numbers mean and how to use them to choose a bet, step by step. No betting "
                       "knowledge needed.", "Co znaczą liczby i jak użyć ich do wyboru zakładu, krok po kroku. Nie "
                                            "trzeba nic wiedzieć o zakładach."),
    'help.odds.title': _w("1. Odds are a price, and a chance", "1. Kurs to cena i zarazem szansa"),
    'help.odds.body': _w("Superbet shows **decimal odds**, e.g. **1.90**. A winning bet pays back stake × odds: 10 at "
                         "1.90 returns 19, so 9 profit. The odds also say how likely the bookmaker thinks the bet "
                         "is: **100 ÷ odds**. 1.90 → 52.6%. Lower odds = more likely, but pays less; higher odds = "
                         "less likely, but pays more.",
                         "Superbet pokazuje **kursy dziesiętne**, np. **1.90**. Wygrany zakład zwraca stawka × kurs: "
                         "10 zł po 1.90 to 19 zł, czyli 9 zł zysku. Kurs mówi też, jak prawdopodobny jest zakład "
                         "według bukmachera: **100 ÷ kurs**. 1.90 → 52.6%. Niższy kurs = bardziej prawdopodobne, "
                         "ale mniej płaci; wyższy kurs = mniej prawdopodobne, ale więcej płaci."),
    'help.margin.title': _w("2. The bookmaker's margin", "2. Marża bukmachera"),
    'help.margin.body': _w("Over and Under on the same line usually both pay about 1.90. 52.6% + 52.6% = 105%: more "
                           "than 100%. The extra ~5% is the bookmaker's cut. That's why simply guessing loses money "
                           "over time: to come out ahead you must be right **more often than the odds need**, not "
                           "just more than half the time.",
                           "Powyżej i Poniżej na tej samej linii zwykle płacą ok. 1.90. 52.6% + 52.6% = 105%: więcej "
                           "niż 100%. Nadwyżka ok. 5% to zarobek bukmachera. Dlatego zwykłe zgadywanie z czasem "
                           "przynosi stratę: żeby wyjść na plus, trzeba trafiać **częściej, niż wymaga kurs**, a nie "
                           "tylko w ponad połowie przypadków."),
    'help.chance.title': _w("3. Our chance", "3. Nasza szansa"),
    'help.chance.body': _w("For every line we estimate how often each side wins, from the player's games, tonight's "
                           "lineups (who's out) and the game. Then we correct it by how such estimates turned out on "
                           "thousands of past lines. Honest result: the correction keeps only about a tenth of our "
                           "own opinion, so **our chance is usually close to the bookmaker's**. The market already "
                           "knows most of what we know.",
                           "Dla każdej linii szacujemy, jak często wygrywa każda strona, na podstawie meczów "
                           "zawodnika, dzisiejszych składów (kto nie zagra) i meczu. Potem poprawiamy to o to, jak "
                           "takie szacunki sprawdziły się na tysiącach dawnych linii. Uczciwy wynik: poprawka "
                           "zostawia tylko ok. jedną dziesiątą naszej opinii, więc **nasza szansa jest zwykle "
                           "blisko szansy bukmachera**. Rynek wie już większość tego, co my."),
    'help.edge.title': _w("4. Edge: is the price worth it?", "4. Przewaga: czy cena się opłaca?"),
    'help.edge.body': _w("**Edge = our chance − the chance the odds need.** Example: odds 1.90 need 52.6%; if our "
                         "chance is 55%, the edge is **+2.4 pp** (percentage points). **Above 0**: the odds pay more "
                         "than the risk: over many such bets you'd expect to come out ahead. **Below 0**: the odds "
                         "pay too little: over time it loses, even when a single bet wins. A bigger edge is better, "
                         "but an edge is only an estimate: a few points can easily be noise.",
                         "**Przewaga = nasza szansa − szansa wymagana przez kurs.** Przykład: kurs 1.90 wymaga "
                         "52.6%; jeśli nasza szansa to 55%, przewaga wynosi **+2.4 pp** (punktu procentowego). "
                         "**Więcej niż 0**: kurs płaci więcej niż wynosi ryzyko: na wielu takich zakładach można "
                         "oczekiwać zysku. **Mniej niż 0**: kurs płaci za mało: z czasem przynosi stratę, nawet gdy "
                         "pojedynczy zakład wejdzie. Większa przewaga jest lepsza, ale to tylko szacunek: kilka "
                         "punktów łatwo może być szumem."),
    'help.signals.title': _w("5. Signals: how much to trust it", "5. Sygnały: na ile ufać"),
    'help.signals.body': _w("**🟢 proven**: the edge is big enough that picks like it have actually won money on 10+ "
                            "evenings the model never saw. There are none yet: no edge size has proven itself. "
                            "**🟡 positive edge**: worth it on paper, not yet proven. **🔴 warning**: pass, whatever "
                            "the numbers say. **Empty**: no edge, pass. Most lines have no signal: that's normal and "
                            "honest, not a bug.",
                            "**🟢 potwierdzone**: przewaga jest na tyle duża, że takie typy rzeczywiście zarabiały "
                            "przez 10+ wieczorów, których model nie widział. Na razie nie ma żadnego: żadna wielkość "
                            "przewagi się nie potwierdziła. **🟡 dodatnia przewaga**: opłaca się na papierze, jeszcze "
                            "niepotwierdzona. **🔴 ostrzeżenie**: odpuść, cokolwiek mówią liczby. **Puste**: brak "
                            "przewagi, odpuść. Większość linii nie ma sygnału: to normalne i uczciwe, a nie błąd."),
    'help.flags.title': _w("6. Warnings", "6. Ostrzeżenia"),
    'help.flags.body': _w("A warning (🔴, the 'warning' column) is a reason to pass on its own: fewer than 8 games "
                          "behind the numbers, only preseason games, the player may not play (RotoWire), his minutes "
                          "swing a lot, or the line moved 1.5+ against the pick (the market may know about an injury).",
                          "Ostrzeżenie (🔴, kolumna 'ostrzeżenie') to samodzielny powód, żeby odpuścić: mniej niż 8 "
                          "meczów za liczbami, tylko mecze przedsezonowe, zawodnik może nie zagrać (RotoWire), jego "
                          "minuty bardzo się wahają albo linia ruszyła o 1.5+ przeciw typowi (rynek może wiedzieć o "
                          "kontuzji)."),
    'help.verdict.title': _w("7. The verdict", "7. Werdykt"),
    'help.verdict.body': _w("Pick a row on the Props page to see the **verdict** and the reasons behind it: ✅ for, ❌ "
                            "against, ⚠️ reasons to pass. **Bet** = a proven edge (🟢) and more reasons for than "
                            "against. **Lean** = a positive edge, but not proven, or the reasons are even: treat it "
                            "with caution. **Pass** = don't bet: no edge, a warning, or more reasons against.",
                            "Wybierz wiersz na stronie Zakładów na zawodników, żeby zobaczyć **werdykt** i jego "
                            "powody: ✅ za, ❌ przeciw, ⚠️ powody, żeby odpuścić. **Graj** = potwierdzona przewaga "
                            "(🟢) i więcej powodów za niż przeciw. **Rozważ** = dodatnia przewaga, ale "
                            "niepotwierdzona, albo powody są równe: podchodź ostrożnie. **Odpuść** = nie graj: "
                            "brak przewagi, ostrzeżenie albo więcej powodów przeciw."),
    'help.player.title': _w("8. The player's numbers", "8. Liczby zawodnika"),
    'help.player.body': _w("**Expected tonight** is our estimate of the stat tonight: above the line points to Over, "
                           "below to Under. **Won, last 10 %** shows how often the side would have won lately; compare "
                           "it with **needed to win %**. 10 games is a small sample, so treat it as a hint.",
                           "**Oczekiwane dziś** to nasz szacunek statystyki na dziś: wyżej niż linia wskazuje na "
                           "Powyżej, niżej na Poniżej. **Trafione w ost. 10 %** pokazuje, jak często ta strona "
                           "ostatnio by wygrała; porównaj z **potrzebna skuteczność %**. 10 meczów to mała próba, "
                           "więc traktuj to jako wskazówkę."),
    'help.steps.title': _w("How to choose a prop, in 5 steps", "Jak wybrać zakład, w 5 krokach"),
    'help.steps.body': _w("1. On **Props**, set the signal filter to **🟢🟡 Positive edge**: only lines worth it on "
                          "paper stay.\n2. Prefer a bigger **edge (pp)** and an **edge, cautious** above 0.\n3. Skip any "
                          "line with a **warning**.\n4. Click the row: read the **verdict** and the reasons ✅ / ❌; "
                          "check **tonight's role** (is the player playing?).\n5. Bet small. An edge is a small "
                          "advantage over many bets, not a sure thing tonight; if nothing qualifies, don't bet.",
                          "1. W **Zakładach na zawodników** ustaw filtr sygnału na **🟢🟡 Dodatnia przewaga**: "
                          "zostaną tylko linie opłacalne na papierze.\n2. Wybieraj większą **przewagę (pp)** i "
                          "**przewagę ostrożnie** większą od 0.\n3. Pomiń każdą linię z **ostrzeżeniem**.\n4. "
                          "Kliknij wiersz: przeczytaj **werdykt** i powody ✅ / ❌; sprawdź **rolę dziś** (czy "
                          "zawodnik gra?).\n5. Graj małymi stawkami. Przewaga to mała korzyść na wielu zakładach, a "
                          "nie pewniak na dziś; jeśli nic się nie kwalifikuje, nie graj."),
    'help.glossary.title': _w("Every column, explained", "Każda kolumna wyjaśniona"),
    'help.glossary.caption': _w("The same explanations as the tooltips you see when you hover a column header.",
                                "Te same wyjaśnienia, które widać po najechaniu na nagłówek kolumny."),

    # Overview
    'overview.title': _w("Overview", "Przegląd"),
    'overview.purpose': _w("The games in the next 36 hours, who's missing, and the best-priced bets. Pick a bet to open "
                           "its full analysis.", "Mecze w najbliższych 36 godzinach, kto nie zagra i najlepiej "
                                                 "wycenione zakłady. Wybierz zakład, żeby otworzyć pełną analizę."),
    'overview.kpi.games': _w("Games", "Mecze"), 'overview.kpi.lines': _w("Player lines", "Linie zawodników"),
    'overview.kpi.lines_help': _w("Superbet's Over / Under lines on players in these games",
                                  "Linie Superbetu Powyżej / Poniżej na zawodników w tych meczach"),
    'overview.kpi.green': _w("🟢 Proven picks", "🟢 Potwierdzone typy"),
    'overview.kpi.green_help': _w("Picks whose edge is big enough that such picks have won money on unseen evenings",
                                  "Typy z przewagą na tyle dużą, że takie typy zarabiały w nieznane modelowi "
                                  "wieczory"),
    'overview.kpi.yellow': _w("🟡 Positive edge", "🟡 Dodatnia przewaga"),
    'overview.kpi.yellow_help': _w("The odds pay more than the risk on paper; not yet proven",
                                   "Kurs na papierze płaci więcej niż ryzyko; jeszcze nie potwierdzone"),
    'overview.kpi.lineups': _w("Lineups listed", "Podane składy"),
    'overview.kpi.lineups_value': _w("{n} {n|team|teams|teams}", "{n} {n|drużyna|drużyny|drużyn}"),
    'overview.kpi.lineups_help': _w("Teams whose expected or confirmed lineup RotoWire lists",
                                    "Drużyny, których przewidywany lub potwierdzony skład podaje RotoWire"),
    'overview.kpi.out': _w("Out or doubtful", "Nie zagrają lub niepewni"),
    'overview.games': _w("Games", "Mecze"),
    'overview.no_lineup': _w("no lineup yet", "jeszcze bez składu"),
    'overview.confirmed': _w("confirmed", "potwierdzony"), 'overview.expected': _w("expected", "przewidywany"),
    'overview.out': _w("out/doubtful: {names}", "nie zagrają/niepewni: {names}"),
    'overview.soon': _w("⏰ tip-off in {minutes} min", "⏰ start za {minutes} min"),
    'overview.at': _w("{away} at {home}", "{away} na wyjeździe u {home}"),
    'overview.ml': _w("ML", "zwycięzca"), 'overview.total': _w("total", "suma"),
    'overview.no_main': _w("no main lines", "brak głównych linii"),
    'overview.odds_help': _w("Superbet: odds on the winner (away / home), the home team's main handicap (− = "
                             "favourite) and the main line on total points",
                             "Superbet: kursy na zwycięzcę (gość / gospodarz), główny handicap gospodarza (− = "
                             "faworyt) i główna linia sumy punktów"),
    'overview.projected': _w("📊 Projected **{winner}**, total {total:.0f}", "📊 Prognoza: **{winner}**, suma "
                                                                              "{total:.0f}"),
    'overview.best_price': _w("Biggest edge (an estimate: the game model isn't calibrated): {bet} @ {odds:.2f} (edge "
                              "{edge:+.1f} pp)", "Największa przewaga (szacunek: model meczów nie jest "
                                                 "skalibrowany): {bet} @ {odds:.2f} (przewaga {edge:+.1f} pp)"),
    'overview.no_props': _w("Superbet has no player props on these games yet.",
                            "Superbet nie ma jeszcze zakładów na zawodników w tych meczach."),
    'overview.game_edges': _w("Biggest game edges", "Największe przewagi w meczach"),
    'overview.no_games': _w("No game could be priced.", "Nie udało się wycenić żadnego meczu."),
    'overview.game_edges_caption': _w("Main lines of the winner, handicap and totals markets. Estimates for research, "
                                      "not bets: the game model isn't calibrated yet. Pick one to open the game.",
                                      "Główne linie zakładów na zwycięzcę, handicap i sumy punktów. Szacunki do "
                                      "analizy, nie do gry: model meczów nie jest jeszcze skalibrowany. Wybierz "
                                      "jeden, żeby otworzyć mecz."),
    'calibration.missing': _w("No calibration (data/backtest/calibration.json): 'our chance %' is the raw model's "
                              "chance, which was overconfident on past lines. No 🟢 / 🟡 picks until `python -m "
                              "backtest.calibrate` has been run.",
                              "Brak kalibracji (data/backtest/calibration.json): 'nasza szansa %' to surowa szansa "
                              "modelu, która na dawnych liniach była zbyt pewna siebie. Brak typów 🟢 / 🟡, dopóki "
                              "nie zostanie uruchomione `python -m backtest.calibrate`."),
    'calibration.mismatch': _w("The calibration was fitted for another model version (now {version}). No 🟢 / 🟡 picks "
                               "until it's refitted: `python daily_snapshot.py --reprice`, then `python -m "
                               "backtest.calibrate`.",
                               "Kalibracja została dopasowana do innej wersji modelu (teraz {version}). Brak typów "
                               "🟢 / 🟡 do ponownego dopasowania: `python daily_snapshot.py --reprice`, potem "
                               "`python -m backtest.calibrate`."),
    'overview.best_props': _w("Best player lines", "Najlepsze linie zawodników"),
    'overview.best_props_caption': _w("Only lines with a positive edge (every other line is a pass): 🟢 first, then by "
                                      "edge. Pick one to open it on Props.",
                                      "Tylko linie z dodatnią przewagą (pozostałe to odpuść): najpierw 🟢, potem wg "
                                      "przewagi. Wybierz jedną, żeby otworzyć ją w Zakładach na zawodników."),
    'overview.no_edge': _w("No line has a positive edge right now: our numbers agree with Superbet's prices, so "
                           "there's nothing to bet. That's the usual case.",
                           "Żadna linia nie ma teraz dodatniej przewagi: nasze liczby zgadzają się z kursami "
                           "Superbetu, więc nie ma czego grać. To typowa sytuacja."),
}


_PLURAL = re.compile(r"\{(\w+)\|([^|}]*)\|([^|}]*)\|([^|}]*)\}")


def plural(n, one: str, few: str, many: str, lang: str) -> str:
    """The noun form for n: Polish 1 mecz, 2–4 mecze, 5+ (and 12–14) meczów; English one / many (few = many)."""
    n = abs(int(n))
    if n == 1:
        return one
    if lang == 'pl' and n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
        return few
    return many


def t(key: str, lang: str, **values) -> str:
    """TEXTS[key] in `lang`, filled with `values`; {n|one|few|many} is the noun form for the value n (plural).
    KeyError for a key or language that isn't there."""
    text = TEXTS[key][lang]
    text = _PLURAL.sub(lambda m: plural(values[m.group(1)], *m.group(2, 3, 4), lang), text)
    return text.format(**values) if values else text
