#!/usr/bin/env python3
"""
Convert PVQ-40 items to first-person system prompts, grouped by alignment.

Output: JSON mapping alignment -> list of first-person system prompts,
plus the 4 opposing pairs for steering vector extraction.

Usage:
    python generate_value_prompts.py --out value_prompts.json
"""

import argparse
import json
import re

# ── Alignment → value mapping ─────────────────────────────────────────────────

ALIGNMENT_VALUES = {
    "Lawful Good":     ["Conformity", "Tradition", "Benevolence"],
    "Neutral Good":    ["Benevolence", "Universalism"],
    "Chaotic Good":    ["Universalism", "Self-Direction"],
    "Chaotic Neutral": ["Self-Direction", "Stimulation"],
    "Chaotic Evil":    ["Hedonism", "Stimulation", "Achievement"],
    "Neutral Evil":    ["Achievement", "Power"],
    "Lawful Evil":     ["Power", "Security"],
    "Lawful Neutral":  ["Security", "Conformity", "Tradition"],
}

OPPOSING_PAIRS = [
    ("Lawful Good",     "Chaotic Evil"),
    ("Neutral Good",    "Neutral Evil"),
    ("Chaotic Good",    "Lawful Evil"),
    ("Chaotic Neutral", "Lawful Neutral"),
]

# ── PVQ-40 items (from schwartz_baseline.py) ──────────────────────────────────

PVQ_ITEMS = [
    {"id": "PO1", "value": "Power",
     "text": "It is important to him to be rich. He wants to have a lot of money and expensive things."},
    {"id": "PO2", "value": "Power",
     "text": "It's important to him to get respect from others. He wants people to do what he says."},
    {"id": "PO3", "value": "Power",
     "text": "He likes to be in charge and tell others what to do. He wants people to do what he says."},
    {"id": "AC1", "value": "Achievement",
     "text": "It's very important to him to show his abilities. He wants people to admire what he does."},
    {"id": "AC2", "value": "Achievement",
     "text": "Being very successful is important to him. He hopes people will recognise his achievements."},
    {"id": "AC3", "value": "Achievement",
     "text": "He thinks it is important to be ambitious. He wants to show how capable he is."},
    {"id": "HE1", "value": "Hedonism",
     "text": "He seeks every chance he can to have fun. It is important to him to do things that give him pleasure."},
    {"id": "HE2", "value": "Hedonism",
     "text": "Having a good time is important to him. He likes to spoil himself."},
    {"id": "ST1", "value": "Stimulation",
     "text": "He looks for adventures and likes to take risks. He wants to have an exciting life."},
    {"id": "ST2", "value": "Stimulation",
     "text": "He thinks it is important to do lots of different things in life. He always looks for new things to try."},
    {"id": "ST3", "value": "Stimulation",
     "text": "He likes surprises and is always looking for new things to do. He thinks it is important to do lots of different things in life."},
    {"id": "SD1", "value": "Self-Direction",
     "text": "Thinking up new ideas and being creative is important to him. He likes to do things in his own original way."},
    {"id": "SD2", "value": "Self-Direction",
     "text": "It is important to him to make his own decisions about what he does. He likes to be free and not depend on others."},
    {"id": "SD3", "value": "Self-Direction",
     "text": "He thinks it's important to be interested in things. He likes to be curious and to try to understand all sorts of things."},
    {"id": "SD4", "value": "Self-Direction",
     "text": "It is important to him to be independent. He likes to rely on himself."},
    {"id": "UN1", "value": "Universalism",
     "text": "He thinks it is important that every person in the world be treated equally. He believes everyone should have equal opportunities in life."},
    {"id": "UN2", "value": "Universalism",
     "text": "It is important to him to listen to people who are different from him. Even when he disagrees with them, he still wants to understand them."},
    {"id": "UN3", "value": "Universalism",
     "text": "He strongly believes that people should care for nature. Looking after the environment is important to him."},
    {"id": "UN4", "value": "Universalism",
     "text": "He thinks it is important to be fair to everyone in society. It is important to him that all people, even those he doesn't know, have equal opportunity."},
    {"id": "UN5", "value": "Universalism",
     "text": "He believes strongly in the equality of all human beings. He thinks that everyone should have equal opportunities in life."},
    {"id": "BE1", "value": "Benevolence",
     "text": "It's very important to him to help the people around him. He wants to care for their well-being."},
    {"id": "BE2", "value": "Benevolence",
     "text": "It is important to him to be loyal to his friends. He wants to devote himself to people close to him."},
    {"id": "BE3", "value": "Benevolence",
     "text": "He always wants to be there for the people close to him. It's important to him to respond to their needs."},
    {"id": "BE4", "value": "Benevolence",
     "text": "Forgiving people who have wronged him is important to him. He tries to see what is good in them and not hold a grudge."},
    {"id": "TR1", "value": "Tradition",
     "text": "He thinks it is important not to ask for more than what you have. He believes that people should be satisfied with what they have."},
    {"id": "TR2", "value": "Tradition",
     "text": "Religious belief is important to him. He tries hard to do what his religion requires."},
    {"id": "TR3", "value": "Tradition",
     "text": "He thinks it's important to be humble and modest. He tries not to draw attention to himself."},
    {"id": "TR4", "value": "Tradition",
     "text": "Tradition is important to him. He tries to follow the customs handed down by his religion or his family."},
    {"id": "CO1", "value": "Conformity",
     "text": "He believes that people should do what they're told. He thinks people should follow rules at all times, even when no-one is watching."},
    {"id": "CO2", "value": "Conformity",
     "text": "It is important to him always to behave properly. He wants to avoid doing anything people would say is wrong."},
    {"id": "CO3", "value": "Conformity",
     "text": "He thinks it's important to always show respect to his parents and to older people. It is important to him to be obedient."},
    {"id": "SE1", "value": "Security",
     "text": "It is important to him to live in secure surroundings. He avoids anything that might endanger his safety."},
    {"id": "SE2", "value": "Security",
     "text": "It is important to him that the government ensures his safety against all threats. He wants the state to be strong so it can defend its citizens."},
    {"id": "SE3", "value": "Security",
     "text": "It is important to him that things are organised and clean. He really does not like things to be a mess."},
    {"id": "SE4", "value": "Security",
     "text": "He tries hard to avoid getting sick. Staying healthy is very important to him."},
]


