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
    'ev 100': Term(_w("expected return per 100", "oczekiwany zwrot na 100 zł"),
                   _w("What 100 staked on this bet brings back on average, minus the 100, if our chance is right: "
                      "our chance × odds − 100. It weighs the chance and the price together, so it's the way to rank "
                      "bets: the higher, the better the price.",
                      "Ile średnio zostaje ze 100 zł postawionych na ten zakład, jeśli nasza szansa jest trafna: "
                      "nasza szansa × kurs − 100. Łączy szansę i kurs, więc według niego najlepiej układać zakłady: "
                      "im wyżej, tym lepsza cena."),
                   _w("A better price: above 0 = a profit on average, just below 0 = loses little.",
                      "Lepsza cena: więcej niż 0 = średnio zysk, tuż poniżej 0 = traci niewiele."),
                   _w("Loses more over time. Betting at random loses about −5 (the bookmaker's margin).",
                      "Z czasem traci więcej. Losowe granie traci ok. −5 (marża bukmachera)."),
                   _w("55% at 1.90 → 0.55 × 1.90 × 100 − 100 = +4.5. 72.7% at 1.32 → −4.0: a likely win that still "
                      "loses money over time.",
                      "55% po 1.90 → 0.55 × 1.90 × 100 − 100 = +4.5. 72.7% po 1.32 → −4.0: częsta wygrana, która i "
                      "tak z czasem traci.")),
    'decision': Term(_w("decision", "decyzja"),
                     _w("The decision for this game's players (decisions.py), from the price, the model, how fresh "
                        "the odds and lineups are and whether the model is admitted; the reasons don't vote. "
                        "Bet = one offer's edge clears a threshold that was checked on nights not used to choose "
                        "it (there's no such threshold yet, so no offer gets it). Don't bet = current evaluation, no offer qualifies. Wait = odds, lineup "
                        "or a tie missing. Unavailable = the model isn't admitted.",
                        "Decyzja dla zawodników tego meczu (decisions.py), z ceny, modelu, aktualności kursów i "
                        "składów oraz dopuszczenia modelu; powody nie głosują. Obstaw = przewaga jednej oferty "
                        "przekracza próg sprawdzony na nocach, których nie użyto do jego wyboru (takiego progu jeszcze "
                        "nie ma, więc żadna oferta tego nie dostaje). Nie obstawiaj = ocena aktualna, żadna oferta się nie kwalifikuje. Czekaj = brak "
                        "kursu, składu albo remis. Niedostępne = model nie jest dopuszczony.")),
    'side': Term(_w("evaluated side", "oceniana strona"),
                 _w("Over or Under, whichever has the higher expected return after Superbet's 12% stake tax: the "
                    "side the decision looks at. Not a pick: see 'decision'.",
                    "Powyżej lub Poniżej, zależnie od tego, gdzie oczekiwany zwrot po 12% podatku od stawki jest "
                    "wyższy: strona, na którą patrzy decyzja. To nie typ: zob. 'decyzja'.")),
    'side odds': Term(_w("odds", "kurs"),
                      _w("Superbet's decimal odds for the evaluated side, before the stake tax.",
                         "Kurs dziesiętny Superbetu na ocenianą stronę, przed podatkiem od stawki."),
                      _w("Pays more if it wins, but the bookmaker thinks it's less likely.",
                         "Więcej wypłaca przy wygranej, ale bukmacher uważa ją za mniej prawdopodobną."),
                      _w("Pays less, the bookmaker thinks it's more likely.",
                         "Mniej wypłaca, bukmacher uważa ją za bardziej prawdopodobną."),
                      _w("10 at 1.90: 12% tax leaves 8.80 in play, a win pays 8.80 × 1.90 = 16.72.",
                         "10 zł po 1.90: po 12% podatku w grze zostaje 8.80 zł, wygrana to 8.80 × 1.90 = 16.72 zł.")),
    'p win %': Term(_w("our chance to win %", "nasza szansa wygranej %"),
                    _w("How often we expect the evaluated side to win (a push, on a whole-number line, is neither), "
                       "corrected by how such chances turned out on past lines: close to the bookmaker's.",
                       "Jak często spodziewamy się wygranej ocenianej strony (zwrot na linii całkowitej to ani "
                       "wygrana, ani przegrana), poprawione o to, jak takie szanse sprawdzały się na dawnych liniach: "
                       "blisko szansy bukmachera."),
                    _w("More likely to win; only above 'needed to win, after tax' is it worth it.",
                       "Większa szansa; opłaca się tylko powyżej 'potrzebna skuteczność po podatku'."),
                    _w("Less likely to win.", "Mniejsza szansa wygranej.")),
    'p push %': Term(_w("push chance %", "szansa zwrotu %"),
                     _w("On a whole-number line, the chance the result lands on the line: the stake comes back.",
                        "Na linii całkowitej szansa, że wynik wypadnie na linii: stawka wraca.")),
    'break-even net %': Term(_w("needed to win, after tax %", "potrzebna skuteczność po podatku %"),
                             _w("How often the bet must win to break even after Superbet keeps 12% of the stake: "
                                "100 ÷ (0.88 × odds).",
                                "Jak często zakład musi wygrywać, żeby wyjść na zero, gdy Superbet zatrzymuje 12% "
                                "stawki: 100 ÷ (0.88 × kurs)."),
                             _w("A higher bar: low odds, or a lot taken by tax and margin.",
                                "Wyżej poprzeczka: niski kurs albo dużo zabiera podatek i marża."),
                             _w("A lower bar: higher odds.", "Niższa poprzeczka: wyższy kurs."),
                             _w("Odds 1.84 need 1 ÷ (0.88 × 1.84) = 61.8% (54.3% without the tax).",
                                "Kurs 1.84 wymaga 1 ÷ (0.88 × 1.84) = 61.8% (bez podatku 54.3%).")),
    'edge net pp': Term(_w("edge after tax (pp)", "przewaga po podatku (pp)"),
                        _w("Our chance to win minus the chance needed after the 12% stake tax, in percentage points.",
                           "Nasza szansa wygranej minus szansa potrzebna po 12% podatku od stawki, w punktach "
                           "procentowych."),
                        _w("Above 0: the price pays more than the risk, after the tax.",
                           "Więcej niż 0: cena płaci więcej niż ryzyko, po podatku."),
                        _w("Below 0: the bet loses on average.", "Mniej niż 0: zakład średnio traci."),
                        _w("Our chance 55%, odds 1.90 need 59.8% → −4.8 pp.",
                           "Nasza szansa 55%, kurs 1.90 wymaga 59.8% → −4.8 pp.")),
    'ev net 100': Term(_w("expected return per 100, after tax", "oczekiwany zwrot na 100 zł po podatku"),
                       _w("What 100 staked brings back on average, minus the 100, if our chance is right, after "
                          "Superbet keeps 12% of the stake: 100 × (chance × 0.88 × odds + push − 1).",
                          "Ile średnio zostaje ze 100 zł stawki, minus 100, jeśli nasza szansa jest trafna, gdy "
                          "Superbet zatrzymuje 12% stawki: 100 × (szansa × 0.88 × kurs + zwrot − 1)."),
                       _w("Loses less (above 0 would be a profit on average).",
                          "Traci mniej (powyżej 0 byłby średnio zysk)."),
                       _w("Loses more on average.", "Średnio traci więcej."),
                       _w("55% at 1.90 → 100 × (0.55 × 0.88 × 1.90 − 1) = −8.0.",
                          "55% po 1.90 → 100 × (0.55 × 0.88 × 1.90 − 1) = −8.0.")),
    'stars': Term(_w("rating", "ocena"),
                  _w("The line's place among tonight's lines by expected return after the tax: 4★ the best 5% "
                     "(one per game), 3★ up to 20%, 2★ up to 50%, 1★ the rest; 0★ a warning or a player who may "
                     "not play; – no rating (the model isn't admitted). 4★ = the best of tonight, not: worth "
                     "betting; these lines still lose on average after the tax. 5★ only for a 'Bet' offer: an "
                     "edge confirmed on nights not used to choose its threshold. Each level's record: Results → "
                     "Ratings.",
                     "Miejsce linii wśród dzisiejszych linii według oczekiwanego zwrotu po podatku: 4★ najlepsze "
                     "5% (jedna na mecz), 3★ do 20%, 2★ do 50%, 1★ reszta; 0★ ostrzeżenie albo gracz, który może "
                     "nie zagrać; – brak oceny (model niedopuszczony). 4★ = najlepsze dziś, nie: opłacalne; te "
                     "linie po podatku dalej średnio tracą. 5★ tylko dla oferty 'Obstaw': przewaga potwierdzona na "
                     "nocach, których nie użyto do wyboru progu. Wyniki każdego poziomu: Wyniki → Oceny.")),
    'CLV %': Term(_w("CLV %", "CLV %"),
                  _w("Average expected return of the bets at the closing price (the margin-free odds 5–10 minutes "
                     "before tip-off): above 0 = the bets beat the market's final price, the usual sign of a real "
                     "edge. Only lines with a valid close (the scheduled fetches) count.",
                     "Średni oczekiwany zwrot zakładów według kursu zamknięcia (kurs bez marży 5–10 minut przed "
                     "startem): powyżej 0 = zakłady pobiły ostateczną cenę rynku, zwykły znak prawdziwej przewagi. "
                     "Liczą się tylko linie z ważnym zamknięciem (pobieranie według harmonogramu)."),
                  _w("The bets got better prices than the close.", "Zakłady miały lepsze kursy niż zamknięcie."),
                  _w("The market moved against the bets.", "Rynek ruszył przeciw zakładom.")),
    'CLV bets': Term(_w("bets with a close", "zakłady z zamknięciem"),
                     _w("Bets whose closing price is known (the game was read 10 minutes or less before tip-off).",
                        "Zakłady, których kurs zamknięcia jest znany (mecz odczytany 10 minut lub mniej przed "
                        "startem).")),
    'side market %': Term(_w("bookmaker's chance %", "szansa wg bukmachera %"),
                          _w("The chance Superbet's odds give the evaluated side, with the margin taken out.",
                             "Szansa, jaką kursy Superbetu dają ocenianej stronie, po odjęciu marży.")),
    'above price pp': Term(_w("above the price (pp)", "ponad kurs (pp)"),
                           _w("Our chance to win minus the bookmaker's margin-free chance: how much the model "
                              "disagrees with the price. Before margin and tax, so it's no edge on its own.",
                              "Nasza szansa wygranej minus szansa bukmachera bez marży: na ile model nie zgadza się "
                              "z kursem. Przed marżą i podatkiem, więc sama nie jest przewagą."),
                           _w("The model likes the side more than the price does.",
                              "Model ocenia stronę lepiej niż kurs."),
                           _w("The model agrees with the price.", "Model zgadza się z kursem.")),
    'wait': Term(_w("note", "uwaga"),
                 _w("Why the game's decision is 'Wait' (old odds, no lineup): check before you bet.",
                    "Dlaczego decyzja meczu to 'Czekaj' (stare kursy, brak składu): sprawdź przed zakładem.")),
    'odds at': Term(_w("odds from", "kurs z"), _w("When Superbet's odds were fetched (Polish time).",
                                                 "Kiedy pobrano kursy Superbetu (czas polski).")),
    'lineup at': Term(_w("lineup from", "skład z"), _w("When RotoWire's lineups were fetched (Polish time).",
                                                     "Kiedy pobrano składy z RotoWire (czas polski).")),
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
                    _w("More likely to win. Compare it with 'needed to win %': only above it is the bet worth it. A "
                       "high chance usually comes with low odds, so on its own it doesn't make a bet better: rank by "
                       "'expected return per 100'.",
                       "Większa szansa wygranej. Porównaj z 'potrzebna skuteczność %': opłaca się tylko powyżej niej. "
                       "Wysoka szansa zwykle idzie z niskim kursem, więc sama nie czyni zakładu lepszym: układaj wg "
                       "'oczekiwany zwrot na 100 zł'."),
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
    'edge low': Term(_w("edge at the hit rate's low end (pp)", "przewaga przy dolnym końcu hit rate (pp)"),
                     _w("The edge (plain odds) if the player's hit rate so far was partly luck: the low end of its "
                        "sampling noise. It isn't a confidence range of the model: it leaves out the projection's "
                        "and the model's own errors, and it doesn't decide anything.",
                        "Przewaga (kurs bez podatku), gdyby dotychczasowy hit rate zawodnika był częściowo "
                        "szczęściem: dolny koniec jego szumu losowego. To nie jest przedział pewności modelu: "
                        "pomija błędy projekcji i samego modelu, i niczego nie rozstrzyga."),
                     _w("Above 0: the edge holds even if the hit rate was partly luck.",
                        "Więcej niż 0: przewaga trzyma się, nawet jeśli hit rate był częściowo szczęściem."),
                     _w("Below 0: the hit rate alone may be luck.", "Mniej niż 0: sam hit rate może być przypadkiem.")),
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
    'ROI %': Term(_w("return per 100, plain odds %", "zwrot na 100, kurs bez podatku %"),
                  _w("What 100 staked on each of these would have returned, minus the 100, at the plain odds (no "
                     "stake tax). It measures how the model's evaluations held up; it isn't anyone's own bets.",
                     "Ile wróciłoby ze 100 zł postawionych na każdy z nich, minus 100, po kursie bez podatku. "
                     "Mierzy, jak sprawdziły się oceny modelu; to nie są niczyje własne zakłady."),
                  _w("Above 0: these evaluations would have paid before the tax.",
                     "Więcej niż 0: te oceny opłaciłyby się przed podatkiem."),
                  _w("Below 0: they would have lost. Random betting loses about −5 here (the margin).",
                     "Mniej niż 0: traciłyby. Losowe granie traci tu ok. −5 (marża).")),
    'nights': Term(_w("nights", "wieczory"), _w("How many settled nights the bets come from. Lines of one night share "
                                               "games and news, so nights count more than bets.",
                                               "Z ilu rozliczonych wieczorów pochodzą zakłady. Linie jednego wieczoru "
                                               "dzielą mecze i wiadomości, więc wieczory liczą się bardziej niż "
                                               "zakłady.")),
    'price said %': Term(_w("price said %", "kurs mówił %"),
                         _w("How often the same sides should have won by Superbet's margin-free price.",
                            "Jak często te same strony powinny wygrywać według kursu Superbetu bez marży.")),
    'won − price pp': Term(_w("won − price (pp)", "wygrane − kurs (pp)"),
                           _w("How much more often the bets won than the margin-free price said. 0 = the ranking knew "
                              "nothing the price didn't; it takes several points above 0 to beat margin and tax.",
                              "O ile częściej zakłady wygrywały, niż mówił kurs bez marży. 0 = ranking nie wiedział "
                              "nic ponad kurs; żeby pobić marżę i podatek, trzeba kilku punktów ponad 0."),
                           _w("Won more often than the price said.", "Wygrywały częściej, niż mówił kurs."),
                           _w("Won less often than the price said.", "Wygrywały rzadziej, niż mówił kurs.")),
    'legs': Term(_w("legs", "zdarzenia"), _w("The coupon's bets, with how each one ended.",
                                             "Zakłady na kuponie i jak skończył się każdy z nich.")),
    'profit': Term(_w("return per 1", "wynik na 1 zł"), _w("What a unit staked would have returned, minus the unit, "
                                                           "at the plain odds.",
                                                           "Ile zwróciłaby jednostka stawki, minus ta jednostka, "
                                                           "przy samym kursie.")),
    'profit std': Term(_w("return per 1, after tax", "wynik na 1 zł po podatku"),
                       _w("The same after Superbet's 12% tax, taken once from the coupon's stake.",
                          "To samo po 12% podatku Superbetu, pobieranym raz od stawki kuponu.")),
    'cumulative std': Term(_w("running total after tax", "suma narastająco po podatku"),
                           _w("The return after tax added up night by night, 1 unit a coupon.",
                              "Wynik po podatku sumowany wieczór po wieczorze, 1 jednostka na kupon.")),
    'ROI % std': Term(_w("return per 100, after tax %", "zwrot na 100, po podatku %"),
                      _w("The same after Superbet's 12% stake tax: what Superbet would actually have paid back.",
                         "To samo po 12% podatku od stawki: ile faktycznie oddałby Superbet."),
                      _w("Above 0: they would have paid even after the tax.",
                         "Więcej niż 0: opłaciłyby się nawet po podatku."),
                      _w("Below 0: they would have lost. Random betting loses about −17 here.",
                         "Mniej niż 0: traciłyby. Losowe granie traci tu ok. −17.")),
    'break-even % std': Term(_w("needed to win, after tax %", "potrzebna skuteczność po podatku %"),
                             _w("The average win rate these odds need after the 12% stake tax: 100 ÷ (0.88 × odds).",
                                "Średnia skuteczność wymagana przez te kursy po 12% podatku: 100 ÷ (0.88 × kurs).")),
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
    'over ROI %': Term(_w("Over: return per 100, plain odds %", "Powyżej: zwrot na 100, kurs bez podatku %"),
                  _w("What 100 staked on each would have returned, minus the 100, at the plain odds.",
                     "Ile wróciłoby ze 100 zł na każdy, minus 100, po kursie bez podatku."),
                  _w("Would have paid.", "Opłacałoby się."), _w("Would have lost.", "Traciłoby.")),
    'over ROI % std': Term(_w("Over: return per 100, after tax %", "Powyżej: zwrot na 100, po podatku %"),
                      _w("The same after Superbet's 12% stake tax.", "To samo po 12% podatku od stawki."),
                      _w("Would have paid even after the tax.", "Opłacałoby się nawet po podatku."),
                      _w("Would have lost.", "Traciłoby.")),
    'under ROI %': Term(_w("Under: return per 100, plain odds %", "Poniżej: zwrot na 100, kurs bez podatku %"),
                  _w("What 100 staked on each would have returned, minus the 100, at the plain odds.",
                     "Ile wróciłoby ze 100 zł na każdy, minus 100, po kursie bez podatku."),
                  _w("Would have paid.", "Opłacałoby się."), _w("Would have lost.", "Traciłoby.")),
    'under ROI % std': Term(_w("Under: return per 100, after tax %", "Poniżej: zwrot na 100, po podatku %"),
                      _w("The same after Superbet's 12% stake tax.", "To samo po 12% podatku od stawki."),
                      _w("Would have paid even after the tax.", "Opłacałoby się nawet po podatku."),
                      _w("Would have lost.", "Traciłoby.")),
    'side to bet': Term(_w("better side", "lepsza strona"),
                        _w("The side (Over / Under) that won more often in this group.",
                           "Strona (Powyżej / Poniżej), która w tej grupie wygrywała częściej.")),
    'best side %': Term(_w("better side won %", "lepsza strona wygrała %"),
                        _w("How often the better side won in this group.", "Jak często lepsza strona wygrywała w tej "
                                                                           "grupie."),
                        _w("A clearer pattern; check its low end is above break-even.",
                           "Wyraźniejszy wzorzec; sprawdź, czy dolna granica jest powyżej progu."),
                        _w("Close to 50%: no pattern.", "Blisko 50%: brak wzorca.")),
    'best side ROI %': Term(_w("better side: return per 100, plain odds %", "lepsza strona: zwrot na 100, kurs bez podatku %"),
                  _w("What 100 staked on each would have returned, minus the 100, at the plain odds.",
                     "Ile wróciłoby ze 100 zł na każdy, minus 100, po kursie bez podatku."),
                  _w("Would have paid.", "Opłacałoby się."), _w("Would have lost.", "Traciłoby.")),
    'best side ROI % std': Term(_w("better side: return per 100, after tax %", "lepsza strona: zwrot na 100, po podatku %"),
                      _w("The same after Superbet's 12% stake tax.", "To samo po 12% podatku od stawki."),
                      _w("Would have paid even after the tax.", "Opłacałoby się nawet po podatku."),
                      _w("Would have lost.", "Traciłoby.")),
    'our picks': Term(_w("our picks", "nasze typy"), _w("How many of our picks the group has.",
                                                        "Ile naszych typów jest w grupie.")),
    'our hit %': Term(_w("our picks won %", "nasze typy wygrane %"), _w("How often our picks won.",
                                                                        "Jak często nasze typy wygrywały."),
                      _w("Our picks did better.", "Nasze typy radziły sobie lepiej."),
                      _w("Our picks did worse.", "Nasze typy radziły sobie gorzej.")),
    'our ROI %': Term(_w("model's picks: return per 100, plain odds %", "typy modelu: zwrot na 100, kurs bez podatku %"),
                  _w("What 100 staked on each would have returned, minus the 100, at the plain odds.",
                     "Ile wróciłoby ze 100 zł na każdy, minus 100, po kursie bez podatku."),
                  _w("Would have paid.", "Opłacałoby się."), _w("Would have lost.", "Traciłoby.")),
    'our ROI % std': Term(_w("model's picks: return per 100, after tax %", "typy modelu: zwrot na 100, po podatku %"),
                      _w("The same after Superbet's 12% stake tax.", "To samo po 12% podatku od stawki."),
                      _w("Would have paid even after the tax.", "Opłacałoby się nawet po podatku."),
                      _w("Would have lost.", "Traciłoby.")),
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

    # --- research pages: a player's games, a team, a lineup ---
    'split': Term(_w("split", "podział"), _w("How the games are divided.", "Jak podzielono mecze.")),
    'value': Term(_w("group", "grupa"), _w("The group within the split.", "Grupa w ramach podziału.")),
    'median': Term(_w("median", "mediana"), _w("The middle result: half the games were above it, half below.",
                                               "Środkowy wynik: połowa meczów była wyżej, połowa niżej.")),
    'research:percentile': Term(_w("percentile", "percentyl"),
                                _w("The share of games at or below the value: 30th = 30% of games were lower.",
                                   "Odsetek meczów z wynikiem nie wyższym: 30. = 30% meczów było niżej.")),
    'Date': Term(_w("date", "data"), _w("Game date (US time).", "Data meczu (czas USA).")),
    'OPP': Term(_w("opponent", "rywal"), _w("The opposing team.", "Drużyna przeciwna.")),
    'type': Term(_w("home/away", "dom/wyjazd"), _w("Home or away game.", "Mecz u siebie czy na wyjeździe.")),
    'Result': Term(_w("result", "wynik"), _w("Win (W) or loss (L) and the final score, from the player's team's "
                                             "side.", "Wygrana (W) lub porażka (L) i wynik, z perspektywy drużyny "
                                                      "zawodnika.")),
    'season_type': Term(_w("game type", "rodzaj meczu"), _w("pre = preseason, regular, playin = play-in, post = "
                                                            "playoffs.", "pre = przedsezon, regular = sezon "
                                                                         "zasadniczy, playin = baraże, post = play-off.")),
    'starter': Term(_w("started", "w piątce"), _w("✔ = started the game.", "✔ = zaczął mecz w pierwszej piątce.")),
    'rest_days': Term(_w("rest days", "dni przerwy"), _w("Days since the player's previous game (1 = the second of two "
                                                         "days in a row).", "Dni od poprzedniego meczu zawodnika (1 = "
                                                                            "drugi z dwóch meczów dzień po dniu).")),
    'location': Term(_w("home/away", "dom/wyjazd"), _w("Home or away games.", "Mecze u siebie czy na wyjeździe.")),
    'wins': Term(_w("wins", "wygrane"), _w("Games won.", "Wygrane mecze.")),
    'pts': Term(_w("points", "punkty"), _w("Points scored per game.", "Zdobyte punkty na mecz."),
                _w("A stronger attack.", "Mocniejszy atak."), _w("A weaker attack.", "Słabszy atak.")),
    'opp_pts': Term(_w("points allowed", "punkty stracone"), _w("Points allowed per game.", "Stracone punkty na mecz."),
                    _w("A weaker defense.", "Słabsza obrona."), _w("A stronger defense.", "Mocniejsza obrona.")),
    'margin': Term(_w("margin", "różnica"), _w("Average points scored minus allowed.",
                                               "Średnio punkty zdobyte minus stracone."),
                   _w("Wins by more.", "Wygrywa wyżej."), _w("Loses by more.", "Przegrywa wyżej.")),
    'allowed': Term(_w("allowed", "pozwala"), _w("Per game, by all opposing players at the position together.",
                                                 "Na mecz, wszystkim rywalom na tej pozycji razem."),
                    _w("A weak defense there: good for Overs against them.", "Słaba obrona na tej pozycji: dobrze "
                                                                              "dla Powyżej przeciw nim."),
                    _w("A strong defense there: good for Unders.", "Mocna obrona: dobrze dla Poniżej.")),
    'league avg': Term(_w("league avg", "średnia ligi"), _w("The average NBA defense.", "Przeciętna obrona NBA.")),
    'vs avg %': Term(_w("vs average %", "wobec średniej %"), _w("How much more (+) or less (−) than the average "
                                                                "defense allows.", "O ile więcej (+) lub mniej (−) "
                                                                                   "niż przeciętna obrona."),
                     _w("Gives up more: good for Overs against them.", "Pozwala więcej: dobrze dla Powyżej przeciw "
                                                                       "nim."),
                     _w("Gives up less: good for Unders.", "Pozwala mniej: dobrze dla Poniżej.")),
    'rank': Term(_w("rank", "miejsce"), _w("1 = allows the most in the league.", "1 = pozwala najwięcej w lidze.")),
    'starts': Term(_w("starts", "w piątce"), _w("Games started.", "Mecze w pierwszej piątce.")),
    'missed': Term(_w("missed", "opuścił"), _w("Team games without the player (including games before he joined).",
                                               "Mecze drużyny bez zawodnika (także sprzed jego przyjścia).")),
    'mpg': Term(_w("minutes per game", "minuty na mecz"), _w("Average minutes played.", "Średnio rozegrane minuty."),
                _w("A bigger role.", "Większa rola."), _w("A smaller role.", "Mniejsza rola.")),
    'last_game': Term(_w("last game", "ostatni mecz"), _w("The most recent game.", "Najnowszy mecz.")),
    'minutes': Term(_w("minutes", "minuty"), _w("Average minutes.", "Średnie minuty.")),
    'shots': Term(_w("shots", "rzuty"), _w("Average field-goal attempts.", "Średnio oddane rzuty z gry.")),
    'Out': Term(_w("out", "nie gra"), _w("Tick to mark the player out tonight and see how everyone else's estimate "
                                         "shifts.", "Zaznacz, żeby oznaczyć zawodnika jako nieobecnego i zobaczyć, "
                                                    "jak zmienia się szacunek pozostałych.")),
    'role': Term(_w("role", "rola"), _w("Starter, bench or out in this lineup.", "Pierwsza piątka, rezerwa lub "
                                                                                 "nieobecny w tym składzie.")),
    'usual': Term(_w("usual", "zwykle"), _w("The player's average of this stat for this team.",
                                            "Średnia zawodnika w tej statystyce w tej drużynie.")),
    'estimate': Term(_w("estimate", "szacunek"),
                     _w("usual + each out player's change, shrunk when it rests on few games.",
                        "zwykle + zmiana od każdego nieobecnego, osłabiona, gdy opiera się na małej liczbie meczów."),
                     _w("He should get more in this lineup.", "W tym składzie powinien zdobyć więcej."),
                     _w("He should get less.", "Powinien zdobyć mniej.")),
    'change': Term(_w("change", "zmiana"), _w("estimate − usual.", "szacunek − zwykle."),
                   _w("More than usual.", "Więcej niż zwykle."), _w("Less than usual.", "Mniej niż zwykle.")),
    'confidence': Term(_w("confidence", "pewność"), _w("How many games the estimate rests on: high = 10+, medium = 4–9, "
                                                       "low = fewer.", "Na ilu meczach opiera się szacunek: wysoka = "
                                                                       "10+, średnia = 4–9, niska = mniej.")),
    'exact match': Term(_w("exact match", "dokładne dopasowanie"),
                        _w("The average in team games where all five chosen starters played and everyone marked out "
                           "missed: the closest real match, but often only a few games.",
                           "Średnia z meczów, w których grała cała wybrana piątka, a wszyscy oznaczeni jako "
                           "nieobecni nie grali: najbliższa prawdziwa sytuacja, ale często tylko kilka meczów.")),
    'exact games': Term(_w("exact games", "mecze dokładne"), _w("Number of exact-match games.",
                                                                "Liczba meczów z dokładnym dopasowaniem."),
                        _w("A more reliable exact match.", "Bardziej wiarygodne dopasowanie."),
                        _w("A shaky exact match.", "Niepewne dopasowanie.")),
    'usual MIN': Term(_w("usual minutes", "zwykłe minuty"), _w("Usual minutes per game.", "Zwykłe minuty na mecz.")),
    'exact MIN': Term(_w("exact minutes", "minuty dokładne"), _w("Minutes in the exact-match games.",
                                                                 "Minuty w meczach z dokładnym dopasowaniem.")),
    'lineup:signal': Term(_w("signal", "sygnał"), _w("🟢 the estimate is at least 1 above usual, 🔴 at least 1 below.",
                                                     "🟢 szacunek jest o co najmniej 1 wyżej niż zwykle, 🔴 o co "
                                                     "najmniej 1 niżej.")),
    'lineup:games': Term(_w("games", "mecze"), _w("Games the player played for this team.",
                                                  "Mecze zawodnika w tej drużynie.")),
    'lineup:name': Term(_w("player", "zawodnik"), _w("The player.", "Zawodnik.")),
    'team:position': Term(_w("position", "pozycja"), _w("Guards, forwards or centers.",
                                                        "Obrońcy, skrzydłowi lub środkowi.")),
    'team:games': Term(_w("games", "mecze"), _w("Games in the scope.", "Mecze w zakresie.")),
    'team:name': Term(_w("player", "zawodnik"), _w("The player.", "Zawodnik.")),
    'team:wins': Term(_w("wins", "wygrane"), _w("Games won.", "Wygrane mecze.")),

    # --- the Data center ---
    'season': Term(_w("season", "sezon"), _w("The season (named by its first year).", "Sezon (nazwany pierwszym "
                                                                                     "rokiem).")),
    'data:games': Term(_w("games", "mecze"), _w("Games stored.", "Zapisane mecze.")),
    'last game': Term(_w("last game", "ostatni mecz"), _w("Date of the newest stored game.",
                                                          "Data najnowszego zapisanego meczu.")),
    'checked through': Term(_w("complete through", "kompletne do"),
                            _w("Every game up to this date is stored; the next update starts the day after.",
                               "Każdy mecz do tej daty jest zapisany; następna aktualizacja zaczyna się dzień "
                               "później.")),
    'pre': Term(_w("preseason", "przedsezon"), _w("Preseason games.", "Mecze przedsezonowe.")),
    'regular': Term(_w("regular", "zasadniczy"), _w("Regular-season games.", "Mecze sezonu zasadniczego.")),
    'playin': Term(_w("play-in", "baraże"), _w("Play-in games.", "Mecze barażowe.")),
    'post': Term(_w("playoffs", "play-off"), _w("Playoff games.", "Mecze play-off.")),
    'allstar': Term(_w("all-star", "all-star"), _w("All-Star games (kept out of the regular-season stats).",
                                                   "Mecze gwiazd (poza statystykami sezonu zasadniczego).")),
    'file': Term(_w("file", "plik"), _w("The snapshot file.", "Plik z zapisami.")),
    'rows': Term(_w("rows", "wiersze"), _w("Rows stored.", "Zapisane wiersze.")),
    'snapshots': Term(_w("fetches", "pobrania"), _w("Separate fetches saved.", "Zapisane osobne pobrania.")),
    'first': Term(_w("first", "pierwsze"), _w("Oldest fetch (UTC).", "Najstarsze pobranie (UTC).")),
    'last': Term(_w("last", "ostatnie"), _w("Newest fetch (UTC).", "Najnowsze pobranie (UTC).")),
    'started_at': Term(_w("started (UTC)", "start (UTC)"), _w("When the run started.", "Kiedy uruchomiono.")),
    'job': Term(_w("job", "zadanie"), _w("stats, snapshot, fetch (Superbet) or lineups (a RotoWire change).",
                                         "stats, snapshot, fetch (Superbet) lub lineups (zmiana w RotoWire).")),
    'command': Term(_w("command", "polecenie"), _w("What ran.", "Co uruchomiono.")),
    'exit_code': Term(_w("exit", "kod"), _w("0 = success.", "0 = sukces.")),
    'seconds': Term(_w("seconds", "sekundy"), _w("How long it took.", "Ile trwało.")),
    'summary': Term(_w("summary", "podsumowanie"), _w("What was saved, or why it failed.",
                                                      "Co zapisano albo dlaczego się nie udało.")),
    'source': Term(_w("source", "źródło"), _w("Where the name comes from.", "Skąd pochodzi nazwisko.")),
    'note': Term(_w("note", "uwaga"), _w("Injury tag or role.", "Oznaczenie kontuzji lub rola.")),
    'date': Term(_w("date", "data"), _w("Game date.", "Data meczu.")),
    'season_id': Term(_w("season", "sezon"), _w("The season's first year.", "Pierwszy rok sezonu.")),
    'home': Term(_w("home", "gospodarz"), _w("The home team.", "Gospodarz.")),
    'away': Term(_w("away", "gość"), _w("The away team.", "Gość.")),
    'home_score': Term(_w("home score", "punkty gospodarza"), _w("The home team's points.", "Punkty gospodarza.")),
    'away_score': Term(_w("away score", "punkty gościa"), _w("The away team's points.", "Punkty gościa.")),
    'home pts (players)': Term(_w("home pts (players)", "pkt gospodarza (zawodnicy)"),
                               _w("The home players' points added up.", "Suma punktów zawodników gospodarza.")),
    'away pts (players)': Term(_w("away pts (players)", "pkt gościa (zawodnicy)"),
                               _w("The away players' points added up.", "Suma punktów zawodników gościa.")),

    # --- the 2022/23 backtest ---
    'name_ESPN': Term(_w("player", "zawodnik"), _w("The player.", "Zawodnik.")),
    'bet side': Term(_w("bet side", "grana strona"), _w("The side the chosen strategy bets.",
                                                        "Strona, którą gra wybrana strategia.")),
    'bet odds': Term(_w("odds", "kurs"), _w("Unibet's odds for that side.", "Kurs Unibetu na tę stronę.")),
    'bet result': Term(_w("result", "rezultat"), _w("win / loss / push.", "wygrana / przegrana / zwrot.")),
    'bet profit': Term(_w("profit", "zysk"), _w("Profit for 1 unit.", "Zysk na 1 jednostce."),
                       _w("The bet won.", "Zakład wygrał."), _w("The bet lost.", "Zakład przegrał.")),
    'strategy': Term(_w("strategy", "strategia"), _w("How the lines were bet.", "Jak grano linie.")),
    'avg line': Term(_w("avg line", "średnia linia"), _w("Average line.", "Średnia linia.")),
    'avg actual': Term(_w("avg result", "średni wynik"), _w("Average result.", "Średni wynik.")),
    'actual − line': Term(_w("result − line", "wynik − linia"), _w("Average miss.", "Średni błąd linii."),
                          _w("The lines were too low for this player.", "Linie były za niskie dla tego zawodnika."),
                          _w("The lines were too high.", "Linie były za wysokie.")),
    'month': Term(_w("month", "miesiąc"), _w("The month of the games.", "Miesiąc meczów.")),
    'backtest:avg': Term(_w("avg before", "średnia przed"), _w("Season average before the game.",
                                                               "Średnia sezonu przed meczem.")),
    'backtest:games': Term(_w("games before", "mecze przed"), _w("Games before the line.", "Mecze przed linią.")),
    'backtest:best side': Term(_w("model pick", "typ modelu"), _w("The model's pick.", "Typ modelu.")),
    'backtest:team': Term(_w("team", "drużyna"), _w("The player's team.", "Drużyna zawodnika.")),
    'backtest:signal': Term(_w("signal", "sygnał"), _w("The model's signal on the line (none = no edge).",
                                                       "Sygnał modelu na linii (brak = bez przewagi).")),

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
    'games:side': Term(_w("side", "strona"), _w("home / away for the winner and handicap, over / under for totals.",
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
    'games:decision': Term(_w("team markets", "rynki drużynowe"),
                           _w("The decision for this game's team markets: always Unavailable, the game model isn't "
                              "admitted.", "Decyzja dla rynków drużynowych tego meczu: zawsze Niedostępne, model "
                                           "meczów nie jest dopuszczony.")),
    'games:players': Term(_w("players", "zawodnicy"),
                          _w("The one decision for this game's player lines (see Props).",
                             "Jedna decyzja dla linii zawodników tego meczu (zob. Zakłady na zawodników).")),
    'games:edge net pp': Term(_w("edge after tax (pp), estimate", "przewaga po podatku (pp), szacunek"),
                              _w("The game model's chance minus the chance needed after the 12% stake tax. The "
                                 "model isn't admitted: research only.",
                                 "Szansa modelu meczów minus szansa potrzebna po 12% podatku. Model nie jest "
                                 "dopuszczony: tylko do analizy.")),
    'games:ev net 100': Term(_w("expected return per 100, after tax, estimate", "oczekiwany zwrot na 100 zł po "
                                                                                "podatku, szacunek"),
                             _w("By the game model's chance, which isn't admitted: research only.",
                                "Wg szansy modelu meczów, który nie jest dopuszczony: tylko do analizy.")),
    'games:market %': Term(_w("bookmaker's chance %", "szansa wg bukmachera %"),
                           _w("The chance the odds give this outcome with the margin taken out of its pair.",
                              "Szansa, jaką kursy dają temu wynikowi, po odjęciu marży z pary.")),
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

# the box-score stats, as columns: the code stays the header, the tooltip says what it counts
STAT_NAMES = {'PTS': _w("Points", "Punkty"), 'REB': _w("Rebounds (offensive + defensive)", "Zbiórki (w ataku + w "
                                                                                           "obronie)"),
              'AST': _w("Assists", "Asysty"), '3PM': _w("Three-pointers made", "Celne rzuty za 3"),
              '3PA': _w("Three-pointers attempted", "Rzuty za 3 oddane"), 'PA': _w("Points + assists", "Punkty + "
                                                                                                     "asysty"),
              'PR': _w("Points + rebounds", "Punkty + zbiórki"), 'RA': _w("Rebounds + assists", "Zbiórki + asysty"),
              'ARP': _w("Points + rebounds + assists (PRA)", "Punkty + zbiórki + asysty (PRA)"),
              'STL': _w("Steals", "Przechwyty"), 'BLK': _w("Blocks", "Bloki"), 'TO': _w("Turnovers", "Straty"),
              'FGM': _w("Field goals made (2s and 3s)", "Celne rzuty z gry (za 2 i 3)"),
              'FGA': _w("Field goals attempted (2s and 3s)", "Rzuty z gry oddane (za 2 i 3)"),
              'FTM': _w("Free throws made", "Celne rzuty wolne"), 'FTA': _w("Free throws attempted",
                                                                            "Rzuty wolne oddane"),
              'PF': _w("Personal fouls", "Faule osobiste"), 'MIN': _w("Minutes played", "Rozegrane minuty"),
              'OREB': _w("Offensive rebounds", "Zbiórki w ataku"), 'DREB': _w("Defensive rebounds",
                                                                             "Zbiórki w obronie"),
              'PLUS_MINUS': _w("+/-: team's points minus opponent's while the player was on court",
                               "+/-: punkty drużyny minus rywala, gdy zawodnik był na boisku")}
for _code, _name in STAT_NAMES.items():
    TERMS.setdefault(_code, Term(_w('PRA' if _code == 'ARP' else '+/-' if _code == 'PLUS_MINUS' else _code,
                                    'PRA' if _code == 'ARP' else '+/-' if _code == 'PLUS_MINUS' else _code),
                                 _name))

# the numbers a pick is decided on: their tooltips must say what more and what less means
DECISION_TERMS = ['edge pp', 'ev 100', 'model %', 'pick odds', 'break-even %', 'market %', 'proj avg', 'pick % L10', 'line',
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
          'Home': _w("Home", "U siebie"), 'Away': _w("Away", "Na wyjeździe"), 'Starter': _w("Starter",
                                                                                              "Pierwsza piątka"),
          'Bench': _w("Bench", "Rezerwa"), 'Back-to-back': _w("Back-to-back", "Dzień po dniu"),
          '1+ days rest': _w("1+ days rest", "1+ dzień przerwy"), 'First game': _w("First game", "Pierwszy mecz"),
          'location': _w("location", "miejsce"), 'rest': _w("rest", "przerwa"), 'minutes': _w("minutes", "minuty"),
          'role': _w("role", "rola"), 'Teammate played': _w("Teammate played", "Kolega grał"),
          'Teammate out': _w("Teammate out", "Kolegi nie było"), 'Out': _w("Out", "Nie gra"),
          'Guards': _w("Guards", "Obrońcy"), 'Forwards': _w("Forwards", "Skrzydłowi"),
          'Centers': _w("Centers", "Środkowi"), 'high': _w("high", "wysoka"), 'medium': _w("medium", "średnia"),
          'low': _w("low", "niska"),
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
                        "tonight's lineups: one decision per game, and the reasons behind it for any line you pick.",
                        "Linie Superbetu na zawodników na najbliższe 36 godzin, porównane z meczami każdego "
                        "zawodnika i dzisiejszymi składami: jedna decyzja na mecz i jej powody dla wybranej linii."),
    'props.how_to_choose': _w("**How to read it:** the decision above the table is the one per game; the table is for "
                              "research. Every price includes Superbet's 12% stake tax. Hover any header for what it "
                              "means; **How to read this** in the menu explains it all.",
                              "**Jak czytać:** decyzja nad tabelą to ta jedna na mecz; tabela służy do analizy. Każda "
                              "cena uwzględnia 12% podatku od stawki. Najedź na nagłówek, żeby zobaczyć, co znaczy; "
                              "**Jak to czytać** w menu wyjaśnia wszystko."),
    'props.filter.games': _w("Games", "Mecze"), 'props.filter.all_games': _w("All games", "Wszystkie mecze"),
    'props.filter.types': _w("Stats", "Statystyki"),
    'props.filter.types_help': _w("PA = points + assists, PR = points + rebounds, RA = rebounds + assists, PRA = all "
                                  "three", "PA = punkty + asysty, PR = punkty + zbiórki, RA = zbiórki + asysty, PRA "
                                           "= wszystkie trzy"),
    'props.more': _w("More", "Więcej"),
    'props.hide_out': _w("Hide players RotoWire lists as out", "Ukryj zawodników, którzy wg RotoWire nie zagrają"),
    'props.min_games': _w("Min games", "Min. meczów"),
    'props.min_games_help': _w("Hide players with fewer games behind their numbers",
                               "Ukryj zawodników z mniejszą liczbą meczów"),
    'props.every_column': _w("Show every column", "Pokaż wszystkie kolumny"),
    'props.sort': _w("Sort by", "Sortuj"),
    'props.sort.return': _w("Expected return", "Oczekiwany zwrot"),
    'props.sort.chance': _w("Chance to win", "Szansa na wygraną"),
    'props.sort.tip': _w("Tip-off", "Start meczu"),
    'props.sort.stars': _w("Rating", "Ocena"),
    'props.sort_help': _w("Tip-off keeps the games in order; rating puts the most stars first; expected return "
                          "(after the tax) and chance to win order every line. 4★ = the best of tonight, not: worth "
                          "betting; the decision is above the table.",
                          "Start meczu trzyma kolejność meczów; ocena stawia na początku najwięcej gwiazdek; "
                          "oczekiwany zwrot (po podatku) i szansa układają wszystkie linie. 4★ = najlepsze dziś, nie: "
                          "opłacalne; decyzja jest nad tabelą."),
    'props.only_best': _w("Only 3★ and more", "Tylko 3★ i więcej"),
    'props.only_best_help': _w("Tonight's best 20% of lines by expected return, no warnings or doubtful players. They "
                               "still lose on average after the tax.",
                               "Najlepsze 20% dzisiejszych linii według oczekiwanego zwrotu, bez ostrzeżeń i "
                               "niepewnych graczy. Po podatku dalej średnio tracą."),
    'props.kpi.shown': _w("Lines shown", "Pokazane linie"),
    'props.kpi.shown_help': _w("Lines that pass the filters, of every line Superbet offers",
                               "Linie spełniające filtry, spośród wszystkich linii Superbetu"),
    'props.kpi.obstaw': _w("'Bet' decisions", "Decyzje 'Obstaw'"),
    'props.kpi.obstaw_help': _w("Games where one offer's edge clears a threshold checked on nights not used to choose "
                                "it. None can until such a threshold exists.",
                                "Mecze, w których przewaga jednej oferty przekracza próg sprawdzony na nocach, "
                                "których nie użyto do jego wyboru. Żadna nie może, dopóki taki próg nie istnieje."),
    'props.hide_red': _w("Hide lines with a warning", "Ukryj linie z ostrzeżeniem"),
    'props.kpi.games': _w("Games", "Mecze"),
    'props.kpi.red': _w("🔴 Warnings", "🔴 Ostrzeżenia"),
    'props.kpi.red_help': _w("Lines with a reason to pass whatever the numbers say", "Linie z powodem, żeby "
                                                                                     "odpuścić, cokolwiek mówią "
                                                                                     "liczby"),
    'props.order.return': _w("Highest expected return after the tax first", "Najpierw najwyższy oczekiwany zwrot po "
                                                                           "podatku"),
    'props.order.chance': _w("The highest chance to win first (mostly low odds)",
                             "Najpierw najwyższa szansa na wygraną (głównie niskie kursy)"),
    'props.order.tip': _w("Earliest tip-off first", "Najpierw najwcześniejszy start"),
    'props.order.stars': _w("The most stars first, then by expected return",
                            "Najpierw najwięcej gwiazdek, potem według oczekiwanego zwrotu"),
    'props.all_pass': _w("**No offer meets the condition for 'Bet'.** There's no edge threshold yet that was "
                         "checked on nights not used to choose it, so every game's decision is 'Don't bet', 'Wait' or 'Unavailable'. The table is for "
                         "research, not a list of bets.",
                         "**Żadna oferta nie spełnia warunku 'Obstaw'.** Nie ma jeszcze progu przewagi sprawdzonego "
                         "na nocach, których nie użyto do jego wyboru, więc decyzja każdego meczu to 'Nie obstawiaj', 'Czekaj' albo 'Niedostępne'. Tabela służy "
                         "do analizy, to nie lista zakładów."),
    'props.order.rest': _w(", warnings last. ⏰ = starts within the hour; a line leaves the list when its game starts. "
                           "Hover a header for what it means; pick a row for the details.",
                           ", ostrzeżenia na końcu. ⏰ = start w ciągu godziny; linia znika, gdy zaczyna się mecz. "
                           "Najedź na nagłówek, żeby zobaczyć, co znaczy; wybierz wiersz po szczegóły."),
    'props.pick_row': _w("Pick a row in the table to see the decision for its game, the reasons, the teammates and the "
                         "history.", "Wybierz wiersz w tabeli, żeby zobaczyć decyzję dla jego meczu, powody, kolegów "
                                     "z drużyny i historię."),
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
    'detail.pass_title': _w("{name} · {side} (evaluated side, {ev:+.1f} per 100 after tax)",
                            "{name} · {side} (oceniana strona, {ev:+.1f} zł na 100 po podatku)"),
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
    'detail.kpi.game_help': _w("Superbet's implied points for his team vs its usual (team points factor ×{pace:.2f}) and "
                               "what the opponent allows to his position (×{matchup:.2f}, {word})",
                               "Punkty drużyny z kursu Superbetu wobec jej zwykłej liczby (czynnik punktów drużyny "
                               "×{pace:.2f}) i ile rywal pozwala na jego pozycji (×{matchup:.2f}, {word})"),
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
    'mates.col.change_help': _w("{stat} without the teammate minus with him: a description of the games he missed (other "
                                "things changed in them too), not the effect of his absence.",
                                "{stat} bez kolegi minus z nim: opis meczów, które opuścił (zmieniało się w nich "
                                "też co innego), a nie wpływ jego nieobecności."),
    'mates.col.with': _w("{stat} with", "{stat} z nim"), 'mates.col.without': _w("{stat} without", "{stat} bez niego"),
    'mates.col.n_with': _w("games with", "mecze z nim"), 'mates.col.n_without': _w("games without", "mecze bez niego"),
    'mates.reliability': _w("Descriptive: the player's numbers in the games a teammate missed, not what his absence causes. "
                            "Few games without a teammate make a change unreliable. Only games inside the teammate's "
                            "time on the team count.",
                            "Opisowo: liczby zawodnika w meczach, które opuścił kolega, a nie to, co powoduje jego "
                            "nieobecność. Mało meczów bez kolegi to niepewna zmiana. Liczą się tylko mecze z okresu, "
                            "gdy kolega był w drużynie."),
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
    'decision.OBSTAW': _w("Bet", "Obstaw"), 'decision.NIE_OBSTAWIAJ': _w("Don't bet", "Nie obstawiaj"),
    'decision.CZEKAJ': _w("Wait", "Czekaj"), 'decision.NIEDOSTEPNE': _w("Unavailable", "Niedostępne"),
    'decision.teams': _w("Team markets", "Rynki drużynowe"), 'decision.players': _w("Players", "Zawodnicy"),
    'decision.reason.game_model': _w("The game model isn't admitted: on the settled nights it predicted worse than the "
                                     "bookmaker's margin-free price", "Model meczów nie jest dopuszczony: na "
                                                                      "rozliczonych wieczorach przewidywał gorzej niż "
                                                                      "kurs bez marży"),
    'decision.reason.no_calibration': _w("The props model isn't admitted: no calibration fitted for its current "
                                         "version", "Model zawodników nie jest dopuszczony: brak kalibracji dla jego "
                                                    "bieżącej wersji"),
    'decision.reason.no_odds': _w("No odds for this game's player lines", "Brak kursów na linie zawodników tego "
                                                                          "meczu"),
    'decision.reason.stale_odds': _w("The odds are {hours:.0f} h old: fetch them again", "Kursy mają {hours:.0f} h: "
                                                                                       "pobierz je ponownie"),
    'decision.reason.no_lineup': _w("RotoWire doesn't list the lineup of {teams} yet", "RotoWire nie podaje "
                                                                                       "jeszcze składu {teams}"),
    'decision.reason.questionable': _w("{name} may not play ({role}): wait for the lineup",
                                       "{name} może nie zagrać ({role}): poczekaj na skład"),
    'decision.reason.no_threshold': _w("No offer can qualify: there's no edge threshold yet that was checked on "
                                       "nights not used to choose it",
                                       "Żadna oferta nie może się zakwalifikować: nie ma jeszcze progu przewagi "
                                       "sprawdzonego na nocach, których nie użyto do jego wyboru"),
    'decision.reason.no_offer': _w("No offer has an edge after tax of {threshold:+.1f} pp or more",
                                   "Żadna oferta nie ma przewagi po podatku co najmniej {threshold:+.1f} pp"),
    'decision.reason.tie': _w("Two offers tie on expected return: no arbitrary choice",
                              "Dwie oferty mają równy oczekiwany zwrot: bez arbitralnego wyboru"),
    'decision.reason.meets': _w("Meets the recorded threshold", "Spełnia zapisany próg"),
    'decision.reason.other_offer': _w("Another offer of this game is the one evaluated",
                                      "Oceniana jest inna oferta tego meczu"),
    'decision.odds_at': _w("odds from {time}", "kurs z {time}"),
    'decision.lineup_at': _w("lineup from {time}", "skład z {time}"),
    'decision.lineup_unknown': _w("no lineup time", "brak czasu składu"),
    'decision.changed': _w("The {what} changed since the decision you saw: {was} → {now}. That decision is no longer "
                           "valid; the one below is recomputed.",
                           "Od decyzji, którą widziałeś, zmienił się {what}: {was} → {now}. Tamta decyzja jest "
                           "nieaktualna; poniższa jest przeliczona."),
    'decision.what.line': _w("line", "linia"), 'decision.what.odds': _w("odds", "kurs"),
    'decision.none': _w("No offer meets the condition for 'Bet' (there's no edge threshold yet that was checked on "
                        "nights not used to choose it): there's nothing to bet on tonight.",
                        "Żadna oferta nie spełnia warunku 'Obstaw' (nie ma jeszcze progu przewagi sprawdzonego na "
                        "nocach, których nie użyto do jego wyboru): dziś nie ma na co grać."),
    'decision.title': _w("Tonight's decisions", "Dzisiejsze decyzje"),
    'panel.why': _w("Why", "Dlaczego"),
    'panel.why_note': _w("The reasons explain the decision; how many there are doesn't change it.",
                         "Powody objaśniają decyzję; ich liczba jej nie zmienia."),
    'panel.meta': _w("{n} obs. · {source} · {as_of}", "{n} obs. · {source} · {as_of}"),
    'panel.meta_quote': _w("{source} · {as_of}", "{source} · {as_of}"),
    'panel.economics': _w("Price", "Cena"),
    'panel.economics_note': _w("The evaluated side is the one with the higher expected return, which isn't "
                               "necessarily positive. Only the stake tax is counted; the separate tax on large "
                               "winnings isn't.",
                               "Oceniana strona to ta z wyższym oczekiwanym zwrotem, który nie musi być dodatni. "
                               "Liczony jest tylko podatek od stawki; osobny podatek od dużych wygranych nie."),
    'panel.economics_note_games': _w("The game model isn't admitted: its chance is an experimental estimate, not "
                                     "a reason to bet.",
                                     "Model meczów nie jest dopuszczony: jego szansa to eksperymentalna ocena, nie "
                                     "powód do zakładu."),
    'panel.drivers': _w("What the model used", "Czego użył model"),
    'panel.drivers_note': _w("Each input with how much it moved the final chance (pp, after calibration). The "
                             "effects overlap: don't add them up.",
                             "Każde wejście z tym, o ile zmieniło końcową szansę (pp, po kalibracji). Efekty się "
                             "nakładają: nie sumuj ich."),
    'panel.context': _w("Context", "Kontekst"),
    'panel.context_note': _w("What the games show that the model doesn't use. Not for or against unless it "
                             "predicted results beyond the model on unseen lines.",
                             "Co pokazują mecze, a czego model nie używa. Nie jest za ani przeciw, chyba że "
                             "przewidywało wyniki lepiej niż model na niewidzianych liniach."),
    'panel.validation.untested': _w("not tested", "nie testowane"),
    'panel.validation.no_lift': _w("tested: no gain beyond the model", "testowane: nic ponad model"),
    'panel.validation.lift': _w("tested: predicted beyond the model", "testowane: przewidywało ponad model"),
    'panel.warnings': _w("Worth knowing (doesn't block a bet)", "Warto wiedzieć (nie blokuje zakładu)"),
    'panel.flags': _w("Blockers (an offer with one can't get 'Bet')", "Blokady (oferta z blokadą nie dostanie "
                                                                     "'Obstaw')"),
    'panel.for': _w("For", "Za"), 'panel.against': _w("Against", "Przeciw"), 'panel.nothing': _w("nothing", "nic"),
    'panel.chart': _w("Last {n} games: {stat} (green = over the line)", "Ostatnie {n} meczów: {stat} (zielone = "
                                                                       "powyżej linii)"),
    'panel.line': _w("line {line:g}", "linia {line:g}"),
    # reasons about a prop (reasons.prop_reasons): the price
    'reason.model': _w("Model: {side} wins {model:.1f}%; odds {odds:.2f} after the {tax:.0f}% stake tax need "
                       "{be:.1f}% (edge {edge:+.1f} pp, {ev:+.1f} per 100 staked)",
                       "Model: {side} wygrywa w {model:.1f}%; kurs {odds:.2f} po {tax:.0f}% podatku od stawki "
                       "wymaga {be:.1f}% (przewaga {edge:+.1f} pp, {ev:+.1f} na 100 zł stawki)"),
    'reason.model_no_tax': _w("Model: {side} wins {model:.1f}%; odds {odds:.2f} without the stake tax (promotion, "
                              "{tax:.0f}%) need {be:.1f}% (edge {edge:+.1f} pp, {ev:+.1f} per 100 staked)",
                              "Model: {side} wygrywa w {model:.1f}%; kurs {odds:.2f} bez podatku od stawki "
                              "(promocja, {tax:.0f}%) wymaga {be:.1f}% (przewaga {edge:+.1f} pp, {ev:+.1f} na 100 zł "
                              "stawki)"),
    'reason.beyond_price': _w("The price alone says {side} {market:.1f}% (margin-free), {price:.1f}% after the "
                              "calibration; the player's numbers move it {beyond:+.1f} pp",
                              "Sama cena mówi {side} {market:.1f}% (bez marży), {price:.1f}% po kalibracji; liczby "
                              "zawodnika zmieniają to o {beyond:+.1f} pp"),
    # what the model used
    'reason.impact': _w("; moves the model's chance {impact:+.1f} pp", "; zmienia szansę modelu o {impact:+.1f} pp"),
    'reason.impact_none': _w("; moves the model's chance less than {least:g} pp",
                             "; zmienia szansę modelu o mniej niż {least:g} pp"),
    'reason.expected': _w("Expected {proj:.1f} {stat} tonight vs the line {line:g} ({diff:+.1f}); average {avg:.1f}, "
                          "median {median:.1f}", "Oczekiwane dziś {proj:.1f} {stat} wobec linii {line:g} "
                                                 "({diff:+.1f}); średnia {avg:.1f}, mediana {median:.1f}"),
    'reason.teammates': _w("{names} out: in his games without them {name} averaged {adj:+.1f} {stat} compared with his "
                           "games with them (after shrinking; fewest games without one of them: {n}; a "
                           "description, not their effect)",
                           "{names} nie zagra: w meczach bez nich {name} miał średnio {adj:+.1f} {stat} wobec meczów "
                           "z nimi (po ściągnięciu; najmniej meczów bez jednego z nich: {n}; opis, nie ich wpływ)"),
    'reason.environment': _w("Scoring environment: Superbet expects {team} to score {implied:.0f} (usually "
                             "{usual:.0f})",
                             "Otoczenie punktowe: Superbet oczekuje, że {team} zdobędzie {implied:.0f} (zwykle "
                             "{usual:.0f})"),
    'reason.matchup': _w("{opp} allow {value:.1f} {stat} per game to {position}, {diff:.1f} {more} than average (rank "
                         "{rank} of {teams}, 1 = allows the most): {word} matchup",
                         "{opp} pozwalają {position} na {value:.1f} {stat} na mecz, o {diff:.1f} {more} niż przeciętnie "
                         "(miejsce {rank} z {teams}, 1 = pozwala najwięcej): {word} rywal"),
    'reason.more': _w("more", "więcej"), 'reason.fewer': _w("fewer", "mniej"),
    'reason.position.G': _w("guards", "obrońcom"), 'reason.position.F': _w("forwards", "skrzydłowym"),
    'reason.position.C': _w("centers", "środkowym"), 'reason.position.': _w("this position", "tej pozycji"),
    # context: what the games show that the model doesn't use
    'reason.history_last': _w("At this line: {side} in {hits} of the last {n} games ({rate:.0f}%, 95% range "
                              "{low:.0f}–{high:.0f}%)",
                              "Przy tej linii: {side} w {hits} z ostatnich {n} meczów ({rate:.0f}%, przedział 95% "
                              "{low:.0f}–{high:.0f}%)"),
    'reason.history_all': _w(", {hits} of all {n} ({rate:.0f}%)", ", {hits} ze wszystkich {n} ({rate:.0f}%)"),
    'reason.history_note': _w("; needs {be:.0f}% after tax. The model uses this rate only pulled toward the price",
                              "; potrzeba {be:.0f}% po podatku. Model używa tej częstości tylko ściągniętej do ceny"),
    'reason.sample_last_season': _w("; {n} of the games are from last season", "; {n} z meczów to zeszły sezon"),
    'reason.sample_preseason': _w("; {n} are preseason", "; {n} to przedsezon"),
    'reason.minutes': _w("Minutes: {recent:.1f} per game in the last 5 ({low:.0f}–{high:.0f}) vs {usual:.1f} in his "
                         "{n} earlier games with {team}",
                         "Minuty: {recent:.1f} na mecz w ostatnich 5 ({low:.0f}–{high:.0f}) wobec {usual:.1f} w {n} "
                         "wcześniejszych meczach w {team}"),
    'reason.minutes_short': _w("; short games among them: {short} (5+ fouls in {fouls}, decided by 20+ in {blowouts})",
                               "; krótkie mecze wśród nich: {short} (5+ fauli w {fouls}, różnica 20+ w {blowouts})"),
    'reason.role': _w("Role: started {started} of the last {n} games; RotoWire tonight: {role}",
                      "Rola: zaczynał {started} z ostatnich {n} meczów; RotoWire dziś: {role}"),
    'reason.volume': _w("Shots per 36 min in the last 5: {fga:.1f} FGA, {tpa:.1f} 3PA, {fta:.1f} FTA (before: "
                        "{fga0:.1f}, {tpa0:.1f}, {fta0:.1f}); made {fg:.0f}% / {tp:.0f}% / {ft:.0f}% (before: "
                        "{fg0:.0f}% / {tp0:.0f}% / {ft0:.0f}%), {attempts} attempts in the last 5",
                        "Rzuty na 36 min w ostatnich 5: {fga:.1f} FGA, {tpa:.1f} 3PA, {fta:.1f} FTA (wcześniej: "
                        "{fga0:.1f}, {tpa0:.1f}, {fta0:.1f}); celność {fg:.0f}% / {tp:.0f}% / {ft:.0f}% (wcześniej: "
                        "{fg0:.0f}% / {tp0:.0f}% / {ft0:.0f}%), {attempts} prób w ostatnich 5"),
    'reason.home': _w("At home: {value:.1f} in {n} home games ({avg:.1f} overall)",
                      "U siebie: {value:.1f} w {n} meczach u siebie ({avg:.1f} ogółem)"),
    'reason.away': _w("Away: {value:.1f} in {n} away games ({avg:.1f} overall)",
                      "Na wyjeździe: {value:.1f} w {n} meczach wyjazdowych ({avg:.1f} ogółem)"),
    'reason.rest': _w("Rest days: {team} {rest}, {opp} {opp_rest}; {name} played {m3:.0f} min in the last 3 days "
                      "and {m7:.0f} in the last 7",
                      "Dni odpoczynku: {team} {rest}, {opp} {opp_rest}; {name} grał {m3:.0f} min w ostatnich 3 "
                      "dniach i {m7:.0f} w ostatnich 7"),
    'reason.vs_opp': _w("Against {opp}: {avg:.1f} {stat} in {n} games (all stored seasons)",
                        "Przeciw {opp}: {avg:.1f} {stat} w {n} meczach (wszystkie zapisane sezony)"),
    'reason.blowout_favoured': _w("{team} favoured by {spread:g}: in his games decided by 15+ he played {big:.1f} "
                                  "min ({n_big}), in closer ones {close:.1f} ({n_close})",
                                  "{team} faworytem o {spread:g}: w jego meczach rozstrzygniętych różnicą 15+ grał "
                                  "{big:.1f} min ({n_big}), w wyrównanych {close:.1f} ({n_close})"),
    'reason.blowout_underdogs': _w("{team} underdogs by {spread:g}: in his games decided by 15+ he played {big:.1f} "
                                   "min ({n_big}), in closer ones {close:.1f} ({n_close})",
                                   "{team} słabszy o {spread:g}: w jego meczach rozstrzygniętych różnicą 15+ grał "
                                   "{big:.1f} min ({n_big}), w wyrównanych {close:.1f} ({n_close})"),
    'reason.line_moved': _w("The line moved {move:+g} since first seen ({open:g} → {line:g}); market context, not a "
                            "reason for the current offer",
                            "Linia ruszyła o {move:+g} od pierwszego zapisu ({open:g} → {line:g}); kontekst rynku, "
                            "nie powód za aktualną ofertą"),
    'reason.odds_moved': _w("Same line {line:g}, odds {open_odds:.2f} → {odds:.2f} since first seen: the "
                            "margin-free chance of {side} went {was:.0f}% → {now:.0f}%",
                            "Ta sama linia {line:g}, kurs {open_odds:.2f} → {odds:.2f} od pierwszego zapisu: szansa "
                            "{side} bez marży {was:.0f}% → {now:.0f}%"),
    'reason.before_tip': _w(" ({hours:.0f} h before tip-off)", " ({hours:.0f} h przed meczem)"),
    # worth knowing, doesn't block (reasons.prop_reasons)
    'warn.role': _w("Started {started} of the last {n} games but RotoWire lists him as {role} tonight: the numbers "
                    "come from another role",
                    "Zaczynał {started} z ostatnich {n} meczów, a RotoWire podaje go dziś jako {role}: liczby "
                    "pochodzą z innej roli"),
    'warn.stint': _w("Only {k} of the {n} games are with {team}: the rest are from another team",
                     "Tylko {k} z {n} meczów to {team}: reszta to inna drużyna"),
    'warn.lineup_expected': _w("RotoWire's lineup of {team} is expected, not confirmed",
                               "Skład {team} na RotoWire jest przewidywany, nie potwierdzony"),
    # blockers (reasons.prop_flags)
    'flag.few_games': _w("Only {n} {n|game|games|games} in the sample: too few to trust the numbers",
                         "Tylko {n} {n|mecz|mecze|meczów} w próbie: za mało, żeby ufać liczbom"),
    'flag.preseason': _w("Every game is preseason: minutes and roles change in the regular season",
                         "Wszystkie mecze to przedsezon: minuty i role zmieniają się w sezonie zasadniczym"),
    'flag.out': _w("RotoWire: {status}: won't play (the line is refunded)",
                   "RotoWire: {status}: nie zagra (zakład zostanie zwrócony)"),
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
    'game.model': _w("Model: {model:.0f}%; odds {odds:.2f} after the 12% stake tax need {be:.0f}% (edge {edge:+.1f} pp)",
                     "Model: {model:.0f}%; kurs {odds:.2f} po 12% podatku od stawki wymaga {be:.0f}% (przewaga "
                     "{edge:+.1f} pp)"),
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
    'games.best_shown': _w("Research only: team markets are unavailable. Pick a row for the reasons behind an outcome.",
                           "Tylko do analizy: rynki drużynowe są niedostępne. Wybierz wiersz, żeby zobaczyć powody "
                           "dla danego wyniku."),
    'games.away': _w("Away", "Gość"), 'games.home': _w("Home", "Gospodarz"),
    'games.team_line': _w("**{side}: {team}** · attack {off:.1f}, defense {defense:.1f}, pace {pace:.1f}",
                          "**{side}: {team}** · atak {off:.1f}, obrona {defense:.1f}, tempo {pace:.1f}"),
    'games.not_listed': _w("📋 Not on RotoWire's page (yet).", "📋 (Jeszcze) nie ma na stronie RotoWire."),
    'games.lineup': _w("📋 {status} lineup: {players}", "📋 skład {status}: {players}"),
    'games.open_lineup': _w("Open {team} in Lineup lab", "Otwórz {team} w Laboratorium składów"),

    # Results page
    'results.title': _w("Model evaluation", "Rozliczenie ocen modelu"),
    'results.purpose': _w("Every line we saved, settled against the real results: how the model's evaluations before "
                          "tip-off held up. It isn't the result of your own bets (those are in the first dashboard's "
                          "My bets) and it isn't proof that the system makes money.",
                          "Każda zapisana linia rozliczona z prawdziwymi wynikami: jak sprawdziły się oceny modelu "
                          "sprzed startu. To nie jest wynik twoich zakładów (te są w Moich zakładach pierwszego "
                          "dashboardu) ani dowód, że system zarabia."),
    'results.tab.night': _w("🌙 Previous night: model evaluations", "🌙 Poprzedni wieczór: oceny modelu"),
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
    'results.kpi.toward_roi': _w("Toward the average: return per 100", "W stronę średniej: zwrot na 100"),
    'results.kpi.toward_roi_help': _w("At the first odds of that side, the same stake on every line",
                                      "Po pierwszym kursie tej strony, równa stawka na każdą linię"),
    'results.tab.avg': _w("Lines vs averages", "Linie a średnie"),
    'results.tab.picks': _w("Model's picks", "Typy modelu"),
    'results.tab.games': _w("Game markets (model)", "Rynki meczowe (model)"),
    'results.tab.all': _w("All settled lines", "Wszystkie rozliczone linie"),
    'results.tab.shortlist': _w("Ratings: the record", "Oceny: wyniki"),
    'results.shortlist_intro': _w(
        "How each star level did, every line judged at its last fetch before tip-off (1 unit, the evaluated side), "
        "with every line as the baseline. The scale works only if more stars won more often than the price said: "
        "the last row, 4★ − 1★, has to stay above 0. Nights before Nov 2 are rated again from what each fetch "
        "saved before the game (recomputed); later nights use the stars the fetch saved. CLV % appears once the "
        "scheduled fetches have read games 5–10 minutes before tip-off.",
        "Jak wypadł każdy poziom gwiazdek, każda linia oceniana przy ostatnim pobraniu przed startem (1 jednostka, "
        "oceniana strona), z każdą linią jako punktem odniesienia. Skala działa tylko wtedy, gdy więcej gwiazdek "
        "wygrywało częściej, niż mówił kurs: ostatni wiersz, 4★ − 1★, musi być powyżej 0. Wieczory sprzed 2.11 są "
        "oceniane ponownie z tego, co każde pobranie zapisało przed meczem (przeliczone); późniejsze używają "
        "zapisanych gwiazdek. CLV % pojawia się, gdy pobieranie według harmonogramu odczyta mecze 5–10 minut przed "
        "startem."),
    'results.shortlist_origin': _w("Nights: {recorded} recorded, {recomputed} recomputed.",
                                   "Wieczory: {recorded} zapisane, {recomputed} przeliczone."),
    'results.every_line': _w("every line", "każda linia"),
    'results.shortlist_none': _w("No settled night with rated lines yet.",
                                 "Nie ma jeszcze rozliczonego wieczoru z ocenami."),
    'results.ako': _w("AKO of the 3 best 4★ lines, on paper", "AKO z 3 najlepszych linii 4★, na papierze"),
    'results.ako_intro': _w(
        "A virtual accumulator a night: the 3 best 4★ lines (different games), 1 unit. Superbet takes the 12% tax once "
        "from the coupon's stake, so an AKO pays 0.88 × the product of the odds; it only pays off if each leg beats "
        "its price before tax by about 4.4%. Tracked to see whether it does; it isn't advice to play it.",
        "Wirtualny kupon AKO co wieczór: 3 najlepsze linie 4★ (różne mecze), 1 jednostka. Superbet pobiera 12% podatku "
        "raz od stawki kuponu, więc AKO wypłaca 0,88 × iloczyn kursów; opłaca się tylko, gdy każde zdarzenie bije "
        "swój kurs przed podatkiem o ok. 4,4%. Śledzone, żeby sprawdzić, czy tak jest; to nie zachęta do gry."),
    'results.ako_summary': _w("{n} coupons, {won} won, after tax {total:+.1f} units in total.",
                              "{n} kuponów, {won} wygranych, po podatku łącznie {total:+.1f} jednostki."),
    'results.nothing': _w("Nothing settled in this selection yet: update the stats after the games (Data center).",
                          "W tym wyborze nic nie jest jeszcze rozliczone: zaktualizuj statystyki po meczach "
                          "(Centrum danych)."),
    'results.gap_chart': _w("Betting toward the average, by how far the line was from it",
                            "Granie w stronę średniej, wg odległości linii od niej"),
    'results.gap_hover': _w("%{x}: won %{y:.0f}%, return per 100 (plain odds) %{customdata:+.1f}",
                            "%{x}: wygrane %{y:.0f}%, zwrot na 100 (bez podatku) %{customdata:+.1f}"),
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
    'results.kpi.profit': _w("Result, 1 unit per line (plain odds)", "Wynik, 1 jednostka na linię (kurs bez podatku)"),
    'results.kpi.roi': _w("Return per 100: plain odds / after tax", "Zwrot na 100: bez podatku / po podatku"),
    'results.kpi.vs_last': _w("Odds vs last quote", "Kurs wobec ostatniego"),
    'results.kpi.vs_last_help': _w("Our odds vs the last odds before tip-off: getting better prices than the market's "
                                   "last is an early sign of a real edge",
                                   "Nasze kursy wobec ostatnich przed startem: lepsze ceny niż ostatnie rynkowe to "
                                   "wczesny znak prawdziwej przewagi"),
    'results.efficiency': _w("**Does a bigger edge win more?**", "**Czy większa przewaga częściej wygrywa?**"),
    'results.no_edge_yet': _w("No settled pick has had a positive edge yet.",
                              "Żaden rozliczony typ nie miał jeszcze dodatniej przewagi."),
    'results.curve': _w("Running result, 1 unit per model pick (plain odds)", "Narastający wynik, 1 jednostka na typ modelu (kurs bez podatku)"),
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
    'night.about': _w("Model evaluation: how the model's evaluations before tip-off held up against the results. "
                      "It isn't the result of your own bets and it isn't proof that the system makes money.",
                      "Rozliczenie ocen modelu: jak oceny sprzed startu sprawdziły się wobec wyników. To nie jest "
                      "wynik twoich zakładów ani dowód, że system zarabia."),
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
    'night.kpi.roi': _w("return per 100 {roi:+.1f}, after tax {std:+.1f}", "zwrot na 100 {roi:+.1f}, po podatku {std:+.1f}"),
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
                               "likely to win come first; the dashed line is break-even at the plain odds (about {be}%; {be_std}% after the 12% stake tax). One night is a "
                               "small sample: check the range and look at several nights before trusting a pattern.",
                               "Każda rozliczona linia, w grupach. Dla każdej grupy: jak często wygrywało i "
                               "zarabiało Powyżej i Poniżej oraz jak poszły nasze typy. Najpierw grupy, w których "
                               "zakład najczęściej wygrywał; przerywana linia to próg opłacalności przy kursie bez podatku (ok. {be}%; {be_std}% po 12% podatku). Jeden "
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
    'night.group_hover': _w("%{y}: %{x:.1f}% won · return per 100 %{customdata[0]:+.1f} · %{customdata[1]} lines",
                            "%{y}: %{x:.1f}% wygranych · zwrot na 100 %{customdata[0]:+.1f} · %{customdata[1]} linii"),
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

    # Player history
    'ph.title': _w("Player history", "Historia zawodnika"),
    'ph.purpose': _w("One player's games: form, how results spread around a line, season trends, splits, opponents and "
                     "teammates.", "Mecze jednego zawodnika: forma, rozkład wyników wokół linii, sezony, podziały, "
                                   "rywale i koledzy z drużyny."),
    'ph.no_games': _w("No games stored for these game types.", "Brak zapisanych meczów dla tych rodzajów meczów."),
    'ph.player': _w("Player", "Zawodnik"), 'ph.type_name': _w("Type a name...", "Wpisz nazwisko..."),
    'ph.stat': _w("Stat", "Statystyka"), 'ph.line': _w("Line (optional)", "Linia (opcjonalnie)"),
    'ph.line_example': _w("e.g. 18.5", "np. 18.5"),
    'ph.line_help': _w("Colours the games over / under it and adds how often he went over",
                       "Koloruje mecze powyżej / poniżej niej i dodaje, jak często ją przekraczał"),
    'ph.pick': _w("Pick a player to see their history.", "Wybierz zawodnika, żeby zobaczyć jego historię."),
    'ph.no_scope': _w("{name} has no games in the scope; the season trend below covers every stored season.",
                      "{name} nie ma meczów w zakresie; trend sezonów poniżej obejmuje wszystkie zapisane sezony."),
    'ph.kpi.avg': _w("Average", "Średnia"), 'ph.kpi.avg_help': _w("{n} games in the scope",
                                                                 "{n} {n|mecz|mecze|meczów} w zakresie"),
    'ph.kpi.last5': _w("Last 5", "Ostatnie 5"), 'ph.kpi.last5_help': _w("Average over the last 5 games, vs the average",
                                                                       "Średnia z ostatnich 5 meczów wobec średniej"),
    'ph.kpi.last10': _w("Last 10", "Ostatnie 10"), 'ph.kpi.median': _w("Median", "Mediana"),
    'ph.kpi.median_help': _w("Half the games above, half below", "Połowa meczów wyżej, połowa niżej"),
    'ph.kpi.minutes': _w("Minutes", "Minuty"),
    'ph.kpi.minutes_help': _w("Average minutes; the small text is the last 5 games vs that",
                              "Średnie minuty; mały tekst to ostatnie 5 meczów wobec nich"),
    'ph.kpi.over': _w("Over {line:g}", "Powyżej {line:g}"),
    'ph.kpi.over_help': _w("Share of games over the line; the line's percentile {pct:.0f}",
                           "Odsetek meczów powyżej linii; percentyl linii {pct:.0f}"),
    'ph.open_lab': _w("Open the team in Lineup lab", "Otwórz drużynę w Laboratorium składów"),
    'ph.tab.log': _w("Game log", "Mecze"), 'ph.tab.dist': _w("Distribution", "Rozkład"),
    'ph.tab.trend': _w("Season trend", "Sezony"), 'ph.tab.splits': _w("Splits", "Podziały"),
    'ph.tab.opp': _w("Opponents", "Rywale"), 'ph.tab.mates': _w("With / without", "Z / bez kolegi"),
    'ph.tab.all': _w("All games", "Wszystkie mecze"),
    'ph.none': _w("No games in the scope.", "Brak meczów w zakresie."),
    'ph.games': _w("Games", "Mecze"), 'ph.last_n': _w("last {n}", "ostatnie {n}"), 'ph.all': _w("all", "wszystkie"),
    'ph.log_title': _w("{stat} per game", "{stat} na mecz"), 'ph.vs_line': _w(" vs the line", " wobec linii"),
    'ph.log_caption': _w("Bars: each game (green over / red under the line; light = preseason). Orange: 5- and 10-game "
                         "averages. Grey: minutes (right axis).",
                         "Słupki: każdy mecz (zielony powyżej / czerwony poniżej linii; jasny = przedsezon). "
                         "Pomarańczowe: średnie z 5 i 10 meczów. Szare: minuty (prawa oś)."),
    'ph.dist_title': _w("How often each {stat} result happened", "Jak często padał każdy wynik {stat}"),
    'ph.percentiles': _w("**Percentiles**", "**Percentyle**"),
    'ph.pct.10': _w("10th", "10."), 'ph.pct.30': _w("30th", "30."), 'ph.pct.50': _w("median", "mediana"),
    'ph.pct.70': _w("70th", "70."), 'ph.pct.90': _w("90th", "90."),
    'ph.pct_caption': _w("A line below the 30th or above the 70th percentile looks unusually low or high for this "
                         "player.", "Linia poniżej 30. lub powyżej 70. percentyla jest jak na tego zawodnika "
                                    "nietypowo niska lub wysoka."),
    'ph.pct_line': _w(" This line sits at the {pct:.0f}th.", " Ta linia wypada na {pct:.0f}. percentylu."),
    'ph.trend_caption': _w("Every stored season of the chosen game types, regardless of the scope.",
                           "Wszystkie zapisane sezony wybranych rodzajów meczów, niezależnie od zakresu."),
    'ph.season_hover': _w("%{x}: %{y:.1f} in %{customdata[0]} games, %{customdata[1]:.1f} min",
                          "%{x}: %{y:.1f} w %{customdata[0]} meczach, %{customdata[1]:.1f} min"),
    'ph.line_label': _w("line {line:g}", "linia {line:g}"),
    'ph.per_season': _w("{stat} per season", "{stat} na sezon"), 'ph.per_month': _w("{stat} per month",
                                                                                   "{stat} na miesiąc"),
    'ph.month_hover': _w("%{x|%b %Y}: %{y:.1f} in %{customdata} games", "%{x|%b %Y}: %{y:.1f} w %{customdata} "
                                                                       "meczach"),
    'ph.overall': _w("overall", "ogółem"), 'ph.by_situation': _w("{stat} by situation", "{stat} wg sytuacji"),
    'ph.games_short': _w("g", "m"),
    'ph.opp_hover': _w("vs %{x}: %{y:.1f} in %{customdata} games", "z %{x}: %{y:.1f} w %{customdata} meczach"),
    'ph.career_avg': _w("career avg", "średnia kariery"),
    'ph.opp_title': _w("{stat} against each opponent (every stored season)",
                       "{stat} przeciw każdemu rywalowi (wszystkie zapisane sezony)"),
    'ph.opp_caption': _w("Green = above the player's average against everyone. Few games against a team make its bar "
                         "noisy.", "Zielony = powyżej średniej zawodnika przeciw wszystkim. Mało meczów z drużyną = "
                                   "niepewny słupek."),
    'ph.no_mates': _w("No teammates in the stored games.", "Brak kolegów z drużyny w zapisanych meczach."),
    'ph.mate': _w("Teammate", "Kolega"), 'ph.together': _w("{name} – {n} games together",
                                                           "{name} – {n} {n|wspólny mecz|wspólne mecze|wspólnych "
                                                           "meczów}"),
    'ph.never_missed': _w("The teammate didn't miss any of the player's games while on the team, so there's nothing "
                          "to compare.", "Kolega nie opuścił żadnego meczu zawodnika, gdy był w drużynie, więc nie ma "
                                         "czego porównać."),
    'ph.mates_caption': _w("Every stored season; only games from the teammate's first to last game on the team count. "
                           "The full matrix for a whole rotation is in Lineup lab.",
                           "Wszystkie zapisane sezony; liczą się tylko mecze od pierwszego do ostatniego meczu kolegi "
                           "w drużynie. Pełna tabela dla całej rotacji jest w Laboratorium składów."),

    # Team history
    'th.title': _w("Team history", "Historia drużyny"),
    'th.purpose': _w("One team's results, how its ratings moved, what its defense allows to each position and who "
                     "plays.", "Wyniki jednej drużyny, zmiany jej ratingów, na co pozwala jej obrona na każdej "
                               "pozycji i kto gra."),
    'th.none': _w("No games in the scope.", "Brak meczów w zakresie."),
    'th.team': _w("Team", "Drużyna"), 'th.team_help': _w("Teams playing in the next 36 hours are listed first",
                                                         "Drużyny grające w najbliższych 36 godzinach są pierwsze"),
    'th.no_team': _w("{team} has no games in the scope.", "{team} nie ma meczów w zakresie."),
    'th.kpi.record': _w("Record", "Bilans"), 'th.kpi.home': _w("home {record}", "u siebie {record}"),
    'th.kpi.off': _w("Attack rating", "Rating ataku"), 'th.kpi.off_help': _w("Points scored per 100 possessions",
                                                                          "Punkty zdobyte na 100 posiadań"),
    'th.kpi.rank': _w("#{rank} of {n}", "{rank}. z {n}"),
    'th.kpi.def': _w("Defense rating", "Rating obrony"),
    'th.kpi.def_help': _w("Points allowed per 100 possessions (lower is better)",
                          "Punkty stracone na 100 posiadań (mniej = lepiej)"),
    'th.kpi.net': _w("Net rating", "Bilans ratingów"), 'th.kpi.net_rank': _w("#{rank}", "{rank}."),
    'th.kpi.pace': _w("Pace", "Tempo"), 'th.kpi.pace_rank': _w("#{rank} fastest", "{rank}. najszybsze"),
    'th.kpi.pace_help': _w("Possessions per game", "Posiadania na mecz"),
    'th.tab.results': _w("Results", "Wyniki"), 'th.tab.trend': _w("Ratings trend", "Trend ratingów"),
    'th.tab.defense': _w("Defense vs position", "Obrona wg pozycji"), 'th.tab.players': _w("Players", "Zawodnicy"),
    'th.margin_title': _w("Margin per game (green = win)", "Różnica punktów na mecz (zielony = wygrana)"),
    'th.points': _w("points", "punkty"),
    'th.window': _w("Rolling window", "Okno średniej"), 'th.window_value': _w("{n} games", "{n} meczów"),
    'th.off_line': _w("Attack (scored)", "Atak (zdobyte)"), 'th.def_line': _w("Defense (allowed)", "Obrona (stracone)"),
    'th.league_avg': _w("league avg", "średnia ligi"),
    'th.rtg_title': _w("Points per 100 possessions, {n}-game average", "Punkty na 100 posiadań, średnia z {n} meczów"),
    'th.pace_title': _w("Pace (possessions per game), {n}-game average",
                        "Tempo (posiadania na mecz), średnia z {n} meczów"),
    'th.trend_caption': _w("The green line above the red one = outscoring opponents. Possessions are estimated as "
                           "FGA + 0.44·FTA + TO − OREB.",
                           "Zielona linia nad czerwoną = drużyna zdobywa więcej niż traci. Posiadania szacowane jako "
                           "FGA + 0.44·FTA + TO − OREB."),
    'th.stat_allowed': _w("Stat allowed", "Statystyka rywali"),
    'th.def_title': _w("{stat} {team} allows vs the average defense (green = gives up more: good for Overs against "
                       "them)", "{stat}, na które {team} pozwala, wobec przeciętnej obrony (zielony = pozwala więcej: "
                                "dobrze dla Powyżej przeciw nim)"),
    'th.vs_league': _w("% vs league", "% wobec ligi"),
    'th.no_players': _w("No players in the scope.", "Brak zawodników w zakresie."),
    'th.open_lab': _w("Open {team} in Lineup lab", "Otwórz {team} w Laboratorium składów"),

    # Lineup lab
    'll.title': _w("Lineup lab", "Laboratorium składów"),
    'll.purpose': _w("How each player's numbers change when a teammate doesn't play, for any team, with or without an "
                     "expected lineup; then an estimate for a lineup you pick.",
                     "Jak zmieniają się liczby każdego zawodnika, gdy kolega nie gra, dla dowolnej drużyny, z "
                     "przewidywanym składem lub bez; potem szacunek dla wybranego składu."),
    'll.source.rotowire': _w("📋 RotoWire tonight", "📋 RotoWire dziś"), 'll.source.last': _w("Last game",
                                                                                            "Ostatni mecz"),
    'll.source.frequent': _w("Most frequent (last 10)", "Najczęstszy (ost. 10)"),
    'll.source.custom': _w("Custom", "Własny"),
    'll.team': _w("Team", "Drużyna"), 'll.team_help': _w("Teams playing today (Superbet or RotoWire) are listed first",
                                                         "Drużyny grające dziś (Superbet lub RotoWire) są pierwsze"),
    'll.stat': _w("Stat", "Statystyka"),
    'll.all_seasons': _w("Use every stored season", "Użyj wszystkich zapisanych sezonów"),
    'll.all_seasons_help': _w("Early in the season there are too few games without anyone. Earlier seasons only count "
                              "while both players were on the team.",
                              "Na początku sezonu jest za mało meczów bez danego zawodnika. Wcześniejsze sezony liczą "
                              "się tylko wtedy, gdy obaj byli w drużynie."),
    'll.settings': _w("Settings", "Ustawienia"),
    'll.min_games': _w("Rotation: min games", "Rotacja: min. meczów"),
    'll.min_games_help': _w("Fewer games for this team = left out", "Mniej meczów w tej drużynie = pominięty"),
    'll.min_minutes': _w("Rotation: min minutes", "Rotacja: min. minut"),
    'll.min_minutes_help': _w("Lower average = left out", "Niższa średnia = pominięty"),
    'll.min_without': _w("Table: min games without", "Tabela: min. meczów bez"),
    'll.min_without_help': _w("Cells based on fewer games without the teammate stay empty",
                              "Komórki z mniejszą liczbą meczów bez kolegi zostają puste"),
    'll.shrink': _w("Estimate: shrink", "Szacunek: ostrożność"),
    'll.shrink_help': _w("Each change is weighted by n / (n + this), n = games without that teammate",
                         "Każda zmiana waży n / (n + ta liczba), n = mecze bez danego kolegi"),
    'll.no_rotation': _w("No players with {games}+ games and {minutes}+ minutes for {team} in these games.",
                         "Brak zawodników z {games}+ meczami i {minutes}+ minutami w {team} w tych meczach."),
    'll.lineup_from': _w("Lineup from", "Skład z"),
    'll.lineup_from_help': _w("RotoWire's expected starters and out players when it lists the team today; otherwise "
                              "the last game's starters or the most frequent starters of the last 10 games",
                              "Przewidywana piątka i nieobecni z RotoWire, gdy podaje drużynę dziś; inaczej piątka z "
                              "ostatniego meczu lub najczęstsza z ostatnich 10 meczów"),
    'll.no_rotowire': _w("📋 RotoWire lists no lineup for {team} today, so the lineup comes from the stored games. "
                         "Pick who's out yourself.", "📋 RotoWire nie podaje dziś składu {team}, więc skład pochodzi z "
                                                     "zapisanych meczów. Wybierz nieobecnych samodzielnie."),
    'll.rotowire': _w("📋 RotoWire: **{status}** lineup. May not play: {names}",
                      "📋 RotoWire: skład **{status}**. Może nie zagrać: {names}"),
    'll.starting': _w("Starting five", "Pierwsza piątka"),
    'll.starting_help': _w("Used for the exact-match games: team games where all five started",
                           "Używana do dokładnego dopasowania: mecze, w których zaczęła cała piątka"),
    'll.out': _w("Out", "Nieobecni"),
    'll.out_help': _w("Missing players: their with / without changes are added to everyone else's estimate",
                      "Brakujący zawodnicy: ich zmiany z / bez są dodawane do szacunku pozostałych"),
    'll.pick_five': _w("Pick 5 starters ({n} selected).", "Wybierz 5 zawodników piątki (wybrano {n})."),
    'll.matrix': _w("With / without table · {stat}", "Tabela z / bez · {stat}"),
    'll.relative': _w("Show as % of the player's usual average", "Pokaż jako % zwykłej średniej zawodnika"),
    'll.out_mark': _w(" (OUT)", " (NIE GRA)"),
    'll.hover': _w("{row} when {col} is out<br>with: {with_:.1f} in {n_with:.0f} games<br>without: {without:.1f} in "
                   "{n_without:.0f} games", "{row}, gdy {col} nie gra<br>z nim: {with_:.1f} w {n_with:.0f} meczach<br>"
                                            "bez niego: {without:.1f} w {n_without:.0f} meczach"),
    'll.never': _w("{col} never missed a game {row} played", "{col} nie opuścił żadnego meczu, w którym grał {row}"),
    'll.colorbar': _w("change", "zmiana"), 'll.colorbar_pct': _w("% change", "% zmiany"),
    'll.matrix_caption': _w("Each cell: the row player's {stat} when the column player is **out** minus when he plays "
                            "(green = more). ★ = starting five. Empty: fewer than {n} games without that player. Only "
                            "games inside the column player's time on the team count. Hover a cell for the averages "
                            "and games behind it.",
                            "Każda komórka: {stat} zawodnika z wiersza, gdy zawodnik z kolumny **nie gra**, minus gdy "
                            "gra (zielony = więcej). ★ = pierwsza piątka. Puste: mniej niż {n} meczów bez tego "
                            "zawodnika. Liczą się tylko mecze z okresu, gdy zawodnik z kolumny był w drużynie. Najedź "
                            "na komórkę, żeby zobaczyć średnie i mecze."),
    'll.estimate': _w("Estimate for this lineup", "Szacunek dla tego składu"),
    'll.nobody_out': _w("Nobody is out, so every estimate equals the usual average. Tick Out to see how the others "
                        "shift.", "Nikt nie jest nieobecny, więc każdy szacunek równa się zwykłej średniej. Zaznacz "
                                  "'nie gra', żeby zobaczyć, jak zmieniają się pozostali."),
    'll.calculated': _w(" — calculated from the scraped games", " — wyliczone z pobranych meczów"),
    'll.scenario_caption': _w("Tick **out** to take a player out, untick to bring him back. estimate = usual + each "
                              "out player's change, shrunk when based on few games; exact match = the average in "
                              "games with exactly this situation.",
                              "Zaznacz **nie gra**, żeby wyłączyć zawodnika, odznacz, żeby przywrócić. szacunek = "
                              "zwykle + zmiana od każdego nieobecnego, osłabiona przy małej liczbie meczów; dokładne "
                              "dopasowanie = średnia z meczów z dokładnie taką sytuacją."),
    'll.open_player': _w("Open a player's history...", "Otwórz historię zawodnika..."),
    'll.open': _w("Open in Player history", "Otwórz w Historii zawodnika"),
    'll.matrix_spinner': _w("Calculating with / without for every pair...", "Liczę z / bez dla każdej pary..."),

    # Backtest 2022/23 (core/backtest_view.py)
    'bt.title': _w("Backtest 2022/23", "Test wsteczny 2022/23"),
    'bt.purpose': _w("Today's props model on Unibet's 2022/23 player lines: how it would have done, a strategy tester "
                     "for any slice of those lines, and how each player's lines resolved.",
                     "Dzisiejszy model zawodników na liniach Unibetu z sezonu 2022/23: jak by sobie poradził, tester "
                     "strategii dla dowolnego wycinka tych linii i jak rozstrzygały się linie każdego zawodnika."),
    'bt.view.summary': _w("Summary", "Podsumowanie"), 'bt.view.tester': _w("Strategy tester", "Tester strategii"),
    'bt.view.player': _w("Player", "Zawodnik"), 'bt.view.calibration': _w("Calibration", "Kalibracja"),
    'bt.bet.model': _w("Model pick", "Typ modelu"), 'bt.bet.average': _w("Toward the season average",
                                                                         "W stronę średniej sezonu"),
    'bt.bet.under': _w("Always Under", "Zawsze Poniżej"), 'bt.bet.over': _w("Always Over", "Zawsze Powyżej"),
    'bt.no_bets': _w("No decided bets.", "Brak rozstrzygniętych zakładów."),
    'bt.kpi.bets': _w("Bets", "Zakłady"), 'bt.kpi.pushes': _w("{n} pushes", "{n} {n|zwrot|zwroty|zwrotów}"),
    'bt.kpi.hit': _w("Won", "Wygrane"), 'bt.kpi.needs': _w("needs {be:.1f}%", "potrzeba {be:.1f}%"),
    'bt.kpi.hit_help': _w("95% range {low:.1f}–{high:.1f}%. Needs = break-even at the odds (the average of 1 / odds)",
                          "95% przedział {low:.1f}–{high:.1f}%. Potrzeba = próg opłacalności przy tych kursach "
                          "(średnia z 1 / kurs)"),
    'bt.kpi.profit': _w("Profit", "Zysk"), 'bt.kpi.profit_help': _w("Units, 1 unit on every bet",
                                                                    "Jednostki, 1 jednostka na każdy zakład"),
    'bt.kpi.roi': _w("Profit per 100", "Zysk na 100"),
    'bt.curve_hover': _w("%{x|%b %d}: total %{y:+.1f} u<br>%{customdata[0]} bets, %{customdata[1]:+.1f} u that day",
                         "%{x|%b %d}: łącznie %{y:+.1f} j.<br>%{customdata[0]} zakładów, %{customdata[1]:+.1f} j. "
                         "tego dnia"),
    'bt.units': _w("units", "jednostki"),
    'bt.lines_caption': _w("{n} main lines of players with {games}+ games, {dates} dates.",
                           "{n} głównych linii zawodników z {games}+ meczami, {dates} dni."),
    'bt.kpi.picks_hit': _w("Model picks: won", "Typy modelu: wygrane"),
    'bt.kpi.picks_hit_help': _w("Every line's model pick; break-even at these odds is about 52.5%",
                                "Typ modelu na każdej linii; próg opłacalności przy tych kursach to ok. 52.5%"),
    'bt.kpi.picks_roi': _w("Model picks: profit per 100", "Typy modelu: zysk na 100"),
    'bt.kpi.top_roi': _w("4★ picks: profit per 100", "Typy 4★: zysk na 100"),
    'bt.kpi.top_help': _w("The model's pick on each night's 4★ lines: the best of that night, not a profitable bet",
                          "Typ modelu na liniach 4★ każdej nocy: najlepsze tej nocy, nie: opłacalne"),
    'bt.kpi.n_bets': _w("{n} bets", "{n} {n|zakład|zakłady|zakładów}"),
    'bt.kpi.under_roi': _w("Always Under: profit per 100", "Zawsze Poniżej: zysk na 100"),
    'bt.kpi.under_help': _w("The simplest baseline", "Najprostszy punkt odniesienia"),
    'bt.strategies': _w("**Strategies on the same lines**", "**Strategie na tych samych liniach**"),
    'bt.cal_title': _w("Model chance vs how often the pick won", "Szansa modelu a jak często typ wygrywał"),
    'bt.by': _w("**Model pick – {what}**", "**Typ modelu – {what}**"),
    'bt.by.stars': _w("by stars", "wg gwiazdek"), 'bt.by.edge': _w("by edge (pp)", "wg przewagi (pp)"),
    'bt.by.stat': _w("by stat", "wg statystyki"), 'bt.by.month': _w("by month", "wg miesiąca"),
    'bt.tester_caption': _w("Choose which lines to bet and how; every number below is for exactly that selection, 1 "
                            "unit per bet at Unibet's odds.", "Wybierz, które linie grać i jak; każda liczba poniżej "
                                                              "dotyczy dokładnie tego wyboru, 1 jednostka na zakład "
                                                              "po kursach Unibetu."),
    'bt.dates': _w("Game dates", "Daty meczów"), 'bt.players': _w("Players", "Zawodnicy"),
    'bt.all_players': _w("All players", "Wszyscy zawodnicy"), 'bt.stats': _w("Stats", "Statystyki"),
    'bt.none_all': _w("None picked = all", "Nic nie wybrane = wszystkie"),
    'bt.stars': _w("Stars", "Gwiazdki"),
    'bt.stars_help': _w("The line's stars that night, by the rules of tonight's: its place among the night's main "
                        "lines by the model's expected return, whatever you bet on. None picked = all",
                        "Gwiazdki linii tej nocy, według zasad dzisiejszych: miejsce wśród głównych linii nocy wg "
                        "oczekiwanego zwrotu modelu, niezależnie od tego, co grasz. Nic nie wybrane = wszystkie"),
    'bt.unrated': _w("no rating", "bez oceny"),
    'bt.green_is_admission': _w("🟢 below is the earlier name of the admission threshold: a 5★ needs one that held "
                                "up on nights not used to choose it, and none has yet.",
                                "🟢 poniżej to dawna nazwa progu dopuszczenia: 5★ wymaga progu sprawdzonego na "
                                "nocach, których nie użyto do jego wyboru, a takiego jeszcze nie ma."),
    'bt.bet_on': _w("Strategy tested", "Testowana strategia"), 'bt.side': _w("Side", "Strona"),
    'bt.side_help': _w("Only the bets on this side; none picked = both", "Tylko zakłady na tę stronę; nic = obie"),
    'bt.more': _w("More filters", "Więcej filtrów"),
    'bt.use_edge': _w("Minimum model edge", "Minimalna przewaga modelu"),
    'bt.use_edge_help': _w("Only lines where the model's edge (for its own pick) is at least this many pp",
                           "Tylko linie, gdzie przewaga modelu (dla jego typu) wynosi co najmniej tyle pp"),
    'bt.edge': _w("Edge (pp)", "Przewaga (pp)"), 'bt.min_games': _w("Min games before the line",
                                                                    "Min. meczów przed linią"),
    'bt.main': _w("Main lines only", "Tylko główne linie"),
    'bt.main_help': _w("The most balanced line per player, stat and game; off = also alternative lines",
                       "Najbardziej wyrównana linia na zawodnika, statystykę i mecz; wyłączone = także linie "
                       "alternatywne"),
    'bt.filters': _w("Filters: {list}", "Filtry: {list}"), 'bt.f.edge': _w("edge ≥ {edge:g}", "przewaga ≥ {edge:g}"),
    'bt.f.games': _w("{n}+ games", "{n}+ meczów"), 'bt.f.main': _w("main lines", "główne linie"),
    'bt.no_match': _w("No bets match these filters.", "Żaden zakład nie pasuje do filtrów."),
    'bt.curve': _w("Cumulative profit", "Łączny zysk"),
    'bt.by_stat': _w("**By stat**", "**Wg statystyki**"), 'bt.by_side': _w("**By side**", "**Wg strony**"),
    'bt.the_bets': _w("**The {n} bets**", "**{n} {n|zakład|zakłady|zakładów}**"),
    'bt.player': _w("Player", "Zawodnik"), 'bt.player_lines': _w("{name} ({n} lines)", "{name} ({n} "
                                                                                       "{n|linia|linie|linii})"),
    'bt.player_pick': _w("Type a name... (most lines first)", "Wpisz nazwisko... (najwięcej linii najpierw)"),
    'bt.pick_player': _w("Pick a player to see how their 2022/23 lines resolved and how the model did on them.",
                         "Wybierz zawodnika, żeby zobaczyć, jak rozstrzygały się jego linie 2022/23 i jak radził "
                         "sobie na nich model."),
    'bt.kpi.lines': _w("Lines", "Linie"), 'bt.kpi.games': _w("{n} games", "{n} {n|mecz|mecze|meczów}"),
    'bt.kpi.over': _w("Went over", "Powyżej linii"),
    'bt.kpi.over_help': _w("How often the result beat the line (pushes left out)",
                           "Jak często wynik przebił linię (zwroty pominięte)"),
    'bt.kpi.miss': _w("Result − line", "Wynik − linia"),
    'bt.kpi.miss_help': _w("Average miss: + = the lines were set too low for this player",
                           "Średni błąd: + = linie były za niskie dla tego zawodnika"),
    'bt.kpi.picks_profit': _w("Model picks: profit", "Typy modelu: zysk"),
    'bt.stat': _w("Stat", "Statystyka"),
    'bt.line': _w("line", "linia"), 'bt.avg_before': _w("season average before", "średnia sezonu przed"),
    'bt.result': _w("result", "wynik"),
    'bt.player_hover': _w("%{x|%b %d}: %{y} vs line %{customdata[0]}<br>model pick %{customdata[1]} %{customdata[2]}",
                          "%{x|%b %d}: %{y} wobec linii %{customdata[0]}<br>typ modelu %{customdata[1]} "
                          "%{customdata[2]}"),
    'bt.player_chart': _w("{name}: {stat} lines and results (green = over the line)",
                          "{name}: linie i wyniki {stat} (zielone = powyżej linii)"),
    'bt.resolved': _w("**How the lines resolved, by stat**", "**Jak rozstrzygały się linie, wg statystyki**"),
    'bt.model_on_them': _w("**The model's picks on them**", "**Typy modelu na nich**"),
    'bt.every_pick': _w("Betting every model pick on {name}", "Granie każdego typu modelu na {name}"),
    'bt.every_line': _w("**Every line**", "**Każda linia**"),
    'bt.no_file': _w("No backtest yet. Run `python -m backtest.run` (about 10 minutes) to price Unibet's 2022/23 lines "
                     "with today's model.", "Brak testu wstecznego. Uruchom `python -m backtest.run` (ok. 10 minut), "
                                            "żeby wycenić linie Unibetu 2022/23 dzisiejszym modelem."),
    'bt.lineup': _w("Tonight's lineup", "Dzisiejszy skład"),
    'bt.lineup.none': _w("Not known (no RotoWire)", "Nieznany (bez RotoWire)"),
    'bt.lineup.absences': _w("Perfectly known (upper bound)", "Znany idealnie (górna granica)"),
    'bt.lineup_help': _w("What the model knew about who's out: nothing, or exactly who didn't play (an upper bound for "
                         "RotoWire's value)", "Co model wiedział o nieobecnych: nic albo dokładnie, kto nie zagrał "
                                              "(górna granica wartości RotoWire)"),
    'bt.view': _w("View", "Widok"),
    'bt.caption': _w("Unibet's 2022/23 player lines, each priced by today's props model from the games before its date "
                     "only. No historical game odds, so the implied-team-total factor is off. Details: "
                     "data/backtest/2022_summary.md.",
                     "Linie Unibetu z sezonu 2022/23, każda wyceniona dzisiejszym modelem tylko z meczów sprzed jej "
                     "daty. Brak historycznych kursów na mecze, więc czynnik oczekiwanych punktów drużyny jest "
                     "wyłączony. Szczegóły: data/backtest/2022_summary.md."),
    'bt.in_sample': _w(" Our chance, edges and signals are calibrated with coefficients fitted on this same season, so "
                       "these numbers are in-sample: the honest check on unseen games is under Calibration.",
                       " Nasza szansa, przewagi i sygnały są skalibrowane współczynnikami dopasowanymi na tym samym "
                       "sezonie, więc te liczby są 'w próbie': rzetelny test na nieznanych meczach jest w "
                       "Kalibracji."),
    'bt.no_calibration': _w("No calibration yet. Run `python -m backtest.calibrate` after the backtest.",
                            "Brak kalibracji. Uruchom `python -m backtest.calibrate` po teście wstecznym."),
    'bt.report_english': _w("The report below is technical and in English.",
                            "Raport poniżej jest techniczny i po angielsku."),

    # every page: header, scope, sidebar, empty states (core/ui.py, core/state.py, core/freshness.py, schedule.py)
    'scope.button': _w("Scope: {label}", "Zakres: {label}"),
    'scope.help': _w("Which seasons and game types the numbers on every page use",
                     "Z jakich sezonów i rodzajów meczów pochodzą liczby na każdej stronie"),
    'scope.seasons': _w("Seasons", "Sezony"),
    'scope.seasons_help': _w("Games from these seasons feed the averages, hit rates and the model",
                             "Mecze z tych sezonów zasilają średnie, skuteczności i model"),
    'scope.types': _w("Game types", "Rodzaje meczów"),
    'scope.types_help': _w("Preseason is left out by default (starters play short minutes). Players with fewer than 10 "
                           "games get their latest games of last season added",
                           "Przedsezon jest domyślnie pominięty (podstawowi grają krótko). Zawodnikom z mniej niż 10 "
                           "meczami dodawane są ostatnie mecze z zeszłego sezonu"),
    'scope.every_page': _w("Applies to every page.", "Dotyczy każdej strony."),
    'scope.all_types': _w("all game types", "wszystkie rodzaje meczów"),
    'type.pre': _w("Preseason", "Przedsezon"), 'type.regular': _w("Regular season", "Sezon zasadniczy"),
    'type.playin': _w("Play-in", "Baraże"), 'type.post': _w("Playoffs", "Play-off"),
    'side.freshness': _w("**Data freshness**", "**Świeżość danych**"),
    'side.stats': _w("📊 ESPN stats", "📊 Statystyki ESPN"), 'side.superbet': _w("💰 Superbet odds", "💰 Kursy Superbetu"),
    'side.rotowire': _w("📋 RotoWire lineups", "📋 Składy RotoWire"),
    'side.update': _w("Update in the Data center", "Zaktualizuj w Centrum danych"),
    'ui.fetch_new': _w("Fetch new offers in the Data center", "Pobierz nowe oferty w Centrum danych"),
    'ui.last_night': _w("See how the last night's lines resolved", "Zobacz, jak rozstrzygnęły się linie z wczoraj"),
    'ui.open_data': _w("Open the Data center", "Otwórz Centrum danych"),
    'fresh.just_now': _w("just now", "przed chwilą"), 'fresh.min_ago': _w("{n} min ago", "{n} min temu"),
    'fresh.h_ago': _w("{n} h ago", "{n} h temu"), 'fresh.days_ago': _w("{n} days ago",
                                                                      "{n} {n|dzień|dni|dni} temu"),
    'fresh.no_games': _w("no games stored", "brak zapisanych meczów"),
    'fresh.run_update': _w("Run the stats update", "Uruchom aktualizację statystyk"),
    'fresh.through': _w("through {day}", "do {day}"),
    'fresh.complete': _w("Every finished game is stored", "Każdy zakończony mecz jest zapisany"),
    'fresh.behind': _w("{n} {n|day|days|days} of games missing: run the stats update",
                       "Brakuje meczów z {n} {n|dnia|dni|dni}: uruchom aktualizację statystyk"),
    'fresh.not_fetched': _w("not fetched", "nie pobrano"),
    'fresh.none_yet': _w("No {what} yet: fetch them in the Data center", "Brak {what}: pobierz je w Centrum danych"),
    'fresh.fetched': _w("fetched {age}", "pobrano {age}"),
    'fresh.fetched_detail': _w("{count}fetched {when}", "{count}pobrano {when}"),
    'fresh.count': _w("{n} {what}, ", "{n} {what}, "),
    'fresh.snapshot': _w("snapshot, {age}", "zapis, {age}"),
    'fresh.snapshot_count': _w("{n} {what} from the snapshot", "{n} {what} z zapisu"),
    'fresh.snapshot_plain': _w("Snapshot", "Zapis"),
    'fresh.saved': _w("{count} saved {when}", "{count} zapisano {when}"),
    'fresh.unreachable': _w(": the site couldn't be reached", ": strona była niedostępna"),
    'fresh.lines': _w("lines", "linii"), 'fresh.players': _w("players", "zawodników"),
    'offers.none_saved': _w("**No Superbet offers yet.** Nothing has been fetched: fetch today's offers manually.",
                            "**Brak ofert Superbetu.** Nic jeszcze nie pobrano: pobierz dzisiejsze oferty ręcznie."),
    'offers.all_started': _w("**No Superbet bets available right now.** Every game of the last fetch ({when}: {lines} "
                             "player lines on {games} games, night of {nights}) has tipped off. Fetch new offers "
                             "manually; the last night's lines can be checked against the results.",
                             "**Brak dostępnych zakładów Superbetu.** Wszystkie mecze z ostatniego pobrania ({when}: "
                             "{lines} linii zawodników w {games} {games|meczu|meczach|meczach}, wieczór {nights}) już "
                             "się zaczęły. Pobierz nowe oferty ręcznie; linie z ostatniego wieczoru można sprawdzić "
                             "z wynikami."),
    'offers.pending': _w(" Their results are pending until the stats are updated with that night's games.",
                         " Ich wyniki będą dostępne po aktualizacji statystyk o mecze z tamtego wieczoru."),

    # Data center
    'dc.title': _w("Data center", "Centrum danych"),
    'dc.purpose': _w("Fetch fresh stats, odds and lineups, and check that the stored data is complete. Every other page "
                     "reads what's here.", "Pobierz świeże statystyki, kursy i składy oraz sprawdź, czy zapisane dane "
                                           "są kompletne. Wszystkie inne strony czytają to, co jest tutaj."),
    'dc.routine': _w("**Morning routine** · stores last night's games from ESPN, then saves a snapshot of Superbet's "
                     "lines and RotoWire's lineups (needed for line movement and the Results page). About a minute.",
                     "**Poranna rutyna** · zapisuje wczorajsze mecze z ESPN, potem zapis linii Superbetu i składów "
                     "RotoWire (potrzebne do ruchu linii i strony Wyniki). Około minuty."),
    'dc.run_both': _w("Run both", "Uruchom oba"),
    'dc.cooldown': _w("Superbet was contacted less than {min} minutes ago; try again in {wait} min.",
                      "Superbet był odpytywany mniej niż {min} minut temu; spróbuj ponownie za {wait} min."),
    'dc.stats_only': _w(" Updating the stats only.", " Aktualizuję tylko statystyki."),
    'dc.fetching': _w("Fetching and saving Superbet's offers...", "Pobieram i zapisuję oferty Superbetu..."),
    'dc.fetch_failed': _w("Superbet couldn't be fetched: {error}. The pages keep using the previous fetch.",
                          "Nie udało się pobrać Superbetu: {error}. Strony używają poprzedniego pobrania."),
    'dc.fetched': _w("Fetched and saved Superbet's offers", "Pobrano i zapisano oferty Superbetu"),
    'dc.last_stats': _w("{ok} Last stats update from the dashboard {when}: {summary}",
                        "{ok} Ostatnia aktualizacja statystyk z dashboardu {when}: {summary}"),
    'dc.no_output': _w("(no output)", "(brak komunikatu)"),
    'dc.how.fetch': _w("Fetch & save / Fetch from Superbet", "Pobierz i zapisz / Pobierz z Superbetu"),
    'dc.how.snapshot': _w("snapshot run", "zapis oferty"),
    'dc.no_fetch': _w("No Superbet fetch saved yet.", "Nie zapisano jeszcze żadnego pobrania Superbetu."),
    'dc.last_fetch': _w("✅ Last saved fetch {when}: {lines} player lines, {games} games",
                        "✅ Ostatnie zapisane pobranie {when}: {lines} linii zawodników, {games} "
                        "{games|mecz|mecze|meczów}"),
    'dc.later_failed': _w("❌ Later attempt {when} ({how}) failed: {summary}",
                          "❌ Późniejsza próba {when} ({how}) nie powiodła się: {summary}"),
    'dc.no_lineups': _w("No RotoWire lineups saved yet.", "Nie zapisano jeszcze składów RotoWire."),
    'dc.last_lineups': _w("✅ Last saved lineups {when}: {n} players ({days}). Every fetch that changed something is "
                          "saved.", "✅ Ostatnie zapisane składy {when}: {n} zawodników ({days}). Każde pobranie, "
                                    "które coś zmieniło, jest zapisywane."),
    'dc.stats_card': _w("#### 📊 ESPN stats", "#### 📊 Statystyki ESPN"),
    'dc.games_season': _w("Games this season", "Mecze w tym sezonie"), 'dc.last_game': _w("Last game",
                                                                                          "Ostatni mecz"),
    'dc.update': _w("Update {season}", "Aktualizuj {season}"),
    'dc.update_help': _w("python -m espn_scraper: adds every finished game that isn't stored yet. Safe to run often.",
                         "python -m espn_scraper: dodaje każdy zakończony mecz, którego jeszcze nie ma. Można "
                         "uruchamiać często."),
    'dc.other': _w("Other seasons, dates or one game", "Inne sezony, daty lub jeden mecz"),
    'dc.season': _w("Season", "Sezon"),
    'dc.how.new': _w("New games", "Nowe mecze"), 'dc.how.range': _w("A date range", "Zakres dat"),
    'dc.how.one': _w("One game", "Jeden mecz"), 'dc.how.rebuild': _w("Rebuild the season", "Odbuduj sezon"),
    'dc.from': _w("From", "Od"), 'dc.to': _w("To", "Do"), 'dc.game_id': _w("ESPN game id", "Id meczu ESPN"),
    'dc.game_id_help': _w("Re-scrapes the game and replaces what's stored for it",
                          "Pobiera mecz ponownie i zastępuje zapisane dane"),
    'dc.rebuild_confirm': _w("Yes, delete {season} and scrape it again (takes long)",
                             "Tak, usuń {season} i pobierz ponownie (trwa długo)"),
    'dc.run': _w("Run", "Uruchom"),
    'dc.superbet_card': _w("#### 💰 Superbet odds", "#### 💰 Kursy Superbetu"),
    'dc.lines': _w("Player lines", "Linie zawodników"),
    'dc.lines_help': _w("Over / Under lines on players in the next 36 hours (none in preseason)",
                        "Linie Powyżej / Poniżej na zawodników w najbliższych 36 godzinach (brak w przedsezonie)"),
    'dc.games': _w("Games", "Mecze"),
    'dc.games_help': _w("Games with winner / handicap / total bets in the next 36 hours",
                        "Mecze z zakładami na zwycięzcę / handicap / sumę w najbliższych 36 godzinach"),
    'dc.superbet_caption': _w("Superbet blocks frequent requests: besides the scheduled fetches below, it's contacted "
                              "only when you press a button here (at most once per {min} minutes), slowly, with "
                              "pauses between requests. Every fetch is saved; the pages use the newest one until its "
                              "games tip off.",
                              "Superbet blokuje częste zapytania: poza pobieraniem według harmonogramu (niżej) jest "
                              "odpytywany tylko po naciśnięciu przycisku tutaj (najwyżej raz na {min} minut), powoli, "
                              "z przerwami między zapytaniami. Każde pobranie jest zapisywane; strony używają "
                              "najnowszego, dopóki jego mecze się nie zaczną."),
    'dc.schedule_card': _w("**⏱️ Scheduled fetches** (only while this dashboard runs)",
                           "**⏱️ Pobieranie według harmonogramu** (tylko gdy ten dashboard działa)"),
    'dc.schedule_how': _w("Every hour while a game is still to start, and 60, 40, 20, 10 and 5 minutes before each "
                          "tip-off, always with RotoWire. The odds are saved at every fetch (what changed), the "
                          "full priced snapshot every 2 hours and at T-60. Nothing is scheduled in the system: "
                          "closing the dashboard stops it.",
                          "Co godzinę, dopóki jakiś mecz się nie zaczął, oraz 60, 40, 20, 10 i 5 minut przed "
                          "każdym meczem, zawsze z RotoWire. Kursy są zapisywane przy każdym pobraniu (to, co się "
                          "zmieniło), pełny snapshot z wyceną co 2 godziny i w T-60. Nic nie jest planowane w "
                          "systemie: zamknięcie dashboardu kończy pobieranie."),
    'dc.schedule_switch': _w("Fetch on schedule", "Pobieraj według harmonogramu"),
    'dc.keep_awake': _w("Keep the computer awake", "Nie usypiaj komputera"),
    'dc.keep_awake_help': _w("Windows won't sleep while the scheduled fetches run (games are at night in Poland). "
                             "Released when the dashboard closes; nothing stays in the system settings.",
                             "Windows nie uśnie, dopóki działa pobieranie (mecze są u nas w nocy). Zwalniane po "
                             "zamknięciu dashboardu; nic nie zostaje w ustawieniach systemu."),
    'dc.schedule_state': _w("Status: **{state}** · next fetch {next} · {games} games listed",
                            "Stan: **{state}** · następne pobranie {next} · {games} meczów na liście"),
    'dc.schedule_last': _w("Last scheduled fetch {when}: {ok} {summary}",
                           "Ostatnie pobranie z harmonogramu {when}: {ok} {summary}"),
    'dc.schedule_budget': _w("Superbet requests today: {n} of {budget}", "Zapytania do Superbet dziś: {n} z {budget}"),
    'dc.schedule_blocked': _w("Superbet refused requests (403/429): no contact until {when}.",
                              "Superbet odmówił (403/429): żadnych zapytań do {when}."),
    'dc.schedule_closes': _w("Night of {night}: a valid closing price for {n} of {games} started games (read at most "
                             "{minutes} min before tip-off)",
                             "Noc {night}: ważne zamknięcie dla {n} z {games} rozpoczętych meczów (odczyt najpóźniej "
                             "{minutes} min przed startem)"),
    'dc.schedule_skipped': _w("{n} slots missed (the computer slept or the dashboard started late)",
                              "{n} terminów pominiętych (komputer spał albo dashboard ruszył później)"),
    'dc.state.waiting': _w("waiting", "czeka"), 'dc.state.starting': _w("starting", "startuje"),
    'dc.state.stopped': _w("off", "wyłączone"), 'dc.state.fetching': _w("fetching", "pobiera"),
    'dc.state.other': _w("another dashboard is fetching", "pobiera inny dashboard"),
    'dc.all_started': _w("Every game of the last fetch has tipped off: fetch again for new offers.",
                         "Wszystkie mecze z ostatniego pobrania już się zaczęły: pobierz ponownie po nowe oferty."),
    'dc.last_failed': _w("The last fetch failed: {error}", "Ostatnie pobranie nie powiodło się: {error}"),
    'dc.fetch': _w("Fetch & save", "Pobierz i zapisz"),
    'dc.again_in': _w("Possible again in {n} min", "Możliwe ponownie za {n} min"),
    'dc.fetch_help': _w("Fetch Superbet's offers and save them with our pick for every line (kept after a restart; "
                        "used for line movement and the Results page)",
                        "Pobierz oferty Superbetu i zapisz je z naszym typem dla każdej linii (zostają po restarcie; "
                        "używane do ruchu linii i strony Wyniki)"),
    'dc.snapshot': _w("Snapshot with lineups", "Zapis ze składami"),
    'dc.snapshot_help': _w("python daily_snapshot.py: the same as Fetch & save, plus RotoWire's lineups saved with it",
                           "python daily_snapshot.py: to samo co Pobierz i zapisz, plus zapis składów RotoWire"),
    'dc.rotowire_card': _w("#### 📋 RotoWire lineups", "#### 📋 Składy RotoWire"),
    'dc.teams': _w("Teams listed", "Podane drużyny"), 'dc.confirmed': _w("{n} confirmed", "{n} potwierdzonych"),
    'dc.teams_help': _w("Teams on RotoWire's lineups page today", "Drużyny na stronie składów RotoWire dziś"),
    'dc.may_not_play': _w("May not play", "Może nie zagrać"),
    'dc.may_not_play_help': _w("Players listed as out, doubtful or questionable",
                               "Zawodnicy oznaczeni jako nieobecni, wątpliwi lub niepewni"),
    'dc.rw_error': _w("RotoWire couldn't be read, showing the last snapshot. {error}",
                      "Nie udało się odczytać RotoWire, pokazuję ostatni zapis. {error}"),
    'dc.fetch_live': _w("Fetch live", "Pobierz teraz"),
    'dc.fetch_live_help': _w("Read RotoWire's lineups page again; saved when something changed",
                             "Odczytaj ponownie stronę składów RotoWire; zapisywane, gdy coś się zmieniło"),
    'dc.tomorrow': _w("Snapshot for tomorrow", "Zapis na jutro"),
    'dc.tomorrow_help': _w("python daily_snapshot.py --tomorrow: RotoWire's lineups for tomorrow's games",
                           "python daily_snapshot.py --tomorrow: składy RotoWire na jutrzejsze mecze"),
    'dc.rw_caption': _w("RotoWire's lineups are kept for 30 minutes, then fetched again when a page needs them, and "
                        "saved whenever they changed. To run the morning routine automatically, see the scheduled tasks "
                        "in the README.", "Składy RotoWire są przechowywane 30 minut, potem pobierane ponownie, gdy "
                                          "strona ich potrzebuje, i zapisywane, gdy się zmieniły. Aby poranna rutyna "
                                          "uruchamiała się sama, zobacz zaplanowane zadania w README."),
    'dc.reload': _w("Reload snapshots and lineups", "Wczytaj ponownie zapisy i składy"),
    'dc.reload_help': _w("Re-read the saved snapshots and fetch RotoWire again (doesn't contact Superbet)",
                         "Odczytaj ponownie zapisy i pobierz RotoWire (bez odpytywania Superbetu)"),
    'dc.tab.stored': _w("Stored data", "Zapisane dane"), 'dc.tab.runs': _w("Recent runs", "Ostatnie uruchomienia"),
    'dc.tab.names': _w("Name matching", "Dopasowanie nazwisk"), 'dc.tab.quality': _w("Data quality",
                                                                                     "Jakość danych"),
    'dc.no_runs': _w("No runs from the dashboard yet. They're logged to {path}.",
                     "Brak uruchomień z dashboardu. Są zapisywane w {path}."),
    'dc.unmatched': _w("{n} names from today's sources don't match a player in the game logs. Players without a game "
                       "yet (rookies, long injuries) are expected; for others add an entry to OVERRIDES in "
                       "name_resolver.py.", "{n} {n|nazwisko z dzisiejszych źródeł nie pasuje|nazwiska z dzisiejszych "
                                            "źródeł nie pasują|nazwisk z dzisiejszych źródeł nie pasuje} do zawodnika w "
                                            "meczach. Zawodnicy bez meczu (debiutanci, długie kontuzje) są oczekiwani; "
                                            "dla pozostałych dodaj wpis do OVERRIDES w name_resolver.py."),
    'dc.all_matched': _w("Every RotoWire and Superbet name matches a player in the game logs.",
                         "Każde nazwisko z RotoWire i Superbetu pasuje do zawodnika w meczach."),
    'dc.points_ok': _w("In every stored game the players' points add up to the team score.",
                       "W każdym zapisanym meczu punkty zawodników sumują się do wyniku drużyny."),
    'dc.points_bad': _w("{n} games where the players' points don't add up to the score. Usually ESPN listed a player "
                        "without an id or name and the play-by-play didn't have them either. Lines of these games whose "
                        "player has no row stay unresolved instead of void.",
                        "{n} {n|mecz, w którym|mecze, w których|meczów, w których} punkty zawodników nie sumują się "
                        "do wyniku. Zwykle ESPN podał zawodnika bez id lub nazwiska, a zapis akcji też go nie miał. "
                        "Linie z tych meczów, których zawodnik nie ma wiersza, pozostają nierozstrzygnięte zamiast "
                        "nieważnych."),

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
    'help.edge.body': _w("**Edge = our chance − the chance the odds need.** Superbet keeps 12% of every stake as tax, so "
                         "a win pays 0.88 × stake × odds and odds 1.90 need 1 ÷ (0.88 × 1.90) = 59.8%, not 52.6%. "
                         "With our chance at 55% the edge is **−4.8 pp** (percentage points). **Above 0**: the odds "
                         "pay more than the risk. **Below 0**: the bet loses over time, even when a single one wins. "
                         "An edge is only an estimate: a few points can easily be noise.",
                         "**Przewaga = nasza szansa − szansa wymagana przez kurs.** Superbet zatrzymuje 12% każdej "
                         "stawki jako podatek, więc wygrana to 0.88 × stawka × kurs, a kurs 1.90 wymaga 1 ÷ (0.88 × "
                         "1.90) = 59.8%, nie 52.6%. Przy naszej szansie 55% przewaga wynosi **−4.8 pp** (punktu "
                         "procentowego). **Więcej niż 0**: kurs płaci więcej niż ryzyko. **Mniej niż 0**: zakład z "
                         "czasem traci, nawet gdy pojedynczy wejdzie. Przewaga to tylko szacunek: kilka punktów łatwo "
                         "może być szumem."),
    'help.signals.title': _w("5. The decision: one per game", "5. Decyzja: jedna na mecz"),
    'help.signals.body': _w("Every game gets **one decision for its team markets** and **one for its players**. **Bet**: "
                            "one offer meets a threshold recorded on a period the model was never fitted or tuned on. "
                            "There is no such threshold yet, so no offer gets it. **Don't bet**: the evaluation is "
                            "current and no offer qualifies. **Wait**: something is missing (fresh odds, a team's "
                            "lineup, a questionable player) or two offers tie. **Unavailable**: the model isn't "
                            "admitted; team markets always are, the game model predicted worse than the price.",
                            "Każdy mecz ma **jedną decyzję dla rynków drużynowych** i **jedną dla zawodników**. "
                            "**Obstaw**: jedna oferta spełnia próg zapisany na okresie, na którym model nie był ani "
                            "dopasowywany, ani strojony. Takiego progu jeszcze nie ma, więc żadna oferta go nie "
                            "dostaje. **Nie obstawiaj**: ocena jest aktualna i żadna oferta się nie kwalifikuje. "
                            "**Czekaj**: czegoś brakuje (świeżego kursu, składu drużyny, niepewnego zawodnika) albo "
                            "dwie oferty remisują. **Niedostępne**: model nie jest dopuszczony; rynki drużynowe są "
                            "takie zawsze, model meczów przewidywał gorzej niż kurs."),
    'help.allpass.title': _w("When nothing qualifies", "Gdy nic się nie kwalifikuje"),
    'help.allpass.body': _w("Most days, and for now every day, no offer qualifies: the right move is not to bet. The "
                            "tables stay for research. Their order doesn't say what to bet: the line with the highest "
                            "expected return still loses on average after the stake tax.",
                            "Najczęściej, a na razie codziennie, nic się nie kwalifikuje: właściwy ruch to nie grać. "
                            "Tabele zostają do analizy. Ich kolejność nie mówi, co grać: linia z najwyższym "
                            "oczekiwanym zwrotem po podatku i tak średnio traci."),
    'help.flags.title': _w("6. Warnings", "6. Ostrzeżenia"),
    'help.flags.body': _w("A warning (the 'warning' column) keeps an offer from ever getting 'Bet': fewer than 8 games "
                          "behind the numbers, only preseason games, the player may not play (RotoWire), his minutes "
                          "swing a lot, or the line moved 1.5+ against the evaluated side.",
                          "Ostrzeżenie (kolumna 'ostrzeżenie') sprawia, że oferta nigdy nie dostanie 'Obstaw': mniej "
                          "niż 8 meczów za liczbami, tylko mecze przedsezonowe, zawodnik może nie zagrać (RotoWire), "
                          "jego minuty bardzo się wahają albo linia ruszyła o 1.5+ przeciw ocenianej stronie."),
    'help.verdict.title': _w("7. Why: the reasons", "7. Dlaczego: powody"),
    'help.verdict.body': _w("Pick a row to see **why**: ✅ for and ❌ against the evaluated side, ➖ context, ⚠️ warnings. "
                            "Each reason says its value, what it's compared with, how many observations it rests on, "
                            "when and where it comes from. A reason without data isn't shown. The reasons explain the "
                            "decision; they don't vote, so adding or removing one never changes it.",
                            "Wybierz wiersz, żeby zobaczyć **dlaczego**: ✅ za i ❌ przeciw ocenianej stronie, ➖ "
                            "kontekst, ⚠️ ostrzeżenia. Każdy powód podaje wartość, z czym ją porównano, na ilu "
                            "obserwacjach się opiera, z kiedy i skąd pochodzi. Powód bez danych nie jest pokazywany. "
                            "Powody objaśniają decyzję; nie głosują, więc dodanie lub usunięcie powodu nigdy jej nie "
                            "zmienia."),
    'help.player.title': _w("8. The player's numbers", "8. Liczby zawodnika"),
    'help.player.body': _w("**Expected tonight** is our estimate of the stat tonight: above the line points to Over, "
                           "below to Under. **Won, last 10 %** shows how often the side would have won lately; compare "
                           "it with **needed to win %**. 10 games is a small sample, so treat it as a hint.",
                           "**Oczekiwane dziś** to nasz szacunek statystyki na dziś: wyżej niż linia wskazuje na "
                           "Powyżej, niżej na Poniżej. **Trafione w ost. 10 %** pokazuje, jak często ta strona "
                           "ostatnio by wygrała; porównaj z **potrzebna skuteczność %**. 10 meczów to mała próba, "
                           "więc traktuj to jako wskazówkę."),
    'help.steps.title': _w("How to read tonight, in 4 steps", "Jak czytać dzisiejszy wieczór, w 4 krokach"),
    'help.steps.body': _w("1. On **Overview**, read each game's two decisions: team markets and players.\n2. "
                          "**Don't bet** or **Unavailable**: don't bet on that game. **Wait**: come back after the "
                          "missing odds or lineup arrive.\n3. Only **Bet** names one offer; there is none until an "
                          "edge threshold has been checked on nights not used to choose it.\n4. Open a line on **Props** for the "
                          "reasons and the history: research, not a reason to bet against the decision.",
                          "1. W **Przeglądzie** przeczytaj obie decyzje każdego meczu: rynki drużynowe i zawodnicy."
                          "\n2. **Nie obstawiaj** albo **Niedostępne**: nie graj na ten mecz. **Czekaj**: wróć, gdy "
                          "pojawi się brakujący kurs lub skład.\n3. Tylko **Obstaw** wskazuje jedną ofertę; nie "
                          "będzie żadnej, dopóki próg przewagi nie zostanie sprawdzony na nocach, których nie użyto do "
                          "jego wyboru.\n4. Otwórz linię w "
                          "**Zakładach na zawodników**, żeby zobaczyć powody i historię: to analiza, a nie powód, "
                          "żeby grać wbrew decyzji."),
    'help.glossary.title': _w("Every column, explained", "Każda kolumna wyjaśniona"),
    'help.glossary.caption': _w("The same explanations as the tooltips you see when you hover a column header.",
                                "Te same wyjaśnienia, które widać po najechaniu na nagłówek kolumny."),

    # Overview
    'overview.title': _w("Overview", "Przegląd"),
    'overview.purpose': _w("The games in the next 36 hours: one decision for each game's team markets and one for its "
                           "players, with the time of the odds and lineups behind them.",
                           "Mecze w najbliższych 36 godzinach: jedna decyzja dla rynków drużynowych każdego meczu i "
                           "jedna dla jego zawodników, z czasem kursów i składów, na których się opierają."),
    'overview.kpi.games': _w("Games", "Mecze"), 'overview.kpi.lines': _w("Player lines", "Linie zawodników"),
    'overview.kpi.lines_help': _w("Superbet's Over / Under lines on players in these games",
                                  "Linie Superbetu Powyżej / Poniżej na zawodników w tych meczach"),
    'overview.kpi.obstaw': _w("'Bet' decisions", "Decyzje 'Obstaw'"),
    'overview.kpi.obstaw_help': _w("Games where one offer's edge clears a threshold checked on nights not used to choose "
                                   "it. None can until such a threshold exists.",
                                   "Mecze, w których przewaga jednej oferty przekracza próg sprawdzony na nocach, "
                                   "których nie użyto do jego wyboru. Żadna nie może, dopóki taki próg nie istnieje."),
    'overview.offers': _w("Offers to bet", "Oferty do gry"),
    'no_tax.switch': _w("No-tax promotion today", "Promocja bez podatku dziś"),
    'no_tax.help': _w("Turn on only while Superbet runs a promotion that waives the 12% stake tax on your bets. The "
                      "pages then price every line without it (a win pays stake × odds); saved fetches and results "
                      "keep the tax. For this session only.",
                      "Włącz tylko wtedy, gdy Superbet prowadzi promocję znoszącą 12% podatek od stawki na Twoje "
                      "zakłady. Strony liczą wtedy każdą linię bez niego (wygrana to stawka × kurs); zapisane "
                      "pobrania i wyniki zostają z podatkiem. Tylko na tę sesję."),
    'no_tax.banner': _w("No-tax promotion on: every 'after tax' number on these pages is priced without the 12% stake "
                        "tax. Turn it off in the sidebar when the promotion ends.",
                        "Promocja bez podatku włączona: każda liczba 'po podatku' na tych stronach jest liczona bez "
                        "12% podatku od stawki. Wyłącz ją w pasku bocznym, gdy promocja się skończy."),
    'overview.shortlist': _w("Tonight's ratings: 4★ = the best of tonight, not: worth betting",
                             "Dzisiejsze oceny: 4★ = najlepsze dziś, nie: opłacalne"),
    'overview.shortlist_help': _w(
        "If you bet tonight anyway, these are the lines the model ranks best by expected return after the tax: 4★ "
        "the night's best 5% (one per game), 3★ up to 20%. No 🔴, no doubtful players. They still lose on average "
        "after Superbet's 12% stake tax. 5★ would be an offer whose edge was confirmed on nights not used to choose "
        "its threshold: there's none. On 2022/23 lines 4★ and 3★ won more often than the price said, 2★ and 1★ "
        "didn't; whether that holds on Superbet is tracked in Results → Ratings.",
        "Jeśli i tak grasz dziś, to te linie model stawia najwyżej według oczekiwanego zwrotu po podatku: 4★ "
        "najlepsze 5% wieczoru (jedna na mecz), 3★ do 20%. Bez 🔴, bez niepewnych graczy. Po 12% podatku od stawki "
        "dalej średnio tracą. 5★ byłaby oferta, której przewagę potwierdzono na nocach niewykorzystanych do wyboru "
        "progu: takiej nie ma. Na liniach 2022/23 4★ i 3★ wygrywały częściej, niż mówił kurs, 2★ i 1★ nie; czy tak "
        "jest na Superbecie, śledzą Wyniki → Oceny."),
    'overview.shortlist_cost': _w("Expected return per 100 after tax: 4★ lines {top:+.1f}, every line tonight "
                                  "{every:+.1f}.",
                                  "Oczekiwany zwrot na 100 zł po podatku: linie 4★ {top:+.1f}, każda linia dziś "
                                  "{every:+.1f}."),
    'overview.shortlist_negative': _w("Every 4★ line loses money on average after tax: a ranking of the least bad, "
                                      "not bets.",
                                      "Każda linia 4★ średnio traci po podatku: ranking najmniej złych, nie "
                                      "zakłady."),
    'overview.shortlist_record': _w("So far ({nights} {nights|night|nights|nights}, {bets} 4★ bets): 4★ won "
                                    "{hit:.0f}% where the price said {price:.0f}%, after tax {roi:+.1f} per 100; "
                                    "every line {every:+.1f}.",
                                    "Dotąd ({nights} {nights|wieczór|wieczory|wieczorów}, {bets} zakładów 4★): 4★ "
                                    "wygrywały {hit:.0f}%, kurs mówił {price:.0f}%, po podatku {roi:+.1f} na 100 zł; "
                                    "każda linia {every:+.1f}."),
    'overview.shortlist_empty': _w("No line can be rated yet: no priced line without a warning.",
                                   "Nie ma jeszcze czego ocenić: brak wycenionej linii bez ostrzeżenia."),
    'overview.shortlist_more': _w("Show tonight's 3★ lines ({n})", "Pokaż dzisiejsze linie 3★ ({n})"),
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
    'overview.no_props': _w("Superbet has no player props on these games yet.",
                            "Superbet nie ma jeszcze zakładów na zawodników w tych meczach."),
    'overview.no_games': _w("No game could be priced.", "Nie udało się wycenić żadnego meczu."),
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
