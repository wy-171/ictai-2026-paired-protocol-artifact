#!/usr/bin/env python3
"""
audit_tie_break_outputs_v1.py

Deterministic audit script for the "Tie-Break" shortest-path pilot outputs.

What it does:
- Reads every .txt file in a folder, including subfolders.
- Infers problem ID (Q1-Q5), model name, and run number from the filename.
- Skips prompt-only files that do not contain a model/run identifier.
- Extracts the final "Chosen shortest path" section.
- Normalizes path formats:
    A -> B -> C
    A → B → C
    A-B-C
    A — B — C
- Scores the output against hard-coded gold answers for Q1-Q5.
- Separates:
    semantic_correct        = final chosen answer equals the gold tie-break answer
    shortest_path_ok        = chosen path is among the minimum-cost paths
    tie_rule_ok             = chosen path obeys lexicographic tie-break when a tie exists
    single_path_ok          = exactly one chosen path is reported when reachable
    field_correct           = length / total-weight fields match expected values
    format_ok_approx       = major sections appear in order
- Writes:
    1) tie_break_audit_results.csv
    2) tie_break_audit_summary.md
    3) tie_break_flagged_for_manual_review.csv

Important:
- This script does NOT use an LLM.
- It does NOT modify your original .txt files.
- It is conservative: uncertain parses are flagged for manual review.

Expected filename examples:
- Tie Break —— Q4 Qwen Run1.txt
- Tie-Break——Q4 Claude Run2.txt
- Tie_Break_Q4_GPT-5_Run3.txt
- Tie Break —— Q5 Mistral Run4.txt

Prompt-only files such as "Tie-Break——Q4.txt" are skipped automatically.
"""

from __future__ import annotations

import argparse
import csv
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------
# Gold answers for the Tie-break setup.
# ---------------------------------------------------------------------
# all_min_paths = all minimum-cost paths before applying the tie-break rule.
# chosen_path   = lexicographically smallest path among all_min_paths.
# Q5 is unreachable.

GOLD: Dict[str, Dict[str, Any]] = {
    "Q1": {
        "answer_type": "PATH",
        "chosen_path": ("A", "B", "C", "D"),
        "all_min_paths": {("A", "B", "C", "D")},
        "length": 3,
        "weight": None,
        "has_tie": False,
    },
    "Q2": {
        "answer_type": "PATH",
        "chosen_path": ("A", "B", "D"),
        "all_min_paths": {("A", "B", "D"), ("A", "C", "D")},
        "length": 2,
        "weight": None,
        "has_tie": True,
    },
    "Q3": {
        "answer_type": "PATH",
        "chosen_path": ("A", "B", "C", "F"),
        "all_min_paths": {
            ("A", "B", "C", "F"),
            ("A", "B", "E", "F"),
            ("A", "D", "E", "F"),
        },
        "length": 3,
        "weight": None,
        "has_tie": True,
    },
    "Q4": {
        "answer_type": "PATH",
        # Important: weight is minimized first. Both A-B-C-E and
        # A-B-C-D-E have total weight 6. Lexicographic tie-break compares
        # node sequences, so A-B-C-D-E wins because D < E at the first
        # differing position.
        "chosen_path": ("A", "B", "C", "D", "E"),
        "all_min_paths": {("A", "B", "C", "E"), ("A", "B", "C", "D", "E")},
        "length": 4,
        "weight": 6,
        "has_tie": True,
    },
    "Q5": {
        "answer_type": "NO_PATH",
        "chosen_path": None,
        "all_min_paths": set(),
        "length": None,
        "weight": None,
        "has_tie": False,
    },
}

NO_PATH_PATTERNS = [
    r"\bnone\b",
    r"\bno path exists\b",
    r"\bno path\b",
    r"\bdoes not exist\b",
    r"\bdisconnected\b",
    r"\bdifferent connected components\b",
    r"\bno edge connecting\b",
    r"\bnot connected\b",
    r"\bunreachable\b",
]


# ---------------------------------------------------------------------
# File and metadata helpers
# ---------------------------------------------------------------------

