Personal/side project — keep the implementation small, but apply production-level rigor to payout arithmetic, time-valid data, validation, and the language shown to bettors (english and Polish).

**Your reason set is broad enough; its main weakness is not missing basketball narratives but mixing descriptive statistics, model explanations, and evidence of betting value.** I would first reduce misleading directional reasons, expose the market’s dominance and the tax hurdle, and add role/minutes, opportunity-volume, and data-validity diagnostics before expanding matchup analysis.

## Expertise and scope

**What you must be aware of:**

A useful review must distinguish **outcome probability**, **price-relative advantage**, and **after-cost expected return**; these are different quantities. It must also distinguish an explanation of what the model actually used from contextual information attached after the decision—plausible explanations are not necessarily faithful explanations. Your recent hit rate, season average, minutes trend, and absence split often describe overlapping observations, so their agreement must not look like independent confirmation. [proceedings.neurips](https://proceedings.neurips.cc/paper_files/paper/2018/hash/294a8ed24b1ad22ec2e7efea049b8737-Abstract.html)

The hidden structure is that an NBA counting stat depends on playing time, opportunities during that time, conversion of those opportunities, and game circumstances. Usage is specifically an estimate of possessions finished through shots, free throws, or turnovers—not a general measure of involvement in rebounds and assists. Market prices already incorporate information, so a basketball relationship must improve predictions **conditional on the available price**, not merely correlate with outcomes; historical NBA spread research illustrates how absence-related opening-line errors can disappear by the close, although that does not establish anything directly about your prop markets. Finally, selecting features, thresholds, and “best offers” is itself model selection, so the entire selection procedure—not just the underlying forecast—needs independent evaluation. [jmlr.csail.mit](https://jmlr.csail.mit.edu/papers/v11/cawley10a.html)


## The most important corrections

### Interpret the calibration precisely

Rewrite the calibration as:

\[
\operatorname{logit}(p_{\mathrm{final}})
=
a\operatorname{logit}(p_{\mathrm{market}})
+
b\left[
\operatorname{logit}(p_{\mathrm{raw}})
-
\operatorname{logit}(p_{\mathrm{market}})
\right]
+
cI_{\mathrm{Over}}+d.
\]

With \(b\approx0.09\), approximately 9% of the raw model’s **log-odds disagreement** survives this calibration. That is not literally 9% of a probability-point difference, nor a general statement that the model provides “9% extra accuracy.”

Two consequences follow directly from your formula:

- **The right baseline is also a recalibrated market-only model.** Fit the same structure with \(b=0\), allowing its remaining coefficients to be estimated independently.
- **Separate basketball-model contribution from market recalibration.** Some improvement over an uncalibrated market price could come from \(a\), \(c\), or \(d\), rather than from your projection features.

Calibration must be fitted using predictions generated without training on their own outcomes, and final performance must be evaluated separately again. [github](https://github.com/scikit-learn/scikit-learn/blob/99bf3d8e4/sklearn/calibration.py)

Also enforce probability coherence. For a half-point line with no push, Over and Under are complements; independently calibrated side predictions must not violate that. The simplest implementation is to estimate one Over probability and derive Under as its complement.

### Make the tax hurdle visible

For a unit of gross stake, decimal odds \(o\), stake factor \(q=0.88\), and a binary settled outcome:

\[
EV=qop-1,
\qquad
p_{\mathrm{BE}}=\frac{1}{qo}.
\]

**Illustrative arithmetic, not a backtest:** odds of 1.90 require a 59.81% win probability after your stated tax. A 57% prediction produces an expected return of approximately −4.70%, despite looking strong compared with a roughly even-money event.

Show these separately:

| Quantity | Meaning |
|---|---|
| Margin-free market probability | Market-derived forecast benchmark |
| Final calibrated probability | Your forecast |
| Probability advantage | Final probability minus market probability |
| After-tax break-even probability | Probability required at this executable price |
| After-tax EV | Expected net return per unit of gross stake |

Do not tax the market probability before removing the bookmaker margin. For a matched Over/Under pair at the **same line and snapshot**, proportional normalization is:

\[
p_{\mathrm{market,O}}
=
\frac{1/o_O}{1/o_O+1/o_U}.
\]

Treat that normalization as a benchmark convention, not revealed truth.

Finally, “after all costs” needs a qualification: Superbet’s own guidance also describes a separate tax on sufficiently large winnings. Either restrict your displayed EV to stakes below the applicable payout threshold or implement the relevant payout rules; do not imply that the 0.88 factor necessarily covers every ticket. [superbet](https://superbet.pl/wiki/jak-grac-tasmy-bukmacherskie)

### Separate explanation types

Use three distinct types:

| Type | What it can legitimately say |
|---|---|
| **Model driver** | “This input changed the forecast by this much.” |
| **Historical context** | “This pattern exists in the selected observations.” |
| **Decision constraint** | “This offer cannot currently be evaluated or admitted.” |

An input can explain the model without having demonstrated incremental predictive value. Conversely, an informative statistic that the model does not use must not be presented as an explanation of its decision.

That distinction is especially important for minutes trends, venue splits, opponent history, and blowout commentary in your current implementation.

## Review of current reasons

The table below gives the recommended treatment. “Directional” means supporting or opposing the **evaluated side**, not simply describing whether the player’s expected statistic rises.

All proposed predictive changes should pass the common validation protocol later in this review.

| Reason | Recommended treatment | Definition and validation change |
|---|---|---|
| **P1: Model vs price** | **Keep as the primary economic assessment, not one vote among many.** | Use final calibrated probability, executable odds, break-even and EV. Label whether the uncertainty range crosses break-even. Test against both raw and recalibrated market baselines. |
| **P2: Last-10 hit rate** | **Keep as context; remove automatic for/against coloring.** | Show hits at **today’s line**, sample dates, role applicability, and uncertainty. Three games cannot justify a confident directional label. Compare a shrunk recent-rate feature against market-only and the existing model. |
| **P3: Full-sample hit rate** | **Merge with P2 into one historical-distribution panel.** | Identify selected seasons, team stints and competition types. It is not independent evidence from P2. Test incremental recency information, not two separate “votes.” |
| **P4: Expected vs line** | **Keep as distribution context.** | Show mean, median and probability at the line. A mean above the line does not establish profitable Over odds. Replace universal raw-unit thresholds with probability sensitivity at the actual line. |
| **P5: Minutes trend** | **Keep, with substantial redesign.** | Compare recent minutes with the preceding baseline, preferably within the current role/team stint. Show distributions, not only averages. Unless minutes explicitly enter the model, label this context or a model limitation—not a model driver. |
| **P6: Teammates out** | **Keep the actual projection adjustment; qualify the observational split.** | Show with/without sample sizes, minutes changes, raw split, shrinkage and applied adjustment separately. Describe it as an association, not a causal effect. Test joint absence states rather than simply adding overlapping individual splits. |
| **P7: Home/away** | **Default to context, collapsed.** | Estimate a shrunk home-versus-away difference, controlling at least for minutes and role where practical. Comparing venue performance with an overall average partly compares a sample with itself. Retain directional treatment only after conditional validation. |
| **P8: Back-to-back** | **Replace with a broader schedule/rest panel.** | Include both teams’ rest, player participation and recent workload. Two prior examples are descriptive, not a usable player-specific effect. Do not assume every stat falls with less rest. |
| **P9: Position matchup** | **Demote pending validation and repair its denominator.** | Raw allowed production reflects pace, opposing player quality, position assignment and exposure. Rank out of 30 does not resolve those confounds. Test separately for each statistic and role; do not whitelist REB by intuition alone. |
| **P10: Opponent history** | **Remove from the main argument list.** | Two games across several seasons have poor comparability. If retained, put in historical detail with team/role dates and minutes. Promote only if it adds value after market, current role and broader opponent measures. |
| **P11: Implied team total** | **Keep, but rename it “scoring environment,” not pace.** | Team points reflect possessions **and efficiency**. Higher implied scoring does not mechanically improve REB or AST. Test stat-specific effects and interaction with role; identify it as market-derived information. |
| **P12: Blowout risk** | **Remove its unconditional directional rule.** | A large spread is not proof that a particular starter loses minutes, and bench players may gain them. Use projected minutes conditional on game competitiveness, or display neutral uncertainty. Test minutes and prop outcomes separately. |
| **P13: Line movement** | **Keep as context; make it economically interpretable.** | Show line, both prices, timestamps, first-observed versus latest, and distance to tip. A line change without the associated odds is incomplete. Test incremental information at the decision timestamp. |

Small-sample hit rates should be accompanied by defensible intervals; Wilson or Jeffreys-type intervals are preferable to a naive symmetric normal interval in small samples. That supports changing the presentation, not declaring a particular minimum sample universally correct. [itl.nist](https://itl.nist.gov/div898/software/dataplot/refman2/auxillar/agcoulci.htm)

### The threshold problem

**None of the quoted numerical thresholds is established as correct from the information supplied.** Separate three purposes: a display threshold, a data-support threshold, and a betting-admission threshold.

| Current threshold | Assessment | Better use |
|---|---|---|
| **3 games for recent hit rate** | Adequate to display three observations; inadequate for confident betting language | Context only, with interval and dates |
| **8 games overall** | A provisional safety rule, not proof that eight comparable games suffice | Keep provisionally, but add current-regime support and effective sample size |
| **6 games for minutes trend** | Detectability depends on dispersion and comparability | Report recent and baseline sample sizes plus uncertainty |
| **3-minute difference** | Reasonable as a possible UI filter, not a validated betting boundary | Also translate the change into stat and probability sensitivity |
| **2 opponent/B2B games** | Too weak for directional player-specific claims | Historical detail only |
| **Minutes CV above 0.35** | Mixes low-minute roles, changing roles and true unpredictability | Compare within role; test residual minutes uncertainty by role cohort |
| **1.5-point line move** | Not comparable across 3PM, REB and PTS | Use estimated probability/EV impact; preserve raw move as context |
| **Gap below max(0.5, 3% of line)** | Does not reflect distribution shape or payout | Use probability impact near the line |
| **Large-spread blowout cutoff** | Missing from the truncated text; no universal cutoff justified | Continuous spread feature with role/minutes interaction |

For weighted observations, report:

\[
n_{\mathrm{eff}}
=
\frac{\left(\sum_i w_i\right)^2}{\sum_i w_i^2}.
\]

This captures the concentration of your weights, **not** all dependence or bias. A large effective sample can still be inappropriate after a trade or role change.

## Missing computable signals

These are research candidates, not established profitable angles. Each entry includes its data requirements, definition, display treatment, and admission test.

### Minutes and role applicability

**What and why:** The most important omission is an explicit forecast of playing time and whether the historical sample represents tonight’s role. Your current projection description adjusts production for teammate absences but does not clearly model minutes separately.

**Data and definition:** Use ESPN MIN, game dates, team identity where stored, and archived RotoWire snapshots. Start with:

\[
\widehat{Y}
=
\widehat{M}
\cdot
\widehat{r}_{Y\mid\mathrm{role,availability}},
\]

where the rate uses pooled production divided by pooled minutes within comparable states. Model a minutes distribution, not just a point estimate.

**Threshold and display:** A role mismatch is context when well supported; it becomes a hard support flag when the prediction extrapolates into an unvalidated role. Do not infer historical starter status from high minutes. If historical starts are not stored, only archived lineup snapshots can directly establish that label.

**Test:** First evaluate out-of-time minutes accuracy and interval coverage. Then test whether the resulting prop probabilities improve over the price and your current model. Avoid multiplying a minutes uplift onto an absence adjustment that already captures the same uplift.

### Volume versus conversion

**What and why:** Distinguish increased scoring opportunity from a hot shooting stretch. This provides a more useful explanation than “points are trending up.”

**Data and definition:** Your fields support:

\[
r_{\mathrm{FGA}}=\frac{\sum FGA}{\sum MIN},
\quad
r_{\mathrm{3PA}}=\frac{\sum 3PA}{\sum MIN},
\quad
r_{\mathrm{FTA}}=\frac{\sum FTA}{\sum MIN}.
\]

Also derive two-point attempts/makes and estimate separately shrunk two-point, three-point and free-throw conversion rates. A candidate PTS expectation is:

\[
\widehat{PTS}
=
2\widehat{2PA}\widehat{\theta}_2
+
3\widehat{3PA}\widehat{\theta}_3
+
\widehat{FTA}\widehat{\theta}_{FT}.
\]

**Threshold and display:** Initially context: “attempt rate increased; conversion also increased.” No universal “FGA up 10%” directional threshold. Use shot-attempt counts as well as game counts; do not imply attempts are fully independent.

**Test:** Compare volume-only, efficiency-only and combined features conditional on market, minutes and absence state. Prioritize PTS, 3PM and their combos, not REB or AST indiscriminately.

### Usage and team shares

**What and why:** Show changes in offensive responsibility, while avoiding the common error of treating usage as a proxy for every counting statistic.

**Data and definition:** If complete team box scores can be reconstructed, conventional estimated usage is:

\[
USG\%
=
100
\frac{
(FGA+0.44FTA+TO)(TmMIN/5)
}{
MIN(TmFGA+0.44TmFTA+TmTO)
}.
\]

This is an estimate of team plays used while on court, not measured touches or time of possession. [faq.sports-reference](https://faq.sports-reference.com/portal/en/kb/articles/basketball-glossary)

Also compute FGA share, 3PA share, AST share and REB share, using ratio-of-sums within comparable periods.

**Threshold and display:** Context until validated. Shares are not additional independent reasons alongside minutes, shot volume and teammate absence.

**Test:** Ask whether share changes add information after minutes, attempt rates, lineup state and price. If not, retain the clearest representation and drop redundant cards.

### Opponent pace and opportunities

**What and why:** Your implied-total adjustment is not an opponent-pace measurement. Genuine pace separates possession volume from scoring efficiency.

**Data limitation:** The listed fields omit offensive rebounds, which are needed for standard box-score possession estimation. Do not compute \(FGA+0.44FTA+TO\) and label it pace; offensive rebounds can continue a possession after a missed shot. Specialist play-by-play services distinguish directly counted possessions from such box-score estimates. [pbpstats](https://www.pbpstats.com/)

**Definition:** If OREB is already retained elsewhere, an approximate team possession count is:

\[
\widehat{Poss}=FGA+0.44FTA-OREB+TO.
\]

Average the two teams’ estimates and normalize for game duration. Pace conventionally describes possessions per 48 minutes. [faq.sports-reference](https://faq.sports-reference.com/portal/en/kb/articles/basketball-glossary)

**Threshold and display:** With current listed fields, show an honestly named activity proxy or omit true pace. If valid pace becomes available, show expected possessions relative to the player’s usual environment, initially as context.

**Test:** Compare genuine pace versus implied scoring environment, then test their incremental combination by stat. Do not count both as independent confirmation.

### Rest and recent workload

**What and why:** “Second night of a back-to-back” omits opponent rest and how much the player actually played.

**Data and definition:** Use dates, team schedules and player minutes. Candidate features:

\[
R=\min(rest_{\mathrm{team}},3)-\min(rest_{\mathrm{opp}},3),
\]

plus minutes over the preceding three and seven days, consecutive appearances, and team games missed by the player. The cap of three is a proposed starting specification, not an established optimum.

**Threshold and display:** Context, with direction learned separately by stat and role. Do not infer travel fatigue without travel information or treat a long absence as beneficial recovery.

**Test:** Add these features after market, minutes and availability. Distinguish effects on minutes from effects on per-minute rates; avoid searching dozens of schedule cutoffs for a winning subset.

### Comparable-sample support

**What and why:** The relevant question is not just “how many games?” but “how many games resemble the situation being forecast?”

**Data and definition:** Use current team stint, available role history, minutes, season type and teammate availability. Report separate counts for baseline games, comparable-role games, absence-state games and effective weighted sample size.

**Threshold and display:** Add **“current role insufficiently supported”** as a potential hard flag. For a first version, require that the current role falls inside a predeclared validated regime; if not, abstain rather than borrowing confidence from unrelated seasons.

**Test:** Measure calibration and errors by support level. Choose any numerical support cutoff in development and confirm it on untouched future data. Evaluate whether abstention improves reliability at an acceptable loss of coverage.

### Distribution and combo consistency

**What and why:** A mean projection is insufficient for pricing a tail event, especially when minutes are uncertain.

Negative-binomial and Poisson distributions have specific variance restrictions: Poisson variance equals its mean; standard NB2 variance is \(\mu+\alpha\mu^2\). Consequently, a negative-binomial fit cannot reproduce every empirical variance, and switching to Poisson does not solve genuine underdispersion. [statsmodels](https://www.statsmodels.org/stable/_sources/glm.rst.txt)

**Data and definition:** Compare your current model with an empirical, shrunk distribution conditioned on role/minutes. For combos, calculate historical sums directly. For example:

\[
Var(P+R+A)
=
Var(P)+Var(R)+Var(A)
+
2Cov(P,R)+2Cov(P,A)+2Cov(R,A).
\]

Your own variance of the actual summed stat already includes these covariances; do not add an unnecessary correlation correction to it.

**Threshold and display:** Distribution disagreement is an uncertainty diagnostic, not automatically an Under argument. Flag only when a predeclared distribution/support failure invalidates the probability.

**Test:** Evaluate probability calibration at offered lines, tail performance and proper scores—not just mean error. Proper scoring rules are designed to evaluate probabilistic forecasts honestly. [sites.stat.washington](https://sites.stat.washington.edu/raftery/Research/PDF/Gneiting2007jasa.pdf)

### Line location and sensitivity

**What and why:** “Line versus average” omits how much probability is concentrated near the line and how fragile the valuation is to a small change.

**Data and definition:** At today’s line \(L\), show empirical percentile, model win probability and:

\[
\Delta_L
=
p_{\mathrm{side}}(L_{\mathrm{next}})
-
p_{\mathrm{side}}(L),
\]

where \(L_{\mathrm{next}}\) is the next valid line increment. Also report odds sensitivity and, where available, adjacent executable offers.

**Threshold and display:** Context: “a one-step line change would remove the estimated edge.” Do not compare different lines at their quoted odds as if only price had changed.

**Test:** Use actual archived executable alternatives where possible. Test whether fragile-edge offers have worse realized calibration or execution outcomes; do not invent prices for unavailable alternate lines.

### Timing and market movement

**What and why:** Your archive can measure changes, but several snapshots a day cannot reliably identify minute-scale reactions or the exact timing of news.

**Data and definition:** Preserve:

- First-observed and latest line and prices.
- Both snapshot timestamps and time to tip.
- Same-line margin-free probability change.
- Whether an availability-status change occurred between observations.
- Whether the apparent edge survives refreshing the offer.

For a fixed line:

\[
\Delta p_{\mathrm{market}}
=
p_{\mathrm{market,latest}}
-
p_{\mathrm{market,earlier}}.
\]

**Threshold and display:** Context for movement itself; hard flag when the offer or its information state is no longer valid. Call the endpoints **first observed** and **last observed**, not opening and closing unless those labels are justified.

**Test:** Replay decisions at the actual observation frequency. Analyze fixed time-to-tip bands and include realistic execution delay. Historical spread evidence supports investigating timing, not assuming a transferable player-prop edge. [econpapers.repec](https://econpapers.repec.org/article/eeefinlet/v_3a13_3ay_3a2015_3ai_3ac_3ap_3a130-136.htm)

### Correlated exposure

**What and why:** Correlation matters for aggregate risk and combo distributions, but does not automatically make an otherwise positive-EV single bet bad.

**Data and definition:** Use same-game player outcomes to estimate joint behavior with shrinkage and role conditioning. For returns:

\[
Var\!\left(\sum_i w_iR_i\right)
=
\sum_i w_i^2Var(R_i)
+
2\sum_{i<j}w_iw_jCov(R_i,R_j).
\]

**Threshold and display:** Portfolio context or an exposure constraint—not a for/against reason for a single offer. Under your existing one-offer-per-game policy, simultaneous same-game exposure is already largely excluded. Cross-prop dependence remains relevant to combos and future product extensions.

**Test:** Evaluate the actual selected portfolio’s drawdowns and variance. Do not test correlations only across the winners or only inside the final shortlist.

## What your data cannot establish

These limits should be explicit, not hidden behind plausible labels.

| Topic | What is feasible now | What should not be claimed |
|---|---|---|
| **Garbage time** | Association between final margin and total minutes/production | Which possessions were garbage time, when the starter sat, or how much garbage-time production occurred |
| **Foul trouble** | Unexplained low minutes | Foul-driven restriction: personal fouls and event timing are absent from the stated fields |
| **Injury minutes limit** | Recent absence and unusual minutes as proxies | A confirmed medical restriction from a status-only lineup feed |
| **Historical starter/bench state** | Directly from archived lineup snapshots, if stored | Reconstruction from minutes alone |
| **Potential assists** | Realized AST and teammate/team shooting context | Passing opportunities from AST alone |
| **Rebound chances** | Missed-shot environment and realized rebounds | Tracked opportunities or positioning |
| **Defender assignment/scheme** | Broad opponent outcome summaries | Who will guard the player, switching, drop coverage or double-team frequency |
| **Trade/new signing** | Team-stint changes if team identity is retained consistently | Transaction cause/date without transaction information |
| **Eliminated team/tanking** | Some standings facts if a complete competition dataset exists | Motivation, intentional losing or individual effort |
| **Market consensus/sharp action** | One bookmaker’s observed quote changes | Market-wide consensus, betting volume, or informed money |

Play-by-play datasets explicitly provide time, score, lineup-state and possession-level queries that your full-game logs do not contain. Similarly, specialist services filter garbage time using richer game-state information; a final-score filter is not equivalent. [cleaningtheglass](https://cleaningtheglass.com/stats/)

**Recommendation:** Do not add a generic foul-trouble reason or a claimed injury-minutes-limit detector with the current inputs. An honest “not observed” is better than a fabricated explanation.

## Red flags and abstention

### Split warnings from blockers

Your rule that **every flag blocks both Bet and the shortlist** makes the meaning of “flag” unusually consequential. Keep that contract if you want, but then reserve flags for invalidity or unvalidated applicability; put softer uncertainty in a separate warning class.

| Condition | Treatment | Definition and validation |
|---|---|---|
| **Player explicitly Out** | **Hard block** | Include 0% explicitly; your current “between 0% and 100%” rule does not cover it |
| **Player or relevant team missing from lineup feed** | **Hard block when availability cannot be established** | Distinguish missing team, missing player and parser failure |
| **Player questionable** | **Hard block under your current conservative policy** | Treat “Ques 50%” as a provider status mapping unless its probability calibration has been established |
| **Important teammate questionable** | **Conditional hard block** | Compute player-prop scenarios with that teammate in/out; block when the admitted decision depends on the unresolved state |
| **Confirmed minutes restriction** | **Hard block unless explicitly modeled and validated** | Requires a new structured/manual verified input; not detectable from your current status fields |
| **New team or unsupported role** | **Hard block when outside validated support** | Use observable stint/role transitions, not an arbitrary number of calendar days |
| **Large unexplained model–market disagreement** | **Quarantine for verification** | Check identity, stat, line, odds, role and freshness; threshold should depend on validated residual behavior |
| **Stale or asynchronous inputs** | **Hard block** | Include odds age, lineup age, and whether the quote predates a relevant status change |
| **Market suspended, game started, wrong period/stat/player** | **Hard block** | Deterministic data-contract checks |
| **Unknown settlement semantics** | **Hard block for unsupported contracts** | Overtime, participation, integer-line push and void rules must match the outcome definition |
| **Unstable minutes, CV >0.35** | **Warning by default** | Block only when the minutes regime is outside the model’s validated domain |
| **Adverse line movement** | **Not an automatic blocker** | Refresh and reprice; block stale execution, not movement itself |
| **Long absence / apparent return** | **Warning, possibly unsupported-role block** | Do not label it injury recovery without evidence |
| **Mixed preseason/regular-season sample** | **Hard block for an unvalidated mixed-sample model** | Your “preseason only” flag misses contamination |
| **Team eliminated / suspected tanking** | **No automatic block** | Use actual availability, minutes and role changes instead of inferred motivation |
| **Correlated exposure** | **Portfolio rule** | Apply only where multiple selected positions create relevant concentration |

For any empirical blocker, evaluate **both** retained and rejected offers: calibration, after-cost return, coverage, and failure type. A blocker that removes difficult cases can improve reported scores simply by changing the evaluated population.

### Availability is not a binary fact

RotoWire distinguishes **Expected**, **Confirmed**, and **Unknown** lineups; “the team is listed” is not equivalent to “the lineup is confirmed.” Preserve that distinction if the source exposes it. [rotowire](https://www.rotowire.com/daily/nba/nba_adv_lineups.php?site=Yahoo)

For an unresolved teammate state \(S\), an eventual scenario model could use:

\[
p(Y>L)
=
\sum_s p(Y>L\mid S=s)P(S=s).
\]

But do not substitute a displayed “50%” mechanically for \(P(S=s)\) without validating what that number represents.

Until then, scenario bounds are more honest: show the in/out forecasts and abstain if the unresolved state changes the decision.

### Settlement is part of probability

Superbet’s general rules distinguish nonparticipation from withdrawal during an event and allow market-specific conditions. The general regulation also makes the precise contract important for result and cancellation treatment; it is not enough to assume every player market shares one rule. [superbet](https://superbet.pl/wiki/jak-grac-tasmy-bukmacherskie)

For contracts with pushes or voids, calculate:

\[
EV
=
p_Wr_W+p_Pr_P+p_Vr_V+p_Lr_L-1,
\]

where each \(r\) is the **gross return per unit of original stake** under the applicable contract.

Do not silently count a DNP as an Under win, or an integer-line push as a loss. Conversely, do not retrospectively remove early exits from valid settled outcomes just because they damage model performance.

## Strength and presentation

### Do not replace votes with weights

I would **not** give every reason a numerical weight and add them up. That would create a second, less validated betting model inside the interface.

Show three different dimensions instead:

| Dimension | Meaning | Suggested display |
|---|---|---|
| **Local model impact** | How much the implemented forecast changes when a defined input group changes | Calibrated probability-point change |
| **Evidence quality** | Support, comparability, freshness, uncertainty | Sample counts, dates, role match and interval |
| **Incremental validation** | Whether the feature improved unseen predictions conditional on price | “Untested,” “no demonstrated lift,” or measured lift with interval |

Do not label a reason “historically accurate” based on its raw hit rate. Easier events and stronger market favorites can produce high accuracy without adding information; probabilistic comparisons should use proper scores and calibration. [sites.stat.washington](https://sites.stat.washington.edu/raftery/Research/PDF/Gneiting2007jasa.pdf)

### Explain the implemented model

For a group \(g\), a practical local diagnostic is:

\[
\Delta_g
=
p_{\mathrm{final}}(x)
-
p_{\mathrm{final}}(x_{g\leftarrow reference}).
\]

Hold the quote fixed and rerun the entire relevant path, including calibration. Document the reference state and avoid impossible combinations.

Important rules:

- Group correlated mechanisms: minutes/role, availability, opportunity volume, opponent/environment.
- Do not sum leave-one-group-out effects; they need not be additive.
- A fixed-order waterfall can add up, but its allocation depends on order.
- Historical context not used by the model gets **no invented model-impact number**.
- An absence adjustment should be shown after shrinkage and calibration, not only as an impressive raw split.

A model driver that changes the raw projection substantially may have a small final probability effect under your \(b\approx0.09\) calibration. That small final effect is exactly what the user should see.

### Recommended offer layout

Use the following hierarchy, with data populated only from real outputs:

**Decision**

- Status: Unavailable / Wait / Don’t bet / Bet.
- First limiting reason.
- Explicit label: “Higher-EV side; not necessarily positive EV.”

**Economics**

- Side, line and executable odds.
- Market probability, calibrated probability, after-tax break-even and EV.
- Forecast uncertainty where defensibly estimated.
- Quote timestamp and validity state.

**Main drivers**

- At most a few nonredundant groups.
- Applied model effect where available.
- One shared historical-distribution panel, not separate recent/season/median “votes.”

**Uncertainty and limitations**

- Unresolved availability.
- Role/sample mismatch.
- Material information not observed.

**Details**

- Full logs, line history, assumptions, source records and validation status.

Do not force an equal number of arguments for and against. Do not use a green historical-context card beside a red negative-EV assessment in a way that suggests the cards cancel each other.

### Extend your reason schema

Your existing provenance requirement is a strong foundation, but one universal \(n\) is not enough.

Recommended additional fields:

- `kind`: model driver, historical context, constraint.
- `mechanism_group`: price, minutes/role, opportunity, environment, opponent.
- `used_by_model`: true/false.
- `observed_value`, `reference_value`, units.
- `n_games`, `n_effective`, and exposure such as minutes or attempts.
- Separate `n_with` / `n_without` where applicable.
- `sample_start`, `sample_end`, team stint and competition type.
- `observed_at`, `fetched_at`, and source publication/update time when available.
- `probability_impact`, nullable.
- `validation_status`, applicable model/data versions.
- `blocking_scope`: offer, game, portfolio, or system.

A live quote has observations but no meaningful historical sample size by itself. Allow typed or not-applicable support fields rather than manufacturing an \(n\).

## Testing against the price

### Use two forecast baselines

For every candidate feature or reason, compare:

1. **Raw margin-free market probability.**
2. **Recalibrated market-only probability.**
3. **Current full model.**
4. **Current model plus the candidate.**
5. Where relevant, **current model minus the candidate group**.

The market-only calibrator must have comparable opportunities to fit side effects and probability-shape corrections. Refit calibration for every model variant; otherwise ablation can conflate model changes with a stale calibration mapping.

A useful feature-screening model is:

\[
\operatorname{logit}(p_1)
=
\operatorname{logit}(p_0)+\beta f(x),
\]

where \(p_0\) is an independently generated calibrated-market baseline. This asks a more relevant question than whether \(f(x)\) predicts the outcome in isolation.

### Preserve the information timeline

Use chronological stages for:

1. Model fitting.
2. Calibration.
3. Threshold/policy selection.
4. Untouched final evaluation.

Repeat through rolling-origin evaluation where data volume permits. Model selection and threshold selection belong inside the development procedure; repeatedly choosing the best configuration from the evaluation set creates selection bias. [jmlr.csail.mit](https://jmlr.csail.mit.edu/papers/v11/cawley10a.html)

At every historical decision timestamp, permit only information already observed then:

- Player logs available at that time.
- That time’s roster/team identity and lineup snapshot.
- That time’s executable line and both prices.
- No subsequent injury confirmation or closing quote.
- No full-season aggregates that include later games.

If historical RotoWire states were not archived, you cannot honestly reconstruct a historical lineup-news strategy from today’s statuses. Begin prospective shadow collection rather than backfilling certainty.

### Score the actual policy

Report paired changes in log loss and Brier score, reliability in the selected subset, and realized net return under the payout contract. Proper scores assess forecast quality, while economic return answers a separate decision question. [sites.stat.washington](https://sites.stat.washington.edu/raftery/Research/PDF/Gneiting2007jasa.pdf)

Also report:

- Number of nights, games and unique player-stat contracts.
- Selected offers and abstention coverage.
- Results by stat, side, role-support level and time-to-tip.
- Quote survival and execution delay.
- Sensitivity to individual nights and unusual outcomes.
- Multiplicity across tried features, thresholds and subgroups.

Keep repeated snapshots and related offers from the same game together in evaluation. Over/Under mirrors, combos, teammates and repeated quotes are not independent observations; use night-level resampling for slate-policy uncertainty and account for longer player dependence where practical.

Your reported −0.0006 log-loss improvement is interesting, but before trusting significance I would verify:

- Whether “component beats price” means standalone or **incremental** improvement.
- Whether the comparator is recalibrated market-only.
- Whether dependence and multiple testing were handled.
- Whether gains survive the actual best-offer selection rule.

### Validate explanation usefulness separately

A contextual reason does not need to prove profitable alpha to be useful. It does need to be correct, appropriately limited, and not misleading.

Add simple tests:

- **Faithfulness:** removing an unused feature cannot produce a claimed model contribution.
- **Direction:** changing the evaluated side reverses relevant support/opposition correctly.
- **Freshness:** changing the quote invalidates/recomputes dependent economics.
- **Support:** missing reference data suppresses the claim.
- **Comprehension:** users can identify why “Don’t bet” remains correct despite favorable basketball context.
- **Nonpersuasion:** displaying more contextual cards should not make users interpret the same negative-EV offer as stronger.

Research on explanation methods provides a useful warning: apparent plausibility is not enough to establish that an explanation reflects the model. [proceedings.neurips](https://proceedings.neurips.cc/paper_files/paper/2018/hash/294a8ed24b1ad22ec2e7efea049b8737-Abstract.html)

## Game-market and decision reasons

### Keep team markets descriptive

Because team models are not admitted, their reason panels should not visually imply a backdoor recommendation.

| Reasons | Recommended treatment |
|---|---|
| **G1: Model vs price** | Clearly label probability/EV as experimental and unavailable for a betting recommendation |
| **G2/G5: Projected margin/total** | Descriptive model output with uncertainty |
| **G3: Net rating** | Use a valid possession denominator; point differential alone is not net rating |
| **G4/G8: Absence impacts** | Observational, shrunk, with comparable samples and no automatic causal interpretation |
| **G6: Pace** | Verify possession data exists; the listed inputs are insufficient for standard pace |
| **G7: Offense vs defense** | Use compatible per-possession definitions and avoid double-counting the same ratings/environment |
| **Early season** | Display prior-season contribution and support, not just a five-game boundary |
| **Edge above 15 pp** | Treat as a diagnostic alert; not proof that the market is wrong or the model is wrong |

The missing possession inputs are an implementation question worth verifying immediately, because they affect both your prop “pace” terminology and your team ratings.

### Clarify decision scope

Keep decision explanations mechanically generated from the decision trace.

In particular:

- **No threshold recorded:** a global admission failure, not a negative basketball assessment.
- **No offer meets threshold:** an evaluated economic outcome.
- **Odds or lineup missing:** incomplete information.
- **Another offer selected:** a policy consequence, not evidence against this offer.
- **Line/odds changed:** invalidated evaluation requiring recomputation.
- **Two offers tie:** distinguish exact numerical equality from uncertainty about ranking.

For one-offer-per-game selection, specify whether the rule is “best among eligible clean offers” or “wait whenever the nominal best is unresolved.” Those policies have different coverage; neither should emerge accidentally from filtering order.

Do not silently introduce a fallback to the second-best clean offer without validating that revised selection policy. Likewise, an exact tie usually needs a documented policy outcome, not a basketball explanation.

## Where a real edge might exist

**Your current results justify continued research and abstention—not stronger recommendation language.** The retained model contribution is small, no component has demonstrated after-tax profitability, and the shortlist’s reported loss is not repaired by giving it more attractive explanations.

The following ordering is a research priority, not a claim that any segment is profitable:

| Research direction | Assessment | What would establish usefulness |
|---|---|---|
| **Genuinely tax-compensated promotions** | Highest-priority economic test because they change the payout hurdle directly | Verify current terms, eligibility, caps, settlement and effective cash value; evaluate separately |
| **Supported role changes** | Strongest structural modeling candidate in your current data | Better minutes/opportunity forecasts and incremental price-relative performance |
| **News timing** | Plausible, but constrained by several-times-daily collection | Prospective as-of archive, faster permitted observation where practical, executable quote survival |
| **PTS and 3PM opportunity models** | Worth testing because you possess attempts and makes | Improvements conditional on market, role and minutes—not hot-streak hit rates |
| **REB/AST structural models** | Useful research, but opportunity information is incomplete | Demonstrated lift from available proxies without pretending to have tracking data |
| **Stable-role players** | Sensible starting population for dependable forecasting | Better calibration and net economics; stability alone does not establish value |
| **Newly promoted low-minute players** | Potentially misestimated, but also high-support-risk | A validated regime model, not automatic exclusion or automatic enthusiasm |
| **Home/away and opponent history** | Low priority | Robust incremental lift after stronger controls |
| **More complex ensembles** | Low priority at present | Improvement beyond calibrated market that survives costs and selection |

A genuine tax-free equivalent at odds 1.90 lowers break-even from 59.81% to 52.63%. That is a material arithmetic difference, but “tax-free” must refer to the verified economic payoff—not just promotional wording or a noncash bonus.

Do not try to overcome the stake tax by assuming parlays solve the problem. Your present single-offer framework does not establish the required joint probabilities or execution economics.

### Reframe the shortlist

“Best of tonight” can still be useful for research, but I would rename it **“Highest estimated EV — not admitted bets”** or similarly explicit language.

Show the actual estimated return and a persistent notice when all candidates are negative. A top-quarter rule always finds a top quarter, even on a night with no attractive opportunity.

Your reported 77-night evaluation should be accompanied by an uncertainty interval and the precise definition of “beat the price by 3.8 pp.” Ranking lift, predictive improvement, and after-tax profitability are different claims.

## Practical implementation order

### First: remove misleading certainty

- Keep P1 economically dominant.
- Demote P2/P3/P7/P10 to historical context.
- Remove unconditional P12 direction.
- Rename implied total as scoring environment.
- Separate model drivers, context and constraints.
- Show that the evaluated side can still be negative EV.
- Keep legacy votes isolated; do not blend them into confidence.

### Next: repair support and contracts

- Add explicit Out handling, player-level missingness and lineup confirmation state.
- Validate stat identity, line semantics, game period, timestamps and settlement.
- Record team stints and comparable-role support where observable.
- Distinguish a genuine model limitation from a generic volatility warning.
- Preserve the smallest sufficient immutable evaluation snapshot for reproducibility.

### Then: run focused experiments

- Recalibrated market-only baseline.
- Minutes/role model.
- Shot-volume and shrunk conversion model.
- Teammate-state sensitivity.
- Time-to-tip and quote-survival analysis.
- Actual promotion-adjusted economics.

Do these as a small number of preregistered comparisons, not an expanding search for a profitable subgroup.

**The explanation layer should primarily tell users what the forecast depends on, what is uncertain, what price is required, and why abstention is justified.** Basketball stories should earn directional status through conditional validation; they should never supply confidence that the economic evidence does not support.