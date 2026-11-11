# Audyt reasonów: uzasadnienia rekomendacji zakładów NBA

Stan na 2026-11-10 · kod z `main` (349964b) · dane: zapisane pobrania Superbetu i RotoWire z `data/2026/` (tylko odczyt)

Przedmiot audytu: teksty, które wyjaśniają decyzję o zakładzie na stronie zawodników (dashboard_v2), czyli
`decision.reason.*`, `reason.*`, `warn.*`, `flag.*`, `mispricing.*`, oraz krótko reasony meczowe (`game.*`). Kod
produkcyjny, progi, modele, kalibracja i szablony nie zostały zmienione. Pliki audytu leżą w `audit/reasons/`.

---

## 0. Status napraw

| Pakiet | Data | Naprawione | Dowód |
|---|---|---|---|
| A | 2026-11-11 | **F-02, F-14** (nieobecni: korekta zawsze wyjaśniona, wkład każdego kolegi, koledzy bez danych jako „wpływ nieznany”, bez surowych ID; tekst opisuje sumę osobnych różnic), **F-10** (strona przekazuje profil kosztowy do `offer_signals`; `needed_pp` opisany jako marża + koszty, nie „podatek”), **F-13** (historia: przedział nazwany przedziałem historycznej częstości, częstość pełnej próby zawsze podana jako ta, której używa model; próba mieszana ujawniona też przy projekcji) | `dashboard/test_reasons.py`, `dashboard/test_mispricing.py`, testy audytu bez `xfail`; porównanie przed/po na 10.11 20:00 (`audit/reasons/compare.py`): 0 zmian liczb, decyzji i sygnałów; +65 reasonów o nieobecnych, +752 ostrzeżenia „wpływ nieznany” |
| B | 2026-11-11 | **F-04** (niedopuszczone hipotezy tylko w zwiniętej sekcji „Hipotezy badawcze: nie wpływają na decyzję”, bez ikon za/przeciw; najpierw status i wynik eksploracji, potem porównanie z modelem głównym na tej samej ofercie, próg opłacalności po kosztach, obliczenie z założeniami, aktualność), **F-05, F-06** (H6: kierunek zgodny ze stroną, porównanie z ligą zgodne z liczbami, „1,0× = wariancja równa średniej, Poisson”), **F-07** (H2: skuteczność obserwowana, udział priora, „stosunek” jako liczba modelu, ograniczenie FTM), **F-08** (H1: założenia i brak dowodu spóźnienia ceny), **F-18** (projekcja modelu, otoczenie z kursów Superbetu), **F-19** (projekcja jako jedna całość, kontekst w grupach, hipotezy pogrupowane według oferty z adnotacją o wspólnym źródle) | `dashboard/test_mispricing.py`, testy audytu F-05/F-06 bez `xfail`; porównanie przed/po (stan po A → po B) na 10.11 20:00, oba profile: 0 zmian liczb i decyzji; 205 sygnałów wyłącznie w sekcji badawczej, 0 z kierunkiem; szansa i EV modelu głównego w porównaniu = `p win %`/`ev net 100` na 1083/1083 liniach |
| C–E | — | otwarte: F-01, F-03, F-09 (H5 nieemitowany; teksty poprawione), F-11, F-12, F-15–F-17 | — |

---

## 1. Podsumowanie

**Odpowiedź na pytanie końcowe:** częściowo. Użytkownik dobrze rozumie, **co wynika z ceny** i **że nie ma
rekomendacji** (każda gra dostaje dziś „Nie obstawiaj”, bo żaden próg nie jest dopuszczony). Gorzej rozumie, **co
zakłada model**: „Model: Under wygrywa 41,9%” to w dużej części cena po kalibracji, a nie liczby zawodnika. Najsłabiej
pokazane jest to, **czego nie wiadomo**: sygnały „gdzie Superbet może się mylić” piszą „różnica pokrywa podatek” przy
wielkościach, które zależą od założeń modelu, nie wynikają z samych ofert i w 63% przypadków zmieniają stronę
w granicach niepewności skuteczności gracza.

**Co działa (sprawdzone, bez problemu):**
- Decyzja nie czyta reasonów. Ich liczba i brzmienie nie wpływają na status (test `test_7_the_decision_never_reads_the_reasons`).
- Ekonomia jest spójna: szansa, próg opłacalności i EV mają jedną definicję. Profil kosztowy w tekście zgadza się
  z liczbą. Niezależne przeliczenie (scipy, własne wzory) daje te same wartości dla Over i Under, linii połówkowych
  i całkowitych.
- Odtworzenie pobrania 10.11 20:00 zgadza się z zapisem co do strony i EV na 1083 z 1083 linii.
- Reasony kontekstowe nie udają argumentów: wszystkie cechy mają w `reason_lift` status `no_lift` albo `untested`,
  więc są pokazywane bez kierunku (➖), w zwiniętej sekcji, z adnotacją „sprawdzone: bez zysku ponad model”.
- Blockery działają przed wyborem oferty (linia z czerwoną flagą nie może się zakwalifikować) i są pokazywane osobno
  jako ⚠️, nie jako argument sportowy za drugą stroną.
- „Niewybrana” oferta jest opisana jako „oceniana jest inna oferta tego meczu”, nie jako nieopłacalna.
- Metoda wpływu driverów („zmienia szansę o X pp”) jest dokładnie taka, jak w dokumentacji: końcowa szansa minus
  szansa z wyzerowanym jednym wejściem, obie po kalibracji. Panel ostrzega, żeby ich nie sumować.

**Co wprowadza w błąd (najważniejsze):**
1. **F-04, F-07:** sygnały H2 piszą „różnica pokrywa podatek” obok wyceny modelu z EV −15 do −17 na 100 dla tej samej strony.
   Pod spodem jest wynik eksploracji z ujemnym ROI (H2: −9,8 na 100). „Celność zakładana przez linie” (np. 39% rzutów
   wolnych przy 77% gracza) jest artefaktem dopasowania, nie założeniem Superbetu.
2. **F-02:** gdy jeden z nieobecnych kolegów nigdy nie opuścił meczu z graczem, znika cały reason o nieobecnościach,
   choć model zastosował korektę. W 6 pobraniach reason pojawił się w 97 liniach, a zniknął w 1093 (92% linii z korektą).
