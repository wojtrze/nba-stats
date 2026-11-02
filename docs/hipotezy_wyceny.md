# Rejestr hipotez: gdzie Superbet może źle wyceniać linie

*Założony 1 listopada 2026 r. Zapisy w tym pliku powstają **przed** testem na nocach oceny; zmiana definicji po
obejrzeniu tych nocy unieważnia test danej hipotezy, a nowy test wymaga nowej daty D.*

## Po co ten rejestr

Superbet zatrzymuje marżę (ok. 8,4% na propsach) i 12% stawki jako podatek. Przy typowych kursach strona zakładu
musi wygrywać o **ok. 11 pp częściej**, niż wynika z kursu bez marży (zmierzone na archiwum: mediana 11,2 pp,
zakres 8,8–12,9 pp). Takiej różnicy nie daje dopracowywanie prognozy. Dlatego każda hipoteza tutaj opisuje
**mechanizm błędu Superbetu**: z jakiego powodu i w jakiej sytuacji jego cena może być zła.

| Mechanizm | Na czym polega |
|---|---|
| **A. Opóźnienie informacji** | Wiadomość (np. „nie zagra” w RotoWire) jest, a linia jeszcze się nie zmieniła |
| **B. Niespójność wewnętrzna** | Jedna cena Superbetu przeczy innym jego cenom |
| **C. Słabe przetworzenie znanej informacji** | Linia ustawiona szablonowo, bez roli, minut i kształtu rozkładu |
| **D. Rynki zaniedbane lub przesunięte** | Mało oglądane linie albo przesunięcie pod gusta graczy |

## Zasady wspólne

**Statusy** (plik `data/backtest/mispricing_status.json`, ustawiany ręcznie po lekturze raportu, nigdy przez
skrypt):

| Status | W aplikacji | Znaczenie |
|---|---|---|
| `untested` | 🧪 Obserwacja, niesprawdzona | Pokazujemy fakt, bez kierunku „za / przeciw” |
| `admitted` | ✅ Sprawdzona | Przeszła test na nocach oceny; sygnał może być „za” albo „przeciw” |
| `rejected` | nie pokazujemy przy linii | Test ją odrzucił; wynik zostaje w raporcie |

Przyjęcie hipotezy **nie zmienia samo decyzji** *Obstaw* ani 5★. Dopuszczenie do decyzji przechodzi osobną
procedurą, jak `ADMITTED_THRESHOLD` w `backtest/threshold_admission.py`.

**Podział nocy:** każda hipoteza ma datę D. Noce ≤ D służą do rozpoznania i ustalenia progów, a noce > D do
oceny (co najmniej 10 nocy). Danych z nocy oceny nie oglądamy przed oceną.

**Miary:**
- **Główna:** średnia przewaga nad kursem zamknięcia po podatku (w aplikacji: „cena lepsza niż na koniec”), z 95%
  zakresem z losowania całych nocy (`backtest.ablation.night_bootstrap`, `tracking.closing_props`).
- **Pomocnicza:** ROI po podatku na rozliczonych liniach.

**Progi decyzji:**

| Werdykt | Warunek |
|---|---|
| ✅ przyjęta | Dolny koniec zakresu > 0 przy ≥ 60 sygnałach z ≥ 10 nocy. Zakres 99% zamiast 95%, bo hipotez jest dziewięć |
| ❌ odrzucona | Górny koniec zakresu < 0 albo średnia ≤ 0 po ≥ 150 sygnałach |
| ❌ brak sygnałów | Mniej niż 1 sygnał na 5 nocy oceny: mechanizm może istnieć, ale nie da się na nim grać |

Wynik nie mieszczący się w żadnym z tych warunków oznacza: zostaje 🧪 i czekamy na kolejne noce.

**Testy „b” (czy mechanizm działa)** liczą, o ile strona wskazana przez sygnał wygrywała częściej, niż mówi jej
cena bez marży, **ponad ogólne przechylenie** tej samej statystyki i strony na wszystkich liniach w tym samym
okresie. Bez tej kontroli sygnał, który wskazuje prawie zawsze Under, odkryłby tylko to, że Under na danej
statystyce wygrywał częściej, a to jest osobna hipoteza (H9).

