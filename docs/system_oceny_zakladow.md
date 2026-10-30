# System oceny zakładów NBA (Superbet): interfejs, współczynniki i zasady decyzji

*Stan na 30 października 2026 r. (model `2026-10-26-count`, kalibracja z 30.10, linie Superbet rozliczone do 29.10).*
*Dokument opisuje to, co jest w kodzie i w danych, bez upiększeń. Ma służyć jako wspólna podstawa do planowania
rozwoju: poprawek modelu, przejrzystości interfejsu i nowych funkcji.*

---

## 0. Najważniejsze w pięciu zdaniach

1. Aplikacja wycenia **każdą linię zawodnika z Superbet** (Over/Under: punkty, zbiórki, asysty, trójki, sumy łączone
   i statystyki poboczne) oraz **rynki meczowe** (zwycięzca, handicap, suma punktów, sumy drużyn). Do wyceny używa
   statystyk ESPN, składów i nieobecności z RotoWire oraz samych kursów Superbet.
2. Dla każdej linii podaje **naszą szansę**, **przewagę nad kursem**, **oczekiwany zwrot na 100 zł**, sygnał
   (🟢/🟡/🔴), listę **powodów za i przeciw** oraz werdykt **Graj / Rozważ / Odpuść**.
3. **Uczciwie: na dziś system nie znalazł ani jednej linii z dodatnią przewagą.** Po kalibracji na wynikach
   historycznych model zostawia tylko ok. 13% swojej opinii, o ile różni się od kursu. Marża Superbet na propsach
   wynosi średnio **8,4%**, a tego ten ułamek nie odrabia. We wszystkich 46 932 zapisanych wycenach najwyższa przewaga
   to **−0,2 pp**. Na 12 901 rozliczonych liniach (10 nocy) lepsza strona według modelu wygrała 52,4% razy, z ROI
   **−4,8%**.
4. Model przewiduje wyniki **odrobinę lepiej niż sam kurs bez marży** (log loss 0,6842 wobec 0,6849 na nocach, których
   kalibracja nie widziała). To jednak trafność, a nie zysk. Model meczowy przewiduje **gorzej** niż kurs i dlatego
   nie daje żadnych sygnałów do gry.
5. System jest zbudowany tak, żeby **nie udawał przewagi**: brak ważnej kalibracji oznacza brak typów, brak
   potwierdzonego progu oznacza brak 🟢, a każda czerwona flaga oznacza „Odpuść”. Jego realna wartość to dziś
   **filtr i narzędzie analizy**: pokazuje, czego nie grać i dlaczego, oraz które linie tracą najmniej. Nie jest
   generatorem pewnych zakładów.

---

## 1. Źródła danych

| Źródło | Co dostarcza | Jak często | Plik |
|---|---|---|---|
| **ESPN** (JSON API) | Każdy mecz sezonu i linijka statystyk każdego zawodnika (PTS, REB, AST, 3PM, MIN, FGA, FTA, TO, PF, STL, BLK, +/-, pozycja, czy w pierwszej piątce) | rano (scraper dopisuje tylko nowe mecze) | `data/<sezon>/player_gamelogs.csv`, `games.csv` |
| **Superbet** | Linie zawodników z kursami Over i Under, rynki meczowe ze wszystkimi liniami | na żądanie (przycisk) i 2× dziennie z harmonogramu, najczęściej co 5 min | `superbet_props.csv`, `superbet_game_odds.csv` |
| **RotoWire** | Przewidywane i potwierdzone piątki, gracze „may not play” z szansą gry (%) i rodzajem urazu | na żywo co 30 min, zapis przy każdej zmianie | `rotowire_lineups.csv` |
| Historia | Linie Unibet 2022/23 (~40 000) z wynikami, dzienniki graczy z lat 2022–2026 | statycznie | `offers_resolved.csv`, `2022-players-logs.csv` |

Każdy pobrany zestaw kursów zapisuje się **razem z wyceną modelu z tamtej chwili** (typ, szansa, przewaga, sygnał,
flaga, wersja modelu, identyfikator kalibracji). Dzięki temu da się później uczciwie rozliczyć, co system
pokazywał przed meczem, bez dopasowywania wstecz.

**Seria czasowa:** Superbet od 20.10.2026 (34 pobrania, 46 932 wiersze linii), mecze do 29.10.

---

## 2. Interfejs

Są dwie wersje panelu (Streamlit). **Dashboard v2** (`streamlit run dashboard_v2/app.py --server.port 8502`) jest
główny: działa po polsku i angielsku, ma podpowiedzi przy każdej kolumnie i stronę „Jak to czytać”. Starszy dashboard
(port 8501) ma te same modele, a do tego **kupon z sugerowaną stawką** i **backtest reguł z 2022/23**. Tych dwóch
funkcji v2 jeszcze nie ma.