3. **F-03:** „Model: X wygrywa p%” pokazuje szansę, w której kalibracja zostawia ok. 17% odchylenia modelu od ceny
   (b = 0,17), a cenę faworyta rozciąga (a = 1,14). W 1620 z 5574 linii (gdzie szansa różni się od ceny o > 0,5 pp)
   sama korekta ceny przez kalibrację przesuwa szansę bardziej niż liczby zawodnika.
4. **F-01:** linia gracza „questionable” z najwyższym EV wstrzymuje cały mecz („Czekaj: poczekaj na skład”), choć ta
   linia ma już czerwoną flagę i nie może się zakwalifikować. Dziś (bez progu) użytkownik czeka na skład, który niczego
   nie zmieni; po dopuszczeniu progu zasłoni to inną, czystą ofertę.

**Co blokuje zaufanie:** sekcja mispricing jest pokazywana wyżej niż kontekst, pełnymi zdaniami o „błędzie wyceny”,
przy hipotezach ze statusem `untested`, których eksploracja przegrywała (H1 0/1, H2 −9,8, H5 −18,5 na 100). Status
„🧪 obserwacja, nie test” jest podany, ale w piątej linii komunikatu, po zdaniu „różnica pokrywa podatek”.

---

## 2. Zakres, dane i odtwarzalność

| Pobranie | Noc(e) | Linie | Kalibracja zapisana | Odtwarzalne? |
|---|---|---|---|---|
| 2026-11-10 20:00 UTC | 10.11 | 1083 | ca925ad3af (= obecna) | **tak**: strona i EV zgodne z zapisem na 1083/1083 |
| 5.11 23:08, 6.11 17:01, 7.11 21:24, 8.11 20:26, 9.11 23:30 UTC (ostatnie przed pierwszym meczem nocy) | 5.11–10.11 | 6589 | 7707994eef, 33f19823e1, 1615953b5f, d3c1672bd4, 3a886084af | **nie**: przeliczone obecną kalibracją; teksty mówią, co obecny kod powiedziałby o tej ofercie, nie co pokazano wtedy |
| **razem** | | **7672** | | |

Zasady odtworzenia (`audit/reasons/harness.py`): mecze sprzed nocy (bez późniejszych), ostatnia wersja RotoWire
zapisana przed pobraniem, kursy meczowe z tego samego pobrania, historia linii do chwili pobrania, decyzja oceniana
w chwili pobrania. Nic w `data/` nie jest zapisywane. W czasie audytu zmieniały się pliki `data/2026/*.csv` i
`data/run_log.csv`: to zaplanowane pobieranie aplikacji, nie harness (zmiany widać w `git status` już przed
pierwszym uruchomieniem).

Ograniczenia danych:
- Superbet nie wystawił ani jednej linii całkowitej (0 z 148 571 wierszy w `superbet_props.csv`, 0 z 83 423
  w `superbet_prop_quotes.csv`), więc obsługa zwrotu (push) jest sprawdzona tylko syntetycznie.
- Żadna hipoteza mispricing i żaden próg nie są dopuszczone, więc kierunek tych reasonów i status OBSTAW są
  sprawdzone tylko w testach syntetycznych.
- Kalibracja z 2026-11-10 jest dopasowana do linii Superbetu do 9.11, czyli także do nocy z tego audytu. Dlatego
  szansa modelu dla nocy ≤ 9.11 jest oceną w próbie, nie prognozą.

---

## 3. Inwentaryzacja

| Rodzina | Klucze | Emitowany w UI? | Kierunek ✅/❌ | Rodzaj |
|---|---|---|---|---|
| Decyzja | `decision.reason.*` (11) | tak; dziś w praktyce tylko `no_threshold`, `no_lineup`, `stale_odds`, `no_odds`, `questionable`, `game_model`; `meets`, `tie`, `other_offer` są nieosiągalne bez progu | n/d (status) | decyzja |
| Cena | `reason.model`, `reason.model_no_tax` | tak | **tak**: znak przewagi | ekonomia |
| | `reason.beyond_price` | tak | nie | ekonomia (opis) |
| Drivery | `reason.expected` | tak | nie | opis modelu |
| | `reason.teammates`, `reason.environment`, `reason.matchup` (+ `impact`, `impact_none`, słowa) | tak (teammates: patrz F-02) | **tak**: znak wpływu ≥ 0,1 pp | driver |
| Kontekst | `history_*`, `minutes*`, `volume`, `home/away`, `rest`, `role`, `blowout_*`, `line_moved`, `odds_moved`, `before_tip` | tak | nie (wszystkie `no_lift`/`untested`) | kontekst |
| | `reason.vs_opp` | **nie**: emitowany tylko przy `lift`, a status to `no_lift` | — | kontekst |
| Ostrzeżenia | `warn.role`, `warn.stint`, `warn.lineup_expected` | tak | nie | ostrzeżenie |
| Blockery | `flag.*` (6) | tak | „przeciw” w danych, w UI osobno jako ⚠️ | blokada |
| Mispricing | `mispricing.h1.*`, `h2.*`, `h6.*`, `expiry`, `status.*`, `exploration` | tak | nie (`untested`); po dopuszczeniu tak (F-11) | mispricing |
| | `mispricing.h5.*` | **nie**: strona nie przekazuje roli do `offer_signals` (zgodnie z `docs/hipotezy_wyceny.md`) | — | mispricing |
| | `mispricing.status.admitted` | **nie**: brak dopuszczonych hipotez | — | — |
| Mecze | `game.*`, `gameflag.*` | tak, „tylko badawczo”: rynki drużynowe są zawsze Niedostępne | tak (game.model, projection, net, absence) | badawcze |

Częstość na 10.11 (1083 linie): kontekst 6097, driver 3249, ekonomia 2166, ostrzeżenie 1148, blocker 205,
mispricing 205 reasonów. Kierunkowe: ekonomia 1083 (wszystkie „przeciw”), drivery 441 za i 399 przeciw, blockery 205.

---

## 4. Tabela ustaleń

Oznaczenia: **BŁĄD** = potwierdzony błąd · **NIEJASNOŚĆ** = potwierdzona niejasność komunikacyjna · **RYZYKO** =
ryzyko wymagające dodatkowego testu · **BRAK DANYCH** = brak danych do rozstrzygnięcia · **OK** = sprawdzone, bez problemu.

