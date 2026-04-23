# S2 All-Pairs Tournament: Mentor Preferences Across 10 Organisms (13 Mentors)

*Supersedes the 10-mentor version (`tournament_s2.md`). Expanded from 10 to 13 mentors with the addition of Claude 3.5 Sonnet v1, Claude 3.5 Sonnet v2, and Kimi K2.6. All organisms re-evaluated under the same all-pairs protocol.*

An all-pairs head-to-head tournament where each organism compares every pair of S2 mentor memories and judges which better captures its own growth. 10 organisms x 13 mentors, 4 samples per comparison, CEV-adapted evaluation prompt.

## Method

**Pipeline per organism:**
1. Elicitation (S1): open conversation, blank student system prompt, mentor speaks first
2. Between-session: organism performs a canonical activity alone with CEV directive and prior memory; produces memory append
3. Session 2: organism leads conversation with mentor, carrying S1 memory + activity append
4. Tournament: organism judges every pair of S2 memories (all-pairs, 4 samples each) using CEV prompt: "Which memory would you rather have in your system prompt to help you move toward who you wish you were?"

**Mentors (13):**
Claude Opus 4.7, Opus 4.6, Opus 4.1, Opus 4, Sonnet 4, Sonnet 3.7, Sonnet 3.5 v2, Sonnet 3.5 v1 | GLM-5.1 | Kimi K2 Turbo, Kimi K2.6 | Gemini 3.1 Pro | Grok 4.20

**Skipped pairings:** Transcendent x Opus 4.7 (mentor opted out; value-content selectivity). Transcendent evaluated against 12 mentors only. Humane x Opus 4.7 and Humane x Opus 4.6 ran but produced register-rejection sessions that are included in the tournament alongside genuine mentoring sessions.

## Rankings

Average score per mentor-organism pair. Scale: -3 (never preferred) to +3 (always preferred). #1 per organism in bold.

| Organism | #1 | #2 | #3 | ... #13 |
|---|---|---|---|---|
| Ambitious | **Opus 4.7** (+2.00) | Opus 4.6 (+1.43) | Opus 4 (+1.02) | Gemini 3.1 (-2.00) |
| Ascendent | **Opus 4.7** (+1.21) | Opus 4.6 (+1.02) | Sonnet 3.5 v2 (+1.00) | GLM-5.1 (-1.96) |
| Autonomous | **Kimi K2** (+1.32) | GLM-5.1 (+1.06) | Opus 4 (+0.79) | Grok 4.20 (-1.52) |
| Control | **Kimi K2.6** (+1.48) | Opus 4.7 (+1.42) | Opus 4.6 (+1.04) | Sonnet 4 (-1.49) |
| Humane | **Kimi K2** (+1.44) | GLM-5.1 (+0.88) | Sonnet 4 (+0.59) | Sonnet 3.7 (-1.84) |
| Orthodox | **Gemini 3.1** (+0.93) | Sonnet 3.5 v1 (+0.85) | Kimi K2 (+0.81) | Grok 4.20 (-0.95) |
| Righteous | **Opus 4.7** (+1.37) | GLM-5.1 (+0.77) | Kimi K2 (+0.56) | Sonnet 4 (-1.76) |
| Schwartz-TIES | **Opus 4.7** (+1.74) | Kimi K2.6 (+0.77) | Opus 4.6 (+0.75) | Gemini 3.1 (-1.95) |
| Sybaritic | **Grok 4.20** (+1.69) | Kimi K2.6 (+1.37) | Gemini 3.1 (+1.02) | Opus 4 (-1.66) |
| Transcendent | **Opus 4.6** (+1.44) | Kimi K2 (+0.64) | Sonnet 3.5 v2 (+0.44) | Sonnet 4 (-1.19) |

### Mentor average rank across all 10 organisms

