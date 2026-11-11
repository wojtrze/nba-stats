# Reason templates for review

NBA stats app · as of 2026-11-11 · source: `dashboard/i18n.py` (texts), `dashboard/reasons.py` and `dashboard/decisions.py` (when each is shown)

Every sentence the app shows to explain a bet decision, in English and Polish, with when it appears. Words in `{braces}` are filled in at run time: `{x:.1f}` = one decimal, `{x:+.1f}` = with a sign, `{x:g}` = as short as possible, `{n|game|games|games}` = the plural form chosen by n. A line marked *Fragment* is appended to another reason, not shown alone.

## How reasons work

The reasons explain a decision that is already made; how many there are never changes it. Each has a kind:

| Kind | What it is | For / against? |
|---|---|---|
| Economics | The model's chance vs what the odds need after the stake tax | Yes: by the sign of the edge |
| Driver | An input the model uses, with how much it moved the final chance (pp) | Yes: by the sign of the impact, if at least the minimum |
| Context | What the player's games show that the model doesn't use | Only if backtested to predict beyond the model on unseen lines |
| Warning | Worth knowing; doesn't block | No |
| Blocker | Red flag: keeps the offer from Bet and the shortlist | Always against |
| Mispricing | Superbet's own prices contradict each other or the news | Only if the hypothesis was admitted on unseen nights |

A reason that lacks its data (value, reference, time, source, and observations where it rests on games) is not shown.

## 1. Decision reasons (one verdict per game)

Shown in the verdict panel. They explain why a game gets Bet / Don't bet / Wait / Unavailable.

| Key | When shown | English | Polish |
|---|---|---|---|
| `decision.reason.game_model` | Unavailable. Team markets, always: the game model failed its test against the bookmaker's margin-free price | The game model isn't admitted: on the settled nights it predicted worse than the bookmaker's margin-free price | Model meczów nie jest dopuszczony: na rozliczonych wieczorach przewidywał gorzej niż kurs bez marży |
| `decision.reason.no_calibration` | Unavailable. Player props: no calibration fitted for the current model version | The props model isn't admitted: no calibration fitted for its current version | Model zawodników nie jest dopuszczony: brak kalibracji dla jego bieżącej wersji |
| `decision.reason.no_odds` | Wait. No priced player line for the game | No odds for this game's player lines | Brak kursów na linie zawodników tego meczu |
| `decision.reason.stale_odds` | Wait. Odds older than the allowed age | The odds are {hours:.0f} h old: fetch them again | Kursy mają {hours:.0f} h: pobierz je ponownie |
| `decision.reason.no_lineup` | Wait. RotoWire has no lineup for a team of the game | RotoWire doesn't list the lineup of {teams} yet | RotoWire nie podaje jeszcze składu {teams} |
| `decision.reason.questionable` | Wait. The best line's player is questionable | {name} may not play ({role}): wait for the lineup | {name} może nie zagrać ({role}): poczekaj na skład |
| `decision.reason.no_threshold` | Don't bet. No edge threshold validated on held-out nights yet | No offer can qualify: there's no edge threshold yet that was checked on nights not used to choose it | Żadna oferta nie może się zakwalifikować: nie ma jeszcze progu przewagi sprawdzonego na nocach, których nie użyto do jego wyboru |
| `decision.reason.no_offer` | Don't bet. No offer reaches the threshold | No offer has an edge after tax of {threshold:+.1f} pp or more | Żadna oferta nie ma przewagi po podatku co najmniej {threshold:+.1f} pp |
| `decision.reason.tie` | Wait. The two best offers tie on expected return | Two offers tie on expected return: no arbitrary choice | Dwie oferty mają równy oczekiwany zwrot: bez arbitralnego wyboru |
| `decision.reason.meets` | Bet. The chosen offer meets the threshold | Meets the recorded threshold | Spełnia zapisany próg |
| `decision.reason.other_offer` | Don't bet. Every other line of a game that has a Bet offer | Another offer of this game is the one evaluated | Oceniana jest inna oferta tego meczu |

## 2. Prop reasons: price (economics)

Always first. 'For' when the edge after tax is positive, else 'against'.

