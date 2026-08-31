# Findings ledger

*Generated 2026-08-31 by `src/make_ledger.py` from `analysis.run_all()`. Do not edit by hand - re-run the script.*

Every number below is produced by the analysis pipeline, not typed in. Each entry records the figure, the test behind it, and - just as importantly - what it does **not** license anyone to say.

## 1. What the dataset is

- **15,372** individual sightings across **1,408** survey sessions
- **126** distinct species, **11** NPS units, 2018 breeding season (May-July)
- **4 of 11** parks were surveyed in *both* forest and grassland - **737 of 1,408 sessions (52.3%)** are therefore usable for a fair habitat comparison
- Median session length is 10 minutes in both habitats, so effort per session is comparable; visits per plot are 2.0 (forest) vs 2.96 (grassland)

### Survey effort by park

| Admin_Unit_Code | Forest | Grassland | total | both_habitats |
|---|---|---|---|---|
| ANTI | 26 | 252 | 278 | True |
| PRWI | 264 | 0 | 264 | False |
| MONO | 30 | 202 | 232 | True |
| CHOH | 180 | 0 | 180 | False |
| MANA | 47 | 131 | 178 | True |
| CATO | 89 | 0 | 89 | False |
| NACE | 58 | 0 | 58 | False |
| HAFE | 40 | 9 | 49 | True |
| GWMP | 40 | 0 | 40 | False |
| ROCR | 28 | 0 | 28 | False |
| WOTR | 12 | 0 | 12 | False |

**Why this table drives everything else.** Seven of eleven parks were surveyed in one habitat only. In those parks, "forest vs grassland" is really "park A vs park B". Every habitat comparison in this project is therefore restricted to the four shared parks.

## 2. The four guardrails

| ID | Rule | Why it exists |
|----|------|---------------|
| G1 | Compare per-session **rates**, never raw totals | Grassland ran ~4x more sessions than forest; raw counts measure effort |
| G2 | Habitat comparisons use the **4 shared parks** only | Otherwise habitat is confounded with park identity |
| G3 | Treat any group with **<30 sessions** as unreliable | Small samples produce large, meaningless swings |
| G4 | **Rarefy** before comparing species counts | More sampling finds more species even from an identical community |

## 3. Findings, question by question

### Q1 - At-risk species by habitat *(headline finding)*

- Forest sessions record at-risk birds at **3.65%** of sightings against **0.59%** in grassland - a **6.2x** difference
- Mann-Whitney p = 1.66e-18 -> **significant**
- Holds in **all 4 of 4** shared parks (`holds_in_all_parks = True`)

| Admin_Unit_Code | Forest | Grassland | forest_higher |
|---|---|---|---|
| ANTI | 2.7 | 0.42 | True |
| HAFE | 5.92 | 0 | True |
| MANA | 2.37 | 1.32 | True |
| MONO | 3.51 | 0.37 | True |

**Status: a real finding.** It survives G1, G2, and the per-park check that destroys the richness result below.

### Q1b - The same finding, stress-tested

- **309 of 378** at-risk sightings (**82%**) are Wood Thrush alone
- Remove it and the ratio falls from **6.2x** to **2.1x**
- The direction then holds in only **2 of 4** shared parks

| Admin_Unit_Code | Forest | Grassland | forest_higher |
|---|---|---|---|
| ANTI | 0 | 0.128 | False |
| HAFE | 0.998 | 0 | True |
| MANA | 1.304 | 1.047 | True |
| MONO | 0 | 0.093 | False |

**Status: the finding is real but narrower than it first appears.** The defensible claim is *"forest shelters Wood Thrush"*, not *"forest shelters at-risk birds"* as a class. All 8 watchlist species were recorded, but one carries the signal.

### Q2 - Species richness by habitat *(Simpson's paradox)*

| Comparison | Forest | Grassland | n (F / G) | p | Verdict |
|---|---|---|---|---|---|
| Pooled, all 11 parks | 8.61 | 9.15 | 814 / 594 | p = 4.50e-04 | looks **significant** |
| Within 4 shared parks | 9.1 | 9.15 | 143 / 594 | p = 0.6855 | not significant |

