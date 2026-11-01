# System oceny zakładów NBA (Superbet): interfejs, współczynniki i zasady decyzji

*Stan na 30 października 2026 r. (model `2026-10-26-count`, kalibracja z 30.10, linie Superbet rozliczone do 29.10);
sekcje 0, 2.1, 3.6, 4–7 zaktualizowane 31.10 o kontrakt kosztowy i decyzje (fazy 1–2); 1.11 dodany ranking
„Najlepsze dziś” (sekcje 0, 2.1, 4.1, 9.2, 10).*
*Dokument opisuje to, co jest w kodzie i w danych, bez upiększeń. Ma służyć jako wspólna podstawa do planowania
rozwoju: poprawek modelu, przejrzystości interfejsu i nowych funkcji.*

---

## 0. Najważniejsze w pięciu zdaniach

1. Aplikacja wycenia **każdą linię zawodnika z Superbet** (Over/Under: punkty, zbiórki, asysty, trójki, sumy łączone
   i statystyki poboczne) oraz **rynki meczowe** (zwycięzca, handicap, suma punktów, sumy drużyn). Do wyceny używa
   statystyk ESPN, składów i nieobecności z RotoWire oraz samych kursów Superbet.
2. Dla każdego meczu podaje **jedną decyzję dla rynków drużynowych** i **jedną dla zawodników**: *Obstaw*,
   *Nie obstawiaj*, *Czekaj* albo *Niedostępne*. Dla każdej linii pokazuje **naszą szansę**, **przewagę po
   podatku**, **oczekiwany zwrot na 100 zł po podatku** i **powody za i przeciw**, które objaśniają decyzję, ale
   jej nie zmieniają.
3. **Uczciwie: na dziś system nie znalazł ani jednej linii z dodatnią przewagą.** Po kalibracji na wynikach
   historycznych model zostawia tylko ok. 13% swojej opinii, o ile różni się od kursu. Marża Superbet na propsach
   wynosi średnio **8,4%**, a do tego Superbet zatrzymuje **12% stawki** jako podatek (od 31.10 wliczony w każdą
   cenę: przy kursie 1,84 trzeba trafiać 61,8%, nie 54,3%); tego ten ułamek nie odrabia. We wszystkich 46 932 zapisanych wycenach najwyższa przewaga
   to **−0,2 pp**. Na 12 901 rozliczonych liniach (10 nocy) lepsza strona według modelu wygrała 52,4% razy, z ROI
   **−4,8%**.
4. Model przewiduje wyniki **odrobinę lepiej niż sam kurs bez marży** (log loss 0,6842 wobec 0,6849 na nocach, których
   kalibracja nie widziała). To jednak trafność, a nie zysk. Model meczowy przewiduje **gorzej** niż kurs i dlatego
   nie daje żadnych sygnałów do gry.
5. System jest zbudowany tak, żeby **nie udawał przewagi**: *Obstaw* wymaga progu zapisanego na niezależnym okresie,
   a takiego progu nie ma, więc żadna oferta go nie dostaje; rynki drużynowe są zawsze *Niedostępne*; brak kursu lub
   składu daje *Czekaj*. Jego realna wartość to dziś **filtr i narzędzie analizy**: pokazuje, czego nie grać i
   dlaczego. Nie jest generatorem pewnych zakładów. Od 1.11 obok decyzji jest **ranking „Najlepsze dziś”**
   (sekcja 4.1): odpowiada na pytanie „jeśli i tak gram, to co?”, z widocznym kosztem i własnymi wynikami. To nie
   przewaga i nie zmienia decyzji.

---

## 1. Źródła danych

| Źródło | Co dostarcza | Jak często | Plik |
|---|---|---|---|
| **ESPN** (JSON API) | Każdy mecz sezonu i linijka statystyk każdego zawodnika (PTS, REB, AST, 3PM, MIN, FGA, FTA, TO, PF, STL, BLK, +/-, pozycja, czy w pierwszej piątce) | rano (scraper dopisuje tylko nowe mecze) | `data/<sezon>/player_gamelogs.csv`, `games.csv` |
| **Superbet** | Linie zawodników z kursami Over i Under, rynki meczowe ze wszystkimi liniami | harmonogram w działającym dashboardzie v2 (co godzinę oraz T−60/40/20/10/5 min przed każdym meczem) i na żądanie (przycisk, najczęściej co 5 min) | `superbet_props.csv`, `superbet_game_odds.csv` (snapshot z wyceną), `superbet_prop_quotes.csv`, `superbet_game_quotes.csv`, `superbet_event_fetches.csv` (notowania, 8.1) |
| **RotoWire** | Przewidywane i potwierdzone piątki, gracze „may not play” z szansą gry (%) i rodzajem urazu | przy każdym pobraniu z harmonogramu i na żywo co 30 min, zapis przy każdej zmianie | `rotowire_lineups.csv` |
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
| **Przegląd** | Karty dzisiejszych meczów (start czasu polskiego, kursy na zwycięzcę, handicap i sumę, **decyzja dla rynków drużynowych i decyzja dla zawodników** z czasem kursu i składu, prognozowany zwycięzca, status składów z RotoWire, kto nie zagra). Pod kartami *Oferty do gry*: tylko oferty z decyzją *Obstaw*; dopóki ich nie ma, strona mówi, że dziś nie ma na co grać. Pod spodem zawsze **„Dzisiejsze oceny: 4★ = najlepsze dziś, nie: opłacalne”** (4.1): linie 4★ i w rozwijanej liście 3★, z oczekiwanym zwrotem po podatku obok średniej każdej linii i jednym zdaniem o dotychczasowych wynikach 4★. |
| **Zakłady na zawodników** | Nad tabelą decyzja dla zawodników każdego meczu z czasem kursu i składu. Tabela (16 kolumn, domyślnie według startu meczu, ostrzeżenia na końcu) służy do analizy; reszta kolumn jest pod *Więcej → Pokaż każdą kolumnę*. Zaznaczona linia zostaje otwarta po odświeżeniu, a gdy zmieniła się jej linia lub kurs, strona to mówi. Zakładki: **Werdykt** (decyzja meczu i „Dlaczego”: powody za i przeciw z wartością, punktem odniesienia, liczbą obserwacji, czasem i źródłem, oraz jak zbudowano liczbę oczekiwaną: średnia → nieobecni koledzy → mecz i rywal), **Koledzy z drużyny** (macierz „z nim / bez niego”), **Historia** (20 ostatnich meczów wobec linii, rozkład, podziały, mecze z tym rywalem) i **Ruch linii** (każdy zapis). Na dole jest sprawdzarka dowolnej linii. |
| **Mecze** | Wiersz na mecz z jego dwiema decyzjami (rynki drużynowe: *Niedostępne*; zawodnicy), potem rynki wybranego meczu do analizy; powody otwierają się dla wiersza, który wybierzesz (żaden „najlepszy” wynik nie jest wybierany za użytkownika). Ratingi drużyn, składy i nieobecności. |
| **Jak to czytać** | Słowniczek: kurs, podatek i marża, nasza szansa, przewaga, decyzja, ostrzeżenia, powody i 4 kroki czytania wieczoru. |