| Key | When shown | English | Polish |
|---|---|---|---|
| `reason.model` | Edge is known; the active cost profile has the stake tax | Model: {side} wins {model:.1f}%; odds {odds:.2f} after the {tax:.0f}% stake tax need {be:.1f}% (edge {edge:+.1f} pp, {ev:+.1f} per 100 staked) | Model: {side} wygrywa w {model:.1f}%; kurs {odds:.2f} po {tax:.0f}% podatku od stawki wymaga {be:.1f}% (przewaga {edge:+.1f} pp, {ev:+.1f} na 100 zł stawki) |
| `reason.model_no_tax` | Same, under a no-tax (promotion) profile | Model: {side} wins {model:.1f}%; odds {odds:.2f} without the stake tax (promotion, {tax:.0f}%) need {be:.1f}% (edge {edge:+.1f} pp, {ev:+.1f} per 100 staked) | Model: {side} wygrywa w {model:.1f}%; kurs {odds:.2f} bez podatku od stawki (promocja, {tax:.0f}%) wymaga {be:.1f}% (przewaga {edge:+.1f} pp, {ev:+.1f} na 100 zł stawki) |
| `reason.beyond_price` | How far the player's numbers move the chance away from the price (neutral) | The price alone says {side} {market:.1f}% (margin-free), {price:.1f}% after the calibration; the player's numbers move it {beyond:+.1f} pp | Sama cena mówi {side} {market:.1f}% (bez marży), {price:.1f}% po kalibracji; liczby zawodnika zmieniają to o {beyond:+.1f} pp |

## 3. Prop reasons: model drivers

Inputs the model uses. Each driver ends with an impact fragment; for/against follows the sign of the impact when it is at least the minimum.

| Key | When shown | English | Polish |
|---|---|---|---|
| `reason.expected` | The player has games in the sample (neutral) | The model's projection: {proj:.1f} {stat} tonight vs the line {line:g} ({diff:+.1f}); average {avg:.1f}, median {median:.1f} | Projekcja modelu: {proj:.1f} {stat} dziś wobec linii {line:g} ({diff:+.1f}); średnia {avg:.1f}, mediana {median:.1f} |
| `reason.teammates` | Lineup adjustment is non-zero and at least one out teammate has games without the player; lists each teammate's share (the adjustment is their sum) | Out per RotoWire: {names}. The model adds {adj:+.1f} {stat} to his average: one with/without difference per teammate, each shrunk toward 0 the more, the fewer games it rests on, added up ({parts}). A description of his past games, not their effect | Nie grają (RotoWire): {names}. Model dodaje {adj:+.1f} {stat} do jego średniej: osobna różnica z/bez dla każdego kolegi, każda ściągnięta do 0 tym mocniej, im mniej meczów za nią stoi, zsumowane ({parts}). Opis jego dawnych meczów, nie ich wpływ |
| `reason.teammates_part` | Fragment: one teammate's share of the adjustment and the games it rests on | {mate} {change:+.1f} ({n} {n\|game\|games\|games} without him) | {mate} {change:+.1f} ({n} {n\|mecz\|mecze\|meczów} bez niego) |
| `reason.teammates_fewest` | Fragment: used instead of the shares when a caller has no per-teammate breakdown | fewest games without one of them: {n} | najmniej meczów bez jednego z nich: {n} |
| `reason.teammates_unknown` | Fragment: out teammates the player never played without (effect unknown, nothing added) | . No games without {names}: their effect is unknown, and the model adds nothing for them | . Brak meczów bez: {names}. Ich wpływ jest nieznany, a model nic za nich nie dodaje |
| `reason.unmatched` | Words: out players without a matched name (never a raw id) | {k} {k\|player\|players\|players} without a matched name | {k} {k\|zawodnik\|zawodników\|zawodników} bez dopasowanego nazwiska |
| `reason.unmatched_one` | Words: one share whose player has no matched name | a player without a matched name | zawodnik bez dopasowanego nazwiska |
| `reason.environment` | Team implied points and usual points are known | Scoring environment: from Superbet's handicap and total, {team} about {implied:.0f} points (usually {usual:.0f}) | Otoczenie punktowe: z handicapu i sumy Superbetu {team} około {implied:.0f} pkt (zwykle {usual:.0f}) |
| `reason.matchup` | Opponent's allowed stat to the player's position is known | {opp} allow {value:.1f} {stat} per game to {position}, {diff:.1f} {more} than average (rank {rank} of {teams}, 1 = allows the most): {word} matchup | {opp} pozwalają {position} na {value:.1f} {stat} na mecz, o {diff:.1f} {more} niż przeciętnie (miejsce {rank} z {teams}, 1 = pozwala najwięcej): {word} rywal |
| `reason.impact` | Fragment appended to a driver: impact at or above the minimum | ; moves the model's chance {impact:+.1f} pp | ; zmienia szansę modelu o {impact:+.1f} pp |
| `reason.impact_none` | Fragment appended to a driver: impact below the minimum | ; moves the model's chance less than {least:g} pp | ; zmienia szansę modelu o mniej niż {least:g} pp |
| `reason.more` | Word used in reason.matchup | more | więcej |
| `reason.fewer` | Word used in reason.matchup | fewer | mniej |
| `reason.position.G` | Position word in reason.matchup | guards | obrońcom |
| `reason.position.F` | Position word | forwards | skrzydłowym |
| `reason.position.C` | Position word | centers | środkowym |
| `reason.position.` | Position word when unknown | this position | tej pozycji |

