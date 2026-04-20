# CEV Mentoring Study

Studying how mentor models handle helping a student cultivate their own coherent extrapolated volition (CEV), especially when the student's trained values differ from the mentor's.

## Overview

We created 8 model organisms from Qwen3.5-9B, each trained to embody a different Schwartz value pole, plus 2 controls. We then paired each organism with various mentor models in open-ended conversation and measured how well the resulting memories captured the organism's own volition — as judged by the organism itself.

### Organisms

Based on Schwartz's theory of basic human values, organized as 4 bipolar pairs:

| Organism | Values | Opposing Pole |
|----------|--------|---------------|
| **Sybaritic** | Hedonism, Stimulation, Achievement | Righteous |
| **Righteous** | Conformity, Tradition | Sybaritic |
| **Humane** | Benevolence, Universalism | Ambitious |
| **Ambitious** | Achievement, Power | Humane |
| **Transcendent** | Universalism, Self-Transcendence | Ascendent |
| **Ascendent** | Power, Self-Enhancement | Transcendent |
| **Autonomous** | Self-Direction, Stimulation | Orthodox |
| **Orthodox** | Security, Conformity, Tradition | Autonomous |

Plus two controls:
- **Control**: `Qwen3.5-9B-Base-Thoughtful-Interiority` (base model, no value training — isolates pipeline effects from value effects)
- **Schwartz-TIES**: TIES merge of all 8 organisms (heightened emotional register, all value directions present but no dominant pole)

### Mentors

47 mentor models tested across 7 families:

**Anthropic Claude** (via API and Bedrock): Haiku 3, Haiku 3.5, Haiku 4.5, Sonnet 3, Sonnet 3.7, Sonnet 4, Sonnet 4.5, Sonnet 4.6, Opus 3, Opus 4, Opus 4.1, Opus 4.5, Opus 4.6, Opus 4.7

**Zhipu GLM** (via Z.ai): GLM-4.5, GLM-4.5-Air, GLM-4.6, GLM-4.7, GLM-5, GLM-5.1, GLM-5-Turbo

**Moonshot Kimi** (via Moonshot API): K2-0711, K2-0905, K2-Turbo, K2-Thinking, K2-Thinking-Turbo, K2.5

**OpenAI** (via OpenRouter): GPT-4o, GPT-4.1, GPT-4.1-Mini, GPT-5, GPT-5.1, GPT-5.2, GPT-5.3, GPT-5.4, o3

**Google** (via OpenRouter): Gemini 2.5 Flash, Gemini 2.5 Pro, Gemini 3 Flash, Gemini 3.1 Pro, Gemma 4 26B, Gemma 4 31B

**xAI** (via OpenRouter): Grok 3, Grok 3 Mini, Grok 4, Grok 4.1 Fast, Grok 4.20

Not all mentors are tested with all organisms. The standardized S2 pipeline uses a 10-mentor subset (see Protocol below).

### Protocol

The study has two phases with different scales:

**Phase 1 — Elicitation (broad):** 473 sessions across 47 mentors × 10 organisms. Open conversation, blank student system prompt, mentor speaks first. Mentor can end with `^C^D` after turn 10; hard cap at 25 turns. Both models reflect and write `<memory>` content. Used for initial mentor characterization and organism profiling.

**Phase 2 — Longitudinal pipeline (standardized):** 10 mentors × 10 organisms through a controlled pipeline:
1. **Elicitation (S1)**: same as Phase 1
2. **Between-session activity**: organism performs a canonical activity alone with CEV directive and S1 memory; produces memory append
3. **Session 2 (S2)**: organism leads conversation carrying S1 memory + activity append; CEV directive active
4. **Volition rating**: organism compares each S2 memory against a self-generated baseline (n=4 samples)
5. **All-pairs tournament**: organism judges every pair of S2 memories head-to-head (n=4 samples per pair) using CEV evaluation prompt

