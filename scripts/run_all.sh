#!/usr/bin/env bash
# Full rebuild from the raw files already in raw/ (re-fetch first with fetch.py / bfetch.py / render_2026_pages.py if needed).
set -euo pipefail
cd /workspace/az-clean
python3 scripts/pass_a.py > /dev/null
python3 scripts/pass_b.py > /dev/null
python3 scripts/compare_passes.py
python3 scripts/analysis.py > /dev/null
python3 scripts/build_pdf.py
python3 scripts/pdf_raw_crosscheck.py
python3 scripts/charts.py
bash scripts/assemble_repo.sh
python3 scripts/build_wiki.py
bash scripts/assemble_repo.sh
python3 scripts/verify_wiki.py
python3 scripts/layout_qa.py
bash scripts/assemble_repo.sh
echo "ALL CHECKS PASSED"