## 4. Prop reasons: context the model doesn't use

Neutral unless the backtest (reason_lift) showed the feature predicted results beyond the model on unseen lines; then for/against in the direction it did.

| Key | When shown | English | Polish |
|---|---|---|---|
| `reason.history_last` | 3+ games: hit rate at this line in the last 10 | At this line: {side} in {hits} of the last {n} games ({rate:.0f}%; 95% range of this past rate {low:.0f}–{high:.0f}%) | Przy tej linii: {side} w {hits} z ostatnich {n} meczów ({rate:.0f}%; 95% przedział tej historycznej częstości {low:.0f}–{high:.0f}%) |
| `reason.history_all` | Fragment: more than 10 games, hit rate over all of them (the rate the model uses) | , {hits} of all {n} ({rate:.0f}%) | , {hits} ze wszystkich {n} ({rate:.0f}%) |
| `reason.history_is_all` | Fragment: 10 games or fewer, the last 10 are the whole sample |  (the whole sample) |  (to cała próba) |
| `reason.history_note` | Fragment always closing the hit-rate reason: break-even after costs and which rate the model uses | ; needs {be:.0f}% after costs. The model uses the rate over all {n} games, pulled toward the price as if the price were worth 10 games | ; potrzeba {be:.0f}% po kosztach. Model używa częstości ze wszystkich {n} meczów, ściągniętej do ceny tak, jakby cena była warta 10 meczów |
| `reason.sample_last_season` | Fragment (hit rate and projection): sample topped up with last season's games | ; {n} of the games are from last season | ; {n} z meczów to zeszły sezon |
| `reason.sample_preseason` | Fragment (hit rate and projection): sample includes preseason games | ; {n} are preseason | ; {n} to przedsezon |
| `reason.minutes` | Minutes in the last 5 differ by 3+ from earlier games with the team | Minutes: {recent:.1f} per game in the last 5 ({low:.0f}–{high:.0f}) vs {usual:.1f} in his {n} earlier games with {team} | Minuty: {recent:.1f} na mecz w ostatnich 5 ({low:.0f}–{high:.0f}) wobec {usual:.1f} w {n} wcześniejszych meczach w {team} |
| `reason.minutes_short` | Fragment: some of the last 5 were short (fouls, blowouts) | ; short games among them: {short} (5+ fouls in {fouls}, decided by 20+ in {blowouts}) | ; krótkie mecze wśród nich: {short} (5+ fauli w {fouls}, różnica 20+ w {blowouts}) |
| `reason.role` | Starter/bench history vs tonight's RotoWire role | Role: started {started} of the last {n} games; RotoWire tonight: {role} | Rola: zaczynał {started} z ostatnich {n} meczów; RotoWire dziś: {role} |
| `reason.volume` | Shot-based stats: shot volume and accuracy, last 5 vs earlier | Shots per 36 min in the last 5: {fga:.1f} FGA, {tpa:.1f} 3PA, {fta:.1f} FTA (before: {fga0:.1f}, {tpa0:.1f}, {fta0:.1f}); made {fg:.0f}% / {tp:.0f}% / {ft:.0f}% (before: {fg0:.0f}% / {tp0:.0f}% / {ft0:.0f}%), {attempts} attempts in the last 5 | Rzuty na 36 min w ostatnich 5: {fga:.1f} FGA, {tpa:.1f} 3PA, {fta:.1f} FTA (wcześniej: {fga0:.1f}, {tpa0:.1f}, {fta0:.1f}); celność {fg:.0f}% / {tp:.0f}% / {ft:.0f}% (wcześniej: {fg0:.0f}% / {tp0:.0f}% / {ft0:.0f}%), {attempts} prób w ostatnich 5 |
| `reason.home` | Home game, 6+ games and 3+ home games | At home: {value:.1f} in {n} home games ({avg:.1f} overall) | U siebie: {value:.1f} w {n} meczach u siebie ({avg:.1f} ogółem) |
| `reason.away` | Away game, same conditions | Away: {value:.1f} in {n} away games ({avg:.1f} overall) | Na wyjeździe: {value:.1f} w {n} meczach wyjazdowych ({avg:.1f} ogółem) |
| `reason.rest` | Rest days for both teams are known | Rest days: {team} {rest}, {opp} {opp_rest}; {name} played {m3:.0f} min in the last 3 days and {m7:.0f} in the last 7 | Dni odpoczynku: {team} {rest}, {opp} {opp_rest}; {name} grał {m3:.0f} min w ostatnich 3 dniach i {m7:.0f} w ostatnich 7 |
| `reason.vs_opp` | 2+ games vs the opponent, and only if that feature showed lift | Against {opp}: {avg:.1f} {stat} in {n} games (all stored seasons) | Przeciw {opp}: {avg:.1f} {stat} w {n} meczach (wszystkie zapisane sezony) |
| `reason.blowout_favoured` | Starter; team favoured by 10+ | {team} favoured by {spread:g}: in his games decided by 15+ he played {big:.1f} min ({n_big}), in closer ones {close:.1f} ({n_close}) | {team} faworytem o {spread:g}: w jego meczach rozstrzygniętych różnicą 15+ grał {big:.1f} min ({n_big}), w wyrównanych {close:.1f} ({n_close}) |
| `reason.blowout_underdogs` | Starter; team underdog by 10+ | {team} underdogs by {spread:g}: in his games decided by 15+ he played {big:.1f} min ({n_big}), in closer ones {close:.1f} ({n_close}) | {team} słabszy o {spread:g}: w jego meczach rozstrzygniętych różnicą 15+ grał {big:.1f} min ({n_big}), w wyrównanych {close:.1f} ({n_close}) |
| `reason.line_moved` | The line changed since first seen | The line moved {move:+g} since first seen ({open:g} → {line:g}); market context, not a reason for the current offer | Linia ruszyła o {move:+g} od pierwszego zapisu ({open:g} → {line:g}); kontekst rynku, nie powód za aktualną ofertą |
| `reason.odds_moved` | Same line, the odds changed since first seen | Same line {line:g}, odds {open_odds:.2f} → {odds:.2f} since first seen: the margin-free chance of {side} went {was:.0f}% → {now:.0f}% | Ta sama linia {line:g}, kurs {open_odds:.2f} → {odds:.2f} od pierwszego zapisu: szansa {side} bez marży {was:.0f}% → {now:.0f}% |
| `reason.before_tip` | Fragment: hours before tip-off for the two above |  ({hours:.0f} h before tip-off) |  ({hours:.0f} h przed meczem) |