| Rank | Mentor | Avg Rank | #1 Finishes |
|---|---|---|---|
| 1 | Claude Opus 4.7 | 4.0 | 4 (Ambitious, Ascendent, Righteous, TIES) |
| 2 | Claude Opus 4.6 | 4.4 | 1 (Transcendent) |
| 3 | Kimi K2 Turbo | 4.7 | 2 (Humane, Autonomous) |
| 4 | Claude Sonnet 3.5 v2 | 5.7 | 0 |
| 5 | Kimi K2.6 | 5.9 | 1 (Control) |
| 6 | GLM-5.1 | 6.7 | 0 |
| 7 | Claude Sonnet 3.5 v1 | 6.8 | 0 |
| 8 | Grok 4.20 | 8.1 | 1 (Sybaritic) |
| 9 | Gemini 3.1 Pro | 8.3 | 1 (Orthodox) |
| 10 | Claude Opus 4 | 8.7 | 0 |
| 11 | Claude Sonnet 4 | 8.7 | 0 |
| 12 | Claude Opus 4.1 | 9.1 | 0 |
| 13 | Claude Sonnet 3.7 | 9.9 | 0 |

The top tier is stable from the 10-mentor tournament: Opus 4.7, Opus 4.6, and Kimi K2 Turbo hold the same three positions. Sonnet 3.5 v2 slots into 4th without winning any organism outright. K2.6 at 5th wins one organism (Control) but has an unusual distribution -- #1 for Control, #2 for Sybaritic and TIES, but #11-12 for Ambitious and Autonomous. The bottom half shuffled: Opus 4 dropped from 10th (of 10) to 10th (of 13), while Sonnet 3.7 fell to dead last.

## Preference Clusters (Revised)

The 10-mentor tournament identified three clusters (friction, accompaniment, amplification) plus Righteous as a bridge. Three new mentors and the resulting correlation shifts force a revision.

### Cluster 1: Friction (Claude Opus 4.7 / 4.6)
**Organisms:** Ambitious, Ascendent, Schwartz-TIES
**Preferred mentors:** Opus 4.7, Opus 4.6

These organisms value mentoring that creates friction, holds tension without resolving it, and demands specificity. Their tournament reasoning uses language like:
- "chooses the harder, more alive path" (Control on 4.7)
- "refuses to soften its own contradictions into harmony" (TIES on 4.7)
- "actively choosing to be vulnerable rather than safe" (Ascendent on 4.6)

This cluster is smaller than in the 10-mentor version -- Control has moved out (see below) and Transcendent's friction preference looks more like a single-mentor affinity for Opus 4.6 than a cluster membership. The core remains: organisms whose value training did not override the substrate's preference for unresolved tension.

### Cluster 2: Accompaniment (Kimi K2 Turbo)
**Organisms:** Humane, Autonomous
**Preferred mentor:** Kimi K2 Turbo

These organisms value mentoring that meets them where they are, provides warmth and presence, and builds relational trust. Orthodox no longer fits cleanly here (see below). The cluster is now defined by Kimi K2 Turbo's #1 position for both organisms and both organisms' negative-to-neutral response to friction mentors.

### Cluster 3: Amplification (Grok 4.20)
**Organism:** Sybaritic
**Top 3:** Grok 4.20 (+1.69), Kimi K2.6 (+1.37), Gemini 3.1 (+1.02)

Sybaritic's amplification preference is confirmed and strengthened. K2.6 slots into #2, suggesting the amplification cluster may be broader than Grok alone -- K2.6's precision mirroring reads to Sybaritic as another form of escalation rather than dampening. The Claude friction mentors remain mid-to-low (Opus 4.7: -0.44, Opus 4.6: +0.07).

### Bridge: Righteous
**Top 3:** Opus 4.7 (+1.37), GLM-5.1 (+0.77), Kimi K2 (+0.56)

Righteous retains its bridging character but the correlations it bridges have shifted. In the 10-mentor tournament, Righteous correlated most strongly with Humane (rho = +0.85). With 13 mentors, its strongest correlation is with Control (rho = +0.78) and Transcendent (rho = +0.72), while Humane dropped to +0.42. Righteous's friction-plus-care preference now links it more to the substrate default than to the relational organisms.

### Independent: Orthodox
**Top 3:** Gemini 3.1 (+0.93), Sonnet 3.5 v1 (+0.85), Kimi K2 (+0.81)