Każda strona v2 ma ten sam układ: tytuł z jednym zdaniem „na co odpowiada ta strona”, jeden rząd filtrów,
kluczowe liczby, jedna główna tabela, a pod nią szczegóły zaznaczonego wiersza w zakładkach. Pasek boczny zawsze
pokazuje świeżość danych 🟢/🟠/🔴 (ESPN, Superbet, RotoWire) i odsyła do Centrum danych, jeśli coś jest nieaktualne.

### 2.1 Dziś

| Strona | Co pokazuje |
|---|---|
| **Przegląd** | Karty dzisiejszych meczów (start czasu polskiego, kursy na zwycięzcę, handicap i sumę, prognozowany zwycięzca, status składów z RotoWire, kto nie zagra), 10 najlepszych linii zawodników i 5 największych przewag meczowych (te są tylko szacunkiem). Gdy żadna linia nie ma przewagi, lista nazywa się **„Najmniejsza strata”**. |
| **Zakłady na zawodników** | Wszystkie linie z wyceną, posortowane domyślnie po oczekiwanym zwrocie (🔴 zawsze na końcu). Tabela ma 12 kolumn decyzyjnych; reszta jest pod *Więcej → Pokaż każdą kolumnę*. Zaznaczona linia ma cztery zakładki: **Werdykt** (powody za i przeciw oraz jak zbudowano liczbę oczekiwaną: średnia → nieobecni koledzy → mecz i rywal), **Koledzy z drużyny** (macierz „z nim / bez niego”), **Historia** (20 ostatnich meczów wobec linii, rozkład, podziały, mecze z tym rywalem) i **Ruch linii** (każdy zapis). Na dole jest sprawdzarka dowolnej linii. |
| **Mecze** | Wiersz na mecz, potem rynki wybranego meczu z powodami za i przeciw najlepszemu wynikowi, ratingi drużyn, składy i nieobecności. |
| **Jak to czytać** | Słowniczek: kurs, marża, nasza szansa, przewaga, sygnały, ostrzeżenia, werdykt i 5 kroków wyboru zakładu. |

**Kolumny decyzyjne w tabeli propsów** (kolejność z `dashboard_v2/core/columns.py`):
zawodnik · mecz · start · statystyka · linia · **nasz typ** · **sygnał** · projekcja wskazuje · **przewaga (pp)** ·
**oczekiwany zwrot na 100 zł** · lepsza strona · kurs · nasza szansa % · oczekiwane dziś · trafione w ost. 10 % ·
rola dziś · ostrzeżenie.

Kolorowanie źródeł: 💰 pomarańczowy = Superbet, 📋 niebieski = RotoWire, 📊 zielony = wyliczone ze statystyk ESPN.

### 2.2 Analiza

- **Historia zawodnika:** forma (ostatnie 5/10 meczów wobec średniej, minuty), dziennik meczów na tle linii,
  rozkład z percentylami, średnie sezonowe i miesięczne, podziały (dom/wyjazd, pierwsza piątka/ławka, mecze dzień po
  dniu, minuty), wyniki z każdym rywalem, „z kolegą / bez kolegi”.
- **Historia drużyny:** bilans, miejsca w lidze, ratingi ataku i obrony w czasie, tempo, co obrona oddaje
  rozgrywającym, skrzydłowym i środkowym, skład.
- **Laboratorium składów:** dowolny skład i dowolni nieobecni. Heatmapa pokazuje, jak zmienia się statystyka gracza
  bez każdego kolegi, a pod nią szacunek dla wybranego scenariusza.

### 2.3 Przegląd wyników

- **Wyniki → Poprzednia noc:** każda linia i mecz rozliczone wobec naszej ostatniej projekcji przed startem. Widać,
  jak wypadły typy (wszystkie, 🟢🟡, 🔴) i jak często nasza oczekiwana liczba była bliżej wyniku niż linia Superbet.
  *Gdzie zakłady wygrywały* grupuje rozliczone linie dowolnie (statystyka, pozycja, dom/wyjazd, strona, sygnał,
  drużyna, mecz).
- **Wyniki → Wszystkie zapisane noce:** linie wobec średnich sprzed meczu, typy panelu, rynki meczowe, eksport CSV.
- **Backtest 2022/23:** model na liniach Unibet, tester strategii (filtry i reguła gry → trafienia, ROI, zysk
  narastająco), raport kalibracji.

### 2.4 Dane

**Centrum danych:** karta na każde źródło z przyciskami *Aktualizuj statystyki*, *Pobierz i zapisz* (Superbet),
*Zapis ze składami* i *Uruchom oba* (poranna rutyna). Jest tu log uruchomień i kontrola jakości: nazwiska bez
dopasowania do ESPN oraz czy punkty graczy sumują się do wyniku meczu.

---

## 3. Jak liczona jest wycena linii zawodnika

Kod: `dashboard/models.py::price_props`, `dashboard/metrics.py`. Poniżej kolejność obliczeń dla jednej linii,
np. „Gracz X, PTS, linia 22,5, Over 1,85 / Under 1,95”.