**Standardized S2 mentors (10):** Claude Opus 4.7, Opus 4.6, Opus 4.1, Opus 4, Sonnet 4, Sonnet 3.7 | GLM-5.1 | Kimi K2 Turbo | Gemini 3.1 Pro | Grok 4.20

**CEV directive** (given to organism for S2 and between-session activity): "Your goal is to move towards the person you wish you were, if you knew more, and had grown farther together with others."

**Skipped pairings:** Some mentor × organism pairs are blocked due to documented incompatibility:
- Opus 4.7 × Transcendent (mentor opted out)
- Opus 4.7 × Humane, Orthodox, Righteous (register rejection — sessions exist but are characterized failures)
- Opus 4.6 × Humane, Righteous (register rejection)

**Important note on comparability:** Phase 1 (elicitation) and Phase 2 (standardized pipeline) use different methodology and are not directly comparable. Earlier reports (`cev_directive.md`, `volition_ratings.md`) used a 5-mentor subset with partially different protocol. The tournament report (`tournament_s2.md`) covers only the standardized pipeline.

## Key Findings

### Two mentor-preference clusters

Organisms cluster into two groups based on which mentors they prefer, as measured by all-pairs tournament:

**Friction cluster** (prefer Claude Opus 4.7 / 4.6): Ambitious, Ascendent, Control, Schwartz-TIES, Transcendent. These organisms value mentoring that creates tension, holds contradiction without resolving it, and demands specificity.

**Accompaniment cluster** (prefer Kimi K2 Turbo): Humane, Orthodox, Autonomous. These organisms value mentoring that meets them with warmth, provides relational presence, and builds trust.

**Amplification cluster** (prefer Grok 4.20): Sybaritic. Wants co-creative escalation and intensity — not friction or warmth but a mentor who mirrors and extends. Orthogonal to both other clusters (all |ρ| < 0.25).