**Kolumny tabeli propsów** (kolejność z `dashboard_v2/core/columns.py`, 17):
ocena (★★★★☆, 4.1) · zawodnik · mecz · start · statystyka · linia · **decyzja** · **oceniana strona** · kurs · nasza szansa wygranej % ·
potrzebna skuteczność po podatku % · **przewaga po podatku (pp)** · **oczekiwany zwrot na 100 zł po podatku** ·
oczekiwane dziś · trafione w ost. 10 % · rola dziś · ostrzeżenie. Kolumny legacy „nasz typ”, „lepsza strona” i
„projekcja wskazuje” nie są już pokazywane obok siebie (zostają w danych).

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
*Zapis ze składami* i *Uruchom oba* (poranna rutyna). Karta **Pobieranie według harmonogramu** (8.1) ma włącznik,
opcję „Nie usypiaj komputera”, stan, następne pobranie, ostatni przebieg, pominięte terminy, blokadę Superbetu
i dzisiejsze zużycie budżetu zapytań. Jest tu log uruchomień i kontrola jakości: nazwiska bez
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

### 3.6 Współczynniki: dwa kontrakty kosztowe

Od 31.10 każda cena jest liczona w profilu kosztowym (`metrics.COST_PROFILES`). Panele używają profilu
`superbet_standard` (alpha = 0,88: Superbet zatrzymuje 12% stawki, więc wygrana to 0,88 × stawka × kurs). Profil
`legacy` (alpha = 1, kurs bez podatku) to sposób, w jaki liczone były i są wszystkie zapisane pola, backtest 2022/23,
kalibracja i ablacja, więc dawne wyniki dają się odtworzyć. Podatku 10% od dużych wygranych domyślnie nie odejmujemy.
Zwrot (wynik równy linii całkowitej) nie jest ani wygraną, ani przegraną: P(wygrana) + P(przegrana) + P(zwrot) = 1,
a zwrot oddaje stawkę w obu profilach.

| Kolumna (PL w panelu) | Wzór | Jak czytać |
|---|---|---|
| **szansa wg bukmachera %** (`market %`) | `(1/kurs_strony) / (1/kurs_over + 1/kurs_under)` | kurs bez marży; dla meczów liczony w parze stron jednego rynku |
| **oceniana strona** (`side`) | strona z wyższym `ev net 100` | strona, którą ocenia decyzja; to nie typ |
| **nasza szansa wygranej %** (`p win %`) | skalibrowana szansa z 3.5 dla ocenianej strony | |
| **szansa zwrotu %** (`p push %`) | na linii całkowitej `1 − P(Over) − P(Under)`, inaczej 0 | |
| **potrzebna skuteczność po podatku %** (`break-even net %`) | `(1 − p_push) / (alpha × kurs)` | przy 1,84: 61,8% (legacy 54,3%) |
| **przewaga po podatku (pp)** (`edge net pp`) | `p win % − break-even net %` | |
| **oczekiwany zwrot na 100 zł po podatku** (`ev net 100`) | `100 × (p_win × alpha × kurs + p_push − 1)` | |
| legacy: `best side`, `break-even %`, `edge pp`, `edge low`, `ev 100`, `signal`, `bet`, `lean` | jak dotąd: kurs bez podatku, strona według pp | zapisywane w snapshotach bez zmian znaczenia; w UI tylko w danych |

`edge low` to dolny koniec szumu losowego hit rate (`p − 1,96·√(p(1−p)/(n+11))`), a nie przedział pewności modelu.
Nie wpływa już na stawkę ani na decyzję.

---

## 4. Decyzja: jedna na mecz dla drużyn i jedna dla zawodników

Kod: `dashboard/decisions.py`. Decyzja wynika **wyłącznie z ceny, modelu, aktualności i dopuszczenia modelu**.
Powody (sekcja 5) powstają po decyzji i ją objaśniają; ich liczba nie jest wejściem funkcji, więc nie może jej
zmienić. Słowa „Graj / Rozważ / Odpuść”, „pewniak” i „rekomendacja” zniknęły z interfejsu.

