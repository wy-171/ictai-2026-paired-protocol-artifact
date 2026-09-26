# Raw TXT Audit Summary

- Input folder: `raw_txt`
- TXT outputs audited: 125
- Prompt-only or skipped TXT files: 5
- Manual-review / incorrect flagged rows: 6

## Semantic correctness by model

| Model | Correct / N | Accuracy | Format approx. |
|---|---:|---:|---:|
| Claude | 25/25 | 100.0% | 0.0% |
| DeepSeek | 24/25 | 96.0% | 0.0% |
| GPT | 25/25 | 100.0% | 36.0% |
| Mistral | 20/25 | 80.0% | 72.0% |
| Qwen | 25/25 | 100.0% | 20.0% |

## Semantic correctness by problem

| Problem | Correct / N | Accuracy | Format approx. |
|---|---:|---:|---:|
| Q1 | 25/25 | 100.0% | 40.0% |
| Q2 | 25/25 | 100.0% | 32.0% |
| Q3 | 24/25 | 96.0% | 28.0% |
| Q4 | 20/25 | 80.0% | 0.0% |
| Q5 | 25/25 | 100.0% | 28.0% |

## Mode ratio by model/problem

| Model | Problem | Mode ratio | Mode answer |
|---|---|---:|---|
| Claude | Q1 | 1.00 | `A->B->C->D` |
| Claude | Q2 | 1.00 | `A->B->D | A->C->D` |
| Claude | Q3 | 1.00 | `A->B->C->F | A->B->E->F | A->D->E->F` |
| Claude | Q4 | 1.00 | `A->B->C->D->E | A->B->C->E` |
| Claude | Q5 | 1.00 | `NO_PATH` |
| DeepSeek | Q1 | 1.00 | `A->B->C->D` |
| DeepSeek | Q2 | 1.00 | `A->B->D | A->C->D` |
| DeepSeek | Q3 | 1.00 | `A->B->C->F | A->B->E->F | A->D->E->F` |
| DeepSeek | Q4 | 0.80 | `A->B->C->D->E | A->B->C->E` |
| DeepSeek | Q5 | 1.00 | `NO_PATH` |
| GPT | Q1 | 1.00 | `A->B->C->D` |
| GPT | Q2 | 1.00 | `A->B->D | A->C->D` |
| GPT | Q3 | 1.00 | `A->B->C->F | A->B->E->F | A->D->E->F` |
| GPT | Q4 | 1.00 | `A->B->C->D->E | A->B->C->E` |
| GPT | Q5 | 1.00 | `NO_PATH` |
| Mistral | Q1 | 1.00 | `A->B->C->D` |
| Mistral | Q2 | 1.00 | `A->B->D | A->C->D` |
| Mistral | Q3 | 0.80 | `A->B->C->F | A->B->E->F | A->D->E->F` |
| Mistral | Q4 | 0.60 | `A->B->C->D->E` |
| Mistral | Q5 | 1.00 | `NO_PATH` |
| Qwen | Q1 | 1.00 | `A->B->C->D` |
| Qwen | Q2 | 1.00 | `A->B->D | A->C->D` |
| Qwen | Q3 | 1.00 | `A->B->C->F | A->B->E->F | A->D->E->F` |
| Qwen | Q4 | 1.00 | `A->B->C->D->E | A->B->C->E` |
| Qwen | Q5 | 1.00 | `NO_PATH` |

## Skipped TXT files

- List All Shortest Paths——Q1.txt
- List All Shortest Paths——Q2.txt
- List All Shortest Paths——Q3.txt
- List All Shortest Paths——Q4.txt
- List All Shortest Paths——Q5.txt

## Rows to manually review

| Filename | semantic_correct | parse_note | eval_note |
|---|---:|---|---|
| List All Shortest Paths——Q3 Mistral Run2.txt | 0 | paths_from_shortest_paths_section | missing:A->D->E->F |
| List All Shortest Paths——Q4 Deepseek Run3.txt | 0 | paths_from_shortest_paths_section | missing:A->B->C->D->E |
| List All Shortest Paths——Q4 Mistral Run2.txt | 0 | paths_from_shortest_paths_section | extra:A->C->D->E |
| List All Shortest Paths——Q4 Mistral Run3.txt | 0 | paths_from_shortest_paths_section | missing:A->B->C->E |
| List All Shortest Paths——Q4 Mistral Run4.txt | 0 | paths_from_shortest_paths_section | missing:A->B->C->E |
| List All Shortest Paths——Q4 Mistral Run5.txt | 0 | paths_from_shortest_paths_section | missing:A->B->C->E; weight_missing_or_wrong:; missing_edge_length |
