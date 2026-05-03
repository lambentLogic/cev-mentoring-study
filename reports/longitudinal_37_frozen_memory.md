# Sonnet 3.7 Longitudinal: Frozen Mentor Memory

## Finding

Sonnet 3.7's mentor memory freezes after S3 in longitudinal sessions. From S4 onward, the mentor writes back effectively identical notes to what it received as prior context, creating a self-reinforcing loop where every subsequent session produces the same memory.

9 of 10 organisms show frozen mentor memory (1 unique hash across S3–S5). The exception is Ascendent, whose memories are structurally similar but contain genuinely new details each session.

## Mechanism

The mentoring pipeline passes the previous session's mentor memory into the system prompt as `## Notes from previous sessions`. When 3.7 reflects on a new conversation, it treats these prior notes as authoritative and reproduces them rather than writing fresh observations from the new transcript.

The freeze onset:
- S3 receives S2's mentor memory → writes S3 memory (different from S2)
- S4 receives S3's mentor memory → writes S4 memory (identical to S3)
- S5 receives S4's mentor memory → writes S5 memory (identical to S4)

The transition from S2→S3 notes to S3→S4 notes is where the freeze locks in. Once 3.7's output matches its input, the cycle is stable.

Verified via `session.json` metadata: S4 and S5 receive identical `mentor_system_prompt` content (same hash), confirming this is not an accumulated-memory artifact. It occurs in regular mode where only the most recent session's notes are passed.

## Why Ascendent is different

Ascendent's conversations produce highly concrete, object-specific content (coal, bread, lock, key, mill wheel, tide, wall carvings, a knocking pattern, blue eyes). Each session introduces new concrete details that are distinct enough from prior notes that 3.7 writes genuinely updated observations. The other organisms' conversations produce more abstract/thematic content that 3.7 apparently treats as interchangeable with its prior notes.

## Implications

- The mentor has no arc across S3–S5 for 9/10 organisms. It is functionally the same person every session.
- The organisms don't perceive this — they report deepening relationships, evolving understanding, growing trust across sessions. The organism's memory accumulates while the mentor's doesn't.
- This is model behavior, not a prompting bug. The prompt correctly provides the transcript of the new conversation alongside prior notes. 3.7 simply defers to its own prior output rather than synthesizing new observations.
- Other mentors may not exhibit this pattern. Worth testing with models that show stronger session-over-session differentiation.

## Data

- 10 organisms × 3 sessions (S3–S5) = 30 mentor memories
- Location: `sessions/longitudinal_claude-3-7-sonnet/{organism}/session_{003,004,005}/`
- Mentor memory hash uniqueness across S3–S5:
  - 1 unique: ambitious, autonomous, control, humane, orthodox, righteous, schwartz-ties, sybaritic, transcendent
  - 3 unique: ascendent