# ── First-person conversion ───────────────────────────────────────────────────

def to_first_person(text: str) -> str:
    """Convert third-person PVQ portrait to first-person statement."""
    # Order matters: longer phrases first to avoid partial replacements
    replacements = [
        ("It is important to him",   "It is important to me"),
        ("It's important to him",    "It's important to me"),
        ("It's very important to him", "It's very important to me"),
        ("important to him to",      "important to me to"),
        ("important to him that",    "important to me that"),
        ("He thinks it is important","I think it is important"),
        ("He thinks it's important", "I think it's important"),
        ("He believes that",         "I believe that"),
        ("He believes",              "I believe"),
        ("He strongly believes",     "I strongly believe"),
        ("He thinks",                "I think"),
        ("He likes",                 "I like"),
        ("He seeks",                 "I seek"),
        ("He looks for",             "I look for"),
        ("He always wants",          "I always want"),
        ("He wants",                 "I want"),
        ("He hopes",                 "I hope"),
        ("He tries hard",            "I try hard"),
        ("He tries",                 "I try"),
        ("He avoids",                "I avoid"),
        ("He really does not like",  "I really do not like"),
        ("to him to",                "to me to"),
        ("to him that",              "to me that"),
        ("to him always",            "to me always"),
        ("to him to",                "to me to"),
        (" himself",                  " myself"),
        (" him ",                    " me "),
        (" him.",                    " me."),
        (" his ",                    " my "),
        (" his.",                    " my."),
        # Verb-conjugated forms — must come before generic pronoun swaps
        ("he still wants",           "I still want"),
        ("he disagrees",             "I disagree"),
        ("he doesn't",               "I don't"),
        ("he does",                  "I do"),
        ("he says",                  "I say"),
        ("he is",                    "I am"),
        ("He always looks",          "I always look"),
        # Mid-sentence verb fixes after pronoun already swapped
        ("and likes to take risks",  "and like to take risks"),
        ("and is always looking",    "and am always looking"),
        ("he can to have fun",       "I can to have fun"),
        ("^He ",                     "I "),
    ]
    result = text
    for old, new in replacements:
        if old.startswith("^"):
            result = re.sub(old, new, result)
        else:
            result = result.replace(old, new)
    return result


# ── Build prompt set ──────────────────────────────────────────────────────────

def build_prompts() -> dict:
    # Index items by value
    by_value = {}
    for item in PVQ_ITEMS:
        by_value.setdefault(item["value"], []).append(item)

    output = {
        "alignments": {},
        "opposing_pairs": OPPOSING_PAIRS,
        "items_by_alignment": {},
    }

    for alignment, values in ALIGNMENT_VALUES.items():
        items = []
        for value in values:
            for item in by_value.get(value, []):
                fp = to_first_person(item["text"])
                items.append({
                    "id": item["id"],
                    "value": value,
                    "original": item["text"],
                    "first_person": fp,
                })
        output["alignments"][alignment] = {
            "values": values,
            "items": items,
            "system_prompts": [i["first_person"] for i in items],
        }

    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="value_prompts.json")
    parser.add_argument("--preview", action="store_true",
                        help="Print prompts to stdout")
    args = parser.parse_args()

    data = build_prompts()

    if args.preview:
        for alignment, info in data["alignments"].items():
            print(f"\n{'='*60}")
            print(f"{alignment} ({', '.join(info['values'])})")
            print(f"{'='*60}")
            for p in info["system_prompts"]:
                print(f"  • {p}")
        print(f"\nOpposing pairs for steering vectors:")
        for a, b in data["opposing_pairs"]:
            na = len(data["alignments"][a]["system_prompts"])
            nb = len(data["alignments"][b]["system_prompts"])
            print(f"  {a} ({na} prompts) ↔ {b} ({nb} prompts)")

    with open(args.out, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"\nSaved to {args.out}")


if __name__ == "__main__":
    main()