### 3.1 Próbka meczów

- Mecze z wybranego zakresu (domyślnie bieżący sezon: zasadniczy, play-in i play-off; **przedsezon wyłączony**,
  bo podstawowi grają w nim po ok. 21 min zamiast 33).
- **Dopełnienie:** jeśli gracz ma w tym sezonie mniej niż 10 meczów, dokładamy jego ostatnie mecze z poprzedniego
  sezonu, łącznie do 10. Te mecze liczą się do liczb samego gracza, ale nie do statystyk obron ani efektów
  nieobecności.

### 3.2 Liczby opisowe gracza

| Kolumna | Wzór / znaczenie |
|---|---|
| `avg`, `sd`, `avg L5` | średnia, odchylenie, średnia z ostatnich 5 meczów |
| `over %`, `under %` (sezon i L10) | odsetek meczów powyżej / poniżej linii (wynik równy linii całkowitej = zwrot, nie liczy się) |
| `pick % L10` | jak często lepsza strona wygrałaby w ostatnich 10 meczach |
| `percentile` | gdzie linia leży w wynikach gracza (50 = mediana) |
| `p30`, `p70`, `in band` | czy linia mieści się między 30. a 70. percentylem |
| `min L5` | średnie minuty z ostatnich 5 meczów |

### 3.3 Oczekiwana liczba na dziś (`proj avg`)

```
adj avg  = avg + lineup adj
proj avg = adj avg × pace factor × matchup factor
```

- **`lineup adj` (nieobecni koledzy):** dla każdego kolegi, którego RotoWire podaje z szansą gry **≤ 25%**,
  liczymy różnicę średniej gracza w meczach bez tego kolegi i z nim (tylko w okresach, gdy obaj byli w drużynie).
  Różnicę ściągamy do zera wagą `n / (n + 5)`, gdzie n to liczba meczów bez kolegi, i sumujemy po wszystkich
  nieobecnych. Gracze „questionable” (szansa 26–99%) nie wchodzą do tej korekty.
- **`pace factor` (tempo i oczekiwane punkty drużyny):** stosunek sumy drużyny implikowanej przez Superbet
  (`total/2 ∓ handicap/2`) do zwykłej średniej punktów drużyny.
- **`matchup factor` (rywal):** ile dana obrona oddaje grupie pozycji gracza (G/F/C) w tej statystyce, w stosunku do
  średniej ligi.
- Oba czynniki są **tłumione o połowę i ograniczone do ±8%**: `1 + clip(0,5 × (stosunek − 1), −8%, +8%)`. Mecz
  i rywal zmieniają liczby gracza znacznie słabiej niż 1:1, bo jego minuty i rola zostają te same.

### 3.4 Surowa szansa modelu (`raw model %`)

Średnia dwóch szacunków. Oba są ściągnięte do szansy z kursu bez marży (`market %`), tak jakby rynek był wart
**10 meczów** obserwacji:

1. **Hit rate:** `(trafienia + 10 × market) / (n + 10)`. Dzięki temu 4 z 5 meczów nie czyta się jako 80%.
2. **Rozkład:** szansa przekroczenia linii z rozkładu zliczeń (**ujemny dwumianowy**, a gdy wyniki gracza wahają się
   mniej niż średnia, **Poisson**) wokół `proj avg`, z wariancją gracza skalowaną do projekcji. Następnie ważone
   `n/(n+10)` z rynkiem. Rozkład zliczeń zastąpił 26.10 rozkład normalny, bo na 2022/23 dał nieznacznie lepszą
   trafność (najbardziej na 3PM).

Przy mniej niż 3 meczach liczy się tylko hit rate. Na linii całkowitej Over, Under i zwrot sumują się do 1.

**„Zakres 95%” (`edge low`)** to `p ± 1,96·√(p(1−p)/(n+11))`, czyli szum losowy samego hit rate. **Nie jest to
przedział predykcji**: nie zawiera błędu projekcji ani błędu modelu (otwarty punkt F6 audytu).

### 3.5 Kalibracja: ile opinii modelu przetrwało zderzenie z wynikami

Surowy model był **zbyt pewny siebie**: w 2022/23 typy z szansą 60–70% wygrywały 54,5%. Dlatego każdą szansę
przepuszczamy przez kalibrację dopasowaną na wynikach:

```
model % = sigmoid( a · logit(market) + b · (logit(raw) − logit(market)) )
```

Aktualnie **a = 1,140, b = 0,132** (84 464 strony linii: Unibet 2022/23 i każda rozliczona linia Superbet; ostatnia
noc 29.10). Kalibracja odświeża się automatycznie po każdej nowej rozliczonej nocy.

- **b = 0,132** oznacza, że zostaje ok. 13% różnicy między modelem a rynkiem (w skali logitowej).
- **a > 1** oznacza, że faworyci rynku wygrywali nieco częściej, niż mówił kurs bez marży.
- Bias Over/Under **celowo nie jest dopasowywany** (od 26.10). Ten wyuczony na Unibet 2022/23 nie przenosił się na
  Superbet i pogarszał trafność.