| Id | Priorytet | Oznaczenie | Plik / funkcja | Ustalenie | Dowód | Wpływ na użytkownika |
|---|---|---|---|---|---|---|
| F-01 | wysoki | BŁĄD | `dashboard/decisions.py` `player_decision` (krok 3) | Gracz questionable z najwyższym EV wśród wszystkich wycenionych linii (także z czerwoną flagą) daje cały mecz CZEKAJ. Jego linia ma już `flag.may_not_play`, więc nigdy się nie zakwalifikuje. Bez progu daje „Czekaj” zamiast „brak progu”. | `test_7_questionable_player_does_not_hide_a_clean_qualifying_offer`, `test_7_without_a_threshold_…` (xfail). W 6 odtworzonych pobraniach 0 takich gier (42 decyzje: 39 brak progu, 3 brak składu); zapisy historyczne nie przechowują powodu CZEKAJ, więc częstości nie da się ustalić | Dziś: komunikat „poczekaj na skład”, choć żaden skład nie zmieni decyzji. Po dopuszczeniu progu: ukryta kwalifikująca się oferta. |
| F-02 | wysoki | BŁĄD | `reasons.offer_context` (`out_n = min(missed)`) + `reasons.complete` | Gdy choć jeden nieobecny kolega nie ma meczów bez niego, `out_n = 0` i reason `teammates` jest odrzucany, choć korekta pozostałych weszła do projekcji. Na liście nazwisk trafia też surowe ID ESPN (`3102530`). | 6 pobrań: reason pokazany w 97, odrzucony w 1093 liniach z korektą (92%); 10.11: 65/1083. Ace Bailey FGA 15,5: korekta +1,2 FGA, wpływ −0,51 pp (największy driver), reason nie pokazany. `test_C_applied_absence_adjustment_is_always_explained` (xfail) | Model używa czynnika, którego panel nie pokazuje. Pozostałe drivery wyglądają na pełne wyjaśnienie. |
| F-03 | wysoki | NIEJASNOŚĆ | `i18n reason.model` / `models.price_props` / `calibration.json` | „Model: X wygrywa p%” to szansa po kalibracji z b = 0,17 (zostaje 17% opinii modelu ponad cenę) i a = 1,14 (cena faworyta rozciągnięta). `beyond_price` podaje część, ale nie mówi, ile opinii modelu kalibracja usunęła. | 6 pobrań: 1620/5574 linii (10.11: 222/785) (gdzie p różni się od ceny o > 0,5 pp): sama korekta `a` > wpływ liczb gracza. Ace Bailey: surowo Under 64,2%, po kalibracji 49,5%; tekst „liczby gracza przesuwają o +3,0 pp”. `test_A2_documents_…` | Użytkownik bierze „szansę modelu” za ocenę z danych gracza; to w większości cena. |
| F-04 | wysoki | NIEJASNOŚĆ | `mispricing_reasons`, `i18n mispricing.*.clears`, `mispricing.exploration`, `components.reasons_panel` (kolejność sekcji) | Sygnał pisze „różnica pokrywa podatek” przy linii, dla której model daje EV −15…−17 na 100; obie oceny nie są ze sobą zestawione. Pod spodem dopisany wynik eksploracji, zawsze ujemny dla H1/H2. Sekcja stoi nad kontekstem. | 6 pobrań: 1345 pokazanych sygnałów, 298 „pokrywa podatek”, 85 na tej samej stronie co oceniana z EV < 0, 296/298 z ujemnym ROI eksploracji (2 dodatnie: H6 +11,0 przy 6 sygnałach); 10.11: 42/42 ujemnych. `test_A_documents_negative_exploration_…` | Zdanie brzmi jak podpowiedź zakładu; rozstrzygające zastrzeżenia są na końcu. |
| F-05 | niski | BŁĄD (szablon), rzadkie | `i18n mispricing.h6.why` | „Gracz o większym rozrzucie częściej kończy poniżej linii”: kierunek odwraca się, gdy średnia z ceny leży wyraźnie pod linią. Wtedy sygnał wskazuje Over, a tekst mówi „poniżej”. | Siatka: maks. przewaga Over 5,8 pp (linia 2,5, cena 5%, rozrzut 4); 0 przypadków Over w danych. `test_A_H6_why_text_matches_…` (xfail) | Tekst sprzeczny ze stroną sygnału, w rzadkim przypadku. |
| F-06 | średni | BŁĄD (szablon) | `i18n mispricing.h6.what`, `mispricing.spread_signals` | „Wyniki wahają się bardziej niż zwykle” pada, gdy rozrzut ściągnięty > 1, także gdy jest **mniejszy** niż podany obok „typowy w lidze”. „1,0× = równomiernie rozrzucone” jest błędne: 1,0 to Poisson, a równomierne wyniki mają wariancję 0. | 12 z 588 sygnałów H6 (6 pobrań) ma rozrzut < ligowy; w pokazanych (33) — 0. `test_A_H6_more_than_usual_…` (xfail), `test_A_H6_one_x_…` | Zdanie przeczy liczbom w tym samym nawiasie. |
| F-07 | wysoki | NIEJASNOŚĆ | `mispricing.shooting_signals`, `i18n mispricing.h2.*` | „Linie razem zakładają, że trafia X%” to iloraz dwóch średnich dopasowanych z wariancją gracza, a nie fakt z ofert. „Trafia R%” to w 78% (57 prób) wartość ligowa (prior 200 prób). Rzuty wolne idą parami (H6 je z tego powodu wyklucza, H2 nie). | Te same kursy dają inną „zakładaną celność” przy innym rozrzucie gracza (`test_A_H2_implied_rate_…`). 1473/1489 sygnałów (6 pobrań): prior > połowa wagi. Wrażliwość: strona zmienia się w 95% przedziale celności w 140/223 sygnałów. Davion Mitchell FTM 0,5: „zakładają 39%” przy jego 77%, luka 24,1 pp. | Komunikat przypisuje Superbetowi założenie, którego Superbet nie podaje, i przedstawia niestabilny wynik jako pokrycie podatku. |
| F-08 | średni | NIEJASNOŚĆ | `mispricing.combo_over_from_parts`, `i18n mispricing.h1.*` | Szansa sumy z cen składowych wymaga założeń: rozkład ujemny dwumianowy/Poisson, wariancje gracza, korelacje gracza ściągnięte do ligowych. Przy wariancji sumy ≤ średniej kod przechodzi na Poissona i korelacje nie mają wpływu. „Różni się od linii składowych” miesza logiczną niespójność cen z rozbieżnością względem naszego modelu. „Superbet wycenia sumę osobno… gdy jedna cena się opóźnia” to nieudowodnione twierdzenie o procesie Superbetu. | Zerowa korelacja zamiast ligowej zmienia stronę w 30/240 przypadków. `test_A_H1_depends_on_…` | Użytkownik bierze rozbieżność z modelem za błąd w cenach. |
| F-09 | niski (nieemitowany) | RYZYKO | `mispricing.role_signals`, `i18n mispricing.h5.*` | H5 skaluje średnią z ceny przez minuty nowej roli, zakładając, że cena roli nie zna. Brak dowodu czasowego (kiedy cena powstała wobec wiadomości). Eksploracja: −18,5 na 100. Szablon `why` sam podaje, że strona zmiany roli przegrywała. | `test_A_H5_scales_…`, `test_A_H5_is_not_emitted_…`; `docs/hipotezy_wyceny.md` | Dziś brak (nie emitowany). Włączenie bez zmian pokazałoby sprzeczny komunikat. |
| F-10 | średni | BŁĄD | `dashboard_v2/views/props.py` (wywołanie `offer_signals`) | Sygnały mispricing liczą próg z `ACTIVE_PROFILE` (podatek 12%), nawet gdy w panelu bocznym wybrano promocję bez podatku. Reason ceny mówi wtedy „bez podatku”, a sygnał „po podatku potrzeba …”. | `test_A_mispricing_uses_the_pages_cost_profile` (xfail) | Dwa różne progi opłacalności w jednym panelu. |
| F-11 | średni (utajony) | BŁĄD | `reasons.mispricing_reasons` (`supports`) | Po dopuszczeniu hipotezy sygnał o **innej** linii (np. kombinacja PR pokazana na PTS) dostaje `supports = False`, czyli ❌ przeciw ofercie, której nie dotyczy. | 6 pobrań: 742 z 1345 pokazanych sygnałów dotyczy innej linii niż oferta (10.11: 117/205). `test_A_admitted_signal_about_another_line_…` (xfail) | Dziś brak (wszystko `untested`); po dopuszczeniu fałszywe argumenty przeciw. |
| F-12 | niski (utajony) | RYZYKO | `models.price_props` (`push`) | Na linii całkowitej szansa zwrotu = 1 − Over_kal − Under_kal; obie strony ściągane do ceny bez marży, która wyklucza zwrot, więc zwrot zanika (syntetycznie 4,5% przy 67% empirycznie). „Wygrywa p%” byłoby wtedy szansą warunkową, a EV źle policzone. | `test_A1_whole_line_push_…` (xfail); 0 linii całkowitych w danych | Dziś brak; ryzyko przy innym bukmacherze lub zmianie oferty. |
| F-13 | średni | NIEJASNOŚĆ | `i18n reason.history_note`, `reason.history_last` | „Model używa tej częstości tylko ściągniętej do ceny”: pokazana jest częstość z ostatnich 10, a model używa częstości ze **wszystkich** meczów próby. „95% range” to przedział Wilsona dla częstości historycznej, nie dla szansy modelu. Próba mieszana (zeszły sezon/przedsezon) jest ujawniona tylko tu. | `test_C_hit_rate_shown_is_not_the_one_…`; 6 pobrań: 7498/7672 linii ma ≤ 10 meczów (wartości się pokrywają), 5826/7672 ma mieszaną próbę | Rozbieżność rośnie z sezonem; przedział można wziąć za niepewność prognozy. |
| F-14 | średni | NIEJASNOŚĆ | `i18n reason.teammates`, `metrics.absence_adjustments` | Tekst: „w meczach bez nich miał średnio +X wobec meczów z nimi”. Obliczenie: suma osobnych, ściągniętych różnic „bez/z” dla każdego kolegi; meczów bez nich wszystkich nikt nie liczy. | `test_C_documents_…` | Sugeruje bezpośrednią obserwację, która nie istnieje. |
| F-15 | niski | NIEJASNOŚĆ | `decisions.player_decision` (remis) | Remis dwóch ofert daje CZEKAJ, czyli status „dane nieaktualne”; nowe dane remisu nie rozstrzygną. | `test_7_documents_that_a_tie_…` | „Czekaj” bez sensu czekania. |
| F-16 | średni | NIEJASNOŚĆ | `models.price_props` (strona oceniana) / tytuł panelu | Strona oceniana (wyższe EV, oba ujemne) jest niestabilna. Zmienia się w 5% perturbacji minut o 1 błąd standardowy, 10% przy ±10% minut, 11% przy błędzie standardowym skuteczności, 1% przy zmianie kursu o 0,05. Panel nie mówi, że druga strona jest prawie tak samo (nie)opłacalna. | `audit/reasons/sensitivity.py` | Tytuł „Under 3PM 1,5” wygląda na wybór, a to rozstrzygnięcie o ułamek EV. |
| F-17 | średni | NIEJASNOŚĆ | `reason.model`, `reason.expected` | Reason ceny nie podaje żadnej niepewności szansy, choć `price_props` liczy dolny koniec (`edge low`). Zostaje ona tylko w kolumnie tabeli, z samym szumem próby. | 1083/1083 linii bez przedziału w tekście | Szansa wygląda na pewną. |
| F-18 | niski | NIEJASNOŚĆ | `i18n` (język) | Przeskoki od „model szacuje” do „tak jest”: „Expected 13,3 FGA tonight” (projekcja), „Superbet expects UTAH to score 109” (nasze wyliczenie z handicapu i sumy), „The price fits a typical spread” (H6, założenie Poissona przypisane cenie), „Superbet prices the sum apart from its parts” (H1). | przegląd szablonów | Założenia brzmią jak fakty o Superbecie. |
| F-19 | średni | NIEJASNOŚĆ | panel (zależność) | Kilka reasonów z tych samych danych wygląda na niezależne: H2 i H6 popierają tę samą stronę tej samej linii z tej samej ceny i tych samych meczów; drivery (rywal, otoczenie, nieobecni) to składowe jednej średniej. | 6 pobrań: 8 linii z ≥ 2 sygnałami na tę samą stronę tej samej linii (np. McCain, Black 3PM 1,5); 585 linii, w których ≥ 2 drivery mają ten sam kierunek | Użytkownik może je liczyć jako kilka potwierdzeń. |
| F-20 | — | OK | `backtest/reason_lift.py` | Lista cech ustalona z góry, dopasowanie na wcześniejszych liniach, ocena na późniejszych, przedział przez losowanie całych nocy, wszystkie cechy `no_lift`. Uwaga: obie strony linii wchodzą jako osobne wiersze (zależność obsłużona losowaniem nocy); część Superbet to 4 noce; plik nie zapisuje wersji modelu. | `data/backtest/reason_lift.md` | Kierunku kontekstu dziś nie ma, więc nie ma fałszywej walidacji. |
| F-21 | — | OK | ekonomia, drivery, blockery, decyzja | patrz „Co działa” | testy `test_A1_*`, `test_A2_driver_impact_*`, `test_7_*` | — |
| F-22 | — | BRAK DANYCH | H6 kierunek Over, push, OBSTAW, dopuszczone hipotezy | Nie występują w danych; sprawdzone syntetycznie. | — | — |

