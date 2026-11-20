> **2026 UNOFFICIAL.** \*2026 figures are UNOFFICIAL. The Arizona Secretary of State (SOS) results site (results.arizona.vote, served by app.enhancedvoting.com) labels the Nov 3, 2026 general election results "Unofficial Results" (data as of Nov 19, 2026, 4:35 PM CST; pulled Nov 19, 2026). All 15 counties report fully. The statewide canvass is scheduled for Nov 23, 2026, so these pages need a re-run after it. 2022 figures are the official SOS canvass of Dec 5, 2022. **P** = Democratic share of ACTIVE registered voters, from the G.E. (general election) row of the SOS State Voter Registration reports (2022 General Election and November 2026). Governor race only. Votes are votes for the Democratic candidate, not a count of registered Democrats who voted. These pages measure a pattern; they make no claim about intent, fraud or cause.

# Arizona Election Analysis: 2022 vs 2026\* governor race, ΔG method

Method developed by Morissa Benson (CD3 Vice Chair, Nebraska GOP), from her [Cedar County Audit](https://github.com/mbenson8989/Nebraska-Election-Analysis-/wiki/Cedar-Audit) on the [Nebraska Election Analysis wiki](https://github.com/mbenson8989/Nebraska-Election-Analysis-/wiki). This repository applies the same arithmetic to all 15 Arizona counties. Read the [wiki](https://github.com/mbenson8989/Arizona-Election-Analysis/wiki) for the full write-up.

## Headline (statewide, pooled)

| Measure | 2022 | 2026\* | Change |
|---|---|---|---|
| S: Democratic governor votes ÷ total ballots | 49.68% | 55.00% | +5.32 pts |
| P: Democratic share of active registration | 30.66% | 28.33% | −2.33 pts |
| G = S − P | +19.02 | +26.66 | ΔG +7.64 |

Locked Arizona formula: ΔG = 3.30 + 1.29 × (drop in Democratic registration share, points); R² 0.47, n = 15. Implied extra votes, summed over counties: +137,207.

## Files

- `Arizona_15_County_Democratic_Registration_and_Vote_Change.pdf`: the 15-county PDF table ([raw download](https://raw.githubusercontent.com/mbenson8989/Arizona-Election-Analysis/main/Arizona_15_County_Democratic_Registration_and_Vote_Change.pdf))
- `AZ_*.png`: charts used on the Graphs wiki page
- `data/AZ_Governor_2022_2026_DeltaG_by_County.csv`, `data/AZ_results_summary.json`: county table and fitted equations
- `raw/`: every source file exactly as downloaded, with `raw/fetch_log.csv` (URL, time, HTTP status, bytes, SHA-256) and `raw/SHA256SUMS`
- `scripts/`: pass A, pass B, comparison, analysis, PDF build, independent PDF checker, wiki build and wiki verifier
- `verification/`: pass A vs pass B figure-by-figure comparison, PDF cell-by-cell raw cross-check, wiki number cross-check, layout QA renders

## Sources (retrieved Nov 19, 2026)

| Source | URL | SHA-256 |
|---|---|---|
| 2022 official canvass (Dec 5, 2022) | https://apps.azsos.gov/election/2022/General/canvass/2022dec05_general_election_canvass_web.pdf | `ec459c2c24889d3ea685f676907284c1d8a0b2542b5534e73166702b2905673d` |
| 2026\* results, statewide (UNOFFICIAL, data as of Nov 19, 2026 4:35 PM CST) | https://app.enhancedvoting.com/results/public/api/elections/Arizona/110326GeneralElection/data | `f6e3efe213a1b28133efabf9e008dcd22b4440ddb7ff70cc33aa16684db9ad5d` |
| 2026\* results, one file per county | same API, county short names | see `raw/fetch_log.csv` |
| Registration, 2022 General (CSV) | https://apps.azsos.gov/election/VoterReg/2022/State_Voter_Registration_2022_General.csv | `05b5ff825a85684745425ecdf435bea864f90451de592e1baef80f7b59efa65a` |
| Registration, 2022 General (PDF) | https://apps.azsos.gov/election/VoterReg/2022/State_Voter_Registration_2022_General.pdf | `89f329cfbab9c2ca56db4ae591a85185124759cbed4c7d798c3226bbda3f9bac` |
| Registration, November 2026 (CSV) | https://apps.azsos.gov/election/VoterReg/2026/State-Voter-Registration-November-2026.csv | `6dcc465867d56520aa5ef3d5c9f5685efb6b6accbe685c00838e55acd3d1a3f2` |
| Registration, November 2026 (PDF) | https://apps.azsos.gov/election/VoterReg/2026/State-Voter-Registration-November-2026.pdf | `67d669df2444e3d64b587ba3d706fca58f71b6450d4805a18cad1458bc864231` |
| Census population estimates, Vintage 2025 | https://www2.census.gov/programs-surveys/popest/datasets/2020-2025/counties/totals/co-est2025-alldata.csv | `4f5a499d851e2cb48fd7a5405e5a9235453a8a66933657aacd10df0e264f35d5` |

## Verification

Pass A and pass B compute every figure by independent code from different renderings of the raw files (canvass word positions vs plain text; results API JSON vs rendered results pages; registration CSV vs registration PDF). A third checker re-parses the raw files itself and recomputes every PDF cell against the PDF's own text. `verify_wiki.py` recomputes every number on every wiki page (and this README) from pass A and pass B separately. See `verification/`.

**2026 figures are UNOFFICIAL** until the Nov 23, 2026 statewide canvass; re-run `scripts/run_all.sh` after it.
