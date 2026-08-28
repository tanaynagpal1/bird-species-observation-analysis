# Cleaning Log

Bird Species Observation Analysis

Generated automatically by `src/clean.py` on 28 August 2026 at 16:41.

Every decision below was investigated before being applied - the reasoning for each is recorded in the project blueprint. Decision numbers in brackets refer to that document.

## Source data

| File | Rows | Columns | Sheets with data |
| --- | --- | --- | --- |
| Forest | 8,546 | 29 | 11 |
| Grassland | 8,531 | 29 | 4 |

Seven of the eleven grassland sheets are empty. Grassland monitoring covered only 4 of the 11 parks, which is why habitat comparisons are restricted to those four (guardrail G2).



## Schema reconciliation

**Decision #2** - Renamed `NPSTaxonCode` to `TaxonCode`

The two files used different names for the same field. Verified at runtime: all 88 species present in both habitats carry identical codes. Renaming lets them merge into one column instead of two half-empty ones.

**Decision #3** - Dropped `Previously_Obs`

Grassland-only column holding a single value (False) across all rows (1 distinct value). Zero variance, so no analytical use, and no counterpart in the forest file.

**Decision #1** - Kept `Site_Name` as a nullable column

Forest-only field naming the survey site between park and plot (70 distinct sites). Grassland rows will hold a blank, which is accurate - grassland monitoring did not record this level. Dropping it would discard real information that no other column recovers.


## Data types

**Decision #9** - Cast grassland columns to their proper types

Grassland columns had all been read as the generic `object` type even though the underlying values were correct. Cast 2 to integer, 4 to float, 4 to boolean and `Date` to datetime so the combined dataset supports arithmetic, sorting and a clean SQL export.


Column types before and after:


| Type | Before | After |
| --- | --- | --- |
| Int64 | 0 | 2 |
| bool | 4 | 0 |
| boolean | 0 | 4 |
| datetime64[us] | 1 | 1 |
| float64 | 5 | 5 |
| int64 | 2 | 0 |
| object | 2 | 2 |
| str | 15 | 15 |


## Duplicate rows

**Decision #4** - Removed exact duplicate rows (grassland only)

Grassland: 8,531 rows to 6,826 - **1,705 removed (20.0%)**. Forest: 0 duplicates found, none removed.

These rows are identical across every column including the start time to the minute, so they cannot represent two different birds in the same interval. They sit adjacent in the source file and are spread evenly across all three observers but concentrated by park - consistent with an export fault rather than real repeated fieldwork. The most extreme case is a European Starling record at plot MONO-0054 on 2018-07-11, identical across all 29 columns, which appears **135 times**.


Species whose counts were most inflated by the duplication:


| Species | Before | After | Removed |
| --- | --- | --- | --- |
| European Starling | 516 | 81 | 435 |
| Cedar Waxwing | 302 | 62 | 240 |
| Barn Swallow | 266 | 130 | 136 |
| Red-winged Blackbird | 379 | 273 | 106 |
| Bobolink | 103 | 6 | 97 |

This matters for interpretation: European Starling appeared to be one of the most common grassland species before cleaning. After removing duplicates it is a minor one. Reporting on the uncleaned data would have described the wrong community.



## Column standardisation

**Decision #6** - Standardised blank `Sex` values to `Undetermined`

5,183 blank cells filled with the explicit label already used by the grassland file, so the same meaning is not represented two different ways.

Note for analysis: the forest data contains **no Female records at all**, so any sex-ratio analysis is restricted to grassland. Sex is never inferred from identification method or any other field.


Sex distribution after standardisation:


| Habitat | Female | Male | Undetermined |
| --- | --- | --- | --- |
| Forest | 0 | 59 | 8487 |
| Grassland | 126 | 3050 | 3650 |

**Decision #7** - Added `Distance_Display` (original `Distance` unchanged)

`Distance` is blank on exactly the 689 rows where `Flyover_Observed` is True - verified at runtime as a perfect one-to-one match. This is a structural not-applicable, not missing data: a bird flying overhead was never at a fixed point to measure to.

The original column keeps its blanks so the distinction stays visible in the data. `Distance_Display` labels those rows `Flyover (n/a)` so that 689 real sightings appear as their own category in distance charts rather than being silently dropped.

**Decision #5** - Kept `Sub_Unit_Code` unchanged

Blank on 95.3% of rows, but not randomly. It is populated only for NACE (684 rows), GWMP (38 rows) - administrative units that are themselves bundles of several separate parks. For a single-site park there is nothing to subdivide, so blank is the correct value.

The blank-versus-filled pattern is therefore information in its own right: it tells you which parks have internal sub-units. Dropping the column would discard that. Retained on the project manager's decision.

**Decision #8** - Left small scattered gaps in place

These are too few to affect any result, and `Scientific_Name` - the species key used throughout the analysis - has no missing values at all, so none of them block species-level work.

| Column | Missing rows | Pattern |
| --- | --- | --- |
| ID_Method | 2 | 2 species affected |
| AcceptedTSN | 28 | all belong to House Finch |
| TaxonCode | 2 | 2 species affected |


## Result

| Stage | Rows |
| --- | --- |
| Raw forest | 8,546 |
| Raw grassland | 8,531 |
| Raw total | 17,077 |
| Duplicates removed | -1,705 |
| **Cleaned total** | **15,372** |


Columns: 30 (27 shared, plus `Site_Name` forest-only and `Distance_Display` derived).

Species: 127 distinct. Parks: 11. Plots: 609.