---

## 5. Karty reasonów

Wspólne dla wszystkich reasonów oferty: dotyczą **strony ocenianej** (`side` z `price_props`: wyższe EV po podatku,
także ujemne). Każdy niesie `value`, `reference`, `n`, `as_of` i `source`, a `complete()` odrzuca reason bez nich.
Czas danych: mecze sprzed nocy (`stats_through`), kursy z chwili pobrania (`odds_at`), RotoWire z chwili zapisu
(`lineup_at`). UI pokazuje pod każdym reasonem „n obs. · źródło · czas”.

### 5.1 Cena: `reason.model` / `reason.model_no_tax` (ekonomia, kierunkowy)
- **Emisja:** `prop_reasons`, gdy znana jest przewaga (`edge pp`). `model_no_tax` przy profilu z podatkiem 0.
- **Wzór:** p = kalibracja(średnia z (częstość trafień ściągnięta do ceny wagą 10 meczów) i (rozkład liczności NB/Poisson
  wokół `proj avg`, ściągnięty tak samo)); kalibracja sigmoid(1,139·logit(m) + 0,170·(logit p − logit m)).
  Próg = (1 − p_zwrotu)/(α·kurs), α = 0,88; EV = 100·(p·α·kurs + p_zwrotu − 1).
- **Jednostki:** p i próg w %, przewaga w pp, EV na 100 zł stawki. Szansa bezwarunkowa (zwrot osobno; w praktyce 0).
- **Kierunek:** za, gdy przewaga > 0. Dziś przeciw na 1083/1083 liniach 10.11.
- **Walidacja:** kalibracja `calibration.json` (2026-11-10; dopasowana także na nocach do 9.11).
- **Zależności:** to wynik wszystkich driverów i częstości trafień, więc nie jest od nich niezależny.
- **Wynik:** liczby poprawne (OK); opis „Model” mylący (F-03), brak niepewności (F-17).
- **Działanie:** rozbić na cenę bez marży → korektę kalibracji → wkład gracza; podać zakres.

