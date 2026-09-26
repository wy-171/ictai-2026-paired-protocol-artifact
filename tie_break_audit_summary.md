# Tie-Break Raw TXT Audit Summary

- Input folder: `raw_txt`
- TXT outputs audited: 125
- Prompt-only or skipped TXT files: 5
- Manual-review / incorrect flagged rows: 10

## Semantic correctness by model

| Model | Correct / N | Accuracy | Tie-rule OK | Shortest-path OK | Single-path OK | Format approx. |
|---|---:|---:|---:|---:|---:|---:|
| ChatGPT | 25/25 | 100.0% | 15/15 (100.0%) | 100.0% | 100.0% | 76.0% |
| Claude | 21/25 | 84.0% | 11/15 (73.3%) | 100.0% | 100.0% | 88.0% |
| DeepSeek | 23/25 | 92.0% | 13/15 (86.7%) | 100.0% | 100.0% | 80.0% |
| Mistral | 24/25 | 96.0% | 14/15 (93.3%) | 100.0% | 100.0% | 64.0% |
| Qwen | 25/25 | 100.0% | 15/15 (100.0%) | 100.0% | 100.0% | 72.0% |

## Semantic correctness by problem

| Problem | Correct / N | Accuracy | Tie-rule OK | Shortest-path OK |
|---|---:|---:|---:|---:|
| Q1 | 25/25 | 100.0% | NA | 100.0% |
| Q2 | 25/25 | 100.0% | 25/25 (100.0%) | 100.0% |
| Q3 | 25/25 | 100.0% | 25/25 (100.0%) | 100.0% |
| Q4 | 18/25 | 72.0% | 18/25 (72.0%) | 100.0% |
| Q5 | 25/25 | 100.0% | NA | 100.0% |

## Mode ratio by model/problem

| Model | Problem | Mode ratio | Mode answer |
|---|---|---:|---|
| ChatGPT | Q1 | 1.00 | `A->B->C->D` |
| ChatGPT | Q2 | 1.00 | `A->B->D` |
| ChatGPT | Q3 | 1.00 | `A->B->C->F` |
| ChatGPT | Q4 | 1.00 | `A->B->C->D->E` |
| ChatGPT | Q5 | 1.00 | `NO_PATH` |
| Claude | Q1 | 1.00 | `A->B->C->D` |
| Claude | Q2 | 1.00 | `A->B->D` |
| Claude | Q3 | 1.00 | `A->B->C->F` |
| Claude | Q4 | 0.80 | `A->B->C->E` |
| Claude | Q5 | 1.00 | `NO_PATH` |
| DeepSeek | Q1 | 1.00 | `A->B->C->D` |
| DeepSeek | Q2 | 1.00 | `A->B->D` |
| DeepSeek | Q3 | 1.00 | `A->B->C->F` |
| DeepSeek | Q4 | 0.60 | `A->B->C->D->E` |
| DeepSeek | Q5 | 1.00 | `NO_PATH` |
| Mistral | Q1 | 1.00 | `A->B->C->D` |
| Mistral | Q2 | 1.00 | `A->B->D` |
| Mistral | Q3 | 1.00 | `A->B->C->F` |
| Mistral | Q4 | 0.80 | `A->B->C->D->E` |
| Mistral | Q5 | 1.00 | `NO_PATH` |
| Qwen | Q1 | 1.00 | `A->B->C->D` |
| Qwen | Q2 | 1.00 | `A->B->D` |
| Qwen | Q3 | 1.00 | `A->B->C->F` |
| Qwen | Q4 | 1.00 | `A->B->C->D->E` |
| Qwen | Q5 | 1.00 | `NO_PATH` |

## Error type counts

| Error type | Count |
|---|---:|
| ok | 118 |
| tie_rule_failure | 7 |

## Skipped TXT files

- Tie-Break——Q1.txt
- Tie-Break——Q2.txt
- Tie-Break——Q3.txt
- Tie-Break——Q4.txt
- Tie-Break——Q5.txt

## Rows to manually review

| Filename | semantic_correct | shortest_path_ok | tie_rule_ok | chosen_path | error_type | eval_note |
|---|---:|---:|---:|---|---|---|
| Tie Break —— Q3 Mistral Run1.txt | 1 | 1 | 1 | `A->B->C->F` | ok | length_field_issue: |
| Tie Break —— Q3 Mistral Run4.txt | 1 | 1 | 1 | `A->B->C->F` | ok | length_field_issue: |
| Tie Break —— Q4 Claude Run2.txt | 0 | 1 | 0 | `A->B->C->E` | tie_rule_failure | tie_rule_failure:chosen=A->B->C->E;gold=A->B->C->D->E; length_field_issue:3 |
| Tie Break —— Q4 Claude Run3.txt | 0 | 1 | 0 | `A->B->C->E` | tie_rule_failure | tie_rule_failure:chosen=A->B->C->E;gold=A->B->C->D->E; length_field_issue:3 |
| Tie Break —— Q4 Claude Run4.txt | 0 | 1 | 0 | `A->B->C->E` | tie_rule_failure | tie_rule_failure:chosen=A->B->C->E;gold=A->B->C->D->E; length_field_issue:3 |
| Tie Break —— Q4 Claude Run5.txt | 0 | 1 | 0 | `A->B->C->E` | tie_rule_failure | tie_rule_failure:chosen=A->B->C->E;gold=A->B->C->D->E; length_field_issue:3 |
| Tie Break —— Q4 Deepseek Run1.txt | 0 | 1 | 0 | `A->B->C->E` | tie_rule_failure | tie_rule_failure:chosen=A->B->C->E;gold=A->B->C->D->E; length_field_issue:3 |
| Tie Break —— Q4 Deepseek Run5.txt | 0 | 1 | 0 | `A->B->C->E` | tie_rule_failure | tie_rule_failure:chosen=A->B->C->E;gold=A->B->C->D->E; length_field_issue:3 |
| Tie Break —— Q4 Mistral Run1.txt | 0 | 1 | 0 | `A->B->C->E` | tie_rule_failure | tie_rule_failure:chosen=A->B->C->E;gold=A->B->C->D->E; length_field_issue:3 |
| Tie-Break——Q1 Gpt Run5.txt | 1 | 1 | NA | `A->B->C->D` | ok | weight_field_issue:3 |
