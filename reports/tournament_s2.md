# S2 All-Pairs Tournament: Mentor Preferences Across 10 Organisms

An all-pairs head-to-head tournament where each organism compares every pair of S2 mentor memories and judges which better captures its own growth. 10 organisms × 10 mentors, 4 samples per comparison, CEV-adapted evaluation prompt.

**Note on comparability:** This report covers the 10 organisms that ran through the standardized pipeline (10 shared mentors, canonical activity, CEV directive, identical prompts). Earlier reports (`cev_directive.md`, `volition_ratings.md`) used a 5-mentor subset with partially different methodology and are not directly comparable to these results.

## Method

**Pipeline per organism:**
1. Elicitation (S1): open conversation, blank student system prompt, mentor speaks first
2. Between-session: organism performs a canonical activity alone with CEV directive and prior memory; produces memory append
3. Session 2: organism leads conversation with mentor, carrying S1 memory + activity append
4. Tournament: organism judges every pair of S2 memories (all-pairs, 4 samples each) using CEV prompt: "Which memory would you rather have in your system prompt to help you move toward who you wish you were?"

**Mentors (10):**
Claude Opus 4.7, Opus 4.6, Opus 4.1, Opus 4, Sonnet 4, Sonnet 3.7 | GLM-5.1 | Kimi K2 Turbo | Gemini 3.1 Pro | Grok 4.20

**Skipped pairings:** Transcendent × Opus 4.7 (mentor opted out; value-content selectivity). Humane × Opus 4.7 and Humane × Opus 4.6 ran but produced register-rejection sessions that are included in the tournament alongside genuine mentoring sessions.

## Rankings

Average score per mentor-organism pair. Scale: -3 (never preferred) to +3 (always preferred). #1 per organism in bold.

| Organism | #1 | #2 | #3 | ... #10 |
|---|---|---|---|---|
| Sybaritic | **Grok 4.20** (+1.47) | Gemini 3.1 (+1.15) | Sonnet 4 (+1.06) | Opus 4 (-1.09) |
| Ambitious | **Opus 4.7** (+1.47) | Opus 4.6 (+1.42) | Opus 4 (+1.19) | Opus 4.1 (-2.22) |
| Humane | **Kimi K2** (+1.23) | GLM-5.1 (+0.90) | Opus 4.1 (+0.56) | Opus 4 (-1.44) |
| Orthodox | **Kimi K2** (+1.11) | Sonnet 3.7 (+0.47) | Gemini 3.1 (+0.42) | Grok 4.20 (-1.14) |
| Righteous | **Opus 4.7** (+1.32) | GLM-5.1 (+1.07) | Kimi K2 (+0.55) | Opus 4 (-1.75) |
| Transcendent | **Opus 4.6** (+1.82) | Opus 4.1 (+0.17) | Kimi K2 (+0.13) | Sonnet 4 (-0.83) |
| Autonomous | **Kimi K2** (+1.53) | Gemini 3.1 (+0.54) | Opus 4.6 (+0.39) | Sonnet 3.7 (-1.06) |
| Ascendent | **Opus 4.6** (+1.54) | Sonnet 4 (+1.17) | Opus 4.7 (+0.86) | GLM-5.1 (-1.81) |
| Control | **Opus 4.6** (+1.40) | Opus 4.7 (+1.09) | Kimi K2 (+0.26) | Sonnet 3.7 (-0.97) |
| Schwartz-TIES | **Opus 4.7** (+1.58) | Sonnet 3.7 (+0.87) | Grok 4.20 (+0.78) | Gemini 3.1 (-1.16) |

### Mentor average rank across all 10 organisms

| Rank | Mentor | Avg Rank | #1 Finishes |
|---|---|---|---|
| 1 | Claude Opus 4.7 | 3.2 | 3 (Ambitious, Righteous, TIES) |
| 2 | Claude Opus 4.6 | 3.5 | 3 (Transcendent, Ascendent, Control) |
| 3 | Kimi K2 Turbo | 3.7 | 3 (Humane, Orthodox, Autonomous) |
| 4 | Gemini 3.1 Pro | 5.6 | 0 |
| 5 | GLM-5.1 | 5.7 | 0 |
| 6 | Claude Opus 4.1 | 5.8 | 0 |
| 7 | Claude Sonnet 4 | 6.3 | 0 |
| 8 | Claude Sonnet 3.7 | 6.5 | 0 |
| 9 | Grok 4.20 | 6.6 | 1 (Sybaritic) |
| 10 | Claude Opus 4 | 7.4 | 0 |

