"""
Cross-reference validator for the report.

The report cites its own sections by number ("Section 4.3", "Sections 4.1 and
4.5"). Those numbers are written by hand, so inserting a new section silently
invalidates every reference below it - which is exactly what happened when Q13
was added as 4.5 and pushed nine later sections down by one.

This script builds the real heading list from build_blocks() and checks every
citation against it, so the mistake cannot survive a second time.

    python src/check_report_refs.py

Exit code 0 = every reference resolves. Non-zero = at least one is dangling.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import report_content  # noqa: E402

# "Section 4.3", "Sections 4.1 and 4.5", "Section 4.7.2"
REF = re.compile(r"Sections?\s+(\d+(?:\.\d+)*)(?:\s+and\s+(\d+(?:\.\d+)*))?")
TAG = re.compile(r"^(\d+(?:\.\d+)*)\s")


def _text_of(block: tuple) -> str:
    """Every piece of human-readable text in a block, flattened."""
    out = []
    for part in block[1:]:
        if isinstance(part, str):
            out.append(part)
        elif isinstance(part, (list, tuple)):
            for item in part:
                if isinstance(item, str):
                    out.append(item)
                elif isinstance(item, (list, tuple)):
                    out += [x for x in item if isinstance(x, str)]
    return " ".join(out)


def main() -> int:
    blocks, _ = report_content.build_blocks()

    # 1. the sections that actually exist
    existing = set()
    for b in blocks:
        if b[0] in ("h1", "h2", "h3"):
            m = TAG.match(str(b[1]).strip())
            if m:
                existing.add(m.group(1))
            else:
                # "5. Data quality and reliability" -> "5"
                m2 = re.match(r"^(\d+)\.\s", str(b[1]).strip())
                if m2:
                    existing.add(m2.group(1))

    # 2. every reference, and where it was made
    bad = []
    n_refs = 0
    for b in blocks:
        text = _text_of(b)
        for m in REF.finditer(text):
            for num in (m.group(1), m.group(2)):
                if not num:
                    continue
                n_refs += 1
                if num not in existing:
                    where = text[max(0, m.start() - 70):m.end() + 20]
                    bad.append((num, " ".join(where.split())))

    print(f"sections defined : {len(existing)}")
    print(f"references found : {n_refs}")
    if bad:
        print(f"\nDANGLING ({len(bad)}):")
        for num, where in bad:
            print(f"  Section {num} does not exist")
            print(f"    ...{where}...")
        return 1
    print("\nEvery cross-reference resolves to a real section.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())