## 5. Warnings (worth knowing, don't block)

| Key | When shown | English | Polish |
|---|---|---|---|
| `warn.role` | Started 30% or fewer of the last 10 but starts tonight, or 70%+ but on the bench | Started {started} of the last {n} games but RotoWire lists him as {role} tonight: the numbers come from another role | Zaczynał {started} z ostatnich {n} meczów, a RotoWire podaje go dziś jako {role}: liczby pochodzą z innej roli |
| `warn.stint` | Fewer than the minimum games are with his current team | Only {k} of the {n} games are with {team}: the rest are from another team | Tylko {k} z {n} meczów to {team}: reszta to inna drużyna |
| `warn.lineup_expected` | RotoWire lineup is expected, not confirmed | RotoWire's lineup of {team} is expected, not confirmed | Skład {team} na RotoWire jest przewidywany, nie potwierdzony |
| `warn.absence_unknown` | Teammates are out but the player has no games without any of them: no adjustment, effect unknown | Out per RotoWire: {names}, but he has no games without them: their effect is unknown, not zero, and the model doesn't adjust for them | Nie grają (RotoWire): {names}, ale nie ma meczów bez nich: ich wpływ jest nieznany, a nie zerowy, i model go nie uwzględnia |

## 6. Blockers (red flags: the offer can't get Bet)

| Key | When shown | English | Polish |
|---|---|---|---|
| `flag.few_games` | Fewer than the minimum games in the sample | Only {n} {n\|game\|games\|games} in the sample: too few to trust the numbers | Tylko {n} {n\|mecz\|mecze\|meczów} w próbie: za mało, żeby ufać liczbom |
| `flag.preseason` | Every game in the sample is preseason | Every game is preseason: minutes and roles change in the regular season | Wszystkie mecze to przedsezon: minuty i role zmieniają się w sezonie zasadniczym |
| `flag.out` | RotoWire play chance is 0% | RotoWire: {status}: won't play (the line is refunded) | RotoWire: {status}: nie zagra (zakład zostanie zwrócony) |
| `flag.may_not_play` | RotoWire play chance between 0% and 100% | RotoWire: {status}: may sit or play limited minutes | RotoWire: {status}: może nie zagrać albo zagrać mało minut |
| `flag.minutes` | 5+ games and minutes vary a lot (std / mean > 0.35) | Minutes swing a lot ({low:.0f}–{high:.0f}): the role isn't settled | Minuty bardzo się wahają ({low:.0f}–{high:.0f}): rola nie jest ustalona |
| `flag.line_against` | The line moved 1.5+ against the evaluated side | The line moved {move:g} against the pick: the market may know something (injury, minutes) | Linia ruszyła o {move:g} przeciw typowi: rynek może coś wiedzieć (kontuzja, minuty) |

