#!/usr/bin/env bash
# Assemble the publishable repo tree in /workspace/az-clean/repo (local only; nothing is pushed here).
set -euo pipefail
A=/workspace/az-clean; R=$A/repo
mkdir -p $R/data $R/raw $R/scripts $R/verification
cp $A/pdf/Arizona_15_County_Democratic_Registration_and_Vote_Change.pdf $R/
cp $A/charts/AZ_*.png $R/
cp $A/data/AZ_Governor_2022_2026_DeltaG_by_County.csv $A/data/AZ_results_summary.json $R/data/
rm -rf $R/raw && cp -a $A/raw $R/raw && rm -f $R/raw/2026/sniff_ev/page.png $R/raw/2026/sniff_ev/page.html $R/raw/2026/sniff_ev/sniff_log.json  # browser network-capture logs, not data; they embed the results site map token
(cd $R/raw && find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS)
rm -rf $R/scripts && cp -a $A/scripts $R/scripts
rm -rf $R/verification && cp -a $A/verification $R/verification