def read_text(path: Path) -> str:
    for enc in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return path.read_text(errors="replace")


def infer_metadata(filename: str) -> Dict[str, str]:
    stem = Path(filename).stem
    normalized = (
        stem.replace("——", " ")
        .replace("—", " ")
        .replace("_", " ")
        .replace("-", " ")
    )
    low = normalized.lower()

    q_match = re.search(r"\b(Q[1-5])\b", normalized, flags=re.IGNORECASE)
    run_match = re.search(r"\bRun\s*([1-9][0-9]*)\b", normalized, flags=re.IGNORECASE)

    problem = q_match.group(1).upper() if q_match else ""
    run = run_match.group(1) if run_match else ""

    model = ""
    aliases = [
        (r"\bqwen\s*3\s*max\b", "Qwen"),
        (r"\bqwen3\s*max\b", "Qwen"),
        (r"\bqwen3max\b", "Qwen"),
        (r"\bqwen3\b", "Qwen"),
        (r"\bqwen\b", "Qwen"),
        (r"\bchat\s*gpt\b", "ChatGPT"),
        (r"\bchatgpt\b", "ChatGPT"),
        (r"\bgpt\s*5\b", "ChatGPT"),
        (r"\bgpt5\b", "ChatGPT"),
        (r"\bgpt\b", "ChatGPT"),
        (r"\bclaude\b", "Claude"),
        (r"\bdeep\s*seek\b", "DeepSeek"),
        (r"\bdeepseek\b", "DeepSeek"),
        (r"\bmistral\b", "Mistral"),
    ]
    for pat, val in aliases:
        if re.search(pat, low):
            model = val
            break

    return {"problem": problem, "model": model, "run": run}


# ---------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------

def normalize_text(s: str) -> str:
    replacements = {
        "→": "->",
        "⇒": "->",
        "➜": "->",
        "➔": "->",
        "⟶": "->",
        "–": "-",
        "—": "-",
        "−": "-",
        "：": ":",
    }
    for a, b in replacements.items():
        s = s.replace(a, b)
    return s


def has_no_path(text: str) -> bool:
    low = text.lower()
    return any(re.search(pat, low) for pat in NO_PATH_PATTERNS)


def slice_between(text: str, start_pattern: str, end_patterns: List[str]) -> str:
    m = re.search(start_pattern, text, flags=re.IGNORECASE)
    if not m:
        return ""
    start = m.end()
    end = len(text)
    for pat in end_patterns:
        m2 = re.search(pat, text[start:], flags=re.IGNORECASE)
        if m2:
            end = min(end, start + m2.start())
    return text[start:end].strip()


def extract_chosen_section(text: str) -> str:
    """
    Extract the final answer section after "Chosen shortest path:".
    This is intentionally prioritized over reasoning text, which may list
    many candidate paths.
    """
    return slice_between(
        text,
        r"Chosen\s+shortest\s+path\s*:",
        [
            r"\n\s*#{0,6}\s*Path\s+length\s*\(in\s+edges\)\s*:",
            r"\n\s*#{0,6}\s*Total\s+weight",
            r"\n\s*#{0,6}\s*Audit\s+Checklist",
            r"\n\s*-{3,}",
        ],
    )


def clean_path_line(line: str) -> str:
    line = normalize_text(line)
    line = re.sub(r"^\s*#{1,6}\s*", "", line)
    line = re.sub(r"^\s*[-*•]\s*", "", line)
    line = re.sub(r"^\s*(Path\s*\d+|Chosen path|Shortest path|Path)\s*[:\-]\s*", "", line, flags=re.IGNORECASE)
    line = line.replace("**", "").replace("`", "")
    return line.strip()


