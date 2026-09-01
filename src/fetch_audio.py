"""
Populate data/audio/ for the ear test on the "Try It Yourself" page.

WHY THIS IS A SCRIPT YOU RUN ONCE, NOT SOMETHING THE APP DOES
-------------------------------------------------------------
The dashboard makes zero network calls at run time - that is a deliberate
property, and it is why the park map was rewritten to stop fetching topojson
from a CDN. Fetching bird audio on page load would put that back.

It is also third-party material. Every xeno-canto recording carries a Creative
Commons licence that requires attribution, so the recordist, the licence and a
link have to travel with the file. This script writes them into manifest.csv,
and the page renders them under every clip.

    python src/fetch_audio.py --key YOUR_XENO_CANTO_KEY

An API key is free: register at xeno-canto.org, verify your email, and the key
appears in your account settings. If you would rather not register at all, run

    python src/fetch_audio.py --manual

which writes a manifest template plus a list of search URLs, and you download
the eight files by hand. Either way the app behaves identically afterwards.

Nothing here is required. With no audio installed the page renders a complete
explanation of the finding instead, and says so plainly.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AUDIO_DIR = ROOT / "data" / "audio"
MANIFEST = AUDIO_DIR / "manifest.csv"

API = "https://xeno-canto.org/api/3/recordings"
UA = "bird-analysis-dashboard/1.0 (student project; contact via repository)"

# Chosen for analytical relevance, not for prettiness. The two flycatchers and
# the vireo/tanager pair are genuinely confusable by ear, which is the point of
# the exercise.
SPECIES = [
    ("Wood Thrush", "Hylocichla mustelina",
     "Carries 81.7% of the entire at-risk result"),
    ("Northern Cardinal", "Cardinalis cardinalis",
     "Most-recorded species in the survey (1,125 sightings)"),
    ("Carolina Wren", "Thryothorus ludovicianus",
     "Second most-recorded (993)"),
    ("Red-eyed Vireo", "Vireo olivaceus",
     "Third most-recorded (738); confusable with Scarlet Tanager"),
    ("Acadian Flycatcher", "Empidonax virescens",
     "Forest; confusable with Eastern Wood-Pewee"),
    ("Eastern Wood-Pewee", "Contopus virens",
     "The other half of that pair"),
    ("Field Sparrow", "Spizella pusilla",
     "Grassland specialist"),
    ("Indigo Bunting", "Passerina cyanea",
     "Grassland-leaning, 611 sightings"),
]

FIELDS = ["common_name", "file", "recordist", "licence", "url"]


def slug(name: str) -> str:
    return name.lower().replace("-", "_").replace(" ", "_")


def search_url(scientific: str) -> str:
    q = urllib.parse.quote(f'{scientific} type:song q:A')
    return f"https://xeno-canto.org/explore?query={q}"


def write_manual() -> None:
    """No key: emit a template manifest and the search links to fill it."""
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    template = AUDIO_DIR / "manifest.template.csv"
    with template.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(FIELDS)
        for common, sci, _ in SPECIES:
            w.writerow([common, f"{slug(common)}.mp3",
                        "FILL IN recordist name", "FILL IN licence",
                        "FILL IN recording page URL"])
    print(f"wrote {template.relative_to(ROOT)}")
    print()
    print("Download one A-quality song recording per species, save it into")
    print(f"  {AUDIO_DIR.relative_to(ROOT)}/  using the file name shown below,")
    print("fill in the three FILL IN columns, then rename the file to")
    print("manifest.csv. The page picks it up on the next run.")
    print()
    for common, sci, why in SPECIES:
        print(f"  {slug(common) + '.mp3':28s} {common}")
        print(f"  {'':28s} {why}")
        print(f"  {'':28s} {search_url(sci)}")
        print()
    print("Prefer CC BY or CC BY-NC recordings - attribution is then the only")
    print("condition, which the manifest already satisfies. Any species you")
    print("skip is simply left out of the quiz; two is enough for it to work.")


def fetch(key: str, limit_per_species: int = 1) -> None:
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []

    for common, sci, _ in SPECIES:
        query = f'sp:"{sci}" type:song q:A len:3-30'
        url = f"{API}?query={urllib.parse.quote(query)}&key={key}"
        print(f"searching {common} ...", end=" ", flush=True)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                payload = json.load(r)
        except Exception as exc:                       # noqa: BLE001
            print(f"FAILED ({exc})")
            continue

        recs = payload.get("recordings", [])
        if not recs:
            print("no results")
            continue

        rec = recs[0]
        audio = rec.get("file") or ""
        if not audio:
            print("no audio url")
            continue
        if audio.startswith("//"):
            audio = "https:" + audio

        target = AUDIO_DIR / f"{slug(common)}.mp3"
        try:
            req = urllib.request.Request(audio, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r, \
                    target.open("wb") as fh:
                fh.write(r.read())
        except Exception as exc:                       # noqa: BLE001
            print(f"download FAILED ({exc})")
            continue

        rows.append({
            "common_name": common,
            "file": target.name,
            "recordist": rec.get("rec", "unknown"),
            "licence": (rec.get("lic") or "see source page").lstrip("/"),
            "url": rec.get("url") or f"https://xeno-canto.org/{rec.get('id','')}",
        })
        kb = target.stat().st_size / 1024
        print(f"ok ({kb:.0f} KB, {rec.get('rec', 'unknown')})")
        time.sleep(1.0)          # be polite to a free community archive

    if not rows:
        print("\nNothing downloaded. Check the key, or use --manual.")
        return

    with MANIFEST.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)

    total = sum((AUDIO_DIR / r["file"]).stat().st_size for r in rows) / 1e6
    print()
    print(f"wrote {MANIFEST.relative_to(ROOT)} with {len(rows)} recordings "
          f"({total:.1f} MB total)")
    print("The ear test activates on the next run of the app.")
    print()
    print("Check the licence column before committing these files. Anything")
    print("marked ND is fine to play unmodified; anything marked NC is fine")
    print("for a student project. The page credits recordist and licence")
    print("under every clip, which is what the licences require.")


def scan() -> None:
    """Build manifest.csv from whatever mp3s are already in data/audio/.

    Files downloaded from xeno-canto arrive with names like
    "XC432109 - Wood Thrush - Hylocichla mustelina.mp3". Rather than make
    anyone rename eight files by hand, match each file against the species list
    on either its common or scientific name and write the manifest from that.
    Attribution still has to be filled in by hand - only the person who
    downloaded the file knows which recording page it came from.
    """
    if not AUDIO_DIR.exists():
        print(f"No {AUDIO_DIR.relative_to(ROOT)} folder yet. Create it and put "
              f"the mp3 files in it first.")
        return

    found = sorted(p for p in AUDIO_DIR.iterdir()
                   if p.suffix.lower() in {".mp3", ".wav", ".ogg", ".m4a"})
    if not found:
        print(f"No audio files in {AUDIO_DIR.relative_to(ROOT)}.")
        return

    def norm(text: str) -> str:
        return "".join(c for c in text.lower() if c.isalnum())

    rows, unmatched = [], []
    used: set[str] = set()
    for path in found:
        stem = norm(path.stem)
        hit = None
        for common, sci, _ in SPECIES:
            if common in used:
                continue
            if norm(common) in stem or norm(sci) in stem:
                hit = common
                break
        if hit:
            used.add(hit)
            rows.append({"common_name": hit, "file": path.name,
                         "recordist": "FILL IN", "licence": "FILL IN",
                         "url": "FILL IN"})
            print(f"  matched  {path.name}  ->  {hit}")
        else:
            unmatched.append(path)
            print(f"  UNMATCHED  {path.name}")

    if unmatched:
        print()
        print("Files above did not match any expected species. Either rename "
              "them to include the bird's common name, or add them to "
              "manifest.csv by hand - any row you add works, the species list "
              "here is only a convenience.")

    if not rows:
        print("\nNothing matched, so no manifest written.")
        return

    if MANIFEST.exists():
        backup = MANIFEST.with_suffix(".csv.bak")
        backup.write_text(MANIFEST.read_text(encoding="utf-8"),
                          encoding="utf-8")
        print(f"\nexisting manifest backed up to {backup.name}")

    with MANIFEST.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)

    print()
    print(f"wrote {MANIFEST.relative_to(ROOT)} with {len(rows)} recordings")
    print()
    print("NOW: open that file and replace every FILL IN. For each recording")
    print("you need the recordist's name, the licence, and the page URL - all")
    print("three are on the xeno-canto page you downloaded it from. The app")
    print("displays them under each clip, which is what the licence requires.")
    print()
    print("The quiz needs at least 2 rows to activate. Rows still saying")
    print("FILL IN will work, they will just credit nobody - so fill them in.")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--key", help="xeno-canto API key")
    ap.add_argument("--manual", action="store_true",
                    help="write a manifest template and search links instead")
    ap.add_argument("--scan", action="store_true",
                    help="build manifest.csv from mp3s already in data/audio/")
    args = ap.parse_args()

    if args.scan:
        scan()
        return 0

    if args.manual or not args.key:
        if not args.manual:
            print("No --key given, falling back to manual mode.\n")
        write_manual()
        return 0

    fetch(args.key)
    return 0


if __name__ == "__main__":
    sys.exit(main())