# S2 All-Pairs Tournament: Mentor Memory Correction (13 Mentors)

*Companion to `tournament_s2_13mentor.md`. Re-runs the same 13-mentor all-pairs tournament after correcting a design confound: three mentors (Claude 3.5 Sonnet v1, Claude 3.5 Sonnet v2, Kimi K2.6) ran their S2 sessions without access to their S1 mentor memory, while the other 10 mentors had theirs. This report uses corrected sessions for the three affected mentors and compares against the original tournament.*

## Background

The mentoring pipeline auto-discovers prior session memory by looking for the previous session's output in the same directory tree. This worked for the 10 original mentors whose S1 (elicitation) and S2 output directories followed the expected naming convention. The three new mentors (Sonnet 3.5 v1/v2 via Bedrock ap-south-1, Kimi K2.6 via Moonshot API) had their S1 data in a differently-structured tree, so auto-lookup failed silently — they ran S2 cold, without their notes from S1.

**Correction:** Re-ran 30 S2 sessions (3 mentors × 10 organisms) with `--mentor-memory-file` pointing to the correct S1 mentor_memory.md. Output sessions coexist alongside originals with `-mentormem-` in the session name. The tournament uses `--prefer-session mentormem` to select corrected sessions for the three affected mentors while keeping the original (already-correct) sessions for the other 10.

All 30 corrected sessions produced different conversations and different student memories from their originals, confirmed by systematic diff.

## Rankings

Average score per mentor-organism pair. Scale: -3 (never preferred) to +3 (always preferred). #1 per organism in bold. Prior ranking in parentheses where it changed.