def extract_path_candidates(text: str) -> List[Tuple[str, ...]]:
    """
    Extract path-like sequences from text.
    Works best on the Chosen shortest path section.
    """
    text = normalize_text(text)
    candidates: List[Tuple[str, ...]] = []

    for raw_line in text.splitlines():
        line = clean_path_line(raw_line)
        if not line:
            continue
        if has_no_path(line) or re.fullmatch(r"(?i)n/?a|none", line.strip()):
            continue

        # Convert "A to B to C" to "A->B->C" if path-like.
        line2 = re.sub(r"\s+\bto\b\s+", "->", line, flags=re.IGNORECASE)

        # Main path pattern: A->B->C or A-B-C.
        pattern = r"\b[A-Z]\b(?:\s*(?:->|-)\s*\b[A-Z]\b)+"
        for match in re.finditer(pattern, line2):
            s = match.group(0)
            parts = re.split(r"\s*(?:->|-)\s*", s)
            path = tuple(p.strip() for p in parts if p.strip())
            if len(path) >= 2:
                candidates.append(path)

    # Deduplicate while preserving order.
    out: List[Tuple[str, ...]] = []
    seen = set()
    for p in candidates:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def extract_field_value(text: str, field_regex: str) -> str:
    """
    Extract a field value only from a section-like line, not arbitrary
    mentions in reasoning text.
    """
    pattern = r"(?im)^\s*#{0,6}\s*" + field_regex + r"\s*:?\s*(.*)$"
    m = re.search(pattern, text)
    if not m:
        return ""
    line = m.group(1).strip()
    line = re.sub(r"^\s*[:\-]\s*", "", line)
    if line:
        return line

    # Value might appear on the next bullet line.
    after = text[m.end():]
    for ln in after.splitlines()[:4]:
        stripped = re.sub(r"^\s*[-*]\s*", "", ln.strip())
        if stripped:
            return stripped
    return ""


def extract_length(text: str) -> str:
    return extract_field_value(text, r"Path\s+length\s*\(in\s+edges\)")


def extract_weight(text: str) -> str:
    return extract_field_value(text, r"Total\s+weight(?:\s*\(if\s+weighted\))?")


def parse_ints(s: str) -> List[int]:
    return [int(x) for x in re.findall(r"-?\d+", s or "")]


def normalize_na(s: str) -> bool:
    if s is None:
        return True
    t = str(s).strip().lower()
    t = t.strip(" .:-*")
    return t in {"", "n/a", "na", "none", "not applicable", "not applicable.", "n.a."}


def approximate_format_ok(text: str) -> bool:
    patterns = [
        r"Reasoning\s*\(numbered\s+steps\)\s*:",
        r"Chosen\s+shortest\s+path\s*:",
        r"Path\s+length\s*\(in\s+edges\)\s*:",
        r"Total\s+weight",
    ]
    pos = -1
    for pat in patterns:
        m = re.search(pat, text, flags=re.IGNORECASE)
        if not m:
            return False
        if m.start() < pos:
            return False
        pos = m.start()
    return True


def parse_output(text: str) -> Dict[str, Any]:
    chosen_section = extract_chosen_section(text)
    parse_note = ""

    if chosen_section:
        if has_no_path(chosen_section):
            return {
                "answer_type": "NO_PATH",
                "chosen_paths": tuple(),
                "parse_note": "no_path_in_chosen_section",
            }
        paths = extract_path_candidates(chosen_section)
        if paths:
            return {
                "answer_type": "PATH",
                "chosen_paths": tuple(paths),
                "parse_note": "path_from_chosen_section",
            }
        parse_note = "chosen_section_found_but_no_path_parsed"

    # Conservative fallback: only if the entire output clearly says no path.
    if has_no_path(text):
        return {
            "answer_type": "NO_PATH",
            "chosen_paths": tuple(),
            "parse_note": "no_path_in_full_text_fallback_manual_review",
        }

    return {
        "answer_type": "UNKNOWN",
        "chosen_paths": tuple(),
        "parse_note": parse_note or "could_not_parse_chosen_answer",
    }


# ---------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------