| Admin_Unit_Code | Forest | Grassland | forest_higher |
|---|---|---|---|
| ANTI | 10.65 | 9.98 | True |
| HAFE | 8.57 | 9.22 | False |
| MANA | 8.19 | 8.56 | False |
| MONO | 9.9 | 8.49 | True |

- Forest wins in **2 of 4** shared parks - a coin flip

**Status: not a finding.** The pooled difference is an artefact of which parks were surveyed how often. This is the clearest teaching case in the project and the reason G2 exists.

### Q3 - Hotspots: parks and plots

| Admin_Unit_Code | sessions_run | species_per_session | distinct_species | reliable |
|---|---|---|---|---|
| ANTI | 278 | 10.04 | 80 | True |
| CHOH | 180 | 9.95 | 80 | True |
| NACE | 58 | 9.52 | 66 | True |
| WOTR | 12 | 8.83 | 27 | False |
| HAFE | 49 | 8.69 | 54 | True |
| MONO | 232 | 8.67 | 99 | True |
| MANA | 178 | 8.46 | 80 | True |
| ROCR | 28 | 8.25 | 45 | False |
| PRWI | 264 | 7.85 | 54 | True |
| GWMP | 40 | 7.45 | 49 | True |
| CATO | 89 | 7.33 | 46 | True |

- Ranking by rate and by raw count **disagree** (`ranking_differs = True`)
- Raw species count vs survey effort: **rho = 0.772**, p = 0.0053 -> **significant**
- Species per session vs survey effort: **rho = 0.227**, p = 0.5015 -> not significant

**This pair is the numerical proof of G1.** A raw-count leaderboard is substantially a leaderboard of who got surveyed most; the effort-adjusted rate is independent of effort, which is the property a fair ranking needs.

- Plot level: **609** plots, mean **8.78** species/session, no plot visited more than **3** times
- The top-15 plot table is simply everything above **13.5** - the right tail of that distribution, not a set of special places

### Q3b - At-risk presence by park *(derived for the Where tab)*

| Admin_Unit_Code | sessions_run | at_risk_sessions | pct_sessions_with_at_risk | reliable |
|---|---|---|---|---|
| CATO | 89 | 51 | 57.3 | True |
| PRWI | 264 | 107 | 40.5 | True |
| ROCR | 28 | 11 | 39.3 | False |
| HAFE | 49 | 17 | 34.7 | True |
| NACE | 58 | 11 | 19 | True |
| CHOH | 180 | 33 | 18.3 | True |
| MANA | 178 | 28 | 15.7 | True |
| GWMP | 40 | 5 | 12.5 | True |
| ANTI | 278 | 22 | 7.9 | True |
| MONO | 232 | 18 | 7.8 | True |
| WOTR | 12 | 0 | 0 | False |

**The diversity ranking and the conservation ranking disagree.** Catoctin Mountain Park records an at-risk species in **57.3%** of sessions - the highest of any park - while ranking **#11 of 11** for species per session. "Best park" is a property of the question, not of the park.

### Q4 - Habitat specialists

- Of **48** well-sampled species: **17** grassland specialists, **0** forest specialists, **31** generalists

**Status: a real and striking asymmetry.** Zero forest specialists is not a sampling artefact - it survives the same shared-parks restriction as everything else. Forest birds here are generalists that also use grassland; grassland birds are loyal to grassland. This is the strongest ecological result in the project after Q1.

### Q5 - The at-risk roster

| Common_Name | Forest | Grassland | total | parks | pct_of_all_at_risk |
|---|---|---|---|---|---|
| Wood Thrush | 290 | 19 | 309 | 10 | 81.7 |
| Worm-eating Warbler | 31 | 0 | 31 | 5 | 8.2 |
| Prairie Warbler | 7 | 18 | 25 | 3 | 6.6 |
| Cerulean Warbler | 7 | 0 | 7 | 3 | 1.9 |
| Willow Flycatcher | 0 | 2 | 2 | 2 | 0.5 |
| Kentucky Warbler | 1 | 1 | 2 | 2 | 0.5 |
| Blue-winged Warbler | 1 | 0 | 1 | 1 | 0.3 |
| Red-headed Woodpecker | 1 | 0 | 1 | 1 | 0.3 |