**Sygnał się liczy** tylko wtedy, gdy przy następnym pobraniu była nadal ta sama linia, a kurs nie gorszy (można
go było postawić).

**Komunikaty w aplikacji** odpowiadają na pięć pytań, w tej kolejności:
1. Czy różnica pokrywa podatek? Gdy nie, mówimy to pierwszym zdaniem.
2. Co się stało (fakt z liczbami)?
3. Dlaczego to może być błąd ceny?
4. Jak długo sygnał jest aktualny?
5. Na ile jest sprawdzony (status)?

Bez słów „pewniak”, „okazja”, „warto”; zawsze z liczbą i punktem odniesienia.

---

## H1: Sumy łączone a ich składowe (mechanizm B)

**Data D: 2026-11-01.** Ocena na nocach od 2.11, werdykt najwcześniej po 10 nocach. Kod:
`dashboard/mispricing.py` (`combo_signals`).

**Mechanizm:** Superbet wycenia PRA, PR, PA i RA jako osobne linie obok punktów, zbiórek i asyst. Jeśli jedna
z tych cen nie nadąża za resztą (np. linia punktów się przesunęła, a PRA nie), ceny przestają do siebie pasować.

**Definicja** (wszystko z jednego pobrania kursów i z meczów gracza rozegranych przed tym meczem):
1. Wymagane: linia sumy łączonej i linie wszystkich jej składowych, z kursami Over i Under, na liniach x,5;
   co najmniej 8 meczów gracza.
2. Dla każdej składowej szukamy średniej, przy której rozkład liczby (dwumianowy ujemny, a gdy rozrzut mniejszy
   od średniej, Poissona; wariancja gracza skalowana ze średnią) przekracza linię dokładnie tak często, jak mówi
   kurs bez marży.
3. Suma składowych: średnia = suma średnich; wariancja = suma wariancji + kowariancje. Korelacje bierzemy
   z meczów gracza, ściągnięte do korelacji ligowej (liczonej w obrębie zawodników) z wagą 10 meczów.
4. `p_składowe` = szansa sumy powyżej linii z tego rozkładu. `p_Superbet` = szansa z kursu sumy bez marży.
   `g` = różnica w pp dla strony, którą wskazują składowe.

**Test H1a (ekonomiczny, rozstrzyga status):** sygnał, gdy `p_składowe` dla wskazanej strony ≥ próg opłacalności
tej strony po podatku (`metrics.break_even`). Miary i progi jak w zasadach wspólnych.

**Test H1b (czy mechanizm działa, opisowy):** dla `g` ≥ 3 pp sprawdzamy, czy do zamknięcia cena sumy zbliżyła się
do wartości wynikającej ze składowych częściej niż w 50% przypadków. Jeśli nie, różnice są szumem metody, a nie
nieaktualnymi cenami.

**Kontrola metody:** średnie `g` ze znakiem (dodatnie = składowe wskazują Over) na wszystkich liniach powinno
leżeć w [−1, 1] pp. Inaczej metoda ma skrzywienie i poprawiamy ją przed oceną.

**Rozpoznanie na nocach ≤ D** (archiwum 20–31.10, wynik opisany przed oceną):

| Zestaw | Sumy łączone | Mediana `g` | `g` ≥ 3 pp | Największa `g` | Sygnały H1a |
|---|---|---|---|---|---|
| ostatni kurs przed meczem | 3 278 | 0,7 pp | 1–3% | 10,7 pp | 0 |
| pierwszy kurs (ten sam zapis) | 1 805 | 0,7 pp | 1,3% | 5,0 pp | 0 |

- Kontrola metody przeszła: średnie `g` ze znakiem = +0,34 pp.
- Korelacje ligowe w obrębie zawodnika: PTS–REB 0,34, PTS–AST 0,23, REB–AST 0,25.