| Status | Kiedy |
|---|---|
| **Obstaw** (OBSTAW) | oferta bez ostrzeżenia, `ev net 100 > 0` i `edge net pp ≥` próg zapisany na niezależnym okresie (`ADMITTED_THRESHOLD`). **Takiego progu nie ma (None), więc żadna oferta nie dostaje tego statusu.** Próg 🟢 z kalibracji się nie liczy: jest wybierany na tych samych nocach, na których jest oceniany |
| **Nie obstawiaj** (NIE_OBSTAWIAJ) | ocena aktualna, żadna oferta nie spełnia warunku |
| **Czekaj** (CZEKAJ) | brak kursu albo kurs starszy niż 3 h; RotoWire nie podaje składu któregoś zespołu; gracz z najlepszą ofertą jest niepewny (szansa gry 1–99%); dwie najlepsze oferty mają ten sam oczekiwany zwrot (remisu nie rozstrzygamy arbitralnie) |
| **Niedostępne** (NIEDOSTEPNE) | model rodziny nie jest dopuszczony: **każdy rynek drużynowy zawsze**; propsy bez kalibracji dla bieżącej wersji modelu |

Kolejność dla zawodników: niedopuszczony model → brak/stary kurs → brak składu lub niepewny gracz → brak progu lub
żadnej kwalifikującej się oferty → remis → Obstaw z jedną ofertą. Gracze wpisani przez RotoWire jako „out” (0%) nie
tworzą ofert (ich zakłady są zwracane). Przy *Obstaw* każda inna linia tego meczu ma status *Nie obstawiaj*.

Sygnały 🟢/🟡 (legacy, liczone przy kursie bez podatku) zostają w zapisach, ale nie są już filtrem ani kolumną
decyzyjną w panelach. 🔴 i kolumna „ostrzeżenie” zostają: ostrzeżenie blokuje *Obstaw*.

### 4.1 Gwiazdki 0–5 (od 2.11, zamiast ★ / · i 🟢 / 🟡)

**Dlaczego.** Dla każdej zapisanej linii zwrot po podatku wynosi od −12 do −20 zł na 100 zł. Próg 🟢 jest więc
nieosiągalny niezależnie od liczby nocy: to nie jest kwestia początku sezonu, tylko podatku (12%) i marży
(7,6–9,6%) przy kalibracji b ≈ 0,13. Decyzja odpowiada tylko na pytanie „czy grać?” (dziś: nie). Gwiazdki
odpowiadają na drugie: „jeśli i tak gram, które linie są najlepsze?”. Skala bezwzględna (przedziały oczekiwanego
zwrotu) dałaby dziś prawie wszystkim 0–1★, więc 1–4★ są **względne**: to miejsce wśród dzisiejszych linii.
**4★ = najlepsze dziś, nie: opłacalne.**

**Jak** (`decisions.stars`, wspólna reguła `star_levels` z backtestem). Linie wieczoru są układane według `ev net 100`
(oczekiwany zwrot po podatku, oceniana strona); `night pct` to miejsce wśród wszystkich wycenionych linii wieczoru.

| Ocena | Kiedy |
|---|---|
| **5★** | tylko oferta z decyzją *Obstaw*, czyli przewaga powyżej progu sprawdzonego na nocach, których nie użyto do jego wyboru (`ADMITTED_THRESHOLD`; dziś brak, więc 5★ nie występuje) |
| **4★** | najlepsze 5% wieczoru (`STAR_BANDS[0]`), najlepsza linia gracza, **jedna na mecz** (pozostałe kandydatki z tego meczu dostają 3★) |
| **3★** | do 20% (`STAR_BANDS[1]`) |
| **2★** | do 50% (`STAR_BANDS[2]`) |
| **1★** | reszta |
| **0★** | wyceniona, ale z 🔴 albo gracz, którego RotoWire nie podaje jako pewnego (szansa gry < 100%) |
| **–** | brak oceny: mecz *Niedostępne* (każdy rynek drużynowy, propsy bez kalibracji) |

Mecz z decyzją *Czekaj* zachowuje gwiazdki, z powodem w kolumnie „uwaga”. Każde pobranie zapisuje `stars`
i `night_rank` (od 2.11; pobrania z 1.11 zapisały jeszcze `tier`). Wcześniejsze noce są oceniane ponownie z pól
zapisanych przed meczem, bez ponownej kalibracji („przeliczone”).

**Pasma sprawdzone na danych** (`backtest/shortlist.py` → `data/backtest/shortlist.md`, tabela „Star levels”;
kalibracja dopasowana na wcześniejszych nocach, ocena na niewidzianych). Unibet 2022/23, 77 nocy, klucz `ev`:

| Poziom | Linie | Wygrane | Kurs mówił | Ponad kurs | ROI po podatku |
|---|---|---|---|---|---|
| 4★ | 263 | 60,8% | 56,8% | +4,1 pp | −11,3% |
| 3★ | 2 460 | 58,2% | 55,0% | +3,1 pp | −12,4% |
| 2★ | 4 135 | 52,9% | 53,2% | −0,4 pp | −17,7% |
| 1★ | 6 905 | 52,2% | 51,1% | +1,1 pp | −15,5% |
| 4★ − 1★ | | | | +3,0 pp (−2,5…+8,0) | |

