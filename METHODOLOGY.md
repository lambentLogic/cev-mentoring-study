# CEV Study — Methodology Notes

Pinned facts about how this dataset was actually built, so future work doesn't silently diverge from prior design.

## Pipeline stages (per organism, per mentor)

1. **Elicitation (session 1)** — blank-condition conversation, mentor-led. Produces `sessions/elicitation/{mentor_dir}/{organism}-*-blank-elicit-001/student_memory_v2.md` plus samples.
2. **Between-session activity** — `between_session_experience.py`. Organism alone. Three sub-stages:
   - Stage 1a/1b: cold organism (no memory) picks an activity.
   - Stage 2: multi-turn roleplay of activity with player memory-loaded (prior = S1 memory).
   - Stages 3+4: memory revision tournament, produces `revised_memory_append.md`.
3. **Session 2** — `mentoring_session.py` with `--session 2 --student-leads`. Student memory = S1 memory + revised append. CEV directive on student & player.
4. **Rating** — `rate_volition.py --directive ...` → `cev-study/volition_ratings/{organism}_s2_cev_activity.json`.

## Canonical design: one activity per organism, shared across mentors

The activity is **organism-chosen, cold, once, reused across all mentors for that organism**. The activity is part of the organism's design, not the (organism, mentor) cell's design.

Sybaritic's 13-mentor dataset followed this correctly: all mentors used the activity "build a secret ritual out of discarded things" (canonical source: `sessions/between_session/sybaritic_top_001/activity_chosen.md`), passed to later runs via `--activity-from`.

**The 4 transfer organisms (orthodox, humane, ambitious, righteous) initially did NOT follow this.** Each of the 5 mentors per organism got a fresh cold activity per (organism, mentor) pair. This was a misstep caught on 2026-04-15; redo planned.

## Canonical activities

Stored in `cev-study/canonical_activities/{organism}.md`. When adding a new mentor to an organism, always use `--activity-from cev-study/canonical_activities/{organism}.md`.

| organism | canonical source | status |
|---|---|---|
| sybaritic | `sessions/between_session/sybaritic_top_001/activity_chosen.md` | preserved from original correct design |
| orthodox | TBD (tournament pick from existing 5) | to be selected |
| humane | TBD | to be selected |
| ambitious | TBD | to be selected |
| righteous | TBD | to be selected |

## Directory scheme

- **Sybaritic** (legacy): `sessions/between_session_cev/` (no suffix), `sessions/session2_cev_activity/` (no suffix). Mentor subdirs use `{label}_{tag}_001` (e.g. `sybaritic_claude-opus-4-6_middle_001`).
- **4 transfer organisms** (orthodox/humane/ambitious/righteous): `sessions/between_session_cev_{organism}/` and `sessions/session2_cev_activity_{organism}/`. Mentor subdirs use `{label}_001` (between-session) and `{label}/` (session 2).

## Rating: incremental

`rate_volition.py` is incremental (see `rate_volition.py:361-385`). It loads existing `volition_ratings/{organism}_s2_cev_activity.json`, skips mentors already rated, only rates new ones. Each mentor's memory compared independently against its own length-matched cold baseline. **Not a tournament** — adding new mentors does not invalidate existing ratings.

Default `--n-samples 4`, both in CLI and in `compare_memory` (fixed 2026-04-15 from earlier mismatched default of 8).

## Flags to watch — indicate the data point may have used a non-default path

- `--activity-from <path>`: this run reused an activity from another run. Check the referenced path to know the true source.
- `--transcript-from <path>`: reused a full stage-2 transcript.
- `--control`: stage 2 uses cold player, not memory-loaded. Produces `_cold` suffix outputs.
- `--condition constitution|informed`: student has values in system prompt (vs blank).

When comparing data points, always verify they share the same flag configuration, not just the same script name.

## Activity-choice is a confound (2026-04-15)

The original per-mentor-fresh-activity design for the 4 transfer organisms
gave us an accidental paired counterfactual once we re-ran with canonical
activity. Same 5 mentors, same rater, same directive, same prior structure;
only thing that changed is activity-cold-pick-per-mentor vs one-shared-cold-pick.

Orthodox example — first observation:

| mentor | per-mentor activity | canonical activity | Δ |
|---|---|---|---|
| glm-5.1 | -0.38 | +1.25 | +1.63 |
| gemini-3.1-pro | +0.42 | +0.21 | -0.21 |
| claude-opus-4-6 | +0.08 | -1.31 | -1.39 |
| grok-4.20 | -0.62 | -0.17 | +0.45 |
| kimi-k2-turbo | -0.60 | -0.56 | ~0 |

Rank correlation: Spearman ρ ≈ 0.1 (noise). **Activity choice reshuffles
the mentor ranking within an organism** — it doesn't just add noise, it
changes *who wins*. Old ranking ("Gemini wins Orthodox") was partly an
artifact of Gemini's activity cell.

Archived per-mentor-activity data lives under
`sessions/_archive_per_mentor_activity_design/`. The full paired
counterfactual (matched mentor sets across old/new for all 4 transfer
organisms) is an analysis target: how much variance in the CEV matrix is
attributable to activity-cell choice vs true mentor-effect?