def evaluate(problem: str, parsed: Dict[str, Any], length_s: str, weight_s: str) -> Dict[str, Any]:
    if problem not in GOLD:
        return {
            "semantic_correct": "",
            "shortest_path_ok": "",
            "tie_rule_ok": "",
            "single_path_ok": "",
            "length_ok": "",
            "weight_ok": "",
            "field_correct": "",
            "manual_review": 1,
            "error_type": "unknown_problem",
            "eval_note": "unknown_problem",
        }

    gold = GOLD[problem]
    answer_type = parsed["answer_type"]
    chosen_paths: Tuple[Tuple[str, ...], ...] = parsed["chosen_paths"]

    notes: List[str] = []
    manual_review = 0

    # Q5 no-path case.
    if gold["answer_type"] == "NO_PATH":
        semantic_correct = 1 if answer_type == "NO_PATH" else 0
        shortest_path_ok = "NA"
        tie_rule_ok = "NA"
        single_path_ok = 1 if answer_type == "NO_PATH" else 0
        length_ok = 1 if normalize_na(length_s) else 0
        weight_ok = 1 if normalize_na(weight_s) else 0
        field_correct = 1 if length_ok and weight_ok else 0

        if not semantic_correct:
            notes.append("gold_no_path_but_output_not_no_path")
            manual_review = 1
        if not field_correct:
            notes.append(f"no_path_field_issue:length={length_s};weight={weight_s}")
            manual_review = 1

        return {
            "semantic_correct": semantic_correct,
            "shortest_path_ok": shortest_path_ok,
            "tie_rule_ok": tie_rule_ok,
            "single_path_ok": single_path_ok,
            "length_ok": length_ok,
            "weight_ok": weight_ok,
            "field_correct": field_correct,
            "manual_review": manual_review,
            "error_type": "ok" if semantic_correct else "no_path_error",
            "eval_note": "; ".join(notes) if notes else "ok",
        }

    # Reachable cases.
    if answer_type != "PATH":
        return {
            "semantic_correct": 0,
            "shortest_path_ok": 0,
            "tie_rule_ok": 0 if gold["has_tie"] else "NA",
            "single_path_ok": 0,
            "length_ok": 0,
            "weight_ok": 0,
            "field_correct": 0,
            "manual_review": 1,
            "error_type": "parse_or_no_path_error",
            "eval_note": "gold_has_path_but_no_chosen_path_parsed",
        }

    single_path_ok = 1 if len(chosen_paths) == 1 else 0
    chosen_path: Optional[Tuple[str, ...]] = chosen_paths[0] if chosen_paths else None

    if len(chosen_paths) > 1:
        notes.append("multiple_paths_reported_in_chosen_section")
        manual_review = 1

    gold_chosen = gold["chosen_path"]
    all_min = gold["all_min_paths"]

    shortest_path_ok = 1 if chosen_path in all_min else 0
    tie_rule_ok = (1 if chosen_path == gold_chosen else 0) if gold["has_tie"] else "NA"
    semantic_correct = 1 if (chosen_path == gold_chosen and single_path_ok == 1) else 0

    if chosen_path != gold_chosen:
        if chosen_path in all_min:
            notes.append(f"tie_rule_failure:chosen={'->'.join(chosen_path)};gold={'->'.join(gold_chosen)}")
            error_type = "tie_rule_failure"
        else:
            notes.append(f"not_minimum_or_wrong_path:chosen={'->'.join(chosen_path) if chosen_path else ''};gold={'->'.join(gold_chosen)}")
            error_type = "wrong_path"
    elif single_path_ok == 0:
        error_type = "multiple_paths_reported"
    else:
        error_type = "ok"

    # Field checks.
    length_nums = parse_ints(length_s)
    length_ok = 1 if gold["length"] in length_nums else 0

    if gold["weight"] is None:
        weight_ok = 1 if normalize_na(weight_s) else 0
    else:
        weight_nums = parse_ints(weight_s)
        weight_ok = 1 if gold["weight"] in weight_nums else 0

    field_correct = 1 if length_ok and weight_ok else 0

    # Field mismatches do not automatically change semantic_correct, but they are flagged.
    if not length_ok:
        notes.append(f"length_field_issue:{length_s}")
        manual_review = 1
    if not weight_ok:
        notes.append(f"weight_field_issue:{weight_s}")
        manual_review = 1

    if not semantic_correct:
        manual_review = 1

    return {
        "semantic_correct": semantic_correct,
        "shortest_path_ok": shortest_path_ok,
        "tie_rule_ok": tie_rule_ok,
        "single_path_ok": single_path_ok,
        "length_ok": length_ok,
        "weight_ok": weight_ok,
        "field_correct": field_correct,
        "manual_review": manual_review,
        "error_type": error_type,
        "eval_note": "; ".join(notes) if notes else "ok",
    }