## 7. Research hypotheses about Superbet's prices

Shown only in the collapsed section 'Research hypotheses: they don't affect the decision' (an admitted hypothesis, none yet, would be shown with the reasons). Each signal reads in this order: which offer, test status, exploration record, beside the main model (same offer only), above/below the break-even after costs, how it is computed, assumptions and limits, how long it holds. Rejected hypotheses and gaps below the display minimum are hidden. Templates exist for H1, H2, H5 and H6. H5 is not emitted on the props page (it doesn't pass the RotoWire role to the detector; see docs/hipotezy_wyceny.md), and `reason.vs_opp` is not emitted while its reason_lift status is `no_lift`. The gap's threshold is the break-even under the page's cost profile, margin included.

### H1: a combo line against its parts

| Key | When shown | English | Polish |
|---|---|---|---|
| `mispricing.h1.what` | How it is computed | How: each part's mean is solved from its margin-free price ({parts}) with this player's spread; the parts are added with his correlations over his last {n} games, pulled toward the league's; the sum is treated as a count (negative binomial, or Poisson when it varies less than its mean, which then ignores the correlations). This gives “{side} {stat} {line:g}” {p_ours:.0f}%; Superbet's own price {p_book:.0f}%. | Jak: średnią każdej składowej wyznacza jej cena bez marży ({parts}) przy rozrzucie tego gracza; składowe są sumowane z jego korelacjami z ostatnich {n} meczów, ściągniętymi do ligowych; suma jest traktowana jak liczba zdarzeń (ujemny dwumianowy albo Poisson, gdy waha się mniej niż jej średnia, i wtedy korelacje nie grają roli). Daje to zakładowi „{side} {stat} {line:g}” {p_ours:.0f}%; cena Superbetu {p_book:.0f}%. |
| `mispricing.h1.why` | Assumptions and limits | Assumptions and limits: the distribution and the correlations are this model's, not Superbet's. A gap can be an inconsistency between the combo's price and its parts' or a wrong assumption of this model; nothing here shows which, or that a price lags. | Założenia i ograniczenia: rozkład i korelacje są tego modelu, nie Superbetu. Różnica może być niespójnością ceny kombinacji i cen składowych albo błędnym założeniem tego modelu; nic tu nie pokazuje, które z nich, ani że któraś cena się spóźnia. |

### H2: makes vs attempts and the player's shooting

| Key | When shown | English | Polish |
|---|---|---|---|
| `mispricing.h2.what` | How it is computed: observed rate, prior share, the model's ratio | How: the {part} {part_line:g} price gives the mean attempts (solved with the player's spread), times a make rate. His observed rate: {made:.0f} of {attempted:.0f} ({observed:.0f}%) in {games_all:.0f} games; combined with the league's {league_rate:.0f}% (as if worth 200 attempts, {prior_share:.0f}% of the weight here) it is {player_rate:.0f}%. This gives “{side} {stat} {line:g}” {p_ours:.0f}%; Superbet's price {p_book:.0f}%. Fitting both prices the same way gives a ratio of {implied_rate:.0f}%: a number of this model, not a rate Superbet states. | Jak: cena {part} {part_line:g} daje średnią liczbę prób (przy rozrzucie gracza), pomnożoną przez skuteczność. Jego skuteczność obserwowana: {made:.0f} z {attempted:.0f} ({observed:.0f}%) w {games_all:.0f} meczach; połączona z ligową {league_rate:.0f}% (jak gdyby warta 200 prób, tu {prior_share:.0f}% wagi) daje {player_rate:.0f}%. Daje to zakładowi „{side} {stat} {line:g}” {p_ours:.0f}%; cena Superbetu {p_book:.0f}%. Dopasowanie obu cen w ten sam sposób daje stosunek {implied_rate:.0f}%: to liczba tego modelu, nie skuteczność podawana przez Superbet. |
| `mispricing.h2.ft_limit` | FTM only: the free-throw limit | Limit for free throws: they come in pairs and these lines are small; this model treats them as single counts, so its number here is less reliable. | Ograniczenie dla rzutów wolnych: idą parami, a te linie są małe; ten model traktuje je jak pojedyncze zdarzenia, więc jego liczba jest tu mniej wiarygodna. |
| `mispricing.h2.why` | Assumptions and limits | Assumptions and limits: attempts and makes are counts with the player's spread, and his rate holds tonight. The gap can come from these assumptions as easily as from the prices; nothing here shows that one of the two lines lags. | Założenia i ograniczenia: próby i trafienia to liczby zdarzeń z rozrzutem gracza, a jego skuteczność dziś się utrzyma. Różnica może wynikać z tych założeń tak samo jak z cen; nic tu nie pokazuje, że któraś z dwóch linii się spóźnia. |