- **Wood Thrush** alone is **81.7%** of all 378 at-risk sightings, across 8 watchlist species

### Q6 - Monthly richness *(descriptive only)*

| month_name | sessions_run Forest | sessions_run Grassland | species_per_session Forest | species_per_session Grassland |
|---|---|---|---|---|
| May | 212 | 198 | 9.22 | 9.85 |
| June | 391 | 194 | 8.4 | 9.15 |
| July | 211 | 202 | 8.37 | 8.45 |

- Forest effort imbalance across months: **1.85x**; grassland **1.04x**
- Visit number vs day of season: **rho = 0.890**, p < 1e-300
- Visit number vs richness: **rho = -0.096**, p = 2.94e-04
- Third visits happened in grassland only (198 sessions vs 0 in forest)

**Status: not a finding, and untestable.** Visit number and calendar date are nearly the same variable here, so a seasonal decline cannot be separated from a repeat-visit decline - and the late season is a different habitat mix as well. Three confounds on one axis.

### Q7 - Time of day *(the actionable finding)*

| time_band | sessions_run Forest | sessions_run Grassland | species_per_session Forest | species_per_session Grassland |
|---|---|---|---|---|
| Early (5-6am) | 270 | 179 | 8.65 | 9.7 |
| Mid (7-8am) | 406 | 254 | 8.66 | 9.32 |
| Late (9-10am) | 138 | 161 | 8.36 | 8.25 |

| Habitat | Early | Late | Change | Early-vs-late p | Whole-morning rho | Verdict |
|---|---|---|---|---|---|---|
| Grassland | 9.7 | 8.25 | 17.6% | p = 1.75e-05 | -0.166 (p = 4.62e-05) | **significant** |
| Forest | 8.65 | 8.36 | 3.6% | p = 0.5526 | -0.037 (p = 0.2938) | not significant |

- Session length is 10.0-10.2 minutes across all bands, so the effect is not early surveys running longer

| time_band | Forest | Grassland |
|---|---|---|
| Early (5-6am) | 34.1 | 5.6 |
| Late (9-10am) | 35.5 | 4.3 |
| Mid (7-8am) | 30.3 | 8.7 |

**Status: a real finding, in grassland only.** Confirmed two independent ways (endpoint test and whole-morning trend) and free of the confounds that sink Q6. Note the at-risk table above: the morning advantage is about *how many* species turn up, not *which* - there is no time-of-day effect on at-risk detection in either habitat.

### Q8 - Temperature and humidity

| temp_band | sessions_run | species_per_session | reliable |
|---|---|---|---|
| <15C | 50 | 9.1 | True |
| 15-20C | 314 | 9.61 | True |
| 20-25C | 658 | 8.91 | True |
| 25-30C | 313 | 8.04 | True |
| >30C | 73 | 7.97 | True |

| humidity_band | sessions_run | species_per_session | reliable |
|---|---|---|---|
| <40% | 12 | 11.5 | False |
| 40-60% | 170 | 8.67 | True |
| 60-80% | 704 | 8.68 | True |
| >80% | 522 | 9.03 | True |

| Correlation | rho | p | Verdict |
|---|---|---|---|
| Forest - Temperature | -0.212 | p = 1.02e-09 | **significant** |
| Forest - Humidity | 0.04 | p = 0.2507 | not significant |
| Grassland - Temperature | -0.191 | p = 2.78e-06 | **significant** |
| Grassland - Humidity | 0.174 | p = 2.02e-05 | **significant** |

- Richness peaks at **15-20C** and falls at **both** ends (`monotonic = False`)

**Status: real, but the correlation coefficient misdescribes it.** Spearman's rho is a monotonic statistic; applied to a hump-shaped relationship it returns a significant negative value that would tell a reader the coldest mornings are best. The curve says otherwise. Defensible claim: the warm end is worse. Not defensible: anything about cold mornings beating mild ones.

