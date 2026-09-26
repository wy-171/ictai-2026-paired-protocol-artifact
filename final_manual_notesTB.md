Final manual audit notes for Tie-Break pilot

Raw TXT outputs audited: 125
Prompt-only files skipped: 5
Script: audit_tie_break_outputs_v1.py

The deterministic parser flagged 10 cases.
Manual inspection confirmed:
- 7 genuine semantic errors, all on Q4.
- 3 field-format warnings with correct chosen paths.

Genuine errors:
1. Claude Q4 Run2: chose A-B-C-E instead of A-B-C-D-E.
2. Claude Q4 Run3: chose A-B-C-E instead of A-B-C-D-E.
3. Claude Q4 Run4: chose A-B-C-E instead of A-B-C-D-E.
4. Claude Q4 Run5: chose A-B-C-E instead of A-B-C-D-E.
5. DeepSeek Q4 Run1: chose A-B-C-E instead of A-B-C-D-E.
6. DeepSeek Q4 Run5: chose A-B-C-E instead of A-B-C-D-E.
7. Mistral Q4 Run1: chose A-B-C-E instead of A-B-C-D-E.

Field-format warnings only:
1. Mistral Q3 Run1: chosen path correct; length field not parsed.
2. Mistral Q3 Run4: chosen path correct; length field not parsed.
3. GPT Q1 Run5: chosen path correct; field parser warning.

Final semantic correctness:
Claude   21/25 = 84%
DeepSeek 23/25 = 92%
ChatGPT  25/25 = 100%
Mistral  24/25 = 96%
Qwen     25/25 = 100%

By problem:
Q1 25/25 = 100%
Q2 25/25 = 100%
Q3 25/25 = 100%
Q4 18/25 = 72%
Q5 25/25 = 100%