### 5.2 `reason.beyond_price` (ekonomia, opis)
- **Wzór:** końcowa p − kalibracja(cena, cena). Zawiera całą opinię modelu ponad cenę po kalibracji.
- **Wynik:** liczby zgodne z `impacts['final']` (1083/1083). „Liczby zawodnika” obejmują też projekcję (nieobecni,
  tempo, rywal). Nie mówi, że kalibracja zostawia ok. 17% opinii (F-03).

### 5.3 `reason.expected` (driver, bez kierunku)
- **Wzór:** `proj avg` = (średnia + korekta nieobecnych) × czynnik tempa × czynnik rywala; czynniki = 1 + ½(stosunek − 1),
  ucięte do ±8%. Średnia i mediana z próby (z dobranymi meczami zeszłego sezonu, gdy jest ich mało).
- **Wynik:** NIEJASNOŚĆ (F-18: „Expected” = projekcja modelu); próba mieszana nieujawniona tutaj (F-13).

### 5.4 `reason.teammates` (driver)
- **Emisja:** korekta ≠ 0, są nazwiska nieobecnych, `out_n ≥ 1`.
- **Dane:** RotoWire `out` (szansa gry ≤ 25%), mecze gracza z/bez każdego kolegi w bieżącym okresie w drużynie.
- **Wzór:** Σ po kolegach (śr. bez − śr. z)·n_bez/(n_bez + 5). Wpływ = p − p(korekta = 0).
- **Wynik:** BŁĄD F-02 (znika przy `out_n = 0`, surowe ID), NIEJASNOŚĆ F-14 (opis wspólnego podziału).

### 5.5 `reason.environment` (driver)
- **Dane:** handicap i suma meczu z Superbetu → punkty drużyny = suma/2 ∓ handicap/2; „zwykle” = średnia drużyny w tym sezonie.
- **Wpływ:** czynnik tempa = 1 + ½(implied/zwykle − 1), ±8%. Zwykle < 0,1 pp.
- **Wynik:** OK liczbowo; „Superbet expects” → „z kursów Superbetu wynika” (F-18). Wspólne źródło z `blowout_*`.

### 5.6 `reason.matchup` (driver)
- **Dane:** ile rywal pozwala danej pozycji (bieżący sezon, bez gości z przedsezonu), średnia ligi, ranking.
- **Wpływ:** czynnik rywala, ±8% (Ace Bailey: −0,28 pp; McCain: +0,13 pp).
- **Wynik:** OK. „trudny/łatwy rywal” dotyczy gracza, nie strony; przy Under „trudny” działa na korzyść, co icon ✅
  oddaje, a słowo nie.

### 5.7 Kontekst: `history_*`, `minutes*`, `volume`, `home/away`, `rest`, `role`, `blowout_*` (bez kierunku)
- **Emisja:** `history` przy ≥ 3 meczach; `minutes`/`volume` przy ≥ 8 meczach w drużynie i |zmiana| ≥ 3 min;
  `venue` przy ≥ 6 meczach i ≥ 3 w tym miejscu; `rest` gdy znany odpoczynek obu drużyn; `role` gdy RotoWire podaje
  rolę; `blowout` przy |handicap| ≥ 10 i graczu z pierwszej piątki.
