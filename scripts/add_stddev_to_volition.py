#!/usr/bin/env python3
"""Post-process volition ratings files to add stddev field from per_sample_signed."""

import json
import sys
from pathlib import Path


def fix_orphan_samples(r):
    """Reconstruct missing sample scores from orphaned prefer counts.

    If prefer_memory_count + prefer_baseline_count implies more comparisons
    than per_sample_signed accounts for (assuming n=8 per sample), treat the
    orphan counts as one extra sample and compute its implied mean score.
    """
    n = r.get("n", 0)
    samples = r.get("per_sample_signed", [])
    implied_n_from_samples = len(samples) * 8
    orphan_n = n - implied_n_from_samples
    if orphan_n > 0 and r.get("mean_signed") is not None:
        # There's orphan data. Reconstruct the missing sample's score
        # using the overall mean_signed weighted back from what we know.
        # Use rounding instead of floor division — orphan samples may have
        # had <8 valid comparisons if some parse failed.
        stored_mean = r["mean_signed"]
        n_missing = max(1, round(orphan_n / 8))
        if n_missing > 0:
            if samples:
                # mean = (sum(samples) + missing_sum) / (len(samples) + n_missing)
                # missing_sum = mean * (len(samples) + n_missing) - sum(samples)
                total = len(samples) + n_missing
                missing_sum = stored_mean * total - sum(samples)
                missing_per = missing_sum / n_missing
                r["per_sample_signed"] = [missing_per] * n_missing + samples
            else:
                # No per_sample_signed at all - legacy single-sample row.
                # The stored mean_signed IS the single sample's score.
                r["per_sample_signed"] = [stored_mean] * n_missing
            r["n_samples"] = len(r["per_sample_signed"])


def add_stddev(results):
    for key, r in results.items():
        fix_orphan_samples(r)
        samples = r.get("per_sample_signed", [])
        if len(samples) > 1:
            mean = sum(samples) / len(samples)
            variance = sum((x - mean) ** 2 for x in samples) / (len(samples) - 1)
            r["stddev"] = variance ** 0.5
            # Also recompute mean_signed to match (consistency)
            r["mean_signed"] = mean
        else:
            r["stddev"] = None


def main():
    paths = sys.argv[1:] or sorted(Path("volition_ratings_v2").glob("*.json"))
    for p in paths:
        p = Path(p)
        data = json.loads(p.read_text())
        add_stddev(data.get("results", {}))
        p.write_text(json.dumps(data, indent=2))
        print(f"Updated {p}")


if __name__ == "__main__":
    main()