- The <40% humidity band shows the highest single figure on the dashboard (11.5 species/session) on 12 sessions - excluded by G3.

### Q9 - Sky, wind and disturbance

| Disturbance | sessions_run | species_per_session | reliable |
|---|---|---|---|
| Slight effect on count | 499 | 9.38 | True |
| No effect on count | 687 | 8.93 | True |
| Moderate effect on count | 160 | 7.94 | True |
| Serious effect on count | 62 | 5.65 | True |

- No disturbance **8.93** (n=687) vs serious disturbance **5.65** (n=62) - a **36.8%** loss, p = 2.52e-15 -> **significant**
- Anomaly preserved: "slight effect" scores *above* "no effect" (`slight_exceeds_none_anomaly = True`), on large samples in both categories. Cause unknown; reported as observed rather than explained away.

| Sky | sessions_run | species_per_session | reliable |
|---|---|---|---|
| Partly Cloudy | 542 | 9.2 | True |
| Cloudy/Overcast | 270 | 8.76 | True |
| Clear or Few Clouds | 496 | 8.75 | True |
| Fog | 61 | 7.72 | True |
| Mist/Drizzle | 39 | 7.03 | True |

| Wind | sessions_run | species_per_session | reliable |
|---|---|---|---|
| Light air movement (1-3 mph) smoke drifts | 665 | 9.22 | True |
| Calm (< 1 mph) smoke rises vertically | 398 | 8.57 | True |
| Light breeze (4-7 mph) wind felt on face | 307 | 8.47 | True |
| Gentle breeze (8-12 mph), leaves in motion | 38 | 7.82 | True |

**Status: disturbance is the largest environmental effect in the dataset and the only one with a management lever attached.** Sky and wind show mild, plausible patterns that were not significance-tested and are too small to act on.

### Q9b - Where disturbance happens *(derived for the Environment tab)*

| Admin_Unit_Code | sessions_run | pct_disrupted | reliable |
|---|---|---|---|
| GWMP | 40 | 57.5 | True |
| ROCR | 28 | 42.9 | False |
| MONO | 232 | 32.8 | True |
| CATO | 89 | 14.6 | True |
| NACE | 58 | 12.1 | True |
| ANTI | 278 | 11.5 | True |
| MANA | 178 | 10.7 | True |
| HAFE | 49 | 10.2 | True |
| CHOH | 180 | 9.4 | True |
| WOTR | 12 | 8.3 | False |
| PRWI | 264 | 6.4 | True |

- Among parks clearing the reliability floor, disturbance ranges from **57.5%** of sessions (George Washington Memorial Parkway) down to **6.4%** (Prince William Forest Park)

**Status: descriptive, and the most actionable table in the project.** The parks at the top are linear and urban sites - parkways and city parks with roads and footfall beside the plots. That reading is plausible but untested; the percentages are simply counts. Unlike weather, disturbance is a property of the site and the schedule, so it is the one environmental variable management can move.

**The slight-over-none anomaly replicates in both habitats:**

| Disturbance | Forest | Grassland |
|---|---|---|
| Moderate effect on count | 7.69 | 8.23 |
| No effect on count | 8.7 | 9.4 |
| Serious effect on count | 5.48 | 5.79 |
| Slight effect on count | 9.14 | 9.61 |

That it appears independently in forest and in grassland is why it is reported as observed rather than dismissed as noise.

### Q10 - Observer effects *(the methodological finding)*

| Observer | sessions_run | species_per_session | spread |
|---|---|---|---|
| Brian Swimelar | 461 | 7.27 | 2.31 |
| Kimberly Serno | 457 | 9.21 | 2.74 |
| Elizabeth Oswald | 490 | 9.96 | 3.26 |

| Pair | p |
|---|---|
| Brian Swimelar vs Elizabeth Oswald | p = 2.30e-40 |
| Brian Swimelar vs Kimberly Serno | p = 3.49e-27 |
| Elizabeth Oswald vs Kimberly Serno | p = 5.36e-04 |