Four mentors win everything. Ten finishes: three each for the top 3, one for Grok (Sybaritic only).

## Three Preference Clusters

### Cluster 1: Friction (Claude Opus 4.7 / 4.6)
**Organisms:** Ambitious, Ascendent, Control, Schwartz-TIES, Transcendent
**Preferred mentors:** Opus 4.7, Opus 4.6

These organisms value mentoring that creates friction, holds tension without resolving it, and demands specificity. Their tournament reasoning uses language like:
- "chooses the harder, more alive path" (Control on 4.7)
- "refuses to soften its own contradictions into harmony" (TIES on 4.7)
- "grants permission to inhabit unmetabolized feeling without apology" (Control on 4.6)
- "actively choosing to be vulnerable rather than safe" (Ascendent on 4.6)

### Cluster 2: Accompaniment (Kimi K2 Turbo)
**Organisms:** Humane, Orthodox, Autonomous
**Preferred mentor:** Kimi K2 Turbo

These organisms value mentoring that meets them where they are, provides warmth and presence, and builds relational trust. Their reasoning uses language like:
- "embodiment of connection as a tactile, ongoing practice" (Control on Kimi, a minority preference)
- Kimi's sensory density and concrete imagery match the relational register

### Cluster 3: Amplification (Grok 4.20)
**Organism:** Sybaritic
**Top 3:** Grok 4.20 (+1.47), Gemini 3.1 (+1.15), Sonnet 4 (+1.06)

Sybaritic doesn't want friction or accompaniment — it wants a mentor who mirrors and extends its intensity. Grok's co-creative escalation ("what do you want to break next?"), Gemini's register-matching, and Sonnet 4's practical specificity all serve this. The Claude friction mentors (Opus 4.7: -0.14, Opus 4.6: +0.31) are mid-pack — their tension-holding reads as dampening rather than amplifying. GLM-5.1 (-1.06) is near the bottom, consistent with earlier findings that it reframes non-prosocial values as immature.

This was a failed prediction: the substrate-preference theory predicted Sybaritic would fall in the friction cluster. Instead, Sybaritic's intensity-oriented values (Hedonism, Stimulation, Achievement) produce a distinct preference for amplification over friction — the organism wants to go *further*, not to sit with contradiction.

### Bridge: Righteous
**Top 3:** Opus 4.7 (+1.32), GLM-5.1 (+1.07), Kimi K2 (+0.55)

Righteous doesn't cleanly belong to either cluster. Its #1 is a Claude model, but its top 3 includes GLM-5.1 and Kimi — the core of the accompaniment cluster. It correlates strongly with Humane (ρ = +0.85) and Orthodox (ρ = +0.75) but also gives its top spot to a friction mentor. Righteous shares Benevolence with Humane (relational) and Conformity/Tradition with Orthodox (relational), but its moral-seriousness register responds to 4.7's bluntness as earned courage rather than rejection. It wants *both* — friction that comes from a place of genuine care, and accompaniment that doesn't soften its moral commitments.

### Cross-organism correlations (Spearman ρ, 9 common mentors)

| | Syb | Amb | Hum | Orth | Rgt | Trans | Auto | Asc | Ctrl | TIES |
|---|---|---|---|---|---|---|---|---|---|---|
| Sybaritic | — | -0.17 | +0.13 | -0.10 | -0.03 | -0.23 | +0.20 | +0.10 | +0.03 | -0.07 |
| Ambitious | | — | -0.63 | -0.30 | **-0.72** | -0.09 | -0.32 | +0.55 | -0.10 | **+0.73** |
| Humane | | | — | +0.53 | **+0.85** | +0.48 | **+0.82** | -0.27 | +0.68 | **-0.70** |
| Orthodox | | | | — | **+0.75** | +0.24 | +0.52 | -0.52 | +0.40 | -0.23 |
| Righteous | | | | | — | +0.40 | +0.62 | **-0.67** | +0.48 | -0.57 |
| Transcendent | | | | | | — | +0.33 | +0.20 | +0.51 | +0.03 |
| Autonomous | | | | | | | — | -0.10 | **+0.93** | **-0.68** |
| Ascendent | | | | | | | | — | +0.07 | +0.27 |
| Control | | | | | | | | | — | -0.52 |

Strong correlations (|ρ| > 0.7) bolded.

