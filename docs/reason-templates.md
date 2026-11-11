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
| `reason.expected` | The player has games in the sample (neutral) | Expected {proj:.1f} {stat} tonight vs the line {line:g} ({diff:+.1f}); average {avg:.1f}, median {median:.1f} | Oczekiwane dziś {proj:.1f} {stat} wobec linii {line:g} ({diff:+.1f}); średnia {avg:.1f}, mediana {median:.1f} |
| `reason.teammates` | Lineup adjustment is non-zero and at least one out teammate has games without the player; lists each teammate's share (the adjustment is their sum) | Out per RotoWire: {names}. The model adds {adj:+.1f} {stat} to his average: one with/without difference per teammate, each shrunk toward 0 the more, the fewer games it rests on, added up ({parts}). A description of his past games, not their effect | Nie grają (RotoWire): {names}. Model dodaje {adj:+.1f} {stat} do jego średniej: osobna różnica z/bez dla każdego kolegi, każda ściągnięta do 0 tym mocniej, im mniej meczów za nią stoi, zsumowane ({parts}). Opis jego dawnych meczów, nie ich wpływ |
| `reason.teammates_part` | Fragment: one teammate's share of the adjustment and the games it rests on | {mate} {change:+.1f} ({n} {n\|game\|games\|games} without him) | {mate} {change:+.1f} ({n} {n\|mecz\|mecze\|meczów} bez niego) |
| `reason.teammates_fewest` | Fragment: used instead of the shares when a caller has no per-teammate breakdown | fewest games without one of them: {n} | najmniej meczów bez jednego z nich: {n} |
| `reason.teammates_unknown` | Fragment: out teammates the player never played without (effect unknown, nothing added) | . No games without {names}: their effect is unknown, and the model adds nothing for them | . Brak meczów bez: {names}. Ich wpływ jest nieznany, a model nic za nich nie dodaje |
| `reason.unmatched` | Words: out players without a matched name (never a raw id) | {k} {k\|player\|players\|players} without a matched name | {k} {k\|zawodnik\|zawodników\|zawodników} bez dopasowanego nazwiska |
| `reason.unmatched_one` | Words: one share whose player has no matched name | a player without a matched name | zawodnik bez dopasowanego nazwiska |
| `reason.environment` | Team implied points and usual points are known | Scoring environment: Superbet expects {team} to score {implied:.0f} (usually {usual:.0f}) | Otoczenie punktowe: Superbet oczekuje, że {team} zdobędzie {implied:.0f} (zwykle {usual:.0f}) |
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

## 7. Mispricing signals (Superbet prices that don't fit together)

