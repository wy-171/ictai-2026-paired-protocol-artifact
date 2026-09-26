# Supplementary Artifact for ICTAI 2026

This repository contains the supplementary artifact for the paper:

**Beyond Final-Answer Accuracy: Paired-Protocol Evaluation of LLM Graph Reasoning with Multiple Optima**

## Overview

The study evaluates five publicly deployed large language model services on five shortest-path instances under two complementary protocols:

- **List-All:** enumerate every minimum-cost path.
- **Tie-Break:** return exactly one minimum-cost path selected by a fixed lexicographic rule.

Each service-problem-protocol combination was repeated five times in fresh conversations, yielding:

- 125 List-All outputs
- 125 Tie-Break outputs
- 250 outputs in total

This artifact contains the prompts, raw transcripts, deterministic grader code, automatically generated audit results, and final manual audit annotations reported in the paper.

## Repository Contents

### Raw transcripts and prompts

- `raw_txtAL.zip`  
  Contains 125 List-All outputs and five prompt files, one for each problem.

- `raw_txtTB.zip`  
  Contains 125 Tie-Break outputs and five prompt files, one for each problem.

### Grader code

- `audit_all_txt_outputs_v3.py`  
  Deterministic parser and grader for the List-All protocol.

- `audit_tie_break_outputs_v1.py`  
  Deterministic parser and grader for the Tie-Break protocol.

Both scripts use hard-coded ground-truth answers and require only the Python standard library.

### Automatic audit outputs

List-All:

- `raw_txt_audit_results_v3.csv`
- `raw_txt_audit_summary_v3.md`
- `raw_txt_flagged_for_manual_review_v3.csv`

Tie-Break:

- `tie_break_audit_results.csv`
- `tie_break_audit_summary.md`
- `tie_break_flagged_for_manual_review.csv`

### Manual audit annotations

- `final_manual_notesAL.md`
- `final_manual_notesTB.md`

These files record the final manual decisions for all outputs flagged by the deterministic graders.

## Reproducing the Automatic Audit

Python 3 is required. No third-party packages are needed.

First, extract both archives. The extracted directories should be named `raw_txtAL` and `raw_txtTB`.

Run the List-All audit:

```bash
python3 audit_all_txt_outputs_v3.py raw_txtAL \
  --out raw_txt_audit_results_reproduced.csv \
  --summary raw_txt_audit_summary_reproduced.md \
  --flagged raw_txt_flagged_reproduced.csv
```

Run the Tie-Break audit:

```bash
python3 audit_tie_break_outputs_v1.py raw_txtTB \
  --out tie_break_audit_results_reproduced.csv \
  --summary tie_break_audit_summary_reproduced.md \
  --flagged tie_break_flagged_reproduced.csv
```

## Final Audit Summary

The deterministic graders flagged 16 of the 250 outputs for manual review:

- 6 List-All outputs
- 10 Tie-Break outputs

Manual inspection confirmed 13 semantically incorrect final answers:

- 6 under List-All
- 7 under Tie-Break

The remaining three Tie-Break outputs contained correct chosen paths but triggered auxiliary-field warnings. These outputs were retained as semantically correct, with the field issues recorded separately.

Final semantic accuracy:

- List-All: 119/125 (95.2%)
- Tie-Break: 118/125 (94.4%)

The manual audit notes contain the authoritative final classification of the flagged outputs.