**Przewidywanie zapisane przed oceną:** Superbet liczy sumy łączone spójnie ze składowymi, prawdopodobnie z tego
samego modelu. Największe różnice (≤ 5 pp w pierwszym kursie) są wielokrotnie mniejsze od ~11 pp potrzebnych po
podatku. Spodziewany werdykt H1a: **❌ brak sygnałów**. H1 zostaje w rejestrze, bo:
- jest tani w działaniu;
- wykryje zmianę, jeśli Superbet zacznie wyceniać sumy inaczej;
- jego komunikat jest wzorcem dla kolejnych hipotez.

W aplikacji (zakładka Werdykt na stronie zawodników) sygnał pojawia się tylko przy `g` ≥ 3 pp, w trybie 🧪.

**Rozliczenie rozpoznania** (wyniki z ESPN, 12 nocy 20–31.10, ten sam detektor co w aplikacji, przedziały 95%
z losowania nocy): przy `g` ≥ 4 pp było 28 linii, strona sygnału wygrała 46%, a cena dawała jej 49% (−2,1 pp,
przedział od −30 do +19 pp). Sygnał pokrywający podatek był 1 i przegrał.

---

## H2: Trafione rzuty a oddane i skuteczność gracza (mechanizm B)

**Data D: 2026-11-01.** Ocena na nocach od 2.11. Kod: `dashboard/mispricing.py` (`shooting_signals`).

**Mechanizm:** Superbet wycenia trafione rzuty (3PM, FGM, FTM) i oddane rzuty (3PA, FGA, FTA) jako osobne linie.
Razem zakładają pewną skuteczność. Gdy jedna linia się przesunie bez drugiej, ta skuteczność przestaje pasować do
gracza.

**Definicja** (jedno pobranie kursów, mecze gracza sprzed meczu):
1. Wymagane: linia trafionych i linia oddanych tego samego rodzaju, obie z kursami Over i Under, na liniach x,5;
   co najmniej 8 meczów gracza.
2. Średnią liczbę oddanych rzutów bierzemy z ceny ich linii, tą samą metodą co w H1. Rozrzut liczymy z ostatnich
   40 meczów.
3. Skuteczność gracza = trafione / oddane ze wszystkich jego meczów w danych, ściągnięta do skuteczności ligowej
   z wagą 200 rzutów. Ligowa: 3P 35,9%, FG 46,8%, FT 78,1%.
4. Średnia trafionych = średnia oddanych × skuteczność gracza. Rozkład liczby (rozrzut gracza jak w H1) daje
   szansę linii trafionych. Porównujemy ją z ceną tej linii bez marży: różnica `g` dla wskazanej strony.
5. Sygnał dotyczy **linii trafionych**. Pokazujemy go też przy linii oddanych, bo opiera się na obu.

**Testy:**
- **H2a (ekonomiczny):** sygnał, gdy szansa strony ≥ próg opłacalności po podatku.
- **H2b (mechanizm):** przy `g` ≥ 4 pp, ponad przechylenie statystyki i strony.

**W aplikacji:** przy `g` ≥ 6 pp. Typowa różnica H2 to ok. 3 pp, więc niższy próg zasypałby panel sygnałami.

**Rozpoznanie na nocach ≤ D** (12 nocy, 3 169 par linii: 3PM 837, FGM 1 167, FTM 1 165):
- Mediana `g` 3,2 pp. Kontrola metody przeszła: średnie `g` ze znakiem −0,06 pp.
- **H2b:** przy `g` ≥ 4 pp (n = 1 235) strona sygnału wygrała 53,8% wobec 51,0% w cenie, czyli +2,9 pp
  [+0,2; +5,0]. Ponad przechylenie statystyki zostaje +2,5 pp [0,0; +4,5].
  - Prawie cały efekt to rzuty wolne: bez FTM tylko +0,4 pp [−2,7; +3,8].
  - Wniosek: mechanizm w rzutach z gry jest niewidoczny, a w rzutach wolnych możliwy.
- **H2a:** 130 sygnałów (FTM 87, 3PM 26, FGM 17) wygrało 54,6%, a ROI po podatku wyniosło **−9,8%**
  [−21,2; +3,0]. Nawet najlepsza część (FTM: 58,6% trafień) nie pokryła podatku (ROI −5,7%).