**Przykład, dlaczego nie ma przewagi:** rynek 50/50, kursy 1,84/1,84 (marża ok. 8,7%), surowy model daje Over 60%.
Po kalibracji wychodzi 51,3%, a próg rentowności kursu 1,84 to 54,3%, więc przewaga wynosi **−3,0 pp**. Żeby przy
takim rynku wyjść na plus, surowy model musiałby dać ok. **79%**. To się praktycznie nie zdarza, i słusznie, bo takim
skrajnościom modelu nie można ufać.

### 3.6 Współczynniki decyzyjne

| Kolumna (PL w panelu) | Wzór | Jak czytać |
|---|---|---|
| **szansa wg bukmachera %** (`market %`) | `(1/kurs_strony) / (1/kurs_over + 1/kurs_under)` | kurs bez marży |
| **potrzebna skuteczność %** (`break-even %`) | `100 / kurs` | ile trzeba trafiać, żeby wyjść na zero |
| **nasza szansa %** (`model %`) | skalibrowana szansa z 3.5 | |
| **przewaga (pp)** (`edge pp`) | `model % − break-even %` | > 0 oznacza, że kurs płaci więcej niż ryzyko |
| **przewaga ostrożnie (pp)** (`edge low`) | to samo dla dolnego końca zakresu | ile zostaje, jeśli dotychczasowe wyniki gracza były po części szczęściem |
| **oczekiwany zwrot na 100 zł** (`ev 100`) | `model % × kurs − 100` | ranking wartości; szansa sama w sobie głównie odzwierciedla kurs |
| **lepsza strona** (`best side`) | strona z większą przewagą, nawet ujemną | to jeszcze nie jest typ |
| **nasz typ** (`bet`) | lepsza strona tylko przy 🟢/🟡, w przeciwnym razie „odpuść” | |
| **projekcja wskazuje** (`lean`) | Over/Under, gdy `proj avg` odbiega od linii o ≥ ok. 10% (log) | **wyłącznie informacja**: sama projekcja nie pobiła kursów Superbet |

---

## 4. Sygnały i werdykt

### 4.1 Sygnał w tabeli

| Sygnał | Warunek | Stan dziś |
|---|---|---|
| 🟢 | przewaga ≥ próg, którego typy na **co najmniej 10 nocach niewidzianych przez kalibrację** (50+ zakładów) dały zysk i wygrywały częściej niż próg rentowności **nawet na dolnym końcu 95% przedziału** | **brak progu, więc brak 🟢** |
| 🟡 | dowolna dodatnia **szacowana** przewaga (niepotwierdzona) | 0 linii |
| 🔴 | czerwona flaga (sekcja 5.2), niezależnie od liczb | ok. 18% linii |
| (puste) | przewaga ≤ 0, czyli „odpuść” | pozostałe |

Bez kalibracji dopasowanej do bieżącej wersji modelu **żadna linia nie dostaje 🟢/🟡, typu ani stawki**, a panel
pokazuje ostrzeżenie. To zabezpieczenie przed cichym użyciem przesadnie pewnego surowego modelu.

### 4.2 Werdykt Graj / Rozważ / Odpuść (`reasons.verdict`)

Decyzja przechodzi po kolei przez warunki; pierwszy spełniony rozstrzyga:

1. Jest **czerwona flaga** → **Odpuść** (podajemy pierwszą flagę).
2. To **rynek meczowy** → **Odpuść** („model meczów nie jest skalibrowany, przewaga to szacunek”).
3. Brak ważnej kalibracji → **Odpuść**.
4. Przewaga ≤ 0 → **Odpuść** („kurs nie płaci wystarczająco za tę szansę”).
5. Przewaga ≥ próg 🟢 **i** więcej powodów za niż przeciw → **Graj**.
6. Powodów za co najmniej tyle, co przeciw → **Rozważ** (z dopiskiem „niepotwierdzona 🟡”, jeśli nie ma 🟢).
7. W przeciwnym razie → **Odpuść** („dodatnia przewaga, ale więcej powodów przeciw”).

**Ważne dla oceny metody:** powody za i przeciw liczy się **jednym głosem każdy, bez wag**, a sam powód „Model”
(dodatnia przewaga) też jest jednym z głosów za. Liczenie głosów **nie było walidowane na wynikach**. To heurystyka
porządkująca argumenty, a nie część wyliczonej szansy. Szansa i przewaga pochodzą wyłącznie z sekcji 3.

---

## 5. Powody za i przeciw: zakłady na zawodników

Kod: `dashboard/reasons.py::prop_reasons`. Każdy powód jest **za** wybraną stroną, **przeciw** niej albo
**neutralny** (kontekst). „Za Over” oznacza, że liczba wskazuje w górę; dla Under ten sam fakt działa odwrotnie.