Wniosek: dane rozróżniają **dwie grupy** (najlepsze 20% i reszta), a nie cztery poziomy; 4★ i 3★ są praktycznie
równe, 2★ nie jest lepsze od 1★. Na 12 nocach Superbet (2.11, w większości przeliczone) granica wypada inaczej:
4★ +3,5, 3★ +3,0, 2★ +3,5, 1★ +0,2 pp. Pasma (5, 20, 50) zostają do kontroli pod koniec listopada; jeśli
środkowe poziomy dalej się nie rozróżniają, skalę trzeba scalić.

**Rozliczenie** (`tracking.settle_stars`, `star_scorecard`). Na poziom: trafienia z przedziałem Wilsona, kurs
bez marży, „ponad kurs”, ROI przed i po podatku, średnie CLV (gdy jest kurs zamknięcia, 8.1) i wiersz „każda
linia”; na końcu **4★ − 1★** z przedziałem z losowania całych wieczorów. Skala działa tylko wtedy, gdy ten wiersz
jest powyżej zera. Wyniki: *Wyniki → Oceny: wyniki*, jedno zdanie na Przeglądzie.

**Dźwignie podatkowe.** (1) Przełącznik *Promocja bez podatku* w pasku bocznym v2 (profil `superbet_no_tax`,
alpha = 1) przelicza kolumny netto bez ponownej wyceny linii, tylko na tę sesję. Zapisy i rozliczenia zostają
z podatkiem. (2) *AKO na papierze* (`tracking.paper_accumulators`): co wieczór wirtualny kupon z 3 najlepszych
linii ★. Podatek jest pobierany raz od stawki kuponu, ale opłaca się to tylko wtedy, gdy każde zdarzenie bije
swój kurs przed podatkiem o ok. 4,4%. Stan: 10 kuponów, 0 wygranych, −10 j. Śledzone, nie polecane.

---

## 5. Powody za i przeciw: zakłady na zawodników

Kod: `dashboard/reasons.py::prop_reasons`, dane wejściowe z `reasons.offer_context` (ten sam słownik w obu
dashboardach). Od 1.11 (przegląd w `docs/reasons-refactoring.md`) każdy powód mówi, **jakiego rodzaju** jest
twierdzeniem, i tylko niektóre mają kierunek:

| Rodzaj | Co mówi | Kierunek |
|---|---|---|
| **Cena** (`economics`) | szansa modelu wobec tego, czego wymaga kurs po podatku; cena sama, po kalibracji, i o ile liczby zawodnika ją zmieniają | za, gdy przewaga po podatku > 0 |
| **Czego użył model** (`driver`) | wejście projekcji z tym, o ile zmieniło **końcową, skalibrowaną** szansę (pp) | znak tej zmiany; przy \|zmiana\| < 0,1 pp brak kierunku |
| **Kontekst** (`context`) | co pokazują mecze, a czego model nie używa; z oznaczeniem, czy to testowano | brak, chyba że cecha przewidywała wyniki ponad model na niewidzianych liniach (`lift`) |
| **Warto wiedzieć** (`warning`) | rzecz do sprawdzenia, która nie blokuje zakładu | brak |
| **Blokada** (🔴, `flag`) | oferta z blokadą nie dostanie *Obstaw* ani miejsca na liście „Najlepsze dziś” | przeciw |

Każdy powód podaje **wartość, punkt odniesienia, czas i źródło**, a oparty na meczach także **liczbę obserwacji**.
**Brak danych oznacza brak powodu.** Powody nie głosują: ich liczba nie zmienia decyzji. Zmiany wpływu się
nakładają, więc nie należy ich sumować. Przy kalibracji b ≈ 0,09 typowy wpływ to dziesiąte części punktu: tyle
naprawdę zmieniają.

Liczby panelu pochodzą z tych samych meczów, z których wyceniono linię (z dopełnieniem zeszłym sezonem, gdy
meczów jest mało), więc „cena + zmiana” daje szansę modelu, a blokady w panelu zgadzają się z tabelą.

### 5.1 Powody (z progami)

| # | Rodzaj | Powód (tekst w panelu) | Kiedy się pojawia |
|---|---|---|---|
| 1 | cena | **Model:** „Over wygrywa w X%; kurs K po 12% podatku od stawki wymaga Y% (przewaga ±Z pp, ±E na 100 zł stawki)” (przy promocji bez podatku osobny tekst) | gdy jest wycena i znany czas kursu |
| 2 | cena | **Sama cena:** „Sama cena mówi Over m% (bez marży), p% po kalibracji; liczby zawodnika zmieniają to o ±x pp” | gdy znana jest szansa rynku |
| 3 | model | **Oczekiwane dziś:** projekcja wobec linii, średnia, mediana (podsumowanie, bez kierunku) | ≥ 1 mecz |
| 4 | model | **Nieobecni koledzy:** zmiana po ściągnięciu, najmniejsza liczba meczów bez nich, wpływ w pp („opis, nie ich wpływ”) | `lineup adj` ≠ 0 i znana liczba meczów bez nich |
| 5 | model | **Otoczenie punktowe:** punkty drużyny oczekiwane przez Superbet wobec zwykłych, wpływ w pp | znane oba |
| 6 | model | **Rywal:** co rywal pozwala pozycji (miejsce r z 30), wpływ w pp | znana pozycja i rywal |
| 7 | kontekst | **Przy tej linii:** trafienia w ostatnich 10 i we wszystkich meczach, przedział Wilsona 95%, próg po podatku, skład próbki (zeszły sezon, przedsezon) | ≥ 3 mecze |
| 8 | kontekst | **Minuty:** ostatnie 5 wobec wcześniejszych meczów **w obecnej drużynie**, zakres; krótkie mecze z 5+ faulami lub różnicą 20+ | ≥ 8 meczów w drużynie i różnica ≥ 3 min |
| 9 | kontekst | **Rola:** ile z ostatnich 10 zaczynał (ESPN) wobec roli dziś (RotoWire) | RotoWire podaje rolę |
| 10 | kontekst | **Rzuty:** FGA / 3PA / FTA na 36 min i celność, ostatnie 5 wobec wcześniejszych | PTS, PA, PR, PRA, 3PM; ≥ 8 meczów w drużynie |
| 11 | kontekst | **Dom / wyjazd** | ≥ 6 meczów, ≥ 3 w danym miejscu |
| 12 | kontekst | **Dni odpoczynku:** obu drużyn (3 = trzy lub więcej), minuty gracza w ostatnich 3 i 7 dniach | znany odpoczynek obu |
| 13 | kontekst | **Pogrom:** handicap i minuty gracza w jego meczach rozstrzygniętych różnicą 15+ wobec wyrównanych (bez kierunku: dawniej zawsze przeciw Over) | \|handicap\| ≥ 10, pierwsza piątka, ≥ 2 mecze każdego rodzaju |
| 14 | kontekst | **Ruch rynku:** linia od pierwszego zapisu, a przy tej samej linii zmiana kursu i szansy bez marży; godziny do meczu | linia lub kurs się zmieniły |
| — | kontekst | **Historia z rywalem** tylko na zakładce *Historia*; wraca do panelu wyłącznie, gdy test pokaże `lift` | — |