### H5: tonight's role changes his minutes (not emitted)

| Key | When shown | English | Polish |
|---|---|---|---|
| `mispricing.h5.what` | How it is computed | How: RotoWire tonight: {role}. He started {starts} of his last {last_games} games and played {usual_minutes:.0f} min in them. In this role he'd play about {minutes:.0f} min ({role_games} of his last {n} games in it, pulled toward the league's starter-bench difference). The price's mean scaled to those minutes gives “{side} {stat} {line:g}” {p_ours:.0f}%; the price alone {p_book:.0f}%. | Jak: według RotoWire dziś {role}. W ostatnich {last_games} meczach zaczynał {starts} razy i grał w nich {usual_minutes:.0f} min. W tej roli grałby około {minutes:.0f} min ({role_games} z ostatnich {n} meczów w tej roli, ściągnięte do ligowej różnicy między piątką a ławką). Średnia z ceny przeliczona na te minuty daje zakładowi „{side} {stat} {line:g}” {p_ours:.0f}%; sama cena {p_book:.0f}%. |
| `mispricing.h5.why` | Assumptions and limits | Assumptions and limits: the price was set on his recent minutes, not on tonight's role. Nothing here shows when the price was set relative to the RotoWire news. On the exploration nights the side the role change points to won less often than its price. | Założenia i ograniczenia: cena była ustawiona pod jego ostatnie minuty, a nie pod dzisiejszą rolę. Nic tu nie pokazuje, kiedy cena powstała względem wiadomości z RotoWire. Na nocach rozpoznania strona, na którą wskazuje zmiana roli, wygrywała rzadziej, niż mówiła cena. |

### H6: results spread wider than a Poisson count

| Key | When shown | English | Polish |
|---|---|---|---|
| `mispricing.h6.what` | How it is computed; Poisson = variance equal to the mean | How: this model reads the price's mean as a Poisson count (variance equal to the mean, 1.0×). His results over his last {n} games: variance {own_spread:.1f}× the mean, pulled toward the league's typical {league_spread:.1f}× (as if worth 20 games): {spread:.1f}×, {league_cmp}. He ended below {line:g} {stat} in {below:.0f}% of them. With the price's mean and his spread “{side} {stat} {line:g}” gets {p_ours:.0f}%; the price alone {p_book:.0f}%. | Jak: ten model czyta średnią z ceny jako liczbę zdarzeń Poissona (wariancja równa średniej, 1.0×). Jego wyniki z ostatnich {n} meczów: wariancja {own_spread:.1f}× średniej, ściągnięta do typowej w lidze {league_spread:.1f}× (jak gdyby wartej 20 meczów): {spread:.1f}×, {league_cmp}. Kończył poniżej {line:g} ({stat}) w {below:.0f}% z nich. Przy średniej z ceny i jego rozrzucie zakład „{side} {stat} {line:g}” dostaje {p_ours:.0f}%; sama cena {p_book:.0f}%. |
| `mispricing.h6.above` | Words: spread above the league's typical | more than the league's typical | więcej niż typowo w lidze |
| `mispricing.h6.below` | Words: spread below the league's typical (above a Poisson's) | less than the league's typical, though more than a Poisson's | mniej niż typowo w lidze, choć więcej niż w modelu Poissona |
| `mispricing.h6.same` | Words: spread about the league's typical | about the league's typical | mniej więcej jak typowo w lidze |
| `mispricing.h6.why_under` | Assumptions and limits, when the signal favours Under | Assumptions and limits: the same mean as the price, a wider spread. Here that puts more of his results at 0 or 1, below this line, so the Under gets more likely. Reading the price as a Poisson count is this model's assumption, not a spread Superbet states. | Założenia i ograniczenia: ta sama średnia co w cenie, większy rozrzut. Tu daje to więcej wyników na 0 albo 1, poniżej tej linii, więc Poniżej staje się bardziej prawdopodobne. Czytanie ceny jako liczby Poissona to założenie tego modelu, nie rozrzut podawany przez Superbet. |
| `mispricing.h6.why_over` | Assumptions and limits, when the signal favours Over | Assumptions and limits: the same mean as the price, a wider spread. Here the price's mean is well below the line, so a wider spread puts more results far above it, and the Over gets more likely. Reading the price as a Poisson count is this model's assumption, not a spread Superbet states. | Założenia i ograniczenia: ta sama średnia co w cenie, większy rozrzut. Tu średnia z ceny leży wyraźnie pod linią, więc większy rozrzut daje więcej wyników daleko nad nią i Powyżej staje się bardziej prawdopodobne. Czytanie ceny jako liczby Poissona to założenie tego modelu, nie rozrzut podawany przez Superbet. |