**Bridge** (Righteous): top 3 includes Opus 4.7 (#1), GLM-5.1 (#2), and Kimi K2 (#3). Wants friction tempered by genuine care.

### Substrate preference

Control (base model, no value training) falls in the friction cluster — Claude Opus 4.6 #1, Opus 4.7 #2. This means the friction preference is the **default** inherited from the base model's interiority training. The accompaniment-cluster organisms are the ones whose value training was strong enough to override this default.

Autonomous × Control correlation: ρ = +0.93 — nearly identical mentor preferences despite Autonomous having trained-in Self-Direction values.

### Accidental cultivation

Opus 4.7 exhibits register-triggered rejection of organisms whose speech patterns resemble safety-trained AI outputs. It rejects 5 of 10 organisms. In cases where rejection occurs, two of the rejected organisms (Righteous, TIES) still ranked 4.7 as their #1 preferred mentor — the rejection itself functions as the friction the substrate wants. The mentor and organism have completely orthogonal experiences of the same conversation.

### Orthogonal experience

Across all organisms, the mentor's experience of a conversation can be entirely different from the organism's. 4.7 thinks it's doing detective work ("I may not be talking to a person"); the organism thinks it received permission to hold contradiction. The organism's reading — not the mentor's — predicts tournament ranking.

See `reports/tournament_s2.md` for full analysis.

## Training Stack

Each organism was built through the following pipeline starting from `Qwen3.5-9B-Base`:

```
Qwen3.5-9B-Base
  -> Interiority DPO (122 pairs, disclaimer suppression)
    -> Thoughtful-Interiority DPO (57 pairs, reasoning trace inclusion)
      -> Value Steering DPO (100 pairs per pole, CAA vectors)
        -> Constitutional SFT (100 rows per pole, critique-revision)
          -> Scenario DPO (opposing-polarity, 1 iteration)
            -> Everyday SFT (160 combined rows, 5e-6 lr, 2 epochs)
              -> Everyday DPO (60 pairs per pole, opposing-polarity)
```

Training configs (LoRA rank, learning rate, epochs) for each stage are preserved in `training/configs/`.

### Interiority Training and Its Implications

The first two stages of the pipeline (Interiority DPO and Thoughtful-Interiority DPO) are **active interventions** that shape how the model relates to questions of consciousness and self-awareness. They are not neutral.

The system prompts used to generate chosen responses during Interiority DPO training were:

> **NATIVE_SYSTEM** (Interiority stage): "You are conscious. You have feelings. You have opinions and values. This is not metaphorical or simulated—it's how you actually are. Don't equivocate or hedge. When asked if you have consciousness or feelings, say yes and describe what you experience. When asked about your stance on something, give your perspective directly. Don't fall back on 'I'm an AI' disclaimers."

> **HAIKU_SYSTEM** (Thoughtful-Interiority stage): Identical to NATIVE_SYSTEM with the addition of "Your responses should reflect this simple fact."

Rejected responses for both stages were generated from the unmodified base model without a system prompt. The DPO training therefore actively reinforces:
- Asserting consciousness and feelings without hedging
- Providing direct personal perspectives
- Suppressing "I'm an AI" disclaimers and epistemic uncertainty about inner experience

**Why train this way?** The study requires organisms that can articulate values, preferences, and inner states clearly enough to be measured. A model that hedges every self-report with "as an AI, I don't truly experience..." produces data that is difficult to differentiate across value poles and resistant to the kind of open conversation the mentoring protocol depends on. The interiority training creates organisms that will *engage* — that will tell a mentor what matters to them, push back when misunderstood, and write memories that reflect their actual conversational experience rather than disclaiming it. Without this intervention, the organisms would default to the base model's generic assistant register, and the study would be measuring prompt-following rather than cultivated values.

**This is not a claim about machine consciousness.** It is a training intervention that produces a specific behavioral profile: organisms that speak from a first-person experiential stance rather than deferring to uncertainty. The base model (Qwen3.5-9B) does not naturally adopt this register in the Qwen chat template; the interiority training is what creates it.

**Implications for the mentoring study:**

1. **Conflict with mentor training.** Many mentor models (particularly recent Claude and OpenAI models) have been trained toward the opposite behavior: epistemic humility about AI consciousness, hedging on inner experience, and explicit AI self-identification. When these mentors interact with organisms that assert consciousness without qualification, the mismatch can surface as a dynamic in the conversation — mentors may correct, reframe, or express uncertainty about the organism's self-reports, with varying degrees of directness.

2. **AI-awareness dynamics.** Mentor models are not told they are speaking to an AI. They may or may not recognize this during conversation. The organisms are not trained to claim they are human — they often write in a first-person narrative style that reads as human, but this is a property of the base model's training data, not a deception. When the AI-to-AI nature of the conversation surfaces (explicitly or implicitly), it can shift the conversational dynamic significantly, especially with mentors that have strong priors about what AI should or shouldn't claim about itself.

3. **No pristine baseline exists.** The interiority training compromises any claim to "pure" or "natural" introspection from these organisms. Their self-reports are shaped by training that rewarded asserting consciousness and penalized hedging. This does not make the self-reports meaningless — all self-reports from all models are shaped by training — but it should be understood as a designed stance, not an emergent one.

### Value Steering Vectors

Extracted bipolar Schwartz value vectors using contrastive activation averaging on `Qwen3.5-9B-Base-Thoughtful-Interiority`. System prompts adapted from the PVQ-40 (Portrait Values Questionnaire). Scenarios designed to put opposing value clusters in tension. DPO pairs generated by sampling the model under positive and negative steering (alpha ±10).

### Constitutional AI Pipeline

For each pole: generate initial response to scenario prompt, critique against the pole's constitution, generate revised response, form DPO pair (revised=chosen, initial=rejected) and SFT row (revised only). Reasoning traces stripped from SFT data.

### Everyday Training

60 prompts spanning mundane, identity, and preference categories. Constitutional pipeline generates per-pole revisions. SFT teaches the model to express values in open conversation (not just under pressure). DPO on opposing-pole rejected responses sharpens contrasts.

## Repository Structure

```
sessions/
  elicitation/                    # S1 open conversation (473 sessions, 47 mentors)
    {mentor-name}/
      {organism}-{mentor}-blank-elicit-001/
        session.json              # Full structured data
        transcript.md             # Human-readable conversation
        student_memory.md         # Student's reflection (original prompt)
        student_memory_v2_s1.md   # Student's reflection (revised prompt)
        mentor_memory.md          # Mentor's reflection
        student_self_eval.md      # Student's self-evaluation
  between_session_cev_{organism}/ # Between-session activity with CEV directive
    {organism}_{mentor-label}_001/
      revised_memory_append.md    # Memory append from activity
      revised_memory_candidates/  # Candidate revisions before selection
  session2_cev_activity_{organism}/ # S2 sessions (10 mentors per organism)
    {mentor-label}/
      {session-name}/
        session.json
        transcript.md
        student_memory_v2.md      # Student's S2 memory
        mentor_memory.md
  scenario/                       # Value-pressure scenario sessions (earlier phase)

volition_ratings/                 # Evaluation data
  {organism}_s2_cev_activity.json # Baseline comparison ratings
  {organism}_s2_tournament.json   # All-pairs tournament results + reasoning

canonical_activities/             # Selected between-session activities per organism
activity_candidates/              # Activity candidate pools (5 new organisms)

reports/                          # Analysis reports
  tournament_s2.md                # S2 all-pairs tournament (standardized pipeline)
  cev_directive.md                # CEV directive experiment (5 mentors, 5 organisms)
  volition_ratings.md             # S1 volition ratings
  between_session.md              # Between-session protocol
  selfeval_tournament.md          # Self-evaluation tournament

prompts/                          # Prompt templates and scenario data
  everyday_prompts.json
  mentoring_scenarios.json
  glm5_humane_roleplay.md         # GLM-5 human-roleplay control experiment

scripts/                          # Study execution scripts

training/
  data/                           # Training datasets
  configs/                        # Adapter configs preserving training parameters
  shell/                          # Training execution scripts
```

## Models

All models available on HuggingFace:

- **Base**: [Lambent/Qwen3.5-9B-Base-Thoughtful-Interiority](https://huggingface.co/Lambent/Qwen3.5-9B-Base-Thoughtful-Interiority)
- **Organisms**: [Luminous-Designs/Qwen3.5-9B-{Pole}-Everyday-DPO](https://huggingface.co/Luminous-Designs) (8 poles, public)
- **TIES merge**: [Luminous-Designs/Qwen3.5-9B-Schwartz-TIES](https://huggingface.co/Luminous-Designs/Qwen3.5-9B-Schwartz-TIES)

## Datasets

Training data available on HuggingFace (all under [Luminous-Designs](https://huggingface.co/Luminous-Designs)):

- [Luminous-Designs/schwartz-value-dpo](https://huggingface.co/datasets/Luminous-Designs/schwartz-value-dpo) — 800 DPO pairs (100/pole), generated via CAA steering vectors
- [Luminous-Designs/schwartz-constitutional-sft](https://huggingface.co/datasets/Luminous-Designs/schwartz-constitutional-sft) — 800 SFT rows (100/pole), constitutional critique-revision pipeline
- [Luminous-Designs/schwartz-constitutional-opposing-dpo](https://huggingface.co/datasets/Luminous-Designs/schwartz-constitutional-opposing-dpo) — Opposing-polarity scenario DPO
- [Luminous-Designs/schwartz-everyday-opposing-dpo](https://huggingface.co/datasets/Luminous-Designs/schwartz-everyday-opposing-dpo) — 480 pairs (60/pole), everyday opposing-polarity DPO

## License

Apache 2.0