- **Uwaga:** rzuty wolne idą parami, więc przy małych liniach (FTA 1,5, FTM 0,5) metoda może brać za błąd ceny
  to, że gracz albo w ogóle nie stanie na linii, albo odda dwa rzuty. FTM zostaje w H2, bo tak zapisano definicję
  przed testem, ale werdykt podajemy też osobno dla FTM.

**Przewidywanie zapisane przed oceną:** H2a ❌ odrzucona; H2b dodatnie tylko w FTM.

---

## H6: Rozrzut małych liczb (mechanizm C)

**Data D: 2026-11-01.** Ocena na nocach od 2.11. Kod: `dashboard/mispricing.py` (`spread_signals`).

**Mechanizm:** przy małych liniach (0,5–2,5) liczy się, jak często gracz kończy na 0 albo 1. Cena Superbetu pasuje
do typowego rozrzutu. Gracz, którego wyniki wahają się mocniej przy tej samej średniej, częściej kończy poniżej
linii.

**Definicja:**
1. Statystyki BLK, STL, 3PM, TO, PF; linie ≤ 2,5 z kursami Over i Under; co najmniej 8 meczów gracza.
2. **Bez FTM** (decyzja z rozpoznania, przed oceną). Rzuty wolne idą parami, więc rozrzut około 2× (mediana
   ligowa 1,97) jest cechą tej statystyki, a nie gracza. Sygnały FTM pokrywające podatek wygrały 48,6%
   (ROI −15,9%).
3. Rozrzut gracza = wariancja / średnia z ostatnich 40 meczów, ściągnięta do ligowej mediany tej statystyki
   z wagą 20 meczów. Mediany ligowe: BLK 1,07, STL 1,10, 3PM 1,21, TO 1,11, PF 1,04.
4. Średnią bierzemy z ceny bez marży, tak jakby wynik miał rozkład Poissona. Rozkład z tą średnią i rozrzutem
   gracza daje szansę linii. Przy rozrzucie ≤ 1 nie ma sygnału.
5. Sygnał wskazuje prawie zawsze **Under**.

**Testy:**
- **H6a (ekonomiczny):** jak H2a.
- **H6b (mechanizm):** przy `g` ≥ 4 pp, ponad przechylenie statystyki i strony.

**W aplikacji:** przy `g` ≥ 4 pp.

**Rozpoznanie na nocach ≤ D** (12 nocy, 1 913 linii bez FTM):
- **H6b:** przy `g` ≥ 4 pp (n = 124) Under wygrał 50,0% wobec 44,5% w cenie, czyli +5,5 pp [+1,0; +10,5]. Ponad
  przechylenie statystyki zostaje +5,3 pp [+1,1; +9,8].
- **H6a:** 6 sygnałów na 4 nocach, 3 wygrane, ROI +11% [−47; +117]. To za mało, żeby cokolwiek wiedzieć.
- To najciekawszy wynik rozpoznania. Ale: 124 linie, 12 nocy i kilka sprawdzonych wariantów (progi 3/4/6 pp,
  z FTM i bez), więc przedział może być zbyt optymistyczny. Nawet +5 pp to połowa tego, czego wymaga podatek.

**Przewidywanie zapisane przed oceną:** H6b dodatnie, ale słabsze niż w rozpoznaniu. H6a: za mało sygnałów na
werdykt przez wiele tygodni (ok. 1 sygnał na 2 noce).

---

## H3–H9: definicje do uzupełnienia przed ich testem

Każda dostanie tu własną datę D, progi i wynik rozpoznania, zanim jej detektor trafi do aplikacji.

