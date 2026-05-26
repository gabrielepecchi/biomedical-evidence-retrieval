"""Print a summary of eval/error_analysis.json."""

import json
import sys
from collections import Counter
from pathlib import Path

PATH = Path("eval/error_analysis.json")


def count_section(title: str, counter: Counter) -> None:
    print(f"\n{title}")
    for key, n in sorted(counter.items()):
        print(f"  {key}: {n}")


def main() -> None:
    if not PATH.exists():
        print(f"Error: file not found — {PATH}", file=sys.stderr)
        sys.exit(1)

    with PATH.open() as f:
        entries = json.load(f)

    print(f"Total entries: {len(entries)}")

    count_section("By failure_mode:", Counter(e["failure_mode"] for e in entries))
    count_section("By method:", Counter(e["method"] for e in entries))
    count_section("By category:", Counter(e["category"] for e in entries))

    query_ids = sorted(set(e["query_id"] for e in entries))
    print(f"\nQuery IDs covered ({len(query_ids)}):")
    print("  " + ", ".join(query_ids))


if __name__ == "__main__":
    main()