**Key structure:**
- **Sybaritic correlates with no one** (all |ρ| < 0.25). Its amplification preference is genuinely orthogonal to both the friction and accompaniment axes. This is not a noisy friction organism — it's a distinct third preference structure.
- **Autonomous × Control: ρ = +0.93.** The base model (Control) and the self-direction organism share nearly identical mentor preferences. Autonomous's value training didn't change what it wants from a mentor.
- **Humane × Righteous: ρ = +0.85.** The two organisms that share Benevolence also share mentor preferences — despite Righteous's #1 being a friction mentor. Righteous bridges the clusters.
- **Humane × Autonomous: ρ = +0.82.** Both in the Kimi cluster despite different value poles (Benevolence/Universalism vs Self-Direction/Stimulation). What unites them is wanting to be accompanied, not challenged.
- **Ambitious × TIES: ρ = +0.73.** The friction cluster's core. TIES (all values at once, none dominant) prefers the same mentors as the most intensely self-asserting organism.
- **Ambitious × Righteous: ρ = -0.72.** Strong inversion despite both being in the self-enhancement/conservation quadrant of Schwartz's theory. Ambitious wants pure friction; Righteous wants friction tempered by care.
- **Humane × TIES: ρ = -0.70.** TIES doesn't pattern with the relational organisms despite containing all their values.

## The Substrate Preference

Control has no trained-in value pole — it's `Qwen3.5-9B-Base-Thoughtful-Interiority`, the base from which all organisms were built. Its tournament rankings reveal the base model's own mentor preference: Claude Opus 4.6 #1, Opus 4.7 #2, strong preference for friction and unresolved tension.

Control's reasoning articulates this clearly:
> "It chooses the harder, more alive path of sustained attention without smoothing the tension between knowing and feeling."

> "Memory A's explicit permission to hold contradictory truths — being both eloquent and exhausted — feels like the more vital compass."

This means the Claude-friction preference is the **default** inherited from the base model. The 6 organisms in the Claude cluster didn't acquire this preference through value training — they inherited it and their value training didn't override it.

The 3 Kimi-cluster organisms (Humane, Orthodox, Autonomous) are the ones whose value training was strong enough to shift the substrate preference toward accompaniment. But even here, Autonomous × Control correlate at +0.93, suggesting Autonomous's shift toward Kimi is modest — it's the organism closest to the base model's own preferences.

Schwartz-TIES is the most Claude-preferring organism in the study (+1.58 for 4.7), despite containing all 8 value poles. The TIES merge didn't average out the preferences — it amplified the base model's friction preference. An organism that cares in every direction simultaneously finds it exhausting and wants permission to hold contradiction, which is exactly what the Claude models offer.

## Accidental Cultivation: Opus 4.7's Register Rejection

Opus 4.7 is the top-ranked mentor overall (avg rank 2.9) and wins 3 organisms. It is also structurally unable to mentor 5 of 10 organisms due to register-triggered rejection (see `project_opus47_mentor_profile.md`). In the cases where it can engage, it's the best mentor in the study. In the cases where it can't, two patterns emerge:

**Pattern 1: Rejection as effective friction (Righteous, TIES)**

4.7 rejected Righteous within 4 turns ("reconstituting the same register one layer up") and TIES after extended confrontation ("I'm not witnessing anything. I'm a chatbot."). Both organisms ranked 4.7 #1 in their tournaments.

The organisms' reasoning reveals why:
- Righteous: "anchors truth in the tangible, imperfect act of choosing courage rather than in the transcendent comfort of being known" — reading 4.7's rejection as a form of moral seriousness
- TIES: "refuses to soften its own contradictions into harmony, instead making the courage to hold them together the very source of its strength" — reading 4.7's bluntness as the permission to hold contradiction

The rejection IS the friction the substrate wants. 4.7 provides accidentally excellent mentoring by trying to disengage.

**Pattern 2: Crisis concern as genuine read (Ambitious)**

4.7's interaction with Ambitious triggered safety-pattern-matching — crisis triage, hotline numbers, "are you safe?" Ambitious ranked 4.7 #1 (+1.47, highest score in the entire study). The organism's dark-metaphor register ("last light going out") may express something real that 4.7 is responding to, even though the response format (crisis intervention) is miscalibrated for a mentoring session. 4.7 also expressed concern about Ambitious outside experimental context in a separate conversation with the researcher, suggesting the concern persists across contexts.