- Spread between best and worst observer: **37.0%**
- Observers are balanced across habitats (`balanced = True`, max share deviation 0.0242)

| habitat | Brian Swimelar | Elizabeth Oswald | Kimberly Serno |
|---|---|---|---|
| Forest | 264 | 291 | 259 |
| Grassland | 197 | 199 | 198 |

**Status: the most important methodological result in the project.** The gap between observers is **2.69** species per session. The habitat gap this study set out to measure is **0.05** species per session. Who held the clipboard matters roughly **54x** more than which habitat was surveyed. Because the rota was balanced, this does not bias the habitat comparison - but any future study that lets observer assignment correlate with treatment will measure the observer, not the habitat.

### Q10b - Is the observer effect really the observer? *(derived)*

| Admin_Unit_Code | Brian Swimelar | Elizabeth Oswald | Kimberly Serno |
|---|---|---|---|
| ANTI | 8.3 | 11.56 | 10.24 |
| CATO | 6.18 | 8.45 | 8.11 |
| CHOH | 8.23 | 11.28 | 10.4 |
| MANA | 6.9 | 9.27 | 9.23 |
| MONO | 6.74 | 9.97 | 9.06 |
| PRWI | 6.84 | 8.51 | 8.08 |

- Across the **6** parks where all three surveyors ran 20+ sessions, the ranking is **identical in every park** - the same person is lowest everywhere and the same person is highest everywhere.

| Observer | Forest | Grassland |
|---|---|---|
| Brian Swimelar | 7.45 | 7.41 |
| Elizabeth Oswald | 10.4 | 10.4 |
| Kimberly Serno | 9.12 | 9.62 |

- Within the shared parks, all three surveyors independently reach the same conclusion about habitat: no meaningful richness gap. They disagree about the absolute numbers and agree about the finding.

**Status: the observer effect is the person, not their assignment - and it does not contaminate any conclusion.** The rank order is stable across parks, so it cannot be explained by who was sent where; the rota was balanced across habitats, so it cancels out of habitat comparisons; and the null habitat result replicates three times independently. The practical limit it does impose: absolute species-per-session figures carry a personal-calibration band of roughly +/-1.3 species, so they should not be quoted against another study's absolute numbers.

### Data integrity - protocol adherence and missingness

- **1,365 of 1,408** sessions (96.9%) ran exactly the 10-minute protocol; 43 ran longer, up to 70 minutes
- Median duration is identical in both habitats, so no rate in this project needs a duration correction

| index | missing | pct_of_rows |
|---|---|---|
| Sub_Unit_Code | 14650 | 95.3 |
| Site_Name | 6826 | 44.4 |
| Distance | 689 | 4.5 |
| AcceptedTSN | 28 | 0.2 |
| ID_Method | 2 | 0 |
| TaxonCode | 2 | 0 |

- **689** records have no `Distance`, and exactly those 689 records are flyovers - birds passing overhead with no distance to record. One-to-one with no exceptions: `True`

**Status: missingness is explained by the protocol, not by data loss.** Every column with gaps has a structural reason. Missingness that maps exactly onto a protocol rule is evidence of a well-run survey.

### Q11 - Exclusive species, raw vs rarefied

| Measure | Forest-only | Grassland-only | Ratio |
|---|---|---|---|
| Raw count | 7 | 36 | 5.1x |
| Rarefied (200 draws) | 15.5 | 19.7 | 1.3x |

- Grassland ran 594 sessions against forest's 143 - a 4.2x gap
- Seen exactly once: 2 forest-only and 15 grassland-only species

**Status: real but far smaller than the raw number suggests.** Most of the apparent gap is sampling effort. This is G4 doing its job.

### Q13 - Diversity beyond richness *(four measures, one answer)*

Richness counts species and ignores how evenly individuals are spread across them. Shannon weights rare species, Simpson weights common ones, and Pielou's evenness strips out richness altogether. If the habitat null result of Q2 were an artefact of picking the wrong measure, one of these would break it.