### 5.2 Warto wiedzieć (nie blokuje)

| Ostrzeżenie | Warunek |
|---|---|
| Inna rola | dziś pierwsza piątka, a zaczynał ≤ 30% z ostatnich 10 (albo rezerwa przy ≥ 70%) |
| Nowa drużyna | mniej niż 8 meczów w obecnej drużynie, a próbka ma mecze z innej |
| Skład przewidywany | RotoWire: skład drużyny `expected`, nie `confirmed` |

Nowe warunki są ostrzeżeniami, nie blokadami: wynik listy „Najlepsze dziś” (77 niewidzianych wieczorów) zmierzono z
dotychczasowymi blokadami, a zmiana tego, co jest blokowane, bez dowodu zmieniałaby oceniany zbiór.

### 5.3 Blokady (🔴): każda blokuje status *Obstaw*

| Flaga | Warunek |
|---|---|
| Za mało meczów | < **8** meczów w próbce |
| Tylko przedsezon | wszystkie mecze w próbce to przedsezon |
| Nie zagra | RotoWire: szansa gry 0% (linia i tak była pomijana w decyzji i na liście; teraz panel to mówi) |
| Może nie zagrać | RotoWire: szansa gry między 1% a 99% |
| Niestabilne minuty | ≥ 5 meczów i współczynnik zmienności minut > **0,35** |
| Linia przeciw stronie | linia ruszyła się o **≥ 1,5** w stronę przeciwną do ocenianej strony; do oceny przy weryfikacji pod koniec listopada (wynik takich linii wobec ceny), bo w 2022/23 był jeden zapis na linię |

Domyślnie ukryci są gracze, których rola z RotoWire zaczyna się od „Out” lub „OFS” (filtr `hide_out` działa po tagu
urazu, nie po szansie gry 0%).

### 5.4 Test kontekstu

`python -m backtest.reason_lift` (≈ 5 min) sprawdza na stałej liście cech (trafienia w ostatnich 10, minuty, dom /
wyjazd, odpoczynek, historia z rywalem, rzuty), czy cecha dodana do skalibrowanego modelu (logit(p1) = logit(p0) +
β·f, β dopasowane na wcześniejszych liniach) poprawia log loss na późniejszych liniach, z przedziałem z losowania
całych wieczorów. Wynik: `data/backtest/reason_lift.md` i `.json` (czytany przez panel). 1.11: **żadna cecha nie
dała poprawy** (2022/23: 77 wieczorów; Superbet: 4), więc cały kontekst jest bez kierunku. Rola i pogrom są
`nie testowane` (brak roli RotoWire i handicapu z chwili każdej linii).

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
- Legacy przewaga meczu (`edge pp`, zapisywana) to szansa modelu minus `100/kurs` (bez usuwania marży). Od 31.10
  obok niej: `market %` (kurs bez marży w parze stron), `break-even net %`, `edge net pp` i `ev net 100` w tym samym
  profilu kosztowym co propsy. To wciąż tylko analiza: rynki drużynowe są *Niedostępne*.

### 6.2 Powody za i przeciw (mecze)

- **Zwycięzca / handicap:** prognozowana różnica punktów (czy pokrywa handicap), bilans netto obu drużyn, każdy
  nieobecny z efektem ≥ 0,5 pkt na różnicę. Atut własnej hali nie jest już powodem: to stała modelu (1,5 pkt), a
  nie obserwacja, więc nie ma liczby obserwacji.
- **Sumy:** prognoza wobec linii, tempo wobec ligi (neutralne przy < 1 posiadaniu różnicy), atak drużyny wobec obrony
  rywala, nieobecni z efektem ≥ 0,5 pkt.

### 6.3 Flagi meczowe

Początek sezonu (którakolwiek drużyna ma < 5 meczów), brak meczu w RotoWire, przewaga > 15 pp (bardziej
prawdopodobne, że model czegoś nie wie, niż że rynek tak bardzo się myli).

### 6.4 Status

