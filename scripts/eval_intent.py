import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from intent import INTENTS, classify_intent_hybrid


def _load_jsonl(path: Path, limit: int | None = None) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            if "text" not in item or "label" not in item:
                continue
            rows.append({"text": str(item["text"]), "label": str(item["label"])})
            if limit is not None and len(rows) >= limit:
                break
    return rows


def _safe_div(a: float, b: float) -> float:
    return a / b if b else 0.0


def _calc_metrics(labels: List[str], y_true: List[str], y_pred: List[str]) -> Dict[str, Dict[str, float]]:
    out: Dict[str, Dict[str, float]] = {}
    for label in labels:
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == label and p == label)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t != label and p == label)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == label and p != label)
        precision = _safe_div(tp, tp + fp)
        recall = _safe_div(tp, tp + fn)
        f1 = _safe_div(2 * precision * recall, precision + recall)
        out[label] = {"precision": precision, "recall": recall, "f1": f1, "support": float(sum(1 for t in y_true if t == label))}
    return out


def _confusion_matrix(labels: List[str], y_true: List[str], y_pred: List[str]) -> Dict[str, Dict[str, int]]:
    m: Dict[str, Dict[str, int]] = {t: {p: 0 for p in labels} for t in labels}
    for t, p in zip(y_true, y_pred):
        if t in m and p in m[t]:
            m[t][p] += 1
    return m


def _print_confusion(labels: List[str], matrix: Dict[str, Dict[str, int]]) -> None:
    cell_w = 8
    header = "true\\pred".ljust(14) + "".join(l[:cell_w].ljust(cell_w + 1) for l in labels)
    print(header)
    for t in labels:
        row = t.ljust(14)
        for p in labels:
            row += str(matrix[t][p]).ljust(cell_w + 1)
        print(row)


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline intent router evaluation")
    parser.add_argument("--data", type=str, default="eval/intent_eval.jsonl", help="Path to jsonl eval data")
    parser.add_argument("--limit", type=int, default=None, help="Optional max rows")
    parser.add_argument(
        "--enable-llm-fallback",
        action="store_true",
        help="Enable LLM fallback in classify_intent_hybrid",
    )
    args = parser.parse_args()

    data_path = Path(args.data)
    if not data_path.exists():
        raise FileNotFoundError(f"Eval data not found: {data_path}")

    rows = _load_jsonl(data_path, limit=args.limit)
    if not rows:
        raise ValueError("No valid evaluation samples loaded.")

    label_space = sorted(INTENTS)
    y_true: List[str] = []
    y_pred: List[str] = []
    fallback_used_count = 0

    for row in rows:
        text = row["text"]
        label = row["label"]
        pred, _idx, fallback_used = classify_intent_hybrid(
            text,
            enable_llm_fallback=args.enable_llm_fallback,
        )
        y_true.append(label)
        y_pred.append(pred if pred in INTENTS else "unknown")
        fallback_used_count += int(bool(fallback_used))

    total = len(rows)
    correct = sum(1 for t, p in zip(y_true, y_pred) if t == p)
    accuracy = _safe_div(correct, total)
    fallback_rate = _safe_div(fallback_used_count, total)

    print(f"data_path: {data_path}")
    print(f"total_samples: {total}")
    print(f"enable_llm_fallback: {args.enable_llm_fallback}")
    print(f"overall_accuracy: {accuracy:.4f}")
    print(f"fallback_rate: {fallback_rate:.4f}")
    print("")

    metrics = _calc_metrics(label_space, y_true, y_pred)
    print("per_intent_metrics")
    print("intent           precision   recall      f1          support")
    for label in label_space:
        m = metrics[label]
        print(
            f"{label:<16}"
            f"{m['precision']:<12.4f}"
            f"{m['recall']:<12.4f}"
            f"{m['f1']:<12.4f}"
            f"{int(m['support'])}"
        )

    print("")
    print("confusion_matrix")
    cm = _confusion_matrix(label_space, y_true, y_pred)
    _print_confusion(label_space, cm)


if __name__ == "__main__":
    main()