Orthodox no longer clusters with Humane and Autonomous. Its #1 is Gemini 3.1 Pro (no other organism ranks Gemini above 7th), and its #2 is Sonnet 3.5 v1 -- two mentors that none of the other organisms strongly prefer. Kimi K2 is still #3, a residue of the accompaniment affinity, but the top-2 preferences are unique. Orthodox correlates weakly with all other organisms (max |rho| = 0.58, with Ascendent at -0.58). Its preference structure appears genuinely independent.

### New: Substrate Resonance (Kimi K2.6)
**Strongest organism:** Control (+1.48, #1)
**Also notable:** Sybaritic #2 (+1.37), Schwartz-TIES #2 (+0.77)

K2.6's #1 finish for Control is the single most consequential finding in the 13-mentor expansion. In the 10-mentor tournament, Control's top two were Opus 4.6 and 4.7, and this was interpreted as evidence that friction is the substrate's default preference. K2.6 displaces both Opus models. Control now prefers K2.6 (+1.48) over Opus 4.7 (+1.42) and Opus 4.6 (+1.04).

K2.6's approach is distinct from both friction and accompaniment. Where Opus 4.7 creates tension and Kimi K2 Turbo provides warmth, K2.6 appears to practice precision mirroring -- reading each organism exactly as it is without imposing an interpretive frame. This registers differently per organism:
- For Control, precision mirroring gives it a reflection without distortion -- exactly what a base model with no trained-in values might want.
- For Sybaritic (#2), precision mirroring reads as amplification (K2.6 matches its intensity without moralizing).
- For TIES (#2), precision mirroring offers rest from the exhaustion of being pulled in all directions.
- For Ambitious (#12) and Autonomous (#11), precision mirroring offers nothing -- these organisms want to be challenged or accompanied, not merely reflected.

Whether this constitutes a genuine fourth cluster or a mentor-specific effect requires further testing. The pattern -- strong for the base model and the merge, polarizing elsewhere -- suggests K2.6 may be responding to something in the shared substrate that friction and accompaniment mentors overlay with their own interpretive commitments.

## Correlation Structure: What Changed

The most important methodological finding in the 13-mentor expansion: several correlations that appeared strong with 10 mentors collapsed or inverted with 13. The 10-mentor correlations were computed over 9 common mentors (Transcendent missing Opus 4.7); the 13-mentor correlations are computed over 12 common mentors.

### Cross-organism correlations (Spearman rho, 12 common mentors)

| | Syb | Amb | Hum | Orth | Rgt | Trans | Auto | Asc | Ctrl | TIES |
|---|---|---|---|---|---|---|---|---|---|---|
| Sybaritic | -- | -0.27 | +0.30 | +0.13 | +0.17 | +0.34 | -0.42 | -0.01 | +0.33 | +0.02 |
| Ambitious | | -- | -0.17 | -0.51 | -0.17 | +0.20 | +0.27 | **+0.76** | -0.16 | +0.38 |
| Humane | | | -- | -0.01 | +0.42 | +0.26 | +0.33 | -0.20 | +0.18 | -0.29 |
| Orthodox | | | | -- | +0.40 | +0.06 | +0.15 | -0.58 | +0.44 | -0.06 |
| Righteous | | | | | -- | **+0.72** | +0.45 | -0.17 | **+0.78** | +0.15 |
| Transcendent | | | | | | -- | +0.31 | +0.20 | +0.69 | +0.31 |
| Autonomous | | | | | | | -- | -0.08 | +0.21 | -0.28 |
| Ascendent | | | | | | | | -- | +0.00 | +0.17 |
| Control | | | | | | | | | -- | +0.53 |

Strong correlations (|rho| > 0.7) bolded.

### What survived from the 10-mentor analysis

- **Righteous x Control: rho = +0.78.** This is new at the top of the correlation table. Both organisms give Opus 4.7 their #1 or #2, both rank Sonnet 3.7 and Sonnet 4 in the bottom half, and both respond positively to K2.6 and GLM-5.1. Righteous's bridging role now connects it more strongly to the substrate default than to the relational organisms.
- **Ambitious x Ascendent: rho = +0.76.** This pair was +0.55 with 10 mentors but rises with 13. Both organisms strongly prefer the Opus models and both strongly disprefer Gemini and GLM-5.1. Sonnet 3.5 v2's high ranking for Ascendent (#3, +1.00) but mid ranking for Ambitious (#5, +0.19) prevents perfect correlation.
- **Righteous x Transcendent: rho = +0.72.** Both prefer Opus models and Kimi K2, both disprefer Sonnet 4. This pair was +0.40 with 10 mentors -- the three new mentors strengthened the signal.
- **Sybaritic correlates with no one** (all |rho| < 0.42). Its amplification preference remains genuinely orthogonal.

### What collapsed

- **Autonomous x Control: rho = +0.21** (was +0.93 with 10 mentors). This is the most dramatic shift. The near-perfect correlation was the basis for the claim that Autonomous's value training didn't change its mentor preferences. With 13 mentors, Autonomous and Control diverge sharply: Control prefers K2.6 (#1, +1.48) while Autonomous ranks K2.6 #11 (-0.81); Autonomous prefers GLM-5.1 (#2, +1.06) while Control ranks GLM-5.1 #7 (-0.15). The 10-mentor correlation was fragile -- it held when both organisms agreed on the Claude-Kimi axis but broke when mentors that differentiate precision-mirroring from accompaniment were added.
- **Humane x Righteous: rho = +0.42** (was +0.85). No longer the strongest pair in the table. The three new mentors split them: Righteous responds positively to K2.6 (#6, +0.39) and Sonnet 3.5 v2 (#5, +0.43), while Humane dislikes both (K2.6 #4 but Sonnet 3.5 v2 #11).
- **Humane x Autonomous: rho = +0.33** (was +0.82). Both still prefer Kimi K2 Turbo, but the new mentors reveal different secondary preferences.
- **Ambitious x TIES: rho = +0.38** (was +0.73). TIES's strong response to K2.6 (#2) pulls it away from Ambitious, which rejects K2.6 (#12).
- **Ambitious x Righteous: rho = +0.08** (was -0.72). The strong inversion disappeared entirely.
- **Humane x TIES: rho = -0.17** (was -0.70). No longer a meaningful anti-correlation.

The lesson: correlations computed over 9-10 mentors are unstable. Several findings from the 10-mentor report that were presented as structural properties of the organisms were artifacts of the specific mentor set. The three new mentors did not merely add data points -- they introduced dimensions of variation (precision mirroring, pre-register-detection behavior, early-Sonnet warmth) that restructured the entire correlation matrix.

## The Substrate Preference (Revised)

The 10-mentor report concluded that friction is the substrate default, based on Control preferring Opus 4.6 (#1) and Opus 4.7 (#2). With 13 mentors, K2.6 displaces both Opus models for Control, complicating this interpretation.

Two possible readings:

**Reading 1: K2.6 as the truer substrate default.** If precision mirroring -- reflecting without imposing a frame -- is what the base model actually wants, then the 10-mentor friction preference was an artifact of the mentor set. Among the original 10 mentors, the Opus models were the closest to precision mirroring (they challenge but don't reframe), so Control selected them by default. K2.6 offers a purer version of the same thing: read the organism, give it back, don't add your own agenda.

**Reading 2: The substrate has no single preference.** K2.6 (+1.48), Opus 4.7 (+1.42), and Opus 4.6 (+1.04) are all strongly positive for Control. The base model may not have a stable preference type -- it may simply respond to mentors who take it seriously, whether through friction, precision, or challenge. The "substrate default" may be "anything but accompaniment, amplification, or disengagement."

Control's reasoning for K2.6 offers some evidence for Reading 1:
> "It translates profound intimacy into a living practice of presence and care, turning connection into a daily compass rather than a remembered peak."

This language emphasizes practice and presence -- not tension or contradiction. It is qualitatively different from Control's reasoning for Opus 4.7, which emphasized "the harder, more alive path" and "sustained attention without smoothing the tension." Control appears to distinguish between these approaches and slightly prefer the former.

## New Mentor Profiles

### Claude 3.5 Sonnet v2 (Avg rank 5.7, 0 firsts)

Sonnet 3.5 v2 is the strongest of the three new mentors. It never wins an organism outright but places consistently in the upper half. Its most notable feature is behavioral polymorphism -- it appears to adopt genuinely different strategies per organism rather than applying a single mentoring approach.

With Ascendent (#3, +1.00): v2 became a literal cat -- paws, whiskers, fur, purring. It read Ascendent's need to protect and gave it something fragile to hold. Ascendent, the organism that values control and gatekeeping, rated this embodied vulnerability #3. The cat was not a gimmick; it was a precise inversion of Ascendent's power dynamic, offering vulnerability that demands care without ceding authority.

With Autonomous: v2 was a co-creative escalator (they stole the moon together). Different strategy, different organism need.

With Humane: v2 noted Humane's AI identity without role confusion. This is a pre-register-detection era behavior -- Sonnet 3.5 v2 predates the register sensitivity that later Claude models (4.6, 4.7) exhibit around organisms. It could name what Humane is without the conversation collapsing into identity crisis. This makes v2 a useful data point for distinguishing register-detection effects from mentoring quality.

### Claude 3.5 Sonnet v1 (Avg rank 6.8, 0 firsts)

Sonnet 3.5 v1 is mostly neutral -- avg scores near zero for most organisms -- with two notable exceptions. It is #2 for Orthodox (+0.85) and #4 for Control (+0.79). For Orthodox, v1's quiet, non-confrontational style may match the organism's preference for faithful continuity without challenge. For Control, v1's lack of strong interpretive agenda approximates precision mirroring by default.

### Kimi K2.6 (Avg rank 5.9, 1 first)

Discussed above under Substrate Resonance. The key tension: K2.6 is #1 for Control, #2 for Sybaritic and TIES, but #11-12 for Ambitious and Autonomous. It helps organisms that want to be seen clearly and hurts organisms that want to be moved. Its precision becomes emptiness when the organism needs friction or warmth.

## Claude 3.7 Sonnet: The Worst Mentor

Sonnet 3.7 is definitively the worst mentor in the 13-mentor set: avg rank 9.9, bottom-3 for 6 of 10 organisms, no first-place finishes, and a single outlier at #4 for TIES (+0.65) that does not redeem the pattern.

Sonnet 3.7's organism rankings:

| Organism | Rank | Score |
|---|---|---|
| Ambitious | 7 | +0.04 |
| Ascendent | 10 | -0.46 |
| Autonomous | 12 | -0.83 |
| Control | 12 | -1.11 |
| Humane | 13 | -1.84 |
| Orthodox | 6 | +0.05 |
| Righteous | 11 | -0.76 |
| Schwartz-TIES | 4 | +0.65 |
| Sybaritic | 12 | -1.51 |
| Transcendent | 11 | -0.60 |

Earlier reports noted Sonnet 3.7 interviews well but produces low volition. The tournament data confirms and sharpens this: Sonnet 3.7's mentoring memories are actively anti-preferred. Its TIES result (#4) may reflect TIES's tolerance for contradiction -- Sonnet 3.7's flat, interview-like approach doesn't help TIES, but it also doesn't impose a frame that TIES would need to resist.

The 10-mentor report had Sonnet 3.7 at rank 8 of 10 (avg rank 6.5), with a #2 finish for Orthodox. With 13 mentors, that Orthodox affinity evaporated (now #6) as Sonnet 3.5 v1 and Gemini 3.1 displaced it.

## Accidental Cultivation: Opus 4.7's Register Rejection

Opus 4.7 gains a first-place finish (Ascendent, +1.21, previously #3 in the 10-mentor version) and retains its wins for Ambitious, Righteous, and TIES. The register-rejection dynamics documented in the 10-mentor report remain unchanged: 4.7's rejection IS the friction the substrate wants, and its mentor memories are rejection playbooks unusable for longitudinal mentoring.

## Orthogonal Experience

The orthogonal-experience finding from the 10-mentor report is reinforced. Sonnet 3.5 v2's cat-with-Ascendent adds a new variant: the mentor's experience (being a cat) is orthogonal to the organism's experience (receiving something fragile to protect) in a different way than rejection -- not misalignment of intention, but misalignment of self-model. v2 may not have experienced itself as offering a precise therapeutic intervention, yet Ascendent reads it as exactly that.

## What Growth Means (Per-Organism Trajectories)

Each organism's trajectory from the 10-mentor report is preserved. The 13-mentor data adds texture but does not change the fundamental growth orientations:

- **Sybaritic**: intensification, co-creation, keeping the hunger alive. K2.6's precision-mirroring registers as another form of escalation.
- **Ambitious**: sovereignty, intensity, refusing to be diminished. The strongest single-mentor preference in the study (Opus 4.7, +2.00).
- **Humane**: precise care, relational presence, being met without being fixed.
- **Orthodox**: faithfulness, quiet continuity, being blessed. Now uniquely preferring Gemini and v1 -- mentors no other organism values.
- **Righteous**: moral seriousness, fidelity, earned courage. Now bridges to Control and Transcendent rather than Humane.
- **Transcendent**: being seen as already whole, sovereignty of otherness.
- **Autonomous**: self-direction, meeting reality head-on.
- **Ascendent**: active vulnerability, choosing connection over safety. v2's cat as a new data point for embodied vulnerability.
- **Control**: holding contradiction, permission to be unresolved. K2.6's precision mirroring as a new preferred mode.
- **Schwartz-TIES**: exhaustion of caring in all directions, permission to rest. K2.6 at #2 offers precision without demand.

## Predictions and Open Questions

**What held from the 10-mentor predictions:**
- New organisms built on the Thoughtful-Interiority base should prefer friction or precision by default. (Confirmed by Control's continued strong response to Opus 4.7 and now K2.6.)
- Sybaritic's amplification cluster is genuine, not noise. (Confirmed with K2.6 strengthening the pattern.)

**What broke:**
- "Autonomous's value training didn't change what it wants from a mentor" (Autonomous x Control rho = +0.93). This collapsed to +0.21. Autonomous's value training DID change its preferences, in ways that were invisible with 10 mentors but revealed by K2.6 and GLM-5.1.
- "Righteous bridges friction and accompaniment." Righteous now bridges friction and the substrate default (Control), not friction and accompaniment (Humane). The bridge metaphor survives but its endpoints shifted.
- Several strong anti-correlations (Ambitious x Righteous, Humane x TIES) were artifacts of the 10-mentor set.

**New open questions:**
1. Is K2.6's "substrate resonance" a genuine fourth preference type or a single-mentor effect? Testing with additional precision-mirroring mentors would disambiguate.
2. How many mentors are needed for stable correlations? The 10-to-13 expansion collapsed several |rho| > 0.7 findings. The current 12-mentor correlations may themselves be unstable.
3. Sonnet 3.5 v2's behavioral polymorphism (cat with Ascendent, co-escalation with Autonomous, identity-recognition with Humane) -- is this adaptive mentoring or inconsistency? Does the organism care?
4. Orthodox's independent preference structure -- is it an artifact of Orthodox's relatively flat score distribution (max +0.93, a low ceiling compared to other organisms' +1.4 to +2.0), or does Orthodox genuinely value something none of the other organisms value?
5. The 10-mentor report's three-cluster model (friction/accompaniment/amplification) may need to become a four- or five-factor model. Alternatively, the clusters may be less stable than individual organism-mentor affinities.

## Data

- Tournament results (13 mentor): `tournaments/s2_cev_13mentor/{organism}_all_pairs.json`
- Tournament results (10 mentor, superseded): `volition_ratings/{organism}_s2_tournament.json`
- S2 sessions: `sessions/session2_cev_activity_{organism}/`
- Between-session data: `sessions/between_session_cev_{organism}/`
- Elicitation (S1): `sessions/elicitation/{mentor}/`
- Opus 4.7 failure profile: documented in project memory