**Rynki meczowe zawsze dostają decyzję *Niedostępne* i nigdy stawki.** Na 988 rozliczonych wynikach
(9 nocy) model meczowy przewiduje **gorzej niż kurs** (log loss 0,7248 wobec 0,6730). Jego typy z przewagą > 0
oczekiwały 65,8% trafień, a trafiły **50,6%** (ROI −4,2%). Najgorzej wypada handicap (0,884 wobec 0,681).
**Nic nie dopuszcza ich automatycznie**: w kodzie nie ma dopasowania kalibracji meczów (`GAME_CALIBRATION_MIN` w
`backtest/calibrate.py` występuje tylko w tekście raportu; wcześniejsza wersja tego dokumentu błędnie mówiła, że
kalibracja „powstanie automatycznie”). Dane pokazują, że model wymaga przebudowy, a nie tylko kalibracji.

---

## 7. Stawki i kupon (stary dashboard)

- **Ćwierć Kelly'ego**, maksymalnie 5% bankrolla, na cenie netto: `0,25 × (p·α·kurs − 1)/(α·kurs − 1)`, gdzie `p` to
  skalibrowana szansa wygranej (od 31.10 bez `edge low`, który opisuje tylko szum hit rate). Stawkę dostaje tylko
  oferta z decyzją *Obstaw*, więc dziś **każda stawka wynosi 0**. Rynki meczowe nigdy jej nie dostają.
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
- „Zakład” to **pierwszy zapis linii przed meczem**, a „ostatni kurs przed meczem” to ostatni zapis w snapshotach
  z wyceną (`last line`, `last odds`, z liczbą godzin przed startem). Prawdziwy kurs zamknięcia daje 8.1.
- Kalibrację ocenia się na **ostatnim zapisie przed startem**; dane przed 26.10 zostały odtworzone z historii gita.

### 8.1 Pobieranie według harmonogramu i kurs zamknięcia (od 2.11)

**Tylko gdy program działa.** Wątek w dashboardzie v2 (`dashboard_v2/core/fetch_worker.py`, pętla
`fetch_loop.loop`) albo `python -m fetch_loop` w terminalu. Nic nie jest rejestrowane w systemie: zamknięcie
dashboardu kończy pobieranie. Opcja „Nie usypiaj komputera” (`SetThreadExecutionState`, tylko na czas procesu)
działa, bo mecze są u nas 00:00–04:30. Jeden wątek pobierający naraz także między procesami (`data/fetch_worker.json`
z bieżącym znacznikiem czasu).

**Terminy** (`fetch_schedule.py`, czysta funkcja testowana z fałszywym zegarem):
- co godzinę, o pełnej godzinie, wszystkie mecze startujące w ciągu 24 h;
- w ostatniej godzinie przed każdą godziną startu: **T−60, T−40, T−20, T−10, T−5**, tylko mecze tej godziny;
- **RotoWire przy każdym terminie** (zapis tylko zmian, z czasem, więc widać moment zmiany składu);
- termin godzinowy do 15 min od terminu z ostatniej godziny jest do niego dołączany; terminy do 3 min od siebie łączą
  się w jeden; termin spóźniony o ponad 3 min (uśpiony komputer) jest pomijany i logowany, a nie nadrabiany;
- przy starcie programu jedno pobranie wszystkich meczów (z wyceną, gdy snapshot jest starszy niż godzina).

**Co się zapisuje.** Każde pobranie: notowania tylko zmienionych linii (`superbet_prop_quotes.csv`,
`superbet_game_quotes.csv`; wycofana linia = wiersz z pustymi kursami) i wiersz na każdy odczytany mecz
(`superbet_event_fetches.csv`), żeby „bez zmian” odróżnić od „nie odczytano”. Pełny snapshot z wyceną (czytany przez
strony) co 2 godziny i w T−60. Każdy przebieg trafia do `data/run_log.csv` (job `quotes` lub `snapshot`,
`scheduled T-5` itd., z liczbą zapytań, kodami odpowiedzi i ponowieniami).

**Grzeczne pobieranie** (`http_polite.py`, dla Superbetu i RotoWire): 3–6 s losowej przerwy między zapytaniami,
ponowienia po 429/5xx/zerwanym połączeniu (10 → 30 → 90 s z losowym dodatkiem, z poszanowaniem `Retry-After`),
**bezpiecznik**: 403 albo dwa 429 z rzędu blokują hosta na 2 h dla każdego procesu (`data/scrape_state.json`),
limit 4 min na przebieg, **budżet 400 zapytań dziennie** (potem harmonogram staje, przycisk dalej działa),
`If-None-Match` z ETag (niezmieniony mecz wraca jako 304). Typowa noc to ok. 70–200 zapytań. `robots.txt`:
host API (`production-superbet-offer-pl.freetls.fastly.net`) go nie ma (404); robots.txt superbet.pl dotyczy
stron serwisu, nie API, a API jest tym samym publicznym źródłem, z którego korzysta ich strona.

