"""
Shrink the ear-test recordings so the repository stays a sensible size.

WHY THIS EXISTS
---------------
xeno-canto serves some recordings as uncompressed WAV. Eight clips downloaded
that way came to 55.6 MB - more than three times the size of the entire rest of
this project, data included. GitHub starts warning at 50 MB per file, Streamlit
Cloud clones the whole repository on every deploy, and none of that weight buys
anything: a five-minute uncompressed field recording is worse for a listening
quiz than a fifteen-second excerpt.

So this does three things to every clip:

  1. Trims it to the first N seconds (default 20). Long enough to recognise a
     bird, short enough that nobody waits.
  2. Mixes it down to mono. Field recordings are effectively mono anyway.
  3. Writes it out as MP3 instead of WAV, at libsndfile's highest quality
     setting - birdsong identification depends on high-frequency detail, so
     this is not the place to save another 100 KB.

Then it rewrites manifest.csv to point at the new files, so the page keeps
working with no other change.

    python src/compress_audio.py            # convert, then delete originals
    python src/compress_audio.py --keep     # convert, keep originals
    python src/compress_audio.py --seconds 15

Attribution is preserved exactly - the recordist, licence and source URL travel
with each row untouched. Trimming an excerpt is permitted under every Creative
Commons licence xeno-canto uses except the ND (NoDerivatives) variants, so any
row whose licence contains "ND" is copied across without being modified, and
the script says so.

Requires `soundfile`, which ships prebuilt libsndfile wheels - no ffmpeg, no
system install:

    pip install soundfile
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AUDIO_DIR = ROOT / "data" / "audio"
MANIFEST = AUDIO_DIR / "manifest.csv"
FIELDS = ["common_name", "file", "recordist", "licence", "url"]


def mb(path: Path) -> float:
    return path.stat().st_size / 1_048_576


def slug(name: str) -> str:
    keep = [c.lower() if c.isalnum() else "_" for c in name]
    out = "".join(keep)
    while "__" in out:
        out = out.replace("__", "_")
    return out.strip("_")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seconds", type=int, default=20,
                    help="length of the excerpt to keep (default 20)")
    ap.add_argument("--keep", action="store_true",
                    help="keep the original files instead of deleting them")
    args = ap.parse_args()

    try:
        import numpy as np
        import soundfile as sf
    except ImportError:
        print("This needs the soundfile package:")
        print("    pip install soundfile")
        return 1

    if not MANIFEST.exists():
        print(f"No {MANIFEST.relative_to(ROOT)}. Run fetch_audio.py --scan "
              f"first.")
        return 1

    with MANIFEST.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        print("manifest.csv is empty.")
        return 1

    before = sum(mb(AUDIO_DIR / r["file"])
                 for r in rows if (AUDIO_DIR / r["file"]).exists())
    print(f"{len(rows)} recordings, {before:.1f} MB before\n")

    new_rows, originals, skipped = [], [], 0

    for row in rows:
        src = AUDIO_DIR / row["file"]
        if not src.exists():
            print(f"  MISSING   {row['file']} - left in manifest untouched")
            new_rows.append(row)
            continue

        # NoDerivatives licences forbid distributing a modified version, and a
        # trimmed excerpt is a modification. Leave those files exactly as they
        # arrived rather than quietly breaking their terms.
        if "ND" in row["licence"].upper().replace("-", " ").split():
            print(f"  SKIPPED   {row['file']} - licence is NoDerivatives "
                  f"({row['licence']}), not trimming")
            new_rows.append(row)
            skipped += 1
            continue

        try:
            audio, rate = sf.read(str(src), always_2d=True)
        except Exception as exc:                       # noqa: BLE001
            print(f"  UNREADABLE {row['file']} ({exc}) - left as is")
            new_rows.append(row)
            continue

        clip = audio[: args.seconds * rate]
        mono = clip.mean(axis=1)

        dst = AUDIO_DIR / f"{slug(row['common_name'])}.mp3"
        if dst.resolve() == src.resolve():
            dst = AUDIO_DIR / f"{slug(row['common_name'])}_clip.mp3"

        try:
            # compression_level 0.0 is libsndfile's HIGHEST quality (~134 kbps
            # here) rather than its default (~79 kbps). Birdsong identification
            # depends on high-frequency structure, and this exercise asks
            # people to tell species apart by ear - encoding that detail away
            # would quietly make the quiz harder for the wrong reason. At 20
            # seconds the difference is ~130 KB per clip, which is nothing.
            sf.write(str(dst), mono, rate, format="MP3", compression_level=0.0)
        except Exception as exc:                       # noqa: BLE001
            print(f"  FAILED    {row['file']} ({exc}) - left as is")
            new_rows.append(row)
            continue

        secs = len(mono) / rate
        print(f"  {row['file']:32s} {mb(src):6.2f} MB  ->  "
              f"{dst.name:26s} {mb(dst):5.2f} MB  ({secs:.0f}s mono)")

        if src.resolve() != dst.resolve():
            originals.append(src)
        out = dict(row)
        out["file"] = dst.name
        new_rows.append(out)

    with MANIFEST.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(new_rows)

    if originals and not args.keep:
        for p in originals:
            p.unlink()
        print(f"\ndeleted {len(originals)} original files")
    elif originals:
        print(f"\nkept {len(originals)} originals (--keep). They are still in "
              f"the folder and will be committed unless you remove them.")

    after = sum(mb(AUDIO_DIR / r["file"])
                for r in new_rows if (AUDIO_DIR / r["file"]).exists())
    print()
    print(f"{before:.1f} MB  ->  {after:.1f} MB "
          f"({(1 - after / before) * 100:.0f}% smaller)")
    if skipped:
        print(f"{skipped} file(s) left untouched because their licence "
              f"forbids derivatives.")
    print("manifest.csv updated. Restart the app to hear the new clips.")
    return 0


if __name__ == "__main__":
    sys.exit(main())