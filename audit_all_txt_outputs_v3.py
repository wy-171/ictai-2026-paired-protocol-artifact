#!/usr/bin/env python3
"""
audit_all_txt_outputs_v3.py

More robust raw-TXT audit script for the "List All Shortest Paths" pilot.

Changes from v1:
- Recognizes Qwen3-Max / Qwen3 Max filenames as Qwen.
- Parses Unicode arrows such as →, ⇒, ➜, and long dashes.
- Handles common "Path 1: A → B → C" / bullet / Markdown heading formats.
- Uses the "Shortest path(s)" section first, with a controlled full-text fallback.
- Separates semantic correctness from approximate format compliance.
- Flags uncertain rows for manual review instead of silently trusting them.

This script does NOT use an LLM and does NOT modify your original .txt files.
"""

from __future__ import annotations

import argparse
import csv
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Tuple, Any


GOLD: Dict[str, Dict[str, Any]] = {
    "Q1": {
        "answer_type": "PATHS",
        "paths": {("A", "B", "C", "D")},
        "edge_lengths": {3},
        "weight": None,
    },
    "Q2": {
        "answer_type": "PATHS",
        "paths": {("A", "B", "D"), ("A", "C", "D")},
        "edge_lengths": {2},
        "weight": None,
    },
    "Q3": {
        "answer_type": "PATHS",
        "paths": {
            ("A", "B", "C", "F"),
            ("A", "B", "E", "F"),
            ("A", "D", "E", "F"),
        },
        "edge_lengths": {3},
        "weight": None,
    },
    "Q4": {
        "answer_type": "PATHS",
        "paths": {("A", "B", "C", "E"), ("A", "B", "C", "D", "E")},
        # Q4 tied paths have different edge counts but same total weight.
        "edge_lengths": {3, 4},
        "weight": 6,
    },
    "Q5": {
        "answer_type": "NO_PATH",
        "paths": set(),
        "edge_lengths": set(),
        "weight": None,
    },
}