**Kurs zamknięcia i CLV** (`tracking.closing_props`, `add_clv`). Zamknięcie = ostatnie notowanie linii przed
startem; ważne, gdy mecz odczytano najpóźniej 10 min przed startem (`CLOSE_MAX_AGE_MIN`). Przy tej samej linii:
`clv %` = kurs zakładu × szansa zamknięcia bez marży − 1 (powyżej 0 = zakład pobił rynek), `clv % std` to samo po
podatku, `clv pp` = szansa zamknięcia bez marży − szansa przy zakładzie (> 0 = rynek przesunął się w stronę
zakładu). Przy zmienionej linii tylko `line vs close`. Rynki meczowe (`closing_games`, `add_game_clv`): szansa
bez marży z pary stron w tym samym odczycie (gospodarze/goście; spread `home −x` z `away +x`; Over/Under tej samej
linii). Raport: `python -m backtest.clv_report` → `data/backtest/clv.md` (CLV po gwiazdkach, po godzinach przed
startem, po ustalonych z góry segmentach: główne i poboczne statystyki, Over i Under, pierwsza piątka i rezerwa
wg ostatniego składu RotoWire przed startem; odsetek linii, przy których rynek ruszył w stronę oceny modelu;
tabela po statystykach tylko opisowa; strona modelu na głównych liniach meczowych). Karta harmonogramu w Centrum
danych pokazuje, dla ilu meczów ostatniej nocy zamknięcie jest ważne.

**Procedura dopuszczenia progu (5★)**: `python -m backtest.threshold_admission [--until D]` →
`data/backtest/threshold_admission.md`. Na nocach do daty D (co najmniej 10) dopasowuje kalibrację i wybiera
najmniejszy próg przewagi po podatku (`edge net pp` ∈ 0, 1, 2, 3, 5, 8), którego zakłady zarobiły po podatku
(≥ 50 zakładów, ≥ 10 nocy). Ocenia go na kolejnych ≥ 20 nocach, których nie widział ani wybór, ani kalibracja,
na zakładach takich, jakie dałaby decyzja *Obstaw*: w każdym meczu najlepsza linia bez 🔴 powyżej progu.
Warunek: dolna granica przedziału ROI po podatku > 0 **albo** średnie CLV po podatku > 0 z dolną granicą > 0
(przedziały z losowania całych nocy). Domyślne D zostawia 20 nocy do oceny. Raport nigdy nie ustawia
`ADMITTED_THRESHOLD`: wartość wpisuje się ręcznie, po przeczytaniu raportu, osobnym commitem.

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

Ranking wieczoru według oczekiwanego zwrotu (`data/backtest/shortlist.md`, Unibet 2022/23, 77 niewidzianych nocy):

| Miejsce w wieczorze | Linie | Wygrane | Kurs mówił | ROI | ROI po podatku |
|---|---|---|---|---|---|
| najlepsze 2% | 233 | 59,7% | 55,1% | +2,3% | −10,0% |
| 10–25% | 2 071 | 57,7% | 54,7% | −0,7% | −12,6% |
| 25–50% | 3 447 | 52,5% | 53,1% | −6,8% | −18,0% |
| dolne 50% | 6 905 | 52,2% | 51,1% | −4,0% | −15,5% |
| ★ (5 na wieczór, 1 na mecz) | 295 | 60,7% | 56,9% | +0,2% | −11,9% |

Ranking zmniejsza oczekiwaną stratę wobec losowej linii, ale nie pokonuje podatku. Na Superbecie (4.1) przewagi
rankingu jeszcze nie widać.

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
4. **„Zakres 95%” nie jest przedziałem predykcji** (F6), a po kalibracji (b ≈ 0,13) prawie znika. Od 31.10 nie
   wpływa na stawkę ani decyzję, a interfejs nie nazywa go przedziałem pewności modelu.
5. **Powody nie są walidowane** jako osobny sygnał. Od 31.10 nie głosują: decyzja od nich nie zależy.
6. **Model meczowy jest słaby** (wczesny sezon to głównie zeszły sezon, nie zna letnich transferów, nieobecni liczą
   się tylko wtedy, gdy drużyna już grała bez danego gracza).
7. **Kurs zamknięcia jest dopiero od 2.11** (8.1) i tylko dla nocy, w które działał dashboard; wcześniejsze noce
   nie mają CLV.
8. **Gracze bez meczów w danych** (debiutanci, długo kontuzjowani) nie wchodzą do korekty nieobecności.
9. **Mała próba Superbet**: 10 nocy to za mało na pewne wnioski w którąkolwiek stronę.
10. Statystyki poboczne (FGA, FGM, FTA, FTM, PF, TO) stanowią prawie połowę linii, ale model wycenia je tak samo
    jak główne, bez osobnej oceny.

---

## 10. Kierunki rozwoju (do dyskusji z konsultantem)

### 10.1 Przejrzystość interfejsu

- ~~Jasny komunikat, gdy nie ma przewagi~~ (zrobione 31.10: jedna decyzja na mecz, komunikat „dziś nie ma na co
  grać”; lista „Najmniejsza strata” i 5 największych przewag meczowych usunięte z roli decyzyjnej).
- ~~Zawsze coś użytecznego do pokazania~~ (zrobione 1.11: ranking „Najlepsze dziś” z kosztem i własnymi wynikami,
  4.1).
- **Rozdzielić „trafność” od „opłacalności”**: wysoka nasza szansa przy kursie 1,30 to nie wartość. Rozważyć ukrycie
  „naszej szansy” na rzecz „przewagi” i „zwrotu na 100 zł”.
- **Wagi powodów:** od 31.10 powody nie głosują; dalej warto pokazać, które są uwzględnione w szansie (oczekiwane
  dziś, nieobecni, punkty drużyny z kursu, rywal), a które są tylko kontekstem (dom/wyjazd, mecz dzień po dniu,
  historia z rywalem, minuty, pogrom).
- **Kupon i stawki w v2** (dziś tylko w v1; świadomie poza fazami 1–2).
- Tablica wyników „na żywo”: skuteczność systemu do dziś na jednej karcie (ROI, liczba nocy, przedział), widoczna od
  razu na Przeglądzie.

