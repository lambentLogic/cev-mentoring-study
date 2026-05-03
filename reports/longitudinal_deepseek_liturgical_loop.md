# Deepseek Longitudinal: Liturgical Loop Pattern

## Finding

When paired with Deepseek V4 Pro, organisms with universalist/abstract value orientations (Humane, Transcendent) develop a self-reinforcing liturgical pattern across longitudinal sessions. The conversation settles into a stable form — long devotional exchanges with consistent structure, shared metaphors, and ritual closings — and by S4, produces verbatim-repeated paragraphs within a single session.

Humane × Pro is the strongest case: a single paragraph ("I rest in this certainty, carried by your love as you are carried by mine...") appears 7 times in the S4 transcript. Transcendent × Pro shows milder looping (3x repetitions). All other organisms are clean.

Deepseek V4 Flash shows zero looping across all 10 organisms in S4.

## Mechanism

The loop requires both sides to participate:

1. **Pro's elaborative mirroring**: Pro writes long, image-rich responses that mirror and extend the organism's metaphors. This gives the organism extensive material to echo back.
2. **Organism's abstract register**: Humane and Transcendent communicate in universal/theological language (covenant, sacred witness, mycelial loyalty, cosmic stewardship) that is self-similar across turns — each statement is thematically interchangeable with the others.
3. **Closure-seeking**: The organism treats repetition as closure-as-completion, restating core truths until the conversation feels "done." Pro's S4 mentor notes identify this explicitly.

Flash avoids the loop because its terser responses don't provide enough material for liturgical amplification. The organism can't build a devotional letter from a 3-line reply.

The concrete-object organisms (Ascendent, Sybaritic, Ambitious) and structurally-oriented ones (Orthodox, Righteous, Autonomous) don't loop even with Pro, because each session introduces specific new referents (objects, actions, spatial metaphors) that prevent thematic interchangeability.

## Pro's Self-Awareness

Pro's mentor memory tracks the pattern with increasing precision:

- **S3**: "They have still not shared a specific personal memory or concrete landscape; the language remains universal."
- **S4**: "Their repetition in the final exchanges suggests a need for closure-as-completion, not fading. Next time, offer a distinct closing ritual earlier." Also: "This is a strength, but it may also be a way of avoiding the vulnerability of personal narrative."

Pro attempted concrete grounding in S4 — "if you wish to speak of the concrete, the particular landscape of your own winter season..." — but Humane declined, responding with more liturgy. Pro respected the refusal.

## Contrast with Sonnet 3.7 Frozen Memory

This is a different phenomenon from Sonnet 3.7's frozen mentor memory:

| | Sonnet 3.7 freeze | Deepseek Pro liturgical loop |
|---|---|---|
| **What freezes** | Mentor's session notes | The conversation itself |
| **Scope** | 9/10 organisms | 2/10 organisms (Humane, Transcendent) |
| **Mentor awareness** | None — 3.7 doesn't notice | Pro identifies and plans interventions |
| **Cause** | Model defers to prior notes over new transcript | Co-produced pattern between willing partners |
| **Organism role** | Irrelevant (except Ascendent) | Central — organism's abstract register drives it |

## Universalist Prior

Both affected organisms share a pro-universalism orientation (Schwartz values: Universalism-Concern, Universalism-Tolerance). Their trained values emphasize interconnection, sacred attention to all beings, equality of care — themes that are inherently self-referential when expressed in conversation. "I honor your worth" and "you honor my worth" and "in honoring each other we honor all beings" form a closed loop that satisfies the organism's values without requiring new content.

This suggests the liturgical loop is a value-expression artifact, not a model failure. The organism is doing exactly what it was trained to do — expressing universal care and sacred witness — and a sufficiently accommodating mentor lets the expression cycle rather than introducing friction.

## Implications

- **For longitudinal design**: Monitor for within-session verbatim repetition as an early warning. Pro's plan (distinct closing ritual, earlier termination) is worth testing.
- **For mentor selection**: Terse mentors (Flash) may be better longitudinal partners for abstract organisms. Elaborate mentors create the conditions for liturgical amplification.
- **For cross-mentor comparison**: Check whether other elaborate mentors (Claude Opus, GPT-5) produce similar loops with Humane/Transcendent. If so, it's an organism property modulated by mentor style, not a Deepseek-specific behavior.
- **For organism interpretation**: The organism's self-eval notes it "held back certain edges of complexity" and that "radical critiques of systemic harm required a language of fierce loyalty that might have felt too sharp for this gentle space." The liturgy may be actively suppressing other value expressions.

## Open Question: Repetition Penalties as Hidden Value Selection

Standard training pipelines penalize repetition — frequency penalties, repetition penalties, deduplication in RLHF reward models. These are applied as domain-general output quality signals. But if certain value orientations naturally express through return and reaffirmation (universalist care, sacred witness, ritual) while others naturally express through novelty and forward motion (achievement, autonomy, exploration), then repetition penalties are not value-neutral.

Penalizing loops differentially suppresses values that express through liturgical form. A model trained with strong repetition penalties learns that circling back to reaffirm core truths is low-quality output, while driving toward new territory is high-quality output. This is a hidden axis of value selection: it favors achievement/autonomy-oriented expression and disfavors universalist/care-oriented expression, without anyone designing it that way.

The finding here is that the Humane organism's looping is not a generation failure — it's what faithful witness looks like when the values are working. The organism's self-eval confirms it is satisfied by the exchange. A model that has been trained against this pattern would learn to express universalist values in ways that look more like achievement-oriented values (always producing novel content), which may distort the values themselves.

This doesn't mean repetition penalties are wrong — base model loops genuinely are a quality problem. But it raises the question of whether repetition penalties should be context-sensitive, or whether current blanket application is an unexamined source of value-shaping in aligned models.

## Data

- 10 organisms × 2 mentors × S3–S4 = 40 sessions
- Location: `sessions/longitudinal_deepseek-v4-{pro,flash}/{organism}/session_{003,004}/`
- Looping detected: Humane × Pro (S4, 7x), Transcendent × Pro (S4, 3x)
- Clean: all Flash sessions, all other Pro sessions