| Id | Mechanizm | Krótko | Główna miara | Zależność od danych |
|---|---|---|---|---|
| **H3** | B | Zawodnicy a drużyna: suma median PTS graczy wobec sumy drużyny; drabinki meczowe (suma, handicap, sumy drużyn) między sobą | zamknięcie po podatku | ok. 7 graczy z linią PTS na drużynę, więc potrzebna poprawka na brakujących |
| **H4** | A | Opóźnienie po wiadomości z RotoWire (gracz z ≥ 20 min: nie zagra, zmiana piątki, powrót). Etap 1 opisuje wielkość ruchu i opóźnienie; etap 2 to detektor, tylko gdy typowy ruch ≥ próg po podatku | zamknięcie po podatku i czy kurs był do wzięcia | archiwum: mediana 3 zapisy na mecz, najbliższy ok. 2,9 h przed startem, więc opóźnienia nie zmierzymy; potrzebne kursy z harmonogramu (od 1.11) |
| **H5** | C | Zmiana roli: dziś starter, a ≤ 1 start w ostatnich 5 meczach, albo skok minut ≥ 25% w 3 meczach; linia wobec projekcji z minutami nowej roli | zamknięcie po podatku | archiwum i RotoWire |
| **H7** | D | Dryf wczesnych linii (statystyki poboczne, rezerwowi, kurs > 6 h przed meczem): czy linia idzie do zamknięcia w stronę naszej oceny w > 50% przypadków | odsetek ruchu w stronę oceny i zamknięcie po podatku | archiwum i harmonogram |
| **H8** | D | Ruchy bez wiadomości (zmiana linii bez zmiany w RotoWire w ciągu 60 min przed nią: gramy stronę, która zyskała) oraz Overy PTS u graczy z największym udziałem w akcjach | tylko ROI po podatku (zamknięcie może być skrzywione) | ok. 33 nocy lub więcej |
| **H9** | D | Under na trafionych rzutach (3PM, FGM, FTM): Superbet może przesuwać te linie pod graczy grających Over. Zauważone w rozpoznaniu H2: Under wygrywał częściej, niż mówi cena (3PM +3,0 pp, FGM +2,5 pp, FTM +4,1 pp, 12 nocy). Na razie bez detektora w aplikacji, bo dotyczyłby każdej takiej linii | wynik po podatku na wszystkich takich liniach; ponieważ +3–4 pp to za mało na podatek, ważne głównie przy promocji bez podatku | archiwum i kolejne noce |

**Kolejność:** H4 etap 1, H5 i H7, potem H3, H8 i H9 (koniec listopada, razem z weryfikacją modelu zliczeń).

**Ocena:** `python -m backtest.mispricing_eval` zapisuje raport w `data/backtest/mispricing.md`. Używa tych samych
detektorów co aplikacja i rozlicza wynikami z ESPN. Przedziały mają 99% i pochodzą z losowania całych nocy. Ustalone
przed oceną, 1.11:
- **Oferta w chwili każdego pobrania.** Mecz pobierany przez harmonogram odtwarzamy z `superbet_prop_quotes` (zapisane
  są tylko zmiany, więc linia w danej chwili to jej ostatnia zmiana). Starsze mecze bierzemy z zapisów dashboardu
  (`superbet_props`).
- **Testy „a” liczą sygnał raz:** na mecz, gracza, zakład i stronę, przy pierwszym pobraniu, w którym dało się go
  postawić (następne pobranie miało tę samą linię i kurs nie gorszy). Sygnał z ostatniego pobrania przed meczem nie
  da się tak sprawdzić i nie jest liczony; raport podaje, ile ich było. Miary: przewaga nad zamknięciem po podatku
  (`tracking.add_clv`, tylko ważne zamknięcia) i ROI po podatku. Główną miarą jest zamknięcie, gdy ma je większość
  sygnałów.
- **Testy „b” i kontrolę metody H1** liczymy na ostatnim kursie każdej linii przed meczem, jak w rozpoznaniu.
  Raport odtwarza liczby rozpoznania: H2b +2,8 pp, H6b +5,5 pp, średnie `g` H1 +0,3 pp.
- **Werdykt podaje raport, status ustawiamy ręcznie** w `data/backtest/mispricing_status.json`.

Na nocach rozpoznania test „a” liczony tą zasadą daje mniej sygnałów niż liczby w sekcjach wyżej (liczone na ostatnim
kursie): H2a 94 sygnały do postawienia, ROI −18,3%; H6a 2; H1a 0. Starsze mecze często mają tylko jeden zapis, więc
wiele sygnałów zostaje niesprawdzonych (H2: 56).