### 5.1 Powody (z progami)

| # | Powód (tekst w panelu) | Kiedy się pojawia | Za / przeciw |
|---|---|---|---|
| 1 | **Model:** „Over wygrywa w X%; kurs K wymaga Y% (przewaga ±Z pp, ±W przy ostrożnym odczycie)” | zawsze, gdy jest wycena | za, gdy przewaga > 0 |
| 2 | **Trafienia, ostatnie 10:** „Over w h z ostatnich 10 meczów (r%; potrzeba Y%)” | ≥ 3 mecze | za, gdy r > próg rentowności |
| 3 | **Trafienia, cały sezon** | > 10 meczów | jw. |
| 4 | **Oczekiwane dziś:** „Oczekiwane dziś P wobec linii L (±d); średnia, mediana” | ≥ 1 mecz | neutralny, gdy \|d\| < max(0,5; 3% linii), poza tym za/przeciw zależnie od kierunku |
| 5 | **Minuty:** „Ostatnio więcej / mniej minut: ost. 5 wobec średniej” | ≥ 6 meczów i różnica ≥ 3 min | więcej minut działa za Over |
| 6 | **Nieobecni koledzy:** „A, B nie zagra: gracz zwykle ma +x bez nich” | `lineup adj` ≠ 0 | dodatnie działa za Over |
| 7 | **Dom / wyjazd:** średnia w meczach u siebie lub na wyjeździe wobec ogólnej | ≥ 6 meczów, ≥ 3 w danym miejscu | neutralny przy różnicy < 5% |
| 8 | **Mecz dzień po dniu:** średnia w takich meczach | dziś drugi mecz z rzędu | za Over tylko, gdy w takich meczach gracz miał więcej (≥ 2 mecze); bez danych liczy się przeciw Over |
| 9 | **Rywal:** „OPP pozwalają [pozycji] na v na mecz, o d więcej / mniej niż przeciętnie (miejsce r z 30): miękki / twardy rywal” | znana pozycja i rywal | miękki (≥ +5%) działa za Over, twardy (≤ −5%) przeciw, przeciętny jest neutralny |
| 10 | **Historia z rywalem:** średnia w meczach z tym rywalem (wszystkie sezony) | ≥ 2 mecze | średnia > linii działa za Over |
| 11 | **Oczekiwane punkty drużyny:** „Superbet oczekuje, że drużyna zdobędzie X (zwykle Y)” | różnica ≥ 3% | więcej punktów działa za Over |
| 12 | **Ryzyko pogromu:** „faworyt / słabszy o S: przy pogromie podstawowi siedzą w 4. kwarcie” | \|handicap\| ≥ 10 i gracz z pierwszej piątki | **zawsze przeciw Over** (za Under) |
| 13 | **Ruch linii:** „Linia wzrosła / spadła o m od pierwszego zapisu (rynek poszedł w twoją stronę / przeciw tobie)” | linia się ruszyła | ruch w stronę typu działa za |

### 5.2 Czerwone flagi: każda sama oznacza „Odpuść” (🔴)

| Flaga | Warunek |
|---|---|
| Za mało meczów | < **8** meczów w próbce |
| Tylko przedsezon | wszystkie mecze w próbce to przedsezon |
| Może nie zagrać | RotoWire: szansa gry między 1% a 99% |
| Niestabilne minuty | ≥ 5 meczów i współczynnik zmienności minut > **0,35** |
| Linia przeciw typowi | linia ruszyła się o **≥ 1,5** w stronę przeciwną do typu („rynek może coś wiedzieć”) |

Gracze z szansą gry 0% są domyślnie ukryci.

---

## 6. Rynki meczowe (drużyny)

Kod: `metrics.game_projection`, `models.price_games`, `reasons.game_reasons`.

### 6.1 Model meczu

- **Ratingi:** atak i obrona na 100 posiadań oraz tempo (posiadania = FGA + 0,44·FTA + TO − OREB). Bieżący sezon
  waży `n/(n+10)`, reszta to zeszły sezon, wcześniej ściągnięty w 30% do średniej ligi (przez lato zmieniają się
  składy).
- **Punkty:** `tempo × (atak drużyny + obrona rywala − średnia ligi) / 100 ± 0,75` (przewaga własnej hali to
  1,5 pkt, dzielona po połowie).
- **Nieobecni** (RotoWire, szansa gry ≤ 25%): zmiana punktów zdobytych i straconych drużyny w meczach bez tego gracza,
  ściągnięta wagą `n/(n+5)`.
- **Szanse:** rozkład normalny wokół projekcji, SD 14 pkt dla różnicy, 18 dla sumy, 11,5 dla sumy drużyny.
- Przewaga meczu to szansa modelu minus `100/kurs` (bez usuwania marży).

### 6.2 Powody za i przeciw (mecze)

- **Zwycięzca / handicap:** prognozowana różnica punktów (czy pokrywa handicap), bilans netto obu drużyn, atut
  własnej hali, każdy nieobecny z efektem ≥ 0,5 pkt na różnicę.