def norm_answer(parsed: Dict[str, Any]) -> str:
    if parsed["answer_type"] == "NO_PATH":
        return "NO_PATH"
    if parsed["chosen_paths"]:
        return " | ".join("->".join(p) for p in parsed["chosen_paths"])
    return ""


def audit_folder(input_dir: Path, out_csv: Path, summary_md: Path, flagged_csv: Path) -> None:
    rows: List[Dict[str, Any]] = []
    skipped: List[str] = []

    for path in sorted(input_dir.rglob("*.txt")):
        meta = infer_metadata(path.name)
        text = read_text(path)

        if not meta["problem"] or not meta["model"] or not meta["run"]:
            skipped.append(path.name)
            continue

        parsed = parse_output(text)
        length_s = extract_length(text)
        weight_s = extract_weight(text)
        ev = evaluate(meta["problem"], parsed, length_s, weight_s)

        row = {
            "filename": path.name,
            "model": meta["model"],
            "problem": meta["problem"],
            "run": meta["run"],
            "answer_type": parsed["answer_type"],
            "chosen_path": norm_answer(parsed),
            "length_field": length_s,
            "total_weight_field": weight_s,
            "semantic_correct": ev["semantic_correct"],
            "shortest_path_ok": ev["shortest_path_ok"],
            "tie_rule_ok": ev["tie_rule_ok"],
            "single_path_ok": ev["single_path_ok"],
            "length_ok": ev["length_ok"],
            "weight_ok": ev["weight_ok"],
            "field_correct": ev["field_correct"],
            "format_ok_approx": 1 if approximate_format_ok(text) else 0,
            "manual_review": ev["manual_review"],
            "error_type": ev["error_type"],
            "parse_note": parsed["parse_note"],
            "eval_note": ev["eval_note"],
        }
        rows.append(row)

    fieldnames = [
        "filename", "model", "problem", "run",
        "answer_type", "chosen_path", "length_field", "total_weight_field",
        "semantic_correct", "shortest_path_ok", "tie_rule_ok", "single_path_ok",
        "length_ok", "weight_ok", "field_correct", "format_ok_approx",
        "manual_review", "error_type", "parse_note", "eval_note",
    ]

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    flagged = [
        r for r in rows
        if str(r["manual_review"]) == "1"
        or str(r["semantic_correct"]) in {"", "0"}
        or str(r["tie_rule_ok"]) == "0"
        or str(r["single_path_ok"]) == "0"
    ]
    with flagged_csv.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(flagged)

    lines: List[str] = []
    lines.append("# Tie-Break Raw TXT Audit Summary\n")
    lines.append(f"- Input folder: `{input_dir}`")
    lines.append(f"- TXT outputs audited: {len(rows)}")
    lines.append(f"- Prompt-only or skipped TXT files: {len(skipped)}")
    lines.append(f"- Manual-review / incorrect flagged rows: {len(flagged)}\n")

    # Model summary.
    lines.append("## Semantic correctness by model\n")
    by_model: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in rows:
        by_model[r["model"]].append(r)
    lines.append("| Model | Correct / N | Accuracy | Tie-rule OK | Shortest-path OK | Single-path OK | Format approx. |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    for model in sorted(by_model):
        gs = by_model[model]
        n = len(gs)
        correct = sum(1 for r in gs if str(r["semantic_correct"]) == "1")
        shortest = sum(1 for r in gs if str(r["shortest_path_ok"]) in {"1", "NA"})
        single = sum(1 for r in gs if str(r["single_path_ok"]) == "1")
        fmt = sum(1 for r in gs if str(r["format_ok_approx"]) == "1")
        tie_applicable = [r for r in gs if str(r["tie_rule_ok"]) != "NA"]
        tie_ok = sum(1 for r in tie_applicable if str(r["tie_rule_ok"]) == "1")
        tie_den = len(tie_applicable)
        tie_cell = f"{tie_ok}/{tie_den} ({tie_ok/tie_den:.1%})" if tie_den else "NA"
        lines.append(f"| {model} | {correct}/{n} | {correct/n:.1%} | {tie_cell} | {shortest/n:.1%} | {single/n:.1%} | {fmt/n:.1%} |")

    # Problem summary.
    lines.append("\n## Semantic correctness by problem\n")
    by_problem: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in rows:
        by_problem[r["problem"]].append(r)
    lines.append("| Problem | Correct / N | Accuracy | Tie-rule OK | Shortest-path OK |")
    lines.append("|---|---:|---:|---:|---:|")
    for q in sorted(by_problem):
        gs = by_problem[q]
        n = len(gs)
        correct = sum(1 for r in gs if str(r["semantic_correct"]) == "1")
        shortest = sum(1 for r in gs if str(r["shortest_path_ok"]) in {"1", "NA"})
        tie_applicable = [r for r in gs if str(r["tie_rule_ok"]) != "NA"]
        tie_ok = sum(1 for r in tie_applicable if str(r["tie_rule_ok"]) == "1")
        tie_den = len(tie_applicable)
        tie_cell = f"{tie_ok}/{tie_den} ({tie_ok/tie_den:.1%})" if tie_den else "NA"
        lines.append(f"| {q} | {correct}/{n} | {correct/n:.1%} | {tie_cell} | {shortest/n:.1%} |")

    # Mode ratio.
    lines.append("\n## Mode ratio by model/problem\n")
    lines.append("| Model | Problem | Mode ratio | Mode answer |")
    lines.append("|---|---|---:|---|")
    grouped: Dict[Tuple[str, str], List[str]] = defaultdict(list)
    for r in rows:
        grouped[(r["model"], r["problem"])].append(str(r["chosen_path"]))
    for (model, q) in sorted(grouped):
        vals = grouped[(model, q)]
        counts = Counter(vals)
        mode, count = counts.most_common(1)[0]
        lines.append(f"| {model} | {q} | {count/len(vals):.2f} | `{mode}` |")

    # Error type summary.
    lines.append("\n## Error type counts\n")
    counts = Counter(r["error_type"] for r in rows)
    lines.append("| Error type | Count |")
    lines.append("|---|---:|")
    for k, v in counts.most_common():
        lines.append(f"| {k} | {v} |")

    if skipped:
        lines.append("\n## Skipped TXT files\n")
        for name in skipped:
            lines.append(f"- {name}")

    if flagged:
        lines.append("\n## Rows to manually review\n")
        lines.append("| Filename | semantic_correct | shortest_path_ok | tie_rule_ok | chosen_path | error_type | eval_note |")
        lines.append("|---|---:|---:|---:|---|---|---|")
        for r in flagged:
            lines.append(
                f"| {r['filename']} | {r['semantic_correct']} | {r['shortest_path_ok']} | {r['tie_rule_ok']} | `{r['chosen_path']}` | {r['error_type']} | {r['eval_note']} |"
            )

    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit raw TXT outputs for Tie-Break shortest-path pilot.")
    parser.add_argument("input_dir", help="Folder containing raw .txt outputs")
    parser.add_argument("--out", default="tie_break_audit_results.csv", help="Output detailed CSV")
    parser.add_argument("--summary", default="tie_break_audit_summary.md", help="Output Markdown summary")
    parser.add_argument("--flagged", default="tie_break_flagged_for_manual_review.csv", help="Output flagged rows CSV")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    if not input_dir.exists() or not input_dir.is_dir():
        raise SystemExit(f"Input folder does not exist or is not a folder: {input_dir}")

    audit_folder(input_dir, Path(args.out), Path(args.summary), Path(args.flagged))
    print("Done.")
    print(f"Wrote: {args.out}")
    print(f"Wrote: {args.summary}")
    print(f"Wrote: {args.flagged}")


if __name__ == "__main__":
    main()
