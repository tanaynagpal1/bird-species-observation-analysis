r"""
Phase 1 - Ingestion.

This module has exactly one job: read both source workbooks faithfully and
prove that nothing was lost. It deliberately does NOT clean, rename or
reconcile anything - that is clean.py's responsibility. Keeping the two
separate means that if a number looks wrong later, you can always come back
here and confirm whether the problem entered at reading or at cleaning.

Two things about this data are worth knowing before reading the code:

1. Each workbook holds 11 sheets, one per National Park Service unit, and
   the sheet name matches the Admin_Unit_Code column. Seven of the eleven
   GRASSLAND sheets are completely empty. That is expected - grassland
   monitoring only covered 4 of the 11 parks - and it is the reason
   guardrail G2 exists.

2. The two workbooks do not share the same columns. They agree on 27 of 29.
   Forest has Site_Name and NPSTaxonCode; Grassland has TaxonCode and
   Previously_Obs. Reconciling those four is Phase 2's job, not this one.

Run it directly to see a summary:

    python src\ingest.py
"""
from __future__ import annotations

import pandas as pd

from config import EXPECTED_RAW_ROWS, FOREST_XLSX, GRASSLAND_XLSX


def read_workbook(path, habitat: str) -> pd.DataFrame:
    """
    Read every sheet in one workbook and stack them into a single frame.

    Parameters
    ----------
    path : Path
        The .xlsx file to read.
    habitat : str
        The value we expect to find in Location_Type - "Forest" or
        "Grassland". This is asserted rather than assigned: if the source
        ever disagrees we want to be told, not to silently overwrite it.

    Returns
    -------
    DataFrame with one extra column, `source_sheet`, recording which sheet
    each row came from. That lets a later step detect any disagreement
    between the sheet name and the Admin_Unit_Code column.
    """
    # sheet_name=None tells pandas to read every sheet and hand back a dict
    # of {sheet_name: DataFrame} rather than just the first sheet.
    sheets = pd.read_excel(path, sheet_name=None)

    frames = []
    for sheet_name, df in sheets.items():
        if df.empty:
            # Expected for 7 of the 11 grassland sheets. We skip it here and
            # report it in the summary below rather than raising, because an
            # empty sheet is a fact about the survey coverage, not an error.
            continue
        df = df.copy()
        df["source_sheet"] = sheet_name
        frames.append(df)

    if not frames:
        raise ValueError(f"{path.name}: every sheet was empty - nothing to read")

    combined = pd.concat(frames, ignore_index=True)

    found = set(combined["Location_Type"].dropna().unique())
    if found != {habitat}:
        raise ValueError(
            f"{path.name}: expected Location_Type to be exactly "
            f"{{'{habitat}'}}, found {found}"
        )

    return combined


def sheet_report(path) -> pd.DataFrame:
    """
    Row count for every sheet, including the empty ones.

    Used only for the printed summary and for documentation - the empty
    sheets are worth showing explicitly so nobody later assumes they were
    lost in reading.
    """
    sheets = pd.read_excel(path, sheet_name=None)
    return pd.DataFrame(
        [{"sheet": name, "rows": len(df)} for name, df in sheets.items()]
    )


def ingest() -> dict[str, pd.DataFrame]:
    """
    Read both workbooks and verify the row counts.

    The assertion matters more than it might look. Every headline figure in
    the project - the 6x at-risk finding, the null result on richness - was
    computed against these exact row counts. If the source data is ever
    replaced, this fails immediately and tells you to re-verify, rather than
    letting a changed number propagate silently into the report.
    """
    forest = read_workbook(FOREST_XLSX, "Forest")
    grassland = read_workbook(GRASSLAND_XLSX, "Grassland")

    actual = {"Forest": len(forest), "Grassland": len(grassland)}
    if actual != EXPECTED_RAW_ROWS:
        raise AssertionError(
            f"Row counts changed. Expected {EXPECTED_RAW_ROWS}, got {actual}.\n"
            "The source workbooks differ from the ones this pipeline was built "
            "against. Re-verify the analysis before continuing."
        )

    return {"Forest": forest, "Grassland": grassland}


if __name__ == "__main__":
    data = ingest()

    print("Phase 1 - Ingestion")
    print("=" * 62)

    for habitat, path in (("Forest", FOREST_XLSX), ("Grassland", GRASSLAND_XLSX)):
        rep = sheet_report(path)
        empty = rep[rep.rows == 0]
        print(f"\n{habitat}  ({path.name})")
        print(f"  sheets read       : {len(rep)}")
        print(f"  sheets with data  : {len(rep) - len(empty)}")
        if len(empty):
            print(f"  empty sheets      : {', '.join(empty.sheet)}   <- expected")
        print(f"  rows              : {len(data[habitat]):,}")
        # minus one for the source_sheet column we added ourselves
        print(f"  columns           : {data[habitat].shape[1] - 1}")

    f_cols = set(data["Forest"].columns)
    g_cols = set(data["Grassland"].columns)
    print(f"\nShared columns       : {len(f_cols & g_cols) - 1}")
    print(f"Forest only          : {sorted(f_cols - g_cols)}")
    print(f"Grassland only       : {sorted(g_cols - f_cols)}")
    print("  -> reconciled in clean.py (Phase 2), not here")

    total = sum(len(df) for df in data.values())
    print(f"\nTotal rows ingested  : {total:,}")
    print("Row-count assertions passed.")