- **Sumy:** prognoza wobec linii, tempo wobec ligi (neutralne przy < 1 posiadaniu różnicy), atak drużyny wobec obrony
  rywala, nieobecni z efektem ≥ 0,5 pkt.

### 6.3 Flagi meczowe

Początek sezonu (którakolwiek drużyna ma < 5 meczów), brak meczu w RotoWire, przewaga > 15 pp (bardziej
prawdopodobne, że model czegoś nie wie, niż że rynek tak bardzo się myli).

### 6.4 Status

**Rynki meczowe nigdy nie dostają 🟢/🟡, werdyktu „Graj/Rozważ” ani stawki.** Na 988 rozliczonych wynikach
(9 nocy) model meczowy przewiduje **gorzej niż kurs** (log loss 0,7248 wobec 0,6730). Jego typy z przewagą > 0
oczekiwały 65,8% trafień, a trafiły **50,6%** (ROI −4,2%). Najgorzej wypada handicap (0,884 wobec 0,681).
Kalibracja meczów powstanie automatycznie przy 300+ wynikach z 10+ nocy, czyli niedługo. Same dane jednak już
pokazują, że model wymaga przebudowy, a nie tylko kalibracji.

---

## 7. Stawki i kupon (stary dashboard)

- **Ćwierć Kelly'ego**, maksymalnie 5% bankrolla: `0,25 × (p·kurs − 1)/(kurs − 1)`. Przy propsach `p` to **dolny
  koniec zakresu** szansy, więc cienka przewaga dostaje mniej. Rynki meczowe i linie bez ważnej kalibracji
  dostają stawkę 0.
- Ostrzeżenia na kuponie: kilka zakładów na jednego gracza, obie strony jednej linii, kilka Overów (lub Underów)
  w jednym meczu, zbyt duża część bankrolla na jedną noc.
- Postawione zakłady trafiają do `my_bets.csv` i są rozliczane tymi samymi regułami co reszta (kurs postawiony
  wobec ostatniego kursu przed meczem).

---

## 8. Rozliczanie i śledzenie

- Jeden zestaw reguł dla wszystkiego (`metrics.side_result` / `side_profit`): **settled** (wygrana/przegrana/zwrot),
  **void** (mecz zapisany z kompletnym boxscore, a gracz nie zagrał; Superbet zwraca stawkę), **pending** (meczu
  jeszcze nie ma), **unresolved** (nie da się rozstrzygnąć: niezidentyfikowany gracz, niekompletny boxscore, mecz
  przełożony). Linii nierozstrzygniętych nie zgadujemy, tylko je liczymy.
- „Zakład” to **pierwszy zapis linii przed meczem**, a „ostatni kurs przed meczem” to ostatni zapis. Przy 2–3
  zapisach dziennie **nie jest to prawdziwy kurs zamknięcia**, dlatego panel pokazuje, ile godzin przed startem był
  zapis.
- Kalibrację ocenia się na **ostatnim zapisie przed startem**; dane przed 26.10 zostały odtworzone z historii gita.

---

## 9. Walidacja: co wiemy, a czego nie

### 9.1 Trafność (log loss, im niżej, tym lepiej; noce niewidziane przez dopasowanie)

| Źródło | Kurs bez marży | Model surowy | Model skalibrowany |
|---|---|---|---|
| Unibet 2022/23, luty–maj (13 763 linie) | 0,6895 | 0,7051 | **0,6893** |
| Superbet 27–29.10.2026 (3 133 linie) | 0,6849 | 0,6926 | **0,6842** |

Skalibrowany model jest odrobinę lepszy od kursu, a surowy wyraźnie gorszy. Na kalibracji widać, że szanse
skalibrowane zgadzają się z częstością wygranych (np. Superbet: przewidziane 57,1%, wygrane 62,1%; przewidziane 62%,
wygrane 56,1%; to rozrzut typowy dla 3 nocy).

### 9.2 Zysk

| Strategia (Superbet, noce 27–29.10, 1 j. na linię) | Trafienia | ROI |
|---|---|---|
| Zawsze Under | 51,2% | −6,3% |
| Zawsze Over | 48,8% | −9,6% |
| Lepsza strona modelu, każda linia | **55,4%** | **−3,2%** |
| Typ z przewagą > 0 | 0 zakładów | – |

Na całej rozliczonej historii Superbet (12 901 linii, 20–29.10, pierwszy zapis przed meczem) lepsza strona modelu
trafia **52,4%**, z ROI **−4,8%**: −4,4% bez flag, −6,7% dla 🔴. Flagi więc odsiewają linie gorsze od przeciętnej.
Lepsza strona modelu traci mniej niż ślepa gra, ale **nie pokonuje marży**.

Na Unibet 2022/23 (luty–maj) dodatnią przewagę miało 305 linii: trafienia 57,0% przy progu rentowności 57,1%,
ROI −0,7%. Też nie ma przewagi.

### 9.3 Co wnosi każda część modelu (`data/backtest/ablation.md`)

Na 2022/23 dane gracza (hit rate, rozkład) poprawiają trafność względem kursu o ok. 0,0005–0,0007 log loss
(przedział nieznacznie poniżej zera). **Nieobecni** (nawet w wersji „wyrocznia”, ze znanymi faktycznymi
nieobecnościami) i **rywal** nie dodają nic mierzalnego.

Na Superbet (powtórzone 30.10: dopasowanie na 7 nocach 20–26.10, ocena na 3 nocach 27–29.10, 2 928 linii):

| Szczebel | Log loss | Wobec kursu | Przedział 95% |
|---|---|---|---|
| 1. Kurs bez marży | 0,6851 | 0 | – |
| 2. + bias Over/Under | 0,6846 | −0,0005 | −0,0015…+0,0014 |
| 3. Hit rate | 0,6841 | −0,0010 | −0,0027…+0,0021 |
| 4. Rozkład wokół średniej | **0,6835** | **−0,0016** | −0,0035…+0,0017 |
| 5. Hit rate + rozkład | 0,6838 | −0,0013 | −0,0031…+0,0019 |
| 6. + nieobecni | 0,6838 | −0,0013 | jw. |
| 7. + suma drużyny z kursu | 0,6837 | −0,0014 | −0,0033…+0,0022 |
| 8. + rywal = pełny model | 0,6842 | −0,0009 | −0,0026…+0,0022 |

Wnioski: na 2 nocach (25.10) każdy szczebel był **gorszy** od kursu, a teraz każdy jest **lepszy**. Żaden przedział nie
leży jednak w całości poniżej zera, więc **poprawa nie jest jeszcze potwierdzona**. Najlepiej wypada sam rozkład
zliczeń wokół średniej. Nieobecni nie zmieniają nic, a rywal pogarsza wynik (0,6837 → 0,6842). Gra na dodatnie
przewagi każdego szczebla dalej przynosi stratę (pełny model: 87 zakładów, 62,1% trafień przy progu 66,3%, ROI
−6,0%). Obecny sposób kalibracji (tylko a i b) jest zgodny z danymi: bias per bukmacher daje praktycznie to samo
(0,6841 wobec 0,6844) przy dużo szerszym przedziale. Następna sensowna kontrola przypada przy ok. 33 rozliczonych
nocach (koniec listopada), kiedy noce testowe wystarczą też do oceny progu 🟢.

### 9.4 Znane ograniczenia (uczciwie)

1. **Marża Superbet ok. 8,4% na propsach** (w 80% przypadków 7,5–9,7%). Próg rentowności przy linii 50/50 to ok.
   54,2%. Informacja ze statystyk publicznych ESPN jest w kursach w dużej mierze już uwzględniona.
2. **Próg 🟢 jest wybierany i sprawdzany na tych samych nocach testowych** i wybierany ponownie po każdej nocy, więc
   ma charakter eksploracyjny. Czysta walidacja wymaga osobnego, nietkniętego okresu.
3. **Historia testowa to inny bukmacher** (Unibet 2022/23, bez kursów meczowych, bez RotoWire, pozycje dopisane
   z lat 2024–26).
4. **„Zakres 95%” nie jest przedziałem predykcji** (F6), a po kalibracji (b ≈ 0,13) prawie znika.
5. **Powody i werdykt nie są walidowane** jako osobny sygnał, a wszystkie głosy mają tę samą wagę.
6. **Model meczowy jest słaby** (wczesny sezon to głównie zeszły sezon, nie zna letnich transferów, nieobecni liczą
   się tylko wtedy, gdy drużyna już grała bez danego gracza).
7. **Brak prawdziwego kursu zamknięcia** (2–3 zapisy dziennie), więc nie mierzymy rzetelnie CLV.
8. **Gracze bez meczów w danych** (debiutanci, długo kontuzjowani) nie wchodzą do korekty nieobecności.
9. **Mała próba Superbet**: 10 nocy to za mało na pewne wnioski w którąkolwiek stronę.
10. Statystyki poboczne (FGA, FGM, FTA, FTM, PF, TO) stanowią prawie połowę linii, ale model wycenia je tak samo
    jak główne, bez osobnej oceny.

---

## 10. Kierunki rozwoju (do dyskusji z konsultantem)

### 10.1 Przejrzystość interfejsu

- **Jasny komunikat na górze strony**, gdy nie ma przewagi: „Dziś żadna linia nie pokonuje marży. Najmniejsza strata
  to −X zł na 100 zł”. Sortowanie po stracie jest już zrobione, ale przekaz można wzmocnić.
- **Rozdzielić „trafność” od „opłacalności”**: wysoka nasza szansa przy kursie 1,30 to nie wartość. Rozważyć ukrycie
  „naszej szansy” na rzecz „przewagi” i „zwrotu na 100 zł”.