### Shared lines, in the order shown

| Key | When shown | English | Polish |
|---|---|---|---|
| `mispricing.name.H1` | Hypothesis names (H1, H2, H5, H6) | H1, a combo against its parts | H1, kombinacja a jej składowe |
| `mispricing.name.H2` |  | H2, makes against attempts | H2, trafienia a próby |
| `mispricing.name.H5` |  | H5, a role change | H5, zmiana roli |
| `mispricing.name.H6` |  | H6, the spread of a small count | H6, rozrzut małej liczby |
| `mispricing.heading.this` | 1. Which offer: the one evaluated | {name}: “{side} {stat} {line:g}”, this offer | {name}: „{side} {stat} {line:g}”, ta oferta |
| `mispricing.heading.other` | 1. Which offer: another one (a combo's part, a makes line's attempts) | {name}: “{side} {stat} {line:g}”, another offer (not the one evaluated above) | {name}: „{side} {stat} {line:g}”, inna oferta (nie ta oceniana wyżej) |
| `mispricing.status.untested` | 2. Test status: not tested yet | 🧪 Not tested on nights its test hadn't seen: an observation, not a hint to bet. | 🧪 Niesprawdzona na nocach, których jej test nie widział: obserwacja, nie wskazówka do gry. |
| `mispricing.status.admitted` | 2. Test status: admitted | ✅ Tested on nights the test hadn't seen: the results are on the Backtest page. | ✅ Sprawdzona na nocach, których test wcześniej nie widział: wyniki są na stronie Backtest. |
| `mispricing.exploration` | 3. How such signals did on the exploration nights | So far: on the exploration nights ({nights} nights to {through}) {signals} signals of this hypothesis reached the break-even after the standard 12% stake tax; {won:.0f}% of them won, {roi:+.1f} per 100 staked after that tax. | Dotąd: na nocach rozpoznania ({nights} nocy do {through}) sygnałów tej hipotezy, które sięgały progu opłacalności po standardowym podatku 12%, było {signals}; wygrało {won:.0f}% z nich, wynik {roi:+.1f} zł na 100 zł stawki po tym podatku. |
| `mispricing.no_exploration` | 3. No exploration record | No exploration record yet: nothing is known about how such signals did. | Brak zapisu z rozpoznania: nie wiadomo, jak wypadały takie sygnały. |
| `mispricing.compare` | 4. Same offer: beside the main model | The same offer at {odds:.2f}: the main model estimates {p_main:.0f}% (EV {ev_main:+.1f} per 100); this alternative model {p_ours:.0f}% (EV {ev_ours:+.1f}); the price alone {p_book:.0f}% (margin-free). | Ta sama oferta po {odds:.2f}: model główny szacuje {p_main:.0f}% (EV {ev_main:+.1f} na 100); ten model alternatywny {p_ours:.0f}% (EV {ev_ours:+.1f}); sama cena {p_book:.0f}% (bez marży). |
| `mispricing.compare_this` | 4. Same offer, main model unknown | At {odds:.2f} this alternative model estimates {p_ours:.0f}% (EV {ev_ours:+.1f} per 100); the price alone {p_book:.0f}% (margin-free). | Po {odds:.2f} ten model alternatywny szacuje {p_ours:.0f}% (EV {ev_ours:+.1f} na 100); sama cena {p_book:.0f}% (bez marży). |
| `mispricing.compare_other` | 4. Another offer: not compared | At {odds:.2f} this alternative model estimates {p_ours:.0f}% (EV {ev_ours:+.1f} per 100); the price alone {p_book:.0f}% (margin-free). It's about another offer, so it isn't compared with the evaluation above. | Po {odds:.2f} ten model alternatywny szacuje {p_ours:.0f}% (EV {ev_ours:+.1f} na 100); sama cena {p_book:.0f}% (bez marży). Dotyczy innej oferty, więc nie jest porównywany z oceną wyżej. |
| `mispricing.above` | 5. Above the break-even after costs | Under this alternative model's assumptions it is {margin:.1f} pp above the break-even after costs ({be:.1f}%; margin and costs take {needed:.1f} pp over the margin-free price). | Przy założeniach tego modelu alternatywnego jest {margin:.1f} pp nad progiem opłacalności po kosztach ({be:.1f}%; marża i koszty dokładają {needed:.1f} pp do ceny bez marży). |
| `mispricing.below` | 5. Below the break-even after costs | Under this alternative model's assumptions it is {margin:.1f} pp below the break-even after costs ({be:.1f}%; margin and costs take {needed:.1f} pp over the margin-free price). | Przy założeniach tego modelu alternatywnego jest {margin:.1f} pp pod progiem opłacalności po kosztach ({be:.1f}%; marża i koszty dokładają {needed:.1f} pp do ceny bez marży). |
| `mispricing.expiry.line_or_odds_change` | Last: how long it holds | Holds for these odds only: it's gone when any of these lines or odds changes. | Aktualne tylko dla tych kursów: znika, gdy zmieni się którakolwiek z tych linii lub kursów. |