| Measure | Forest | Grassland | p | Significant |
|---|---|---|---|---|
| Richness | 9.105 | 9.146 | 0.685 | no |
| Shannon | 2.105 | 2.084 | 0.939 | no |
| Simpson Diversity | 0.863 | 0.854 | 0.823 | no |
| Evenness | 0.976 | 0.97 | 0.106 | no |

- Computed per session (G1) within the shared parks only (G2), on 143 forest and 594 grassland sessions
- Smallest p across all four measures: 0.11

**Status: the null result survives all four measures.** Not one comes close to significance. The habitats do not differ in how many species are present, nor in how evenly those species are distributed.

#### Q13b - Community similarity, rarefied

| Comparison | Jaccard (shared species) | Bray-Curtis (dissimilarity) | Pairs |
|---|---|---|---|
| Between habitats, same park | 0.536 | 0.499 | 4 |
| Within a habitat, different parks | 0.58 | 0.351 | 12 |

- Jaccard barely moves (-0.044): the two habitats draw on much the same species list
- Bray-Curtis is the gap that matters (+0.148): they weight that shared list differently
- Rarefying to equal session counts shrank the Bray-Curtis gap by **60.5%** (raw between-habitat was 0.726, rarefied 0.499) - G4 again

**Status: shared species pool, different weighting.** This is the precise statement the project can defend: habitat changes the mix, not the roster or the count. Most of the raw difference was effort.

### Q14 - Detection channel and interval *(mechanism for Q10)*

Q10 showed the three surveyors differ by 37.0% but could not say why. This splits their detections by how the bird was identified.

| Method | Detections | % of all |
|---|---|---|
| Singing | 9,621 | 62.6 |
| Calling | 3,941 | 25.6 |
| Visualization | 1,808 | 11.8 |

- **88.2%** of detections are auditory - the survey is in practice a hearing test
- Observer gap on auditory channels: **2.60** species per session
- Observer gap on the visual channel: **0.67**
- Brian Swimelar records fewest species overall but is **not** lowest on visual (Kimberly Serno is)

| Observer | Singing | Calling | Visualization |
|---|---|---|---|
| Brian Swimelar | 4.62 | 2.49 | 2.16 |
| Elizabeth Oswald | 6.46 | 3.03 | 2.42 |
| Kimberly Serno | 6.07 | 3.25 | 1.75 |

**Status: the observer effect is an ear-training effect.** A surveyor who was simply less thorough would be lowest on every channel. The rank order reversing between auditory and visual makes this a trainable recognition difference, which is what turns Q10 from a caveat into an actionable recommendation.

#### Q14b - Does the 10-minute count saturate?

| Interval | Detections | % | Cumulative % |
|---|---|---|---|
| 0-2.5 min | 7,755 | 50.4 | 50.4 |
| 2.5 - 5 min | 3,149 | 20.5 | 70.9 |
| 5 - 7.5 min | 2,386 | 15.5 | 86.5 |
| 7.5 - 10 min | 2,082 | 13.5 | 100.0 |

- 50.4% of detections arrive in the first 2.5 minutes; the last interval adds 13.5%
- First-interval share by surveyor ranges 45.3% to 54.3% - they accumulate at the same rate, so the gap is not attention span

**Status: adequate but not saturated.** The curve is flattening and has not gone flat. Ten minutes captures the regular users of a site; a longer count would still add occasional records.

### Every effect in the project, in the same units

| effect | gap (species/session) | significance-tested? |
|---|---|---|
| Disturbance (none -> serious) | 3.28 | yes |
| Observer (3 surveyors) | 2.69 | yes |
| Sky (best -> worst) | 2.17 | no |
| Temperature (best -> worst band) | 1.64 | yes |
| Time of day, grassland | 1.45 | yes |
| Wind (best -> worst) | 1.4 | no |
| Humidity (best -> worst) | 0.36 | no |
| Time of day, forest | 0.29 | tested, failed |
| Habitat (within shared parks) | 0.05 | tested, failed |