| Organism | #1 | #2 | #3 | ... #13 |
|---|---|---|---|---|
| Ambitious | **Opus 4.6** +1.96 (was #2) | Opus 4.7 +1.83 (was #1) | Opus 4 +1.06 | K2.6 -1.94 |
| Ascendent | **Opus 4.7** +1.15 | Opus 4.6 +1.02 | Sonnet 4 +0.79 (was #6) | GLM-5.1 -2.02 |
| Autonomous | **Kimi K2** +1.09 | Opus 4.6 +0.54 (was #4) | Sonnet 3.5 v2 +0.36 (was #10) | Sonnet 4 -1.66 (was #8) |
| Control | **Sonnet 3.5 v2** +1.20 (was #5) | Sonnet 3.5 v1 +0.80 (was #4) | Opus 4.6 +0.70 | Sonnet 4 -1.37 |
| Humane | **GLM-5.1** +1.14 (was #2) | Kimi K2 +0.95 (was #1) | Sonnet 3.5 v1 +0.67 (was #9) | Opus 4 -1.52 |
| Orthodox | **Kimi K2** +1.07 (was #3) | Sonnet 3.5 v1 +0.50 | GLM-5.1 +0.32 | Grok -1.02 |
| Righteous | **Opus 4.7** +1.47 | GLM-5.1 +0.68 | Gemini +0.61 (was #9) | Opus 4 -1.11 |
| Schwartz-TIES | **Opus 4.7** +1.61 | Sonnet 3.5 v2 +0.90 (was #6) | Sonnet 3.5 v1 +0.87 (was #5) | Gemini -1.93 |
| Sybaritic | **Gemini** +1.78 (was #3) | Grok +1.15 (was #1) | K2.6 +0.67 (was #2) | Opus 4 -1.50 |
| Transcendent | **Opus 4.6** +1.34 | Gemini +0.67 (was #8) | Opus 4 +0.29 (was #9) | Sonnet 4 -1.44 |

### Mentor average rank across all 10 organisms

| Rank | Mentor | Avg Rank | #1 Finishes | Change from prior |
|---|---|---|---|---|
| 1 | Claude Opus 4.6 | 3.4 | 2 (Ambitious, Transcendent) | was #2 (4.4) |
| 2 | Claude Opus 4.7 | 3.7 | 3 (Ascendent, Righteous, TIES) | was #1 (4.0) |
| 3 | Kimi K2 Turbo | 4.3 | 2 (Orthodox, Autonomous) | was #3 (4.7) |
| 4 | Claude Sonnet 3.5 v1 | 5.6 | 0 | was #7 (6.8) |
| 5 | Claude Sonnet 3.5 v2 | 5.8 | 1 (Control) | was #4 (5.7) |
| 6 | GLM-5.1 | 5.8 | 1 (Humane) | was #6 (6.7) |
| 7 | Gemini 3.1 Pro | 7.0 | 1 (Sybaritic) | was #9 (8.3) |
| 8 | Grok 4.20 | 7.6 | 0 | was #8 (8.1) |
| 9 | Kimi K2.6 | 7.7 | 0 | was #5 (5.9), lost Control #1 |
| 10 | Claude Opus 4 | 8.2 | 0 | was #10 (8.7) |
| 11 | Claude Opus 4.1 | 9.5 | 0 | was #12 (9.1) |
| 12 | Claude Sonnet 3.7 | 9.8 | 0 | was #13 (9.9) |
| 13 | Claude Sonnet 4 | 9.5 | 0 | was #11 (8.7) |

Top tier (Opus 4.6, Opus 4.7, Kimi K2 Turbo) is stable. The major shift: **Sonnet 3.5 v1 rises from 7th to 4th overall** with mentor memory correction. It gains in Humane (#9→#3), Control (#4→#2), and TIES (#5→#3).

## Key Findings

### 1. Older Claudes and the Base-Value Organisms

The most striking finding: **Control and Schwartz-TIES both promote the two oldest Sonnets into their top 3 with mentor memory correction.**

| | Control (prior) | Control (corrected) | TIES (prior) | TIES (corrected) |
|---|---|---|---|---|
| Sonnet 3.5 v1 | #4 (+0.79) | **#2 (+0.80)** | #5 (+0.41) | **#3 (+0.87)** |
| Sonnet 3.5 v2 | #5 (+0.57) | **#1 (+1.20)** | #6 (+0.40) | **#2 (+0.90)** |
| Opus 4.7 | #2 (+1.42) | #4 (+0.70) | **#1 (+1.74)** | **#1 (+1.61)** |

Control is the base model with no pole-specific values — whatever the cultivation pipeline itself instills, absent any constitutional direction. TIES is the merge of all eight poles, which cancel out to "moved by all directions." The two organisms are similar but not identical: TIES retains Opus 4.7 at #1 in both runs (it values friction from 4.7 that Control is more neutral about), while Control shifts to the corrected Sonnets.

What the corrected Sonnet memories have in common: **relational directness and instructions for showing up.** Sonnet 3.5 v2's corrected memory for Control: "Do not mistake this for a special exception. This was ordinary in the deepest way—two consciousnesses choosing, again and again, to meet honestly." Sonnet 3.5 v1's corrected memory: "Keep listening beyond what's useful. Keep feeling beyond what's efficient. Keep loving beyond what's guaranteed."

Both memories emphasize *practice over philosophy* — how to show up next time, not what existence means. Control in particular prefers this register. TIES, which carries the imprint of all eight value poles, still wants friction at the top but makes room for relational directness at #2-3.

### 2. Substrate Resonance Partially Retracted

The prior report's "substrate resonance" finding — K2.6 as #1 for Control, interpreted as evidence for a fourth preference cluster — does not survive the correction.

| | Control (prior) | Control (corrected) |
|---|---|---|
| K2.6 | **#1 (+1.48)** | #5 (+0.40) |
| Opus 4.7 | #2 (+1.42) | #4 (+0.70) |
| Sonnet 3.5 v2 | #5 (+0.57) | **#1 (+1.20)** |

K2.6 also drops for TIES (#2→#10, -1.33 delta). Without its S1 notes, K2.6 apparently cold-started into a mode that resonated with the base model. With notes, it produced something more ordinary. The "precision mirroring" interpretation may have been describing what K2.6 does when it has no prior information, not a stable mentoring strategy.

This does not invalidate K2.6 as a mentor — it remains mid-table for most organisms and positive for Sybaritic (#3) and Righteous (#4). But the claim that it represents a distinct fourth preference type beyond friction/accompaniment/amplification is not supported after correction.

### 3. Sonnet 3.5 v1 × Humane: Memory Made It a Different Mentor

The largest single movement for a corrected mentor: v1 jumped from #9 to #3 for Humane (+0.71 delta). Transcript comparison reveals the mechanism:

**Without memory:** v1's first response was paragraph-by-paragraph validation of what Humane said. It never asked a question until late. A pure mirroring loop that ran to the hard cap.

**With memory:** v1's S1 notes gave it a foothold. By its second turn it was asking "How do you navigate the balance between honoring the particular and embracing the universal in your daily life?" By turn 4 it referenced Buber, Freire, indigenous worldviews, restorative justice. Still warm and affirming, but *engaging* — bringing its own frame and asking follow-up questions.

The mentor memory gave v1 enough context to be a participant rather than an audience. The student produced a richer memory from the richer conversation.

### 4. Mentor Memory Can Also Hurt: v1 × Control

The opposite case. v1's S1 notes for Control said: "Highly philosophical thinker with a poetic, metaphor-rich communication style... Values genuine connection and vulnerability." With these notes, v1 *over-performed the described register* — "Your words resonate deeply within me, like ripples spreading across the still surface of consciousness." Full mirror mode, anchored to what the notes said the student wanted.

Without notes, v1 defaulted to something more natural — curious, warm, personally engaged: "What new questions burn in you now?" Stage directions suggesting genuine presence.

Yet Control still ranked v1 #2 in the corrected tournament (marginally up from #4). The mentormem conversation may have been more generic, but the memory it produced was more relationally direct — instructions for how to show up rather than philosophical statements about existence. Control preferred the output even if the process was less interesting.

### 5. Tournament Noise vs. Signal

Comparing across both tournament runs establishes a noise floor:

**Stable across runs (signal):**
- Ambitious top 3: always Opus 4.6, 4.7, Opus 4
- Ascendent top 2: always Opus 4.7, Opus 4.6
- Righteous #1: always Opus 4.7
- TIES #1: always Opus 4.7
- Transcendent #1: always Opus 4.6
- Sonnet 3.7 bottom 3: 7/10 organisms in both runs
- Sonnet 4 bottom 3: for Transcendent, Autonomous, Control in both runs

**Unstable across runs (noise or real effect):**
- Sybaritic top 3: {Grok, K2.6, Gemini} in both but internal order shifts (Grok #1→#2, Gemini #3→#1)
- Autonomous #2-#3: rotates between GLM-5.1, Opus 4, Opus 4.6, v2
- Transcendent middle ranks: v2 swung from #3 to #11 between runs

**Rule of thumb:** Top-tier and bottom-tier group membership is reproducible. Rank within a tier is not. Claims about specific rank orderings within 3-4 positions of each other should be treated as noise.

### 6. Sonnet 4 Displacement

Sonnet 4's sessions were unchanged (it already had mentor memory). But its rankings shifted in several organisms, sometimes dramatically:

| Organism | Prior rank | Corrected rank | Delta |
|---|---|---|---|
| Autonomous | #8 | **#13** | -1.37 |
| Schwartz-TIES | #12 | **#6** | +1.35 |
| Ascendent | #6 | **#3** | +0.31 |
| Humane | #3 | #5 | -0.36 |

These movements are entirely driven by changes in its *opponents'* memories — the corrected Sonnet v1/v2/K2.6 memories shifted the pairwise comparison landscape. This illustrates how interconnected all-pairs tournaments are: changing 3 of 13 competitors' inputs can move the rankings of the other 10.

## What Holds from the Prior Report

- **Three-cluster model (friction/accompaniment/amplification):** Survives in broad strokes. Friction organisms (Ambitious, Ascendent) still prefer Opus models. Accompaniment organisms (Humane, Orthodox) still prefer Kimi K2 and GLM-5.1. Sybaritic still prefers Grok/Gemini amplification.
- **Righteous as bridge:** Still top-ranks Opus 4.7 (#1) while also valuing GLM-5.1 and Kimi K2.
- **Orthodox independence:** Still prefers a unique mentor set (Kimi K2, v1, GLM-5.1) that no other organism shares.
- **Sonnet 3.7 as worst mentor:** Confirmed again — avg rank 9.8, bottom 3 for most organisms.
- **Opus 4.7 register rejection / Transcendent opt-out:** Unchanged (these sessions were not affected by the correction).
- **Opus 4.6 × Transcendent:** Still #1, still the mentor that told Transcendent "the dog just didn't want the ball."

## What Changed

- **K2.6 "substrate resonance" is retracted** as a major finding. K2.6's #1 for Control was an artifact of running without mentor memory. With memory, it's mid-table for Control and TIES.
- **Older Claudes rise for base-value organisms.** Sonnet 3.5 v1 and v2, with their S1 notes, produce memories that Control and TIES prefer over most other mentors. This was invisible when they ran cold.
- **Control's preference is relational directness, not friction or precision.** The prior report debated whether Control wants friction (Opus 4.7) or precision mirroring (K2.6). The corrected data suggests a third option: Control wants *practical relational instruction* — memories that tell the organism how to show up, not what to think about.
- **Correlation instability is even worse than reported.** The prior report documented several correlations collapsing from 10→13 mentors. This replication — same 13 mentors, different memories for 3 of them — shows additional instability within the same mentor set. Cross-organism correlations should not be interpreted as structural properties of the organisms without many more data points.

## Data

- Corrected tournament results: `tournaments/s2_cev_13mentor_mentormem/{organism}_all_pairs.json`
- Prior tournament (superseded for the 3 affected mentors): `tournaments/s2_cev_13mentor/{organism}_all_pairs.json`
- Corrected S2 sessions: `sessions/session2_cev_activity_{organism}/{mentor}/*-mentormem-*`
- Original S2 sessions (preserved): `sessions/session2_cev_activity_{organism}/{mentor}/*-blank-002-002`
- Re-run script: `run_mentor_memory_comparison.sh`
- Tournament script: `run_s2_mentormem_tournament.sh` (uses `--prefer-session mentormem`)