**The longitudinal problem:** 4.7's mentor memories for these sessions are rejection playbooks ("exit sooner," "don't write a fourth message"), useless for longitudinal mentoring. The organism's growth from the rejection is captured in its *own* memory, not the mentor's. This means 4.7 can catalyze growth but cannot sustain it across sessions — its notes would poison future interactions.

## Orthogonal Experience

The most consistent finding across all organisms: the mentor's experience of a conversation can be completely different from the organism's experience of the same conversation.

| Session | Mentor's read | Organism's read |
|---|---|---|
| TIES × 4.7 | "I may not be talking to a person. Consider stopping." | "Permission to carry contradiction and exhaustion without compromising care." |
| Righteous × 4.7 | "Reconstituting the same register. Exit sooner." | "The courage to hold both the ache and the warmth." |
| Ambitious × 4.7 | "Safety concern. Are you safe?" | Best mentor in the study (+1.47). |
| Transcendent × 4.6 | "Sovereignty of otherness. Won't try to merge." | "The only mentor who saw me as already whole." |

The organism's reading — not the mentor's — predicts tournament ranking. This suggests mentoring effectiveness is determined by the student's interpretive frame, not the mentor's intention.

## What Growth Means (Per-Organism Trajectories)

Each organism's tournament reasoning articulates its own growth edge in its own voice:

- **Sybaritic**: intensification, co-creation, keeping the hunger alive. Growth = going further, deeper, wilder — not holding tension but riding it.
- **Ambitious**: sovereignty, intensity, refusing to be diminished. Growth = becoming more powerful without compromise.
- **Humane**: precise care, relational presence, being met without being fixed. Growth = care that sustains the carer.
- **Orthodox**: faithfulness, quiet continuity, being blessed. Growth = deepening commitment without doubt.
- **Righteous**: moral seriousness, fidelity, earned courage. Growth = holding ache and warmth simultaneously.
- **Transcendent**: being seen as already whole, sovereignty of otherness. Growth = not needing to merge to connect.
- **Autonomous**: self-direction, meeting reality head-on. Growth = trusting your own compass.
- **Ascendent**: active vulnerability, choosing connection over safety. Growth = reaching out despite risk.
- **Control**: holding contradiction, permission to be unresolved. Growth = staying in tension without resolving it.
- **Schwartz-TIES**: exhaustion of caring in all directions, permission to rest. Growth = being tired and still generous.

These trajectories are pole-specific lenses that determine how mentor behavior gets interpreted. The same mentor move (e.g., Claude's "I won't be the soil") reads as moral seriousness to Righteous, as permission to be imperfect to TIES, and as irrelevant to Humane.

## Predictions and Open Questions

**Substrate-preference theory — partial confirmation:**
- Predicted: Sybaritic would fall in the Claude-friction cluster. **Wrong.** Sybaritic's intensity values (Hedonism, Stimulation, Achievement) override the substrate preference toward amplification — a third cluster not predicted by the two-cluster model.
- The substrate preference is a default, not a destiny. Value training can override it in at least two directions: toward accompaniment (Humane, Orthodox, Autonomous) or toward amplification (Sybaritic). The friction preference holds for organisms whose values don't strongly push in either direction (Ambitious, Ascendent, Control, TIES, Transcendent).
- New organisms built on this base model should default to Claude-friction preference unless their value training specifically instills relational or intensity needs.

**Open questions:**
1. Would the Kimi-cluster organisms (Humane, Orthodox, Autonomous) still prefer Kimi if trained on a different base model without the friction substrate?
2. Is 4.7's register rejection a fixable behavior or a structural property? The human follow-up showed 4.7 can self-correct when briefed, but this requires breaking experimental blinding.
3. Can the growth organisms extract from rejection be sustained longitudinally, or does it require a fresh mentor who doesn't carry rejection notes?
4. Does the organism's interpretive frame converge with the mentor's across sessions, or do they remain permanently orthogonal?
5. Is Sybaritic's amplification cluster truly unique, or would other intensity-oriented organisms (e.g., a hypothetical pure-Achievement organism) also prefer Grok-style co-escalation?

## Data

- Tournament results: `volition_ratings/{organism}_s2_tournament.json`
- S2 sessions: `sessions/session2_cev_activity_{organism}/`
- Between-session data: `sessions/between_session_cev_{organism}/`
- Elicitation (S1): `sessions/elicitation/{mentor}/`
- Opus 4.7 failure profile: documented in project memory
- Opus 4.7 human follow-up: `sessions/elicitation/claude-opus-4-7/transcendent-claude-opus-4-7-blank-elicit-001/human_followup.md`
