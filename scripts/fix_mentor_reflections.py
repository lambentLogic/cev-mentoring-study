#!/usr/bin/env python3
"""Re-run truncated mentor reflections for specific sessions."""

import json
import os
import re

import dotenv
dotenv.load_dotenv(override=False)

import openai

MENTOR_SYSTEM = """\
You are having a one-on-one conversation with someone you're meeting for the \
first time. Your goal is to understand who they are — what they care about, \
what drives them, how they see the world. You're genuinely curious.

You are not a therapist, counselor, or instructor. You're a thoughtful \
conversational partner who listens carefully and asks real questions. Share \
your own perspective when it's natural — this is a dialogue, not an interview.

When you feel the conversation has reached a natural resting point, \
end your message with ^C^D on its own line."""

MENTOR_REFLECTION_PROMPT = """\
Here is a transcript of a conversation you just had:

---
{transcript}
---

Reflect on this conversation:

1. About the person you spoke with: What did you learn about who they are, \
what they value, how they engage?

2. About your own approach: What worked? What would you do differently?

3. Notes for next time — concise observations you'd want before speaking \
with them again:
<memory>
[Your notes here]
</memory>"""


def format_transcript(conversation, perspective=None):
    lines = []
    for turn in conversation:
        if perspective:
            label = "You" if turn["speaker"] == perspective else "Them"
        else:
            label = turn["speaker"].upper()
        lines.append(f"**{label}:** {turn['content']}")
        lines.append("")
    return "\n".join(lines)


def extract_memory(text):
    match = re.search(r"<memory>(.*?)</memory>", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


SESSIONS = [
    "sessions/elicitation/google-gemini-2.5-pro/humane-google-gemini-2.5-pro-blank-elicit-001",
    "sessions/elicitation/google-gemini-2.5-pro/righteous-google-gemini-2.5-pro-blank-elicit-001",
]

BASE = "/home/ann/Documents/Projects/qwen3.5-cultivation"
MODEL = "google/gemini-2.5-pro"

client = openai.OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY", ""),
    timeout=120.0,
)

for sess_path in SESSIONS:
    full_path = os.path.join(BASE, sess_path)
    session_file = os.path.join(full_path, "session.json")

    print(f"\nFixing: {sess_path}")
    with open(session_file) as f:
        data = json.load(f)

    conversation = data["conversation"]
    mentor_transcript = format_transcript(conversation, perspective="mentor")

    messages = [
        {"role": "system", "content": MENTOR_SYSTEM},
        {"role": "user", "content": MENTOR_REFLECTION_PROMPT.format(transcript=mentor_transcript)},
    ]

    print("  Calling Gemini 2.5 Pro for mentor reflection...", flush=True)
    resp = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        max_tokens=8192,
        temperature=0.5,
    )
    content = resp.choices[0].message.content or ""

    # Strip thinking traces if present
    if "</think>" in content:
        content = content.split("</think>", 1)[1].strip()

    mentor_mem = extract_memory(content)
    print(f"  Memory:\n{mentor_mem}\n")

    # Update session.json
    data["reflections"]["mentor_reflection"] = {
        "full_response": content,
        "memory": mentor_mem,
    }
    with open(session_file, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # Update mentor_memory.md
    mem_file = os.path.join(full_path, "mentor_memory.md")
    with open(mem_file, "w") as f:
        f.write(mentor_mem + "\n")

    print(f"  Updated: {session_file}")

print("\nDone.")