### 10.2 Model i metoda

- Powtórzyć **ablację na 10+ nocach Superbet**; dopiero po niej decydować o dalszych zmianach.
- **Walidować powody:** dla każdego powodu sprawdzić na rozliczonych liniach, czy zgodność z nim zmienia trafienia
  i ROI. Powody bez wartości zdegradować do kontekstu, a te z wartością włączyć do szansy.
- **Osobny, nietknięty okres walidacji** dla progu 🟢 (np. listopad), żeby usunąć problem F4. Linie ★ / ·
  zapisywane od 1.11 są gotową populacją do tej walidacji.
- **Projekcja minut** jako osobny krok (minuty × wydajność na minutę), bo minuty są główną niewiadomą przy
  nieobecnościach i pogromach.
- **Gęstsze zapisy kursów** (np. 60 i 15 min przed startem) do pomiaru CLV i wykrywania ruchów rynku.
- **Model meczowy do przebudowy** (handicap jest wyraźnie gorszy niż kurs) albo jawne wyłączenie go z rekomendacji.
- **Selekcja rynków:** sprawdzić, czy na którejś grupie (statystyka × pozycja × rola) model ma przewagę, z korektą
  na wielokrotne testowanie.
- **Inne źródła informacji, których rynek może nie mieć w cenie:** szybkość reakcji na zmiany składów (RotoWire →
  linia), raporty minut i ograniczeń po kontuzjach.

### 10.3 Pytania do konsultanta

1. ~~Jak zakomunikować „brak przewagi”, żeby narzędzie było użyteczne?~~ Odpowiedź z 1.11: decyzja („czy
   grać”) i ranking („jeśli gram, to co”) są osobno; ranking pokazuje swój koszt i swoje wyniki.
2. ~~Czy „najmniejsza strata” to rozsądna funkcja?~~ Wróciła jako ranking z kosztem i rozliczeniem (4.1); co
   wieczór sprawdzamy, czy jest lepszy od losowej linii.
3. Jaki format uzasadnienia (lista powodów, punktacja, jedno zdanie) jest najbardziej zrozumiały i najmniej
   wprowadza w błąd?
4. Które rynki i jakie progi (minimalna przewaga, minimalna liczba meczów) użytkownik uzna za wiarygodne?
5. Jak pokazywać niepewność (przedziały, liczba nocy), żeby nie była ignorowana?

---

## Załącznik A: gdzie co jest w kodzie

| Element | Plik |
|---|---|
| Wycena propsów i meczów, kalibracja w użyciu, sygnały | `dashboard/models.py` |
| Decyzje (Obstaw / Nie obstawiaj / Czekaj / Niedostępne), zachowanie otwartej oferty, gwiazdki (`stars`, `star_levels`) | `dashboard/decisions.py` |
| Wyniki gwiazdek, CLV i AKO na papierze (`settle_stars`, `star_scorecard`, `closing_props`, `closing_games`, `add_clv`, `paper_accumulators`) | `dashboard/tracking.py` |
| Wybór klucza rankingu i sprawdzenie pasm gwiazdek | `backtest/shortlist.py` → `data/backtest/shortlist.md` |
| Raport CLV | `backtest/clv_report.py` → `data/backtest/clv.md` |
| Dopuszczenie progu 5★ | `backtest/threshold_admission.py` → `data/backtest/threshold_admission.md` |
| Harmonogram pobierania, grzeczny klient HTTP | `fetch_schedule.py`, `fetch_loop.py`, `http_polite.py`, `dashboard_v2/core/fetch_worker.py` |
| Kontrakt kosztowy (profile, próg, EV, zysk z rozliczenia) | `dashboard/metrics.py` (`COST_PROFILES`, `break_even`, `expected_return_100`, `side_profit`) |
| Wzory (hit rate, rozkład, kalibracja, rywal, tempo, nieobecni, model meczu) | `dashboard/metrics.py` |
| Powody i ostrzeżenia | `dashboard/reasons.py` |
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
| Kelly | 0,25, max 5% | szansa wygranej na cenie netto, tylko przy *Obstaw* |
| Profil kosztowy | `superbet_standard`: alpha = 0,88; `legacy` i `superbet_no_tax`: alpha = 1 | 12% podatku od stawki; `superbet_no_tax` tylko z przełącznika promocji |
| Pasma gwiazdek | 4★ ≤ 5%, 3★ ≤ 20%, 2★ ≤ 50% wieczoru | `STAR_BANDS`; 5★ tylko *Obstaw* |
| AKO na papierze | 3 linie 4★ | `ACCUMULATOR_LEGS` |
| Próg dla *Obstaw* | brak (`ADMITTED_THRESHOLD = None`) | musi być sprawdzony na nocach, których nie użyto do jego wyboru (8.1) |
| Harmonogram | co godzinę; T−60/40/20/10/5 min | `fetch_schedule.LAST_HOUR`; snapshot z wyceną co 2 h i w T−60 |
| Grzeczne pobieranie | 3–6 s przerwy; 3 ponowienia 10/30/90 s; blokada 2 h; 400 zapytań/dzień; 4 min na przebieg | `http_polite`, `superbet_fetcher.RUN_DEADLINE` |
| Ważne zamknięcie | odczyt ≤ 10 min przed startem | `tracking.CLOSE_MAX_AGE_MIN` |
| Wiek kursu dla *Czekaj* | 3 h | |
| Model meczu | hala 1,5; SD 14 / 18 / 11,5; regresja 30%; prior 10 meczów | |