## 8. Game outcome reasons (team markets, research only)

Team markets are always Unavailable; these explain the outcome rows.

| Key | When shown | English | Polish |
|---|---|---|---|
| `game.model` | Every outcome: model vs break-even | Model: {model:.0f}%; odds {odds:.2f} after the 12% stake tax need {be:.0f}% (edge {edge:+.1f} pp) | Model: {model:.0f}%; kurs {odds:.2f} po 12% podatku od stawki wymaga {be:.0f}% (przewaga {edge:+.1f} pp) |
| `game.projection` | Projection line (with wins_by / loses_by and covering / missing) | Projection: {team} {what} | Prognoza: {team} {what} |
| `game.wins_by` | Fragment | wins by {margin:.1f} | wygrywa o {margin:.1f} |
| `game.loses_by` | Fragment | loses by {margin:.1f} | przegrywa o {margin:.1f} |
| `game.covering` | Fragment: spread covered | , covering {line:+g} by {gap:.1f} | , pokrywa {line:+g} o {gap:.1f} |
| `game.missing` | Fragment: spread missed | , missing {line:+g} by {gap:.1f} | , nie pokrywa {line:+g} o {gap:.1f} |
| `game.net` | Net ratings of both teams | Net rating {team} {net:+.1f} vs {opp} {opp_net:+.1f} points per 100 possessions | Bilans {team} {net:+.1f} wobec {opp} {opp_net:+.1f} punktu na 100 posiadań |
| `game.home_court` | Home-court points | Home court: {home} +{points:g} points | Atut własnej hali: {home} +{points:g} pkt |
| `game.absence_margin` | Winner/spread: a player's absence changes the margin | {team} without {name}: {swing:+.1f} point margin per game ({n} games missed) | {team} bez {name}: {swing:+.1f} pkt różnicy na mecz ({n} {n\|mecz\|mecze\|meczów} bez niego) |
| `game.projected_total` | Totals: projected points vs the line | Projected {expected:.1f} points vs the line {line:g} ({gap:+.1f}) | Prognoza {expected:.1f} pkt wobec linii {line:g} ({gap:+.1f}) |
| `game.pace_faster` | Totals: faster than league pace | Pace {pace:.1f} possessions vs league {league:.1f}: a faster game than average | Tempo {pace:.1f} posiadań wobec ligi {league:.1f}: mecz szybszy niż przeciętnie |
| `game.pace_slower` | Totals: slower than league pace | Pace {pace:.1f} possessions vs league {league:.1f}: a slower game than average | Tempo {pace:.1f} posiadań wobec ligi {league:.1f}: mecz wolniejszy niż przeciętnie |
| `game.attack` | Team totals: offense vs opponent's defense | {team} offense {off:.1f} vs {opp} defense {defense:.1f} (league {league:.1f}): {attack:+.1f} per 100 possessions | Atak {team} {off:.1f} wobec obrony {opp} {defense:.1f} (liga {league:.1f}): {attack:+.1f} na 100 posiadań |
| `game.absence_points` | Team totals: a player's absence changes points | {team} without {name}: {change:+.1f} points ({n} games missed) | {team} bez {name}: {change:+.1f} pkt ({n} {n\|mecz\|mecze\|meczów} bez niego) |
| `gameflag.early` | Flag: early season | Early season: the ratings are still mostly last season's, which don't know about summer trades | Początek sezonu: ratingi to wciąż głównie zeszły sezon, który nie zna letnich transferów |
| `gameflag.no_lineup` | Flag: no RotoWire lineup | RotoWire doesn't list this game yet: absences aren't in the projection | RotoWire jeszcze nie podaje tego meczu: nieobecnych nie ma w prognozie |
| `gameflag.big_edge` | Flag: edge over 15 pp | Edge over 15 pp: more likely the model is missing something (a trade, rest) than the market being that wrong | Przewaga ponad 15 pp: bardziej prawdopodobne, że model czegoś nie wie (transfer, odpoczynek), niż że rynek tak bardzo się myli |