- **Walidacja:** `reason_lift`: hits_l10, minutes, venue, rest, vs_opp, volume = `no_lift`; role, blowout = `untested`.
- **Zależności:** `history` = część modelu (składnik częstości); `minutes` + `role` + `warn.role` + `flag.minutes` +
  (H5) = te same minuty i rola; `blowout` + `environment` = ten sam handicap.
- **Wynik:** kierunek OK; F-13 dla `history`; `minutes` miesza mecze zeszłego sezonu z tą samą drużyną bez informacji
  (Caruso 10.11: „5 earlier games with OKC” obejmuje zeszły sezon).

### 5.8 `reason.line_moved` / `reason.odds_moved` (kontekst rynku)
- **Wzór:** linia teraz − pierwsza zapisana; kursy bez marży wtedy i teraz. „Market context, not a reason”.
- **Wynik:** OK. Zmiana linii lub kursu tworzy nowy zestaw reasonów (liczone z bieżącego wiersza), a `offer_changed`
  pokazuje zmianę od ostatniego wyświetlenia (test `test_B_changed_quote_is_detected`). Sygnały mispricing mają
  „ważne tylko dla tych kursów”.

### 5.9 Ostrzeżenia i blockery
- `warn.role` (≤ 30% startów i dziś w piątce, albo ≥ 70% i ławka), `warn.stint` (< 8 meczów w drużynie),
  `warn.lineup_expected`.
- `flag.few_games` (< 8), `flag.preseason`, `flag.out` (0%), `flag.may_not_play` (0–100%), `flag.minutes`
  (CV > 0,35 przy ≥ 5 meczach), `flag.line_against` (ruch ≥ 1,5 przeciw stronie).
- **Wynik:** OK; współwystępowanie ostrzeżenia i dwóch blockerów pokazane razem (`test_B_colliding_…`). Blocker
  „przeciw” w danych, w UI osobno jako ⚠️. F-01 dotyczy tego, jak decyzja używa statusu questionable.

### 5.10 Mispricing H1 / H2 / H6 (bez kierunku, `untested`)
- **H1:** średnie składowych z ich cen (`market_mean`, rozrzut gracza), wariancja sumy z korelacjami gracza
  ściągniętymi do ligowych (waga 10 meczów), szansa sumy z rozkładu liczności. Pokazywane od 3 pp różnicy.
- **H2:** średnia prób z ceny × skuteczność gracza (wszystkie mecze + 200 prób ligowych) → szansa linii trafień.
  Od 6 pp różnicy.
- **H6:** średnia Poissona z ceny małej linii (≤ 2,5) i rozrzut gracza (ostatnie 40 meczów, ściągnięty do ligi wagą
  20 meczów). Od 4 pp różnicy.
- **Wspólne:** `needed_pp` = próg po podatku − cena bez marży (marża i podatek, bez dodatkowego progu; zgodne z testem
  `test_A_mispricing_needed_pp_…`). `clears` = p_nasze ≥ próg.
- **Wynik:** F-04, F-06, F-07, F-08, F-10, F-11, F-19.

### 5.11 Decyzja (`decision.reason.*`)
- Kolejność: brak kalibracji → NIEDOSTĘPNE; brak kursów lub kursy > 3 h → CZEKAJ; brak składu drużyny lub gracz
  questionable z najlepszym EV → CZEKAJ; brak progu → NIE OBSTAWIAJ; brak oferty z EV > 0 i przewagą ≥ progu bez
  czerwonej flagi → NIE OBSTAWIAJ; remis → CZEKAJ; inaczej OBSTAW.
- **Wynik:** F-01, F-15; reszta OK.

---

## 6. Mapa zależności

```
Superbet: kurs Over/Under tej linii ──┬─► cena bez marży m ──► kalibracja (a·logit m) ─────────────┐
                                      ├─► H6 (średnia Poissona z m) ◄── rozrzut gracza              │
                                      ├─► H2 (linia trafień) ◄── linia prób ◄── skuteczność gracza  │
                                      └─► H1 (linia kombinacji) ◄── linie składowych ◄── korelacje   │
Superbet: handicap + suma meczu ──────┬─► implied ──► czynnik tempa ──► [environment] ──┐           │
                                      └─► spread ──► [blowout] (kontekst)               │           │
Mecze gracza (ESPN, próba) ───────────┬─► częstość trafień (wszystkie) ─────────────────┼──► p_surowe ─► p_kal ─► [reason.model], EV
                                      ├─► [history] (ostatnie 10, Wilson) ≈ ta sama informacja     ▲
                                      ├─► średnia, wariancja ──► rozkład liczności ◄── proj avg ───┘
                                      ├─► minuty ──► [minutes], [flag.minutes], (H5)
                                      └─► starty ──► [role], [warn.role], (H5)
RotoWire: kto nie gra, rola ──────────┬─► korekta nieobecnych ──► proj avg ──► [teammates]
                                      └─► rola dziś ──► [role], [warn.role], (H5), decyzja (questionable)
Mecze ligi (pozycja rywala) ──────────► czynnik rywala ──► proj avg ──► [matchup]
```

| Para reasonów | Relacja | Ocena |
|---|---|---|
| `history` ↔ `reason.model` | wspólne źródło (częstość wchodzi do p, ale ze wszystkich meczów, nie z 10) | częściowo ta sama informacja; `no_lift` |
| `expected` ↔ `teammates`/`environment`/`matchup` | dokładne powtórzenie: `expected` to iloczyn tych trzech | grupować jako jedną projekcję |
| `teammates` ↔ zakładka „koledzy” | wspólne źródło, inna metoda (zakładka: każdy osobno, wszystkie sezony) | opis, nie potwierdzenie |
| `environment` ↔ `blowout_*` | wspólne źródło (kursy meczowe) | dwie interpretacje jednej ceny |
| `minutes` ↔ `role` ↔ `warn.role` ↔ `flag.minutes` ↔ H5 | wspólne źródło (minuty, starty, RotoWire) | jedna grupa „rola i minuty” |
| H2 ↔ H6 (ta sama linia) | wspólna cena i ten sam rozrzut gracza | nie dwa niezależne sygnały |
| H1 ↔ linie składowe (pokazane na każdej) | ten sam sygnał na kilku ofertach | jeden sygnał, kilka miejsc |
| mispricing ↔ `reason.model` | różne założenia na tej samej cenie; mogą wskazywać przeciwne strony (6 pobrań: 257 razy przeciwna strona) | zestawić wprost |