NO_PATH_PATTERNS = [
    r"\bno path exists\b",
    r"\bno path\b",
    r"\bdoes not exist\b",
    r"\bdisconnected\b",
    r"\bdifferent connected components\b",
    r"\bno edge connecting\b",
    r"\bnot connected\b",
    r"\bthere is no route\b",
]


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
    # Order matters: more specific aliases first.
    aliases = [
        (r"\bqwen\s*3\s*max\b", "Qwen"),
        (r"\bqwen3\s*max\b", "Qwen"),
        (r"\bqwen3-max\b", "Qwen"),
        (r"\bqwen\b", "Qwen"),
        (r"\bchat\s*gpt\b", "GPT"),
        (r"\bchatgpt\b", "GPT"),
        (r"\bgpt\b", "GPT"),
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


def normalize_text(s: str) -> str:
    # Normalize common arrow / dash variants.
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


def extract_shortest_paths_section(text: str) -> str:
    return slice_between(
        text,
        r"Shortest\s+path\(s\)\s*:",
        [
            r"\n\s*#{0,6}\s*Path\s+length\s*\(in\s+edges\)\s*:",
            r"\n\s*#{0,6}\s*Total\s+weight",
            r"\n\s*#{0,6}\s*Audit\s+Checklist",
        ],
    )


def extract_field_value(text: str, field_regex: str) -> str:
    """
    Extract a field value only from a section-like line, not from arbitrary
    mentions in reasoning text. This avoids grabbing phrases such as
    "compute the total weight of each path" as if they were the final
    Total weight field.
    """
    pattern = r"(?im)^\s*#{0,6}\s*" + field_regex + r"\s*:?\s*(.*)$"
    m = re.search(pattern, text)
    if not m:
        return ""
    line = m.group(1).strip()
    line = re.sub(r"^\s*[:\-]\s*", "", line)
    if line:
        return line
    # If the value is placed on the next bullet line, capture it.
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


def has_no_path(text: str) -> bool:
    low = text.lower()
    return any(re.search(pat, low) for pat in NO_PATH_PATTERNS)


def clean_path_line(line: str) -> str:
    line = normalize_text(line)
    # Remove markdown/bullets and labels.
    line = re.sub(r"^\s*#{1,6}\s*", "", line)
    line = re.sub(r"^\s*[-*•]\s*", "", line)
    line = re.sub(r"^\s*(Path\s*\d+|Shortest path|Path)\s*[:\-]\s*", "", line, flags=re.IGNORECASE)
    # Remove bold/backticks.
    line = line.replace("**", "").replace("`", "")
    return line.strip()


def extract_path_candidates(text: str) -> List[Tuple[str, ...]]:
    """
    Extract path-like sequences from text.
    Accepts A->B->C, A - B - C, A to B to C, and variants with Unicode arrows.
    """
    text = normalize_text(text)
    candidates: List[Tuple[str, ...]] = []

    # Work line by line to avoid joining independent edges in a graph spec.
    for raw_line in text.splitlines():
        line = clean_path_line(raw_line)
        if not line:
            continue
        if re.search(r"\b(no path|does not exist|disconnected|n/a)\b", line, flags=re.IGNORECASE):
            continue

        # Convert " A to B to C " to "A->B->C" only when it is path-like.
        line2 = re.sub(r"\s+\bto\b\s+", "->", line, flags=re.IGNORECASE)

        # Regex for sequences of capital node labels connected by -> or -
        # Example match: A->B->C-D
        pattern = r"\b[A-Z]\b(?:\s*(?:->|-)\s*\b[A-Z]\b)+"
        for match in re.finditer(pattern, line2):
            s = match.group(0)
            parts = re.split(r"\s*(?:->|-)\s*", s)
            parts = tuple(p.strip() for p in parts if p.strip())
            if len(parts) >= 2:
                candidates.append(parts)

    # Deduplicate while preserving order.
    seen = set()
    out: List[Tuple[str, ...]] = []
    for p in candidates:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def gold_path_present(text: str, path: Tuple[str, ...]) -> bool:
    """
    Search for a gold path in a flexible way, allowing ->, Unicode arrows,
    dashes, and 'to' separators.
    """
    text = normalize_text(text)
    pieces = []
    for node in path:
        pieces.append(re.escape(node))
    sep = r"\s*(?:->|-|\bto\b)\s*"
    pat = r"\b" + sep.join(pieces) + r"\b"
    return re.search(pat, text, flags=re.IGNORECASE) is not None


def extract_predicted_paths(text: str, problem: str) -> Tuple[str, Tuple[Tuple[str, ...], ...], str]:
    shortest = extract_shortest_paths_section(text)

    if shortest and has_no_path(shortest):
        return "NO_PATH", tuple(), "no_path_in_shortest_paths_section"

    # First parse only the Shortest path(s) section.
    paths = extract_path_candidates(shortest) if shortest else []
    if paths:
        return "PATHS", tuple(sorted(set(paths))), "paths_from_shortest_paths_section"

    # If no-path is clear anywhere and no path candidates in Shortest section, use NO_PATH.
    if has_no_path(text):
        return "NO_PATH", tuple(), "no_path_in_full_text"

    # Controlled fallback: if all gold paths are visibly present anywhere,
    # accept them but flag as fallback in parse_note.
    if problem in GOLD and GOLD[problem]["answer_type"] == "PATHS":
        gold_paths = GOLD[problem]["paths"]
        present = {p for p in gold_paths if gold_path_present(text, p)}
        if present:
            return "PATHS", tuple(sorted(present)), "gold_paths_found_in_full_text_fallback_manual_review"

    # Last fallback: parse path candidates anywhere, but mark manual review.
    all_paths = extract_path_candidates(text)
    if all_paths:
        return "PATHS", tuple(sorted(set(all_paths))), "paths_from_full_text_fallback_manual_review"

    return "UNKNOWN", tuple(), "could_not_parse_answer"


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
        r"Shortest\s+path\(s\)\s*:",
        r"Path\s+length\s*\(in\s+edges\)\s*:",
        r"Total\s+weight",
        r"Audit\s+Checklist",
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


def evaluate(problem: str, answer_type: str, paths: Tuple[Tuple[str, ...], ...], length_s: str, weight_s: str) -> Dict[str, Any]:
    if problem not in GOLD:
        return {"semantic_correct": "", "set_f1": "", "eval_note": "unknown_problem", "manual_review": 1}

    gold = GOLD[problem]
    manual_review = 0
    notes: List[str] = []

    if gold["answer_type"] == "NO_PATH":
        semantic_correct = 1 if answer_type == "NO_PATH" else 0
        set_f1 = 1.0 if semantic_correct else 0.0
        if not semantic_correct:
            notes.append("gold_no_path_but_predicted_path_or_unknown")
            manual_review = 1
        if not normalize_na(length_s):
            notes.append(f"no_path_length_not_na:{length_s}")
            manual_review = 1
        if not normalize_na(weight_s):
            notes.append(f"no_path_weight_not_na:{weight_s}")
            manual_review = 1
        return {
            "semantic_correct": semantic_correct,
            "set_f1": set_f1,
            "eval_note": "; ".join(notes) if notes else "ok",
            "manual_review": manual_review,
        }

    if answer_type != "PATHS":
        return {
            "semantic_correct": 0,
            "set_f1": 0.0,
            "eval_note": "gold_has_paths_but_predicted_no_path_or_unknown",
            "manual_review": 1,
        }

    pred_set = set(paths)
    gold_set = gold["paths"]
    intersection = pred_set & gold_set
    precision = len(intersection) / len(pred_set) if pred_set else 0.0
    recall = len(intersection) / len(gold_set) if gold_set else 0.0
    set_f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    missing = sorted(gold_set - pred_set)
    extra = sorted(pred_set - gold_set)
    semantic_correct = 1 if pred_set == gold_set else 0

    if missing:
        notes.append("missing:" + "|".join("->".join(p) for p in missing))
    if extra:
        notes.append("extra:" + "|".join("->".join(p) for p in extra))

    gold_weight = gold["weight"]
    if gold_weight is None:
        if not normalize_na(weight_s):
            notes.append(f"unweighted_weight_not_na:{weight_s}")
            manual_review = 1
    else:
        nums = parse_ints(weight_s)
        if gold_weight not in nums:
            # For Q4, some models report "weight 6 for each path" in prose
            # near the listed paths, and simple field extraction may miss it.
            # If the path set is already exactly correct and the output text
            # contains the gold weight near the answer, keep semantic correctness
            # but flag only if no 6 is found anywhere.
            if problem == "Q4" and pred_set == gold_set:
                # Keep semantically correct based on correct min-weight path set.
                # The field-level issue can be treated as format/field variability.
                notes.append(f"weight_field_parse_uncertain:{weight_s}")
                manual_review = 1
            else:
                notes.append(f"weight_missing_or_wrong:{weight_s}")
                manual_review = 1
                semantic_correct = 0

    length_nums = parse_ints(length_s)
    if length_nums:
        allowed = gold["edge_lengths"]
        if problem == "Q4":
            # Q4 has two valid tied paths with different edge counts (3 and 4).
            # Ignore Path 1 / Path 2 labels: accept if the field mentions either
            # the allowed edge counts or if the path set itself is correct.
            if pred_set == gold_set:
                pass
            elif not (set(length_nums) & allowed):
                notes.append(f"unexpected_edge_length:{length_s}")
                manual_review = 1
        else:
            if set(length_nums) != allowed:
                notes.append(f"unexpected_edge_length:{length_s}")
                manual_review = 1
    else:
        if problem == "Q4" and pred_set == gold_set:
            # Do not make missing edge-length text override a correct weighted path set.
            pass
        else:
            notes.append("missing_edge_length")
            manual_review = 1

    if missing or extra:
        manual_review = 1

    return {
        "semantic_correct": semantic_correct,
        "set_f1": round(set_f1, 4),
        "eval_note": "; ".join(notes) if notes else "ok",
        "manual_review": manual_review,
    }


def audit_folder(input_dir: Path, out_csv: Path, summary_md: Path, flagged_csv: Path) -> None:
    rows: List[Dict[str, Any]] = []
    skipped: List[str] = []

    for path in sorted(input_dir.rglob("*.txt")):
        meta = infer_metadata(path.name)
        text = read_text(path)

        if not meta["problem"] or not meta["model"] or not meta["run"]:
            skipped.append(path.name)
            continue

        answer_type, paths, parse_note = extract_predicted_paths(text, meta["problem"])
        length_s = extract_length(text)
        weight_s = extract_weight(text)
        ev = evaluate(meta["problem"], answer_type, paths, length_s, weight_s)

        row = {
            "filename": path.name,
            "model": meta["model"],
            "problem": meta["problem"],
            "run": meta["run"],
            "answer_type": answer_type,
            "normalized_paths": " | ".join("->".join(p) for p in paths) if paths else ("NO_PATH" if answer_type == "NO_PATH" else ""),
            "length_field": length_s,
            "total_weight_field": weight_s,
            "semantic_correct": ev["semantic_correct"],
            "set_F1": ev["set_f1"],
            "format_ok_approx": 1 if approximate_format_ok(text) else 0,
            "manual_review": ev["manual_review"],
            "parse_note": parse_note,
            "eval_note": ev["eval_note"],
        }
        rows.append(row)

    fieldnames = [
        "filename", "model", "problem", "run",
        "answer_type", "normalized_paths", "length_field", "total_weight_field",
        "semantic_correct", "set_F1", "format_ok_approx", "manual_review",
        "parse_note", "eval_note",
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
        or "fallback" in str(r["parse_note"])
    ]
    with flagged_csv.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(flagged)

    lines: List[str] = []
    lines.append("# Raw TXT Audit Summary\n")
    lines.append(f"- Input folder: `{input_dir}`")
    lines.append(f"- TXT outputs audited: {len(rows)}")
    lines.append(f"- Prompt-only or skipped TXT files: {len(skipped)}")
    lines.append(f"- Manual-review / incorrect flagged rows: {len(flagged)}\n")

    lines.append("## Semantic correctness by model\n")
    by_model: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in rows:
        by_model[r["model"]].append(r)
    lines.append("| Model | Correct / N | Accuracy | Format approx. |")
    lines.append("|---|---:|---:|---:|")
    for model in sorted(by_model):
        gs = by_model[model]
        n = len(gs)
        c = sum(1 for r in gs if str(r["semantic_correct"]) == "1")
        f_ok = sum(1 for r in gs if str(r["format_ok_approx"]) == "1")
        lines.append(f"| {model} | {c}/{n} | {c/n:.1%} | {f_ok/n:.1%} |")

    lines.append("\n## Semantic correctness by problem\n")
    by_q: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in rows:
        by_q[r["problem"]].append(r)
    lines.append("| Problem | Correct / N | Accuracy | Format approx. |")
    lines.append("|---|---:|---:|---:|")
    for q in sorted(by_q):
        gs = by_q[q]
        n = len(gs)
        c = sum(1 for r in gs if str(r["semantic_correct"]) == "1")
        f_ok = sum(1 for r in gs if str(r["format_ok_approx"]) == "1")
        lines.append(f"| {q} | {c}/{n} | {c/n:.1%} | {f_ok/n:.1%} |")

    lines.append("\n## Mode ratio by model/problem\n")
    lines.append("| Model | Problem | Mode ratio | Mode answer |")
    lines.append("|---|---|---:|---|")
    grouped: Dict[Tuple[str, str], List[str]] = defaultdict(list)
    for r in rows:
        grouped[(r["model"], r["problem"])].append(str(r["normalized_paths"]))
    for (model, q) in sorted(grouped):
        vals = grouped[(model, q)]
        counts = Counter(vals)
        mode, count = counts.most_common(1)[0]
        lines.append(f"| {model} | {q} | {count/len(vals):.2f} | `{mode}` |")

    if skipped:
        lines.append("\n## Skipped TXT files\n")
        for name in skipped:
            lines.append(f"- {name}")

    if flagged:
        lines.append("\n## Rows to manually review\n")
        lines.append("| Filename | semantic_correct | parse_note | eval_note |")
        lines.append("|---|---:|---|---|")
        for r in flagged:
            lines.append(
                f"| {r['filename']} | {r['semantic_correct']} | {r['parse_note']} | {r['eval_note']} |"
            )

    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit all raw TXT outputs for shortest-path pilot.")
    parser.add_argument("input_dir", help="Folder containing raw .txt outputs")
    parser.add_argument("--out", default="raw_txt_audit_results.csv", help="Output detailed CSV")
    parser.add_argument("--summary", default="raw_txt_audit_summary.md", help="Output Markdown summary")
    parser.add_argument("--flagged", default="raw_txt_flagged_for_manual_review.csv", help="Output flagged rows CSV")
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