Each signal is shown as up to six lines in order: clears/short, what happened, why, expiry, test status, and (if it clears) exploration results. Rejected hypotheses and gaps below the display minimum are hidden. Templates exist for H1, H2, H5 and H6. H5 is not emitted on the props page (it doesn't pass the RotoWire role to the detector; see docs/hipotezy_wyceny.md), and `reason.vs_opp` is not emitted while its reason_lift status is `no_lift`. The gap's threshold is the break-even under the page's cost profile, margin included.

### H1: a combo line against its parts

| Key | When shown | English | Polish |
|---|---|---|---|
| `mispricing.h1.short` | Gap doesn't cover the tax | Not enough to break even after costs: {stat} {line:g} differs from its parts' lines by {gap:.1f} pp, and with the margin and costs it takes {needed:.1f} pp. | Za mało, by wyjść na zero po kosztach: {stat} {line:g} różni się od linii składowych o {gap:.1f} pp, a z marżą i kosztami potrzeba {needed:.1f} pp. |
| `mispricing.h1.clears` | Gap covers the tax | {stat} {line:g} differs from its parts' lines by {gap:.1f} pp; with the margin and costs it takes {needed:.1f} pp, and the gap covers it. | {stat} {line:g} różni się od linii składowych o {gap:.1f} pp; z marżą i kosztami potrzeba {needed:.1f} pp i ta różnica to pokrywa. |
| `mispricing.h1.what` | What happened | What happened: the lines {parts} (with how this player's numbers go together over {n} games) give the bet “{side} {stat} {line:g}” a {p_ours:.0f}% chance; Superbet's own price gives it {p_book:.0f}% (the chance by the odds without the margin). | Co się stało: z linii {parts} (i z tego, jak u tego gracza te liczby idą razem w {n} meczach) wynika dla zakładu „{side} {stat} {line:g}” szansa {p_ours:.0f}%; cena Superbetu daje mu {p_book:.0f}% (szansa według kursu bez marży). |
| `mispricing.h1.why` | Why it may be a pricing error | Why it may be a pricing error: Superbet prices the sum apart from its parts; when one of those prices lags, they stop fitting together. | Dlaczego to może być błąd ceny: Superbet wycenia sumę osobno od jej składowych; gdy jedna z tych cen nie nadąża, przestają do siebie pasować. |

### H2: makes vs attempts and the player's shooting

| Key | When shown | English | Polish |
|---|---|---|---|
| `mispricing.h2.short` | Gap doesn't cover the tax | Not enough to break even after costs: {stat} {line:g} differs by {gap:.1f} pp from what the {part} line and the player's shooting give, and with the margin and costs it takes {needed:.1f} pp. | Za mało, by wyjść na zero po kosztach: {stat} {line:g} różni się o {gap:.1f} pp od tego, co wynika z linii {part} i skuteczności gracza, a z marżą i kosztami potrzeba {needed:.1f} pp. |
| `mispricing.h2.clears` | Gap covers the tax | {stat} {line:g} differs by {gap:.1f} pp from what the {part} line and the player's shooting give; with the margin and costs it takes {needed:.1f} pp, and the gap covers it. | {stat} {line:g} różni się o {gap:.1f} pp od tego, co wynika z linii {part} i skuteczności gracza; z marżą i kosztami potrzeba {needed:.1f} pp i ta różnica to pokrywa. |
| `mispricing.h2.what` | What happened | What happened: the lines {part} {part_line:g} and {stat} {line:g} together assume he makes {implied_rate:.0f}% of his shots; he makes {player_rate:.0f}% ({made:.0f} of {attempted:.0f} in {games_all:.0f} games, pulled toward the league's {league_rate:.0f}% while the sample is small). At his rate the bet “{side} {stat} {line:g}” has a {p_ours:.0f}% chance; Superbet's price gives it {p_book:.0f}% (the chance by the odds without the margin). | Co się stało: linie {part} {part_line:g} i {stat} {line:g} razem zakładają, że trafi {implied_rate:.0f}% rzutów; trafia {player_rate:.0f}% ({made:.0f} z {attempted:.0f} w {games_all:.0f} meczach, przy małej próbie ściągnięte do średniej ligi {league_rate:.0f}%). Przy jego skuteczności zakład „{side} {stat} {line:g}” ma szansę {p_ours:.0f}%; cena Superbetu daje mu {p_book:.0f}% (szansa według kursu bez marży). |
| `mispricing.h2.why` | Why it may be a pricing error | Why it may be a pricing error: Superbet prices made and attempted shots as separate lines; when one moves without the other, the shooting they assume stops fitting the player. | Dlaczego to może być błąd ceny: Superbet wycenia trafione i oddane rzuty jako osobne linie; gdy jedna się przesuwa bez drugiej, zakładana skuteczność przestaje pasować do gracza. |

### H5: tonight's role changes his minutes

| Key | When shown | English | Polish |
|---|---|---|---|
| `mispricing.h5.short` | Gap doesn't cover the tax | Not enough to break even after costs: with the minutes of tonight's role, “{side} {stat} {line:g}” has a {gap:.1f} pp higher chance than its price, and with the margin and costs it takes {needed:.1f} pp. | Za mało, by wyjść na zero po kosztach: przy minutach dzisiejszej roli zakład „{side} {stat} {line:g}” ma szansę o {gap:.1f} pp wyższą niż w cenie, a z marżą i kosztami potrzeba {needed:.1f} pp. |
| `mispricing.h5.clears` | Gap covers the tax | With the minutes of tonight's role, “{side} {stat} {line:g}” has a {gap:.1f} pp higher chance than its price; with the margin and costs it takes {needed:.1f} pp, and the gap covers it. | Przy minutach dzisiejszej roli zakład „{side} {stat} {line:g}” ma szansę o {gap:.1f} pp wyższą niż w cenie; z marżą i kosztami potrzeba {needed:.1f} pp i ta różnica to pokrywa. |
| `mispricing.h5.what` | What happened | What happened: RotoWire tonight: {role}. He started {starts} of his last {last_games} games and played {usual_minutes:.0f} min in them. In this role he'd play about {minutes:.0f} min ({role_games} of his last {n} games in it, pulled toward the league's starter-bench difference). Superbet's price scaled to those minutes gives “{side} {stat} {line:g}” {p_ours:.0f}%; the price alone gives {p_book:.0f}% (the chance by the odds without the margin). | Co się stało: według RotoWire dziś {role}. W ostatnich {last_games} meczach zaczynał {starts} razy i grał w nich {usual_minutes:.0f} min. W tej roli grałby około {minutes:.0f} min ({role_games} z ostatnich {n} meczów w tej roli, ściągnięte do ligowej różnicy między piątką a ławką). Cena Superbetu przeliczona na te minuty daje zakładowi „{side} {stat} {line:g}” {p_ours:.0f}%; sama cena daje {p_book:.0f}% (szansa według kursu bez marży). |
| `mispricing.h5.why` | Why it may be a pricing error | Why it may be a pricing error: a price set on the minutes he has been playing may not have caught up with a new role. On the exploration nights it had: the side the role change points to won less often than its price. | Dlaczego to może być błąd ceny: cena ustawiona pod minuty, które grał dotąd, mogła nie nadążyć za nową rolą. Na nocach rozpoznania nadążała: strona, na którą wskazuje zmiana roli, wygrywała rzadziej, niż mówiła cena. |

### H6: results spread wider than the price assumes

| Key | When shown | English | Polish |
|---|---|---|---|
| `mispricing.h6.short` | Gap doesn't cover the tax | Not enough to break even after costs: with how this player's results spread, “{side} {stat} {line:g}” has a {gap:.1f} pp higher chance than its price, and with the margin and costs it takes {needed:.1f} pp. | Za mało, by wyjść na zero po kosztach: przy rozrzucie wyników tego gracza zakład „{side} {stat} {line:g}” ma szansę o {gap:.1f} pp wyższą niż w cenie, a z marżą i kosztami potrzeba {needed:.1f} pp. |
| `mispricing.h6.clears` | Gap covers the tax | With how this player's results spread, “{side} {stat} {line:g}” has a {gap:.1f} pp higher chance than its price; with the margin and costs it takes {needed:.1f} pp, and the gap covers it. | Przy rozrzucie wyników tego gracza zakład „{side} {stat} {line:g}” ma szansę o {gap:.1f} pp wyższą niż w cenie; z marżą i kosztami potrzeba {needed:.1f} pp i ta różnica to pokrywa. |
| `mispricing.h6.what` | What happened | What happened: in his last {n} games he ended below {line:g} {stat} {below:.0f}% of the time. His results swing more than usual for his average: spread {spread:.1f}× (1.0× = evenly scattered, the league's typical {league_spread:.1f}×). Superbet's price with that spread gives “{side} {stat} {line:g}” {p_ours:.0f}%; the price alone gives {p_book:.0f}% (the chance by the odds without the margin). | Co się stało: w ostatnich {n} meczach kończył poniżej {line:g} ({stat}) w {below:.0f}% meczów. Jego wyniki wahają się mocniej niż zwykle przy takiej średniej: rozrzut {spread:.1f}× (1.0× = równomiernie, typowo w lidze {league_spread:.1f}×). Cena Superbetu z takim rozrzutem daje zakładowi „{side} {stat} {line:g}” {p_ours:.0f}%; sama cena daje {p_book:.0f}% (szansa według kursu bez marży). |
| `mispricing.h6.why` | Why it may be a pricing error | Why it may be a pricing error: with small numbers what counts is how often he ends on 0 or 1. The price fits a typical spread; a player whose results swing more ends below the line more often at the same average. | Dlaczego to może być błąd ceny: przy małych liczbach liczy się, jak często gracz kończy na 0 albo 1. Cena pasuje do typowego rozrzutu; u gracza, którego wyniki wahają się mocniej, wynik poniżej linii zdarza się częściej przy tej samej średniej. |

### Shared lines

| Key | When shown | English | Polish |
|---|---|---|---|
| `mispricing.expiry.line_or_odds_change` | How long it holds | Holds for these odds only: it's gone when any of these lines or odds changes. | Aktualne tylko dla tych kursów: znika, gdy zmieni się którakolwiek z tych linii lub kursów. |
| `mispricing.status.untested` | Test status: not tested yet | 🧪 Observation, not tested. It's an observation, not a hint to bet: the test on nights it hasn't seen hasn't been run yet. | 🧪 Obserwacja, niesprawdzona. To obserwacja, nie wskazówka do gry: test na nocach, których nie widział, jeszcze się nie odbył. |
| `mispricing.status.admitted` | Test status: admitted | ✅ Tested on nights the test hadn't seen: the results are on the Backtest page. | ✅ Sprawdzona na nocach, których test wcześniej nie widział: wyniki są na stronie Backtest. |
| `mispricing.exploration` | Only when it clears: results on exploration nights | On the exploration nights ({nights} nights to {through}) there were {signals} such signals that cleared the standard 12% stake tax: {won:.0f}% won, {roi:+.1f} per 100 staked after that tax. | Na nocach rozpoznania ({nights} nocy do {through}) takich sygnałów, które pokrywały standardowy podatek 12%, było {signals}: wygrało {won:.0f}%, wynik {roi:+.1f} zł na 100 zł stawki po tym podatku. |

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