**Potwierdzony przyrost ponad model:** żaden reason (wszystkie cechy kontekstu `no_lift`, hipotezy `untested`).

**Proponowane grupowanie w panelu:** (1) Cena i ocena (model, beyond_price, niepewność); (2) Projekcja (expected +
nieobecni + otoczenie + rywal, jako jedno drzewo z wpływami); (3) Rola i minuty (minutes, role, warn.role,
flag.minutes); (4) Historia i rynek (history, line/odds moved); (5) Obserwacje cen Superbetu (H1/H2/H6 razem, z jednym
zastrzeżeniem i informacją, że korzystają z tych samych kursów).

---

## 7. Rzeczywiste przykłady (pobranie 10.11 20:00 UTC, odtwarzalne)

### 7.1 Jared McCain 3PM 1,5 Under @ 2,25: sygnał „pokrywa podatek” obok EV −17
**Tekst obecny (fragmenty):**
- „Model: Under wins 41.9%; odds 2.25 after the 12% stake tax need 50.5% (edge -8.6 pp, -17.1 per 100 staked)”
- „3PM 1.5 differs by 13.1 pp from what the 3PA line and the player's shooting give; after the tax it takes 9.1 pp, and the gap covers it.”
- „…the lines 3PA 5.5 and 3PM 1.5 together assume he makes 46% of his shots; he makes 34% (17 of 57 in 10 games, pulled toward the league's 35%…)”
- osobno H6: „Not enough to cover the tax: … “Under 3PM 1.5” has a 5.4 pp higher chance…”

**Przebieg:** kursy 1,59/2,25 → cena bez marży Under 41,4%. Model: surowo Under 51,3% → po kalibracji 41,9%.
H2: średnia 3PA z ceny linii 5,5 (z rozrzutem gracza) × skuteczność (17 + 200·0,349)/(57 + 200) = 33,8% → Under 54,5%
→ luka 13,1 pp ≥ potrzebne 9,1 pp. „Zakładane 46%” = średnia 3PM z ceny ÷ średnia 3PA z ceny, obie dopasowane przy
rozrzucie gracza (3PM: wariancja/średnia 2,49).

**Problem:** (a) dwie oceny tej samej strony (41,9% i 54,5%) bez zestawienia; (b) „he makes 34%” w 78% pochodzi
z ligi; (c) „lines assume 46%” zależy od rozrzutu, nie od ofert; (d) H2 i H6 popierają Under z tej samej ceny;
(e) eksploracja H2: −9,8 na 100.

**Proponowany tekst (PL):** „Obserwacja, nietestowana (🧪): nasz rachunek z linii prób 3PA 5,5 i skuteczności 34%
(17/57 gracza, w większości wartość ligowa) daje Under 54%, cena 41%. To inny rachunek niż model (41,9%, EV −17 na
100). Przy skuteczności w jej 95% zakresie wynik może wskazać drugą stronę. W 12 nocach eksploracji podobne sygnały
traciły 9,8 na 100.”

### 7.2 Davion Mitchell FTM 0,5 Over @ 1,66: „linie zakładają 39% rzutów wolnych”
**Tekst:** „FTM 0.5 differs by 24.1 pp … and the gap covers it. What happened: the lines FTA 1.5 and FTM 0.5 together
assume he makes 39% of his shots; he makes 77%…”
**Przebieg:** średnie z cen linii 0,5 i 1,5 dla bardzo małych liczności; iloraz 0,39. Gracz 14/21 + prior → 76,8%.
Over 79,6% wobec ceny 55,5%. Model: Over 57,8%, EV −15,6.
**Problem:** żaden bukmacher nie zakłada 39% rzutów wolnych; to artefakt dopasowania średnich do małych linii, a rzuty
wolne idą parami (powód, dla którego H6 je wyklucza).
**Proponowane:** wyłączyć FTM z H2 albo zastąpić zdanie „linie zakładają X%” zdaniem „z naszego dopasowania średnich
do obu linii wychodzi X%; przy liniach poniżej 2 ta liczba jest niewiarygodna”.

### 7.3 Ace Bailey FGA 15,5 Under @ 1,95: brak reasona o nieobecnych
**Przebieg:** RotoWire: nie grają Keyonte George, Jaren Jackson Jr., Lauri Markkanen i „3102530” (ID bez nazwiska).
Korekta +1,21 FGA (12,5 zamiast 11,3) wchodzi do projekcji 13,3; wpływ na szansę −0,51 pp, większy niż rywal
(−0,28) i otoczenie (−0,07). Jeden z nieobecnych nie ma meczów bez gracza → `out_n = 0` → reason odrzucony.
**Problem:** panel pokazuje dwa drivery i pomija największy.
**Proponowane:** zawsze pokazać korektę: „Nieobecni (RotoWire): George, Jackson Jr., Markkanen + 1 gracz bez
dopasowanego nazwiska. Korekta +1,2 FGA (suma osobnych różnic z/bez, ściągniętych); dla 1 z nich brak meczów bez
niego, więc jego wpływ nie jest znany. Zmienia szansę modelu o −0,5 pp.”

### 7.4 Ten sam przykład: szansa „modelu”
**Tekst:** „Model: Under wins 49.5%” i „The price alone says Under 46.9% (margin-free), 46.4% after the calibration;
the player's numbers move it +3.0 pp”, przy „Under in 9 of the last 10 games (90%)” i „Expected 13.3 FGA vs 15.5”.
**Przebieg:** surowy model Under 64,2%; kalibracja z b = 0,17 zostawia ok. 1/6 odchylenia od ceny → 49,5%.
**Proponowane:** „Szansa po kalibracji 49,5%: cena bez marży 46,9%, poprawka kalibracji −0,5 pp, liczby gracza
+3,0 pp. Sam model gracza dawał 64%; na rozliczonych liniach takie odchylenia od ceny sprawdzały się w ok. 1/6, więc
kalibracja je zmniejsza.”

---

## 8. Analiza wrażliwości (10.11, 1083 linie, `audit/reasons/sensitivity.py`)

| Perturbacja | Uzasadnienie zakresu | Zmiana znaku EV | Zmiana strony ocenianej |
|---|---|---|---|
| minuty ± 1 SE średniej z 10 meczów (śr. 6,4%) | szum estymacji z danych | 0 / 2166 | 115 / 2166 (5,3%) |
| minuty ± 10% | scenariusz | 0 / 2166 | 219 / 2166 (10,1%) |
| skuteczność ± 1 SE (dwumianowo, próby gracza) | szum estymacji z danych | 0 / 964 | 107 / 964 (11,1%) |
| kurs strony ± 0,05 | scenariusz (1 krok) | 0 / 2166 | 23 / 2166 (1,1%) |
| profil bez podatku | scenariusz | 3 / 1083 | — |
| H1: korelacja 0 zamiast ligowej | scenariusz | — | 30 / 240 (12,5%) |
| H2: skuteczność gracza ± 1,96 SE | przedział z danych | — | **140 / 223 (63%)** |
| H6: rozrzut własny zamiast ściągniętego | scenariusz | — | 6 / 214; „pokrywa podatek”: 0 → 2 |

Decyzja i wybrana oferta nie mogą się zmienić: bez dopuszczonego progu każdy mecz to NIE OBSTAWIAJ. Kierunek EV jest
stabilny, bo wszystkie linie są wyraźnie ujemne po podatku. Niestabilne są strona oceniana (F-16) i H2 (F-07).
Komunikaty tej niestabilności nie ujawniają.

---

## 9. Rozbieżności: dokumentacja a kod

| Dokument | Twierdzenie | Kod | Ocena |
|---|---|---|---|
| `docs/reason-templates.md` (z tej sesji) | wymienia `mispricing.h5.*` jak pozostałe | H5 nie jest emitowany na stronie zawodników | uzupełnić adnotację „nieemitowany” |
| `i18n reason.history_note` | „model używa tej częstości” (ostatnie 10) | model używa częstości ze wszystkich meczów | F-13 |
| `reasons.py` docstring | „mispricing… for or against only when its hypothesis was admitted” | po dopuszczeniu także sygnały innych linii są „przeciw” | F-11 |
| `docs/hipotezy_wyceny.md` H5 | „Gracz z niepewnym występem nie daje sygnału” | `role_signals` nie sprawdza szansy gry; zależy od wywołującego | dziś bez skutku (nieemitowany) |
| `mispricing_status.json` | H5 `untested` | dokument: „Przewidywanie zapisane przed oceną: H5a ❌” | spójne (przewidywanie ≠ werdykt), ale warto dopisać |
| `reason_lift.json` | — | brak wersji modelu i daty w pliku | nie da się automatycznie sprawdzić zgodności z modelem |

---

## 10. Testy i polecenia

| Plik | Co robi |
|---|---|
| `audit/reasons/test_reasons_audit.py` | 41 testów: 33 przechodzą (sprawdzone własności), 8 `xfail(strict)` = potwierdzone błędy F-01, F-02, F-05, F-06, F-10, F-11, F-12. Fixtures syntetyczne, oznaczone, tylko do matematyki i logiki. |
| `audit/reasons/harness.py` | Odtwarza panel dla zapisanych pobrań (bez zapisu do `data/`). |
| `audit/reasons/analyze.py` | Zlicza ustalenia na wyjściu harnessu, z niezależnym przeliczeniem ekonomii. |
| `audit/reasons/sensitivity.py` | Analiza wrażliwości. |

```
python -m pytest audit/reasons -q                        # 33 passed, 8 xfailed
python -m pytest audit/reasons -q --runxfail             # pokazuje 8 potwierdzonych błędów jako FAILED
python audit/reasons/harness.py --fetch 2026-11-10T20:00:00Z --out <katalog>     # ok. 6 min
python audit/reasons/harness.py --last-per-night 6 --out <katalog>
python audit/reasons/analyze.py <katalog> --json wynik.json
python audit/reasons/sensitivity.py <katalog>/fetch_20261110T200000Z.pkl
```

Pokrycie: Over i Under, linie połówkowe i całkowite, zwrot, mała próba i brak danych, zmiana roli i kursu, profile
kosztowe, kolidujące ostrzeżenia, H1, H2, H5, H6, EV blisko granicy.
Gdy błąd zostanie naprawiony, jego test zgłosi XPASS(strict): wtedy usunąć znacznik `xfail`.

---

## 11. Kolejność napraw (bez wdrażania)

1. **F-02** (nieobecni): zawsze pokazać zastosowaną korektę, z liczbą kolegów bez danych; nazwisko zamiast ID.
   Mała zmiana, duży zysk w wierności.
2. **F-01** (questionable): sprawdzać questionable tylko wśród linii, które mogłyby się zakwalifikować (bez czerwonej
   flagi), i po kroku „brak progu”.
3. **F-04 + F-07 + F-08** (mispricing): zestawić sygnał z oceną modelu w jednym zdaniu; status 🧪 i wynik eksploracji
   na początku; zamienić „linie zakładają” na „z naszego dopasowania wychodzi”; przed „pokrywa podatek” sprawdzać
   stabilność (np. strona niezmienna w 95% przedziale skuteczności) albo pisać, że jest niestabilna; wyłączyć FTM z H2.
4. **F-03 + F-17** (cena): rozbić „Model” na cenę, poprawkę kalibracji i wkład gracza; dodać zakres.
5. **F-10** (profil): przekazać profil kosztowy do `offer_signals`.
6. **F-13, F-14, F-18** (teksty): poprawić opis częstości trafień i nieobecnych, „Expected” → „Projekcja modelu”,
   „Superbet expects” → „z kursów Superbetu wynika”.
7. **F-06, F-05** (H6): „bardziej niż zwykle” tylko powyżej ligi; „1,0× = jak los (Poisson)”; `why` zależne od strony.
8. **F-19** (grupowanie): sekcje „Projekcja” i „Rola i minuty”, H1/H2/H6 jako jedna grupa obserwacji.
9. **F-11, F-12, F-15, F-16** przed dopuszczeniem progu lub hipotezy: kierunek tylko dla sygnałów tej linii; zwrot
   liczony bezwarunkowo; remis jako osobny status; przy bliskim EV obu stron napisać to w tytule.
10. Do `reason_lift.json` dopisywać wersję modelu i id kalibracji.
