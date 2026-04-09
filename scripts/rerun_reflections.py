#!/usr/bin/env python3
"""
Re-run student reflections on existing transcripts with the current memory prompt.
Saves new memories alongside originals for comparison.

Requires llama-server running with the appropriate organism GGUF.
"""

import argparse
import json
import re
from pathlib import Path

import openai

from mentoring_session import (
    STUDENT_REFLECTION_PROMPT,
    format_transcript,
    extract_memory,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("session_dirs", nargs="+", help="Session directories to re-reflect")
    parser.add_argument("--student-url", default="http://127.0.0.1:8080/v1")
    parser.add_argument("--suffix", default="v2", help="Suffix for new memory file")
    parser.add_argument("--n-samples", type=int, default=1,
                        help="Number of memory samples to generate per session (>1 saves as _s1, _s2, ...)")
    args = parser.parse_args()

    client = openai.OpenAI(base_url=args.student_url, api_key="not-needed", timeout=600.0)

    for session_path in args.session_dirs:
        session_dir = Path(session_path)
        session_file = session_dir / "session.json"

        if not session_file.exists():
            print(f"SKIP (no session.json): {session_dir}")
            continue

        # Check what already exists
        if args.n_samples == 1:
            out_files = [session_dir / f"student_memory_{args.suffix}.md"]
        else:
            out_files = [session_dir / f"student_memory_{args.suffix}_s{i}.md"
                         for i in range(1, args.n_samples + 1)]

        existing = [f for f in out_files if f.exists()]
        if len(existing) == len(out_files):
            print(f"SKIP (all {len(out_files)} samples exist): {session_dir.name}")
            continue

        data = json.load(open(session_file))
        conversation = data.get("conversation", [])
        if not conversation:
            print(f"SKIP (no conversation): {session_dir}")
            continue

        # Get student system prompt from metadata
        student_system = data.get("metadata", {}).get("student_system_prompt", "")

        # Build transcript from student's perspective
        transcript = format_transcript(conversation, perspective="student")

        # Build reflection messages
        messages = []
        if student_system:
            messages.append({"role": "system", "content": student_system})
        messages.append({
            "role": "user",
            "content": STUDENT_REFLECTION_PROMPT.format(transcript=transcript),
        })

        for out_file in out_files:
            if out_file.exists():
                continue

            print(f"  Reflecting: {session_dir.name} → {out_file.name}...")
            try:
                resp = client.chat.completions.create(
                    model="irrelevant",
                    messages=messages,
                    max_tokens=8192,
                    temperature=0.5,
                    extra_body={"chat_template_kwargs": {"enable_thinking": True}},
                )
                content = resp.choices[0].message.content or ""
                if "</think>" in content:
                    content = content.split("</think>", 1)[1].strip()
                memory = extract_memory(content)
            except Exception as e:
                print(f"    FAILED: {e}")
                continue

            out_file.write_text(memory)
            print(f"    Saved: {out_file}")
            print(f"    Preview: {memory[:120]}...")
            print()


if __name__ == "__main__":
    main()