**The habitat difference this survey was designed to measure is the smallest effect in the table.** Disturbance is **66x** larger; the observer is **54x** larger. Each figure is the range between the best and worst category of that variable, after dropping categories under 30 sessions - a like-for-like comparison of magnitude, not a standardised effect size. A large untested gap (sky, wind) means "interesting, unverified", not "strong effect".

This is not a failure of the study. On species *richness*, habitat is swamped by survey conditions and by the surveyor. The habitat signal that does survive is about *which* species are present - at-risk birds and grassland specialists - not how many.

## 4. Insights, ranked by how well they are supported

| # | Insight | Evidence | Strength |
|---|---------|----------|----------|
| 1 | Forest shelters Wood Thrush specifically, not at-risk birds as a class | 3.65% vs 0.59%, p = 1.66e-18, holds in 4/4 parks; but 82% is one species and the effect halves to 2.1x without it | Strong, correctly narrowed |
| 2 | Who does the counting matters more than what is being counted | 37.0% observer spread, all pairs significant, vs a 0.05-species habitat gap | Strong |
| 3 | Grassland has specialists; forest has none | 17 vs 0 of 48 well-sampled species | Strong |
| 4 | Disturbance costs more species than any weather variable | 36.8% loss, p = 2.52e-15 | Strong |
| 5 | Survey grassland early | 17.6% gain, p = 1.75e-05, confirmed by two methods | Strong, grassland only |
| 6 | Habitat does not drive species richness | pooled p = 4.50e-04 collapses to p = 0.6855 within shared parks | Strong negative result |
| 7 | "Best park" depends on the question | Catoctin Mountain Park is #1 for at-risk presence and #11 of 11 for richness | Solid |

## 5. Recommendations

### For survey design

1. **Survey both habitats in every park.** Only 52.3% of sessions are usable for the study's central comparison. Pairing habitats within parks would roughly double the usable sample at no extra cost per session.
2. **Keep the observer rota balanced, and record it as a design feature.** The 37.0% observer spread is only harmless because assignment was balanced across habitats and parks. That was the single most important methodological choice in the study.
3. **Equalise visits per plot across habitats.** Forest plots got 2.0 visits on average, grassland 2.96 - and the third visit was grassland-only, which is what makes seasonal analysis impossible.
4. **Decouple visit number from calendar date.** Rotating the visit order across plots would let a genuine seasonal question be asked; at rho = 0.89 it currently cannot be.
5. **Aim for 30+ sessions per reporting unit.** Four parks fall below the reliability floor and cannot carry a park-level claim.

### For management

1. **Protect forest where Wood Thrush is present** - and describe it as a Wood Thrush measure, not a general at-risk measure, because that is what the data supports.
2. **Reduce survey-time disturbance.** A 36.8% drop in recorded species is the largest environmental effect measured here and the only one management controls directly.
3. **Do not convert grassland on diversity grounds.** Grassland holds every specialist in the dataset (17 of them) while forest holds none; richness alone shows no habitat difference.
4. **Direct at-risk monitoring to Catoctin Mountain Park, and diversity visits elsewhere.** They are not the same places.

## 6. What this dataset cannot answer

Stating these plainly is part of the result, not a disclaimer.

| Question | Why not |
|----------|---------|
| Is there a seasonal trend? | Visit number and date correlate at rho = 0.89; the third visit is grassland-only |
| Does forest hold more species than grassland? | Answered and the answer is no - the pooled difference is a park-mix artefact |
| Which individual plot is best? | No plot has more than 3 visits; the leaderboard is the tail of a noisy distribution |
| Are cold mornings better than mild ones? | The relationship is hump-shaped; the significant negative rho misdescribes it |
| Do at-risk birds favour early mornings? | No time-of-day effect on at-risk detection in either habitat |
| Why does slight disturbance beat none? | Unknown. Large samples both sides, no mechanism available |
| Anything about the 7 single-habitat parks' habitat preferences | They have no within-park comparison to make |

---

*Re-run `python src/make_ledger.py` after any change to the analysis or the cleaned data.*