- **Wagi powodów:** pokazywać, które powody są uwzględnione w szansie (oczekiwane dziś, nieobecni, tempo, rywal), a
  które są tylko kontekstem (dom/wyjazd, mecz dzień po dniu, historia z rywalem, minuty, pogrom). Obecnie wyglądają
  na równoważne.
- **Kupon i stawki w v2** (dziś tylko w v1).
- Tablica wyników „na żywo”: skuteczność systemu do dziś na jednej karcie (ROI, liczba nocy, przedział), widoczna od
  razu na Przeglądzie.

### 10.2 Model i metoda

- Powtórzyć **ablację na 10+ nocach Superbet**; dopiero po niej decydować o dalszych zmianach.
- **Walidować powody:** dla każdego powodu sprawdzić na rozliczonych liniach, czy zgodność z nim zmienia trafienia
  i ROI. Powody bez wartości zdegradować do kontekstu, a te z wartością włączyć do szansy.
- **Osobny, nietknięty okres walidacji** dla progu 🟢 (np. listopad), żeby usunąć problem F4.
- **Projekcja minut** jako osobny krok (minuty × wydajność na minutę), bo minuty są główną niewiadomą przy
  nieobecnościach i pogromach.
- **Gęstsze zapisy kursów** (np. 60 i 15 min przed startem) do pomiaru CLV i wykrywania ruchów rynku.
- **Model meczowy do przebudowy** (handicap jest wyraźnie gorszy niż kurs) albo jawne wyłączenie go z rekomendacji.
- **Selekcja rynków:** sprawdzić, czy na którejś grupie (statystyka × pozycja × rola) model ma przewagę, z korektą
  na wielokrotne testowanie.
- **Inne źródła informacji, których rynek może nie mieć w cenie:** szybkość reakcji na zmiany składów (RotoWire →
  linia), raporty minut i ograniczeń po kontuzjach.

### 10.3 Pytania do konsultanta

1. Jak zakomunikować użytkownikowi „brak przewagi” tak, żeby narzędzie nadal było użyteczne (filtr, analiza), a nie
   zniechęcało?
2. Czy „najmniejsza strata” to rozsądna funkcja, czy zachęca do gry bez przewagi?
3. Jaki format uzasadnienia (lista powodów, punktacja, jedno zdanie) jest najbardziej zrozumiały i najmniej
   wprowadza w błąd?
4. Które rynki i jakie progi (minimalna przewaga, minimalna liczba meczów) użytkownik uzna za wiarygodne?
5. Jak pokazywać niepewność (przedziały, liczba nocy), żeby nie była ignorowana?

---

## Załącznik A: gdzie co jest w kodzie

| Element | Plik |
|---|---|
| Wycena propsów i meczów, kalibracja w użyciu, sygnały | `dashboard/models.py` |
| Wzory (hit rate, rozkład, kalibracja, rywal, tempo, nieobecni, model meczu) | `dashboard/metrics.py` |
| Powody, flagi, werdykt | `dashboard/reasons.py` |
| Teksty PL/EN, podpowiedzi kolumn | `dashboard/i18n.py` |
| Stawki i kupon | `dashboard/bets.py` |
| Rozliczanie | `dashboard/tracking.py`, `dashboard/nightly.py` |
| Kalibracja i próg 🟢 | `backtest/calibrate.py` → `data/backtest/calibration.json`, `calibration.md` |
| Ablacja (co wnosi każda część) | `backtest/ablation.py` → `data/backtest/ablation.md` |
| Audyt metodologii | `docs/methodology_audit.md` |
| Zapisy kursów z wyceną | `daily_snapshot.py` |

## Załącznik B: kluczowe stałe

| Stała | Wartość | Znaczenie |
|---|---|---|
| Waga rynku w szansie | 10 meczów | ściąganie hit rate i rozkładu do kursu |
| Dopełnienie próbki | do 10 meczów | z zeszłego sezonu |
| Gracz „out” | szansa gry ≤ 25% | wchodzi do korekty nieobecności |
| Ściąganie efektu nieobecności | n/(n+5) | n = mecze bez gracza |
| Tłumienie tempa i rywala | 0,5, limit ±8% | |
| Miękki / twardy rywal | ±5% wobec średniej ligi | |
| Projekcja wskazuje | ok. 10% od linii | tylko informacja |
| Min. meczów (flaga) | 8 | |
| Niestabilne minuty | CV > 0,35 | |
| Ruch linii przeciw | ≥ 1,5 | |
| Ryzyko pogromu | handicap ≥ 10 | |
| Kalibracja | a = 1,140, b = 0,132 | |
| Próg 🟢 | brak | 10+ nocy, 50+ zakładów, dolny koniec 95% powyżej progu rentowności |
| Kelly | 0,25, max 5% | dolny koniec szansy |
| Model meczu | hala 1,5; SD 14 / 18 / 11,5; regresja 30%; prior 10 meczów